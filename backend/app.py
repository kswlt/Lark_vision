"""
RoboMaster Team Adam 进度管理系统 —— Flask 后端入口。

生产运行（Win7）：
    python app.py
    -> waitress 监听 0.0.0.0:8080，同时提供 dist/ 静态站点与 /api/*

本地调试：
    python app.py --dev
"""
import functools
import json
import logging
import os
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_from_directory

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(BACKEND_DIR)
# 统一从 backend/.env 加载配置（README / .gitignore 均以 backend/.env 为准）
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=False)

# 让 backend 目录可被顶层导入（services / config / data）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.team_config import (  # noqa: E402
    ALLOWED_GROUPS,
    ALLOWED_ROBOTS,
    GROUP_ALIASES,
    PRIORITY_MAP,
    ROBOT_ALIASES,
    TEAM_NAME,
)
from services import aggregates  # noqa: E402
from services.sources import DataStore  # noqa: E402

# 精选文档列表：优先读真实配置 featured_docs.py（.gitignore 已忽略，不入库）；
# 开源用户 clone 后无该文件，回退到示例配置 featured_docs.example.py。
try:
    from config.featured_docs import FEATURED_DOCS  # type: ignore
except ImportError:
    from config.featured_docs_example import FEATURED_DOCS  # type: ignore

VERSION = "1.0.0"

# ---------------- logging ----------------
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

formatter = logging.Formatter(
    "%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S"
)
root = logging.getLogger()
root.setLevel(logging.INFO)
app_log = RotatingFileHandler(
    os.path.join(LOG_DIR, "app.log"), maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
app_log.setFormatter(formatter)
root.addHandler(app_log)
err_log = RotatingFileHandler(
    os.path.join(LOG_DIR, "error.log"), maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
err_log.setLevel(logging.ERROR)
err_log.setFormatter(formatter)
root.addHandler(err_log)
# 控制台输出
console = logging.StreamHandler()
console.setFormatter(formatter)
root.addHandler(console)

# ---------------- app ----------------
app = Flask(__name__, static_folder=None)
store = DataStore()

DIST_DIR = os.path.join(BASE_DIR, "dist")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")


@app.get("/api/health")
def api_health():
    h = store.health_status()
    return jsonify(
        {
            "status": h["status"],
            "version": VERSION,
            "dataSource": h["data_source"],
            "data_source": h["data_source"],
            "feishu": h["feishu"],
            "last_success_sync": h["last_success_sync"],
            "cache_age": h["cache_age"],
            "stale": h["stale"],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )


@app.get("/api/tasks")
def api_tasks():
    return jsonify(store.get_tasks())


@app.get("/api/dashboard")
def api_dashboard():
    tasks = store.get_tasks()
    return jsonify(
        {
            "counts": aggregates.compute_counts(tasks),
            "highlights": aggregates.compute_highlights(tasks),
            "timeline": aggregates.compute_timeline(tasks),
            "matrix": aggregates.compute_matrix(tasks),
            "trend": aggregates.compute_trend(tasks),
        }
    )


@app.get("/api/groups")
def api_groups():
    return jsonify(aggregates.compute_groups(store.get_tasks()))


@app.get("/api/robots")
def api_robots():
    return jsonify(aggregates.compute_robots(store.get_tasks()))


@app.get("/api/worktime/leaderboard")
def api_worktime():
    range_key = request.args.get("range", "week")
    if range_key not in ("week", "month"):
        range_key = "week"
    return jsonify(
        aggregates.compute_worktime_leaderboard(store.get_worktime_records(), range_key)
    )


@app.get("/api/worktime/unchecked")
def api_unchecked():
    from datetime import date

    return jsonify({"names": store.get_unchecked(), "date": date.today().isoformat()})


@app.get("/api/duty")
def api_duty():
    return jsonify(store.get_duty())


@app.get("/api/people")
def api_people():
    recs = store.get_worktime_records()
    wp = aggregates.compute_worktime_people(recs)
    return jsonify(aggregates.compute_people(wp, store.get_tasks()))


@app.get("/api/attendance/face-checkin")
def api_face_checkin():
    """今日已通过摄像头人脸识别打卡的成员名单。"""
    from services.face_checkin import read_today_checkin

    return jsonify(read_today_checkin())


# ---------------- 管理员认证（后台管理接口） ----------------
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "").strip()
VIEWER_TOKEN = os.environ.get("VIEWER_TOKEN", "").strip()
CAMERA_PUBLIC = os.environ.get("CAMERA_PUBLIC", "false").strip().lower() in ("1", "true", "yes")


def _extract_bearer(request) -> str:
    auth = request.headers.get("Authorization", "")
    return auth[7:] if auth.startswith("Bearer ") else ""


def require_admin(fn):
    """简单 Bearer Token 认证。未配置 ADMIN_TOKEN 时管理接口直接拒绝，防止误开放。"""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not ADMIN_TOKEN:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "管理接口未配置 ADMIN_TOKEN（请在 backend/.env 设置后重启）",
                    }
                ),
                503,
            )
        token = _extract_bearer(request)
        if not token or token != ADMIN_TOKEN:
            return jsonify({"status": "error", "message": "未授权：需要有效管理员 Token"}), 401
        return fn(*args, **kwargs)

    return wrapper


