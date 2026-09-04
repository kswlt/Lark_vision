# -*- coding: utf-8 -*-
"""
RoboMaster Team Adam 进度管理系统 —— Flask 后端入口。

生产运行（Win7）：
    python app.py
    -> waitress 监听 0.0.0.0:8080，同时提供 dist/ 静态站点与 /api/*

本地调试：
    python app.py --dev
"""
import logging
import os
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# 让 backend 目录可被顶层导入（services / config / data）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services import aggregates  # noqa: E402
from services.sources import DataStore  # noqa: E402

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


@app.get("/api/health")
def api_health():
    return jsonify(
        {
            "status": "ok",
            "version": VERSION,
            "dataSource": store.data_source,
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


INTERNAL_CAM = "http://127.0.0.1:18080"  # camera_checkin 内部流服务（跨 Session 无权限问题）


@app.get("/api/camera/frame")
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

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/camera/status")
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
def api_face_latest():
    """最近一次人脸识别结果：打卡成功 / 识别到成员 / 陌生人（供前端 UI 提示）。"""
    import json as _json

    p = os.path.join(BASE_DIR, "face_library", "last_recognition.json")
    if not os.path.exists(p):
        return jsonify({"name": None, "time": None, "status": None})
    try:
        with open(p, "r", encoding="utf-8") as f:
            return jsonify(_json.load(f))
    except Exception:
        return jsonify({"name": None, "time": None, "status": None})


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
                "message": "dist 尚未构建。请先在前端执行 npm run build，并将 frontend/dist 上传到本目录。",
            }
        ),
        200,
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


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
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