def require_viewer(fn):
    """摄像头接口鉴权：CAMERA_PUBLIC=true 时放行；否则要求 VIEWER_TOKEN 或 ADMIN_TOKEN。

    兼容 <img src="/api/camera/stream?token=xxx"> 的 MJPEG 流式场景，
    同时支持 Authorization: Bearer xxx 头。
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if CAMERA_PUBLIC:
            return fn(*args, **kwargs)
        token = _extract_bearer(request) or (request.args.get("token") or "").strip()
        if not token:
            return jsonify({"status": "error", "message": "摄像头接口未公开：需要 token"}), 401
        if VIEWER_TOKEN and token == VIEWER_TOKEN:
            return fn(*args, **kwargs)
        if ADMIN_TOKEN and token == ADMIN_TOKEN:
            return fn(*args, **kwargs)
        return jsonify({"status": "error", "message": "未授权：无效 token"}), 403

    return wrapper


@app.post("/api/admin/checkin/sync")
@require_admin
def api_checkin_sync():
    """手动触发：把希沃人脸打卡记录同步到飞书「打卡记录」表（幂等）。"""
    from services.feishu.sync_checkin import sync_checkin_to_feishu

    if not store.client:
        return jsonify({"status": "error", "message": "飞书未配置"}), 503
    try:
        r = sync_checkin_to_feishu(store.client, store.app_token)
        return jsonify({"status": "ok", **r})
    except Exception as e:
        app.logger.warning("checkin sync API error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@app.post("/api/admin/attendance/sync")
@require_admin
def api_attendance_sync():
    """手动触发：把飞书考勤工时数据同步到电子表格（幂等）。"""
    from services.feishu.sync_attendance import sync_attendance_to_sheets

    if not store.client:
        return jsonify({"status": "error", "message": "飞书未配置"}), 503
    try:
        r = sync_attendance_to_sheets(store.client, days=30)
        return jsonify({"status": "ok", **r})
    except Exception as e:
        app.logger.warning("attendance sync API error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


INTERNAL_CAM = os.environ.get(
    "CAMERA_INTERNAL_URL", "http://127.0.0.1:18080"
)  # camera_checkin 内部流服务（跨 Session 无权限问题）


@app.get("/api/camera/frame")
@require_viewer
def api_camera_frame():
    """兼容接口：代理内部流服务的单帧 JPEG（实时链路已改 /api/camera/stream）。"""
    import urllib.request
    try:
        req = urllib.request.Request(INTERNAL_CAM + "/frame", headers={"User-Agent": "RM/1.0"})
        data = urllib.request.urlopen(req, timeout=3).read()
        if not data:
            return jsonify({"status": "offline", "message": "camera frame not ready"}), 200
        from flask import Response

        return Response(data, mimetype="image/jpeg",
                        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                                 "Pragma": "no-cache"})
    except Exception:
        return jsonify({"status": "offline", "message": "camera frame not ready"}), 200


@app.get("/api/camera/stream")
@require_viewer
def api_camera_stream():
    """MJPEG 实时视频流：代理内部流服务（camera_checkin 进程内存缓存，非磁盘轮询）。"""
    import urllib.request

    from flask import Response

    def generate():
        resp = None
        try:
            req = urllib.request.Request(INTERNAL_CAM + "/stream", headers={"User-Agent": "RM/1.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                yield chunk
        except Exception:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                   b"\xff\xd8\xff\xdb\x00\x84\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xd9"
                   b"\r\n")  # 极小占位 JPEG，避免 <img> 报错
        finally:
            if resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame",
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                             "Pragma": "no-cache"})


@app.get("/api/camera/status")
@require_viewer
def api_camera_status():
    """相机服务状态 + FPS 统计（来自内部流服务指标）。"""
    import urllib.request
    from datetime import datetime

    info = {
        "status": "offline", "connected": False, "frameTime": None,
        "capture_fps": 0.0, "preview_fps": 0.0, "recognition_fps": 0.0,
        "frame_age_ms": None, "camera": {},
    }
    try:
        req = urllib.request.Request(INTERNAL_CAM + "/status", headers={"User-Agent": "RM/1.0"})
        raw = urllib.request.urlopen(req, timeout=3).read().decode("utf-8", "ignore")
        import json as _json

        d = _json.loads(raw)
        info["connected"] = bool(d.get("connected"))
        info["capture_fps"] = d.get("capture_fps", 0.0)
        info["preview_fps"] = d.get("preview_fps", 0.0)
        info["recognition_fps"] = d.get("recognition_fps", 0.0)
        ts = d.get("ts", 0)
        if ts:
            info["frameTime"] = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            info["frame_age_ms"] = int((time.time() - ts) * 1000)
        info["status"] = "online" if d.get("connected") else "offline"
    except Exception:
        pass
    return jsonify(info)


@app.get("/api/attendance/face-latest")
@require_viewer
def api_face_latest():
    """最近一次人脸识别结果：打卡成功 / 识别到成员 / 陌生人（供前端 UI 提示）。"""
    import json as _json

    # 路径与摄像头模块一致：FACE_LIBRARY_DIR（默认 ~/.lark_vision/face_library）
    face_lib = os.environ.get(
        "FACE_LIBRARY_DIR", os.path.join(os.path.expanduser("~"), ".lark_vision", "face_library")
    )
    p = os.path.join(face_lib, "last_recognition.json")
    if not os.path.exists(p):
        return jsonify({"name": None, "time": None, "status": None})
    try:
        with open(p, encoding="utf-8") as f:
            return jsonify(_json.load(f))
    except Exception:
        return jsonify({"name": None, "time": None, "status": None})


# ---------------- 飞书云文档（只读） ----------------
@app.get("/api/docs/list")
def api_docs_list():
    """获取展示文档列表（只读，仅白名单）。

    安全：只返回 config/featured_docs.py 中显式配置的精选文档。
    不根据任意 folder_token 枚举应用可访问的其他文档，避免越权暴露。
    """
    return jsonify({"files": FEATURED_DOCS or [], "source": "featured"})


@app.get("/api/docs/content")
def api_docs_content():
    """获取飞书文档内容（只读）。优先读本地备份，本地没有再调飞书API。

    安全：只允许 FEATURED_DOCS 白名单内的 doc_id，避免任意 doc_id 越权读取。
    """
    doc_id = request.args.get("doc_id", "")
    doc_type = request.args.get("type", "docx")
    if not doc_id:
        return jsonify({"content": "", "error": "缺少 doc_id"}), 400

    # 白名单校验：doc_id 必须在 FEATURED_DOCS 中。
    # 白名单为空 = 一个文档都不允许读取（绝不放行任意 doc_id 越权）。
    whitelist_tokens = {d.get("token", "") for d in (FEATURED_DOCS or [])}
    if doc_id not in whitelist_tokens:
        return jsonify({"content": "", "error": "doc_id 不在白名单内"}), 403

    # 优先读本地备份（解决飞书权限不足的问题）
    local_backup = os.path.join(os.path.dirname(__file__), "config", "all_docs_content.json")
    if os.path.exists(local_backup):
        try:
            with open(local_backup, encoding="utf-8") as f:
                backup = json.load(f)
            if doc_id in backup and backup[doc_id].get("content"):
                return jsonify({
                    "content": backup[doc_id]["content"],
                    "type": doc_type,
                    "source": "local_backup"
                })
        except Exception as e:
            app.logger.warning("读取本地文档备份失败: %s", e)

    # 本地没有，调用飞书API
    if not store.feishu_configured or not store.client:
        return jsonify({"content": "", "error": "飞书未配置且本地无备份"}), 503
    try:
        if doc_type == "docx":
            data = store.client.get(f"/docx/v1/documents/{doc_id}/raw_content")
            content = data.get("content", "")
            return jsonify({"content": content, "type": "docx", "source": "feishu_api"})
        elif doc_type == "doc":
            data = store.client.get(f"/doc/v2/{doc_id}/content")
            content = data.get("content", "")
            return jsonify({"content": content, "type": "doc", "source": "feishu_api"})
        else:
            return jsonify({"content": "", "error": f"不支持的文档类型: {doc_type}"}), 400
    except Exception as e:
        app.logger.exception("获取飞书文档内容失败 doc_id=%s", doc_id)
        return jsonify({"content": "", "error": str(e)}), 502


@app.get("/api/meta")
def api_meta():
    """统一队伍配置（供前端读取组别/兵种/别名/优先级）。

    其他 RoboMaster 队伍 fork 后只需修改 backend/config/team.yaml，
    前端通过本接口获取配置，无需修改 TypeScript 源码。
    """
    # code -> 第一个中文名（PRIORITY_MAP 的 value 是英文 key 方向）
    reverse = {}
    for zh, code in PRIORITY_MAP.items():
        reverse.setdefault(code, zh)
    return jsonify({
        "teamName": TEAM_NAME,
        "groups": list(ALLOWED_GROUPS),
        "robots": list(ALLOWED_ROBOTS),
        "groupAliases": GROUP_ALIASES,
        "robotAliases": ROBOT_ALIASES,
        "priorityLabels": reverse,
    })


# ---------------- 静态站点（React dist） ----------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def static_files(path):
    if path.startswith("api/"):
        abort(404)
    if path and os.path.isfile(os.path.join(DIST_DIR, path)):
        resp = send_from_directory(DIST_DIR, path)
        # 带 hash 的 assets 可长缓存；其余页面入口不缓存，确保发布后立即生效
        if not path.startswith("assets/"):
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            resp.headers["Pragma"] = "no-cache"
        return resp
    # 支持 public 目录下的静态文件（如宣传片视频）
    if path and os.path.isfile(os.path.join(PUBLIC_DIR, path)):
        resp = send_from_directory(PUBLIC_DIR, path)
        # 视频文件允许浏览器缓存
        if path.startswith("promo_videos/"):
            resp.headers["Cache-Control"] = "public, max-age=86400"
        else:
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            resp.headers["Pragma"] = "no-cache"
        return resp
    index = os.path.join(DIST_DIR, "index.html")
    if os.path.isfile(index):
        resp = send_from_directory(DIST_DIR, "index.html")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        return resp
    return (
        jsonify(
            {
                "status": "error",
                "message": "dist 尚未构建。请先在前端执行 npm run build（产物输出到仓库根 dist/）。",
            }
        ),
        503,
    )


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"status": "error", "message": "not found"}), 404
    return e


@app.errorhandler(Exception)
def handle_error(e):
    if not request.path.startswith("/api/"):
        app.logger.error("页面请求异常: %s", e, exc_info=True)
        abort(500)
    app.logger.error("API 异常 %s: %s", request.path, e, exc_info=True)
    return jsonify({"status": "error", "message": "internal error"}), 500


def _checkin_sync_loop():
    """后台定时：每天 22:00 把希沃人脸打卡同步到飞书（幂等）。启动后首个整点也会补一次。"""
    from services.feishu.sync_checkin import sync_checkin_to_feishu

    if not store.client:
        app.logger.info("checkin sync: 飞书未配置，定时同步停用")
        return
    synced_today = False
    while True:
        try:
            now = datetime.now()
            # 每天 22:00 后同步一次；非 22 点窗口重置标记（允许第二天再同步）
            if now.hour >= 22 and not synced_today:
                try:
                    r = sync_checkin_to_feishu(store.client, store.app_token)
                    app.logger.info("checkin sync scheduled: %s", r)
                except Exception as e:
                    app.logger.warning("checkin sync scheduled error: %s", e)
                synced_today = True
            if now.hour < 22:
                synced_today = False
        except Exception:
            pass
        time.sleep(300)


def _attendance_sync_loop():
    """后台定时：每天 22:30 把飞书考勤工时同步到电子表格（幂等）。"""
    from services.feishu.sync_attendance import sync_attendance_to_sheets

    if not store.client:
        app.logger.info("attendance sync: 飞书未配置，定时同步停用")
        return
    synced_today = False
    while True:
        try:
            now = datetime.now()
            if now.hour >= 22 and now.minute >= 30 and not synced_today:
                try:
                    r = sync_attendance_to_sheets(store.client, days=30)
                    app.logger.info("attendance sync scheduled: %s", r)
                except Exception as e:
                    app.logger.warning("attendance sync scheduled error: %s", e)
                synced_today = True
            if now.hour < 22:
                synced_today = False
        except Exception:
            pass
        time.sleep(300)


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    # 后台定时：人脸打卡每日同步飞书（幂等；写权限未开通只记日志不影响主服务）
    if os.environ.get("FEISHU_CHECKIN_SYNC_ENABLED", "1") == "1":
        import threading

        threading.Thread(target=_checkin_sync_loop, daemon=True).start()
        app.logger.info("checkin 每日同步飞书定时任务已启动（每天 22:00）")
    # 后台定时：飞书考勤工时每日同步到电子表格（幂等）
    if os.environ.get("FEISHU_ATTENDANCE_SYNC_ENABLED", "1") == "1":
        import threading

        threading.Thread(target=_attendance_sync_loop, daemon=True).start()
        app.logger.info("attendance 每日同步电子表格定时任务已启动（每天 22:30）")
    if "--dev" in sys.argv:
        app.logger.info("开发模式 Flask dev server: http://localhost:%s", port)
        app.run(host=host, port=port, debug=True, threaded=True)
        return
    from waitress import serve

    app.logger.info(
        "RoboMaster Dashboard v%s 启动: dataSource=%s, dist=%s",
        VERSION,
        store.data_source,
        DIST_DIR,
    )
    app.logger.info("Waitress 监听 %s:%s", host, port)
    serve(app, host=host, port=port, threads=12)


if __name__ == "__main__":
    main()
