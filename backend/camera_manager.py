# -*- coding: utf-8 -*-
"""
CameraManager：华睿大华工业相机多线程管理（采集 / 预览 / 识别 解耦）。
架构：
    Harvester(仅采集线程持有)
         │  fetch_buffer (相机自由运行，目标 30FPS)
         ▼
    [Camera Capture Thread] ── latest_frame (内存缓存, 锁保护) ──┐
         │                                                       │
         ├──────────────► [Preview Encoder Thread] ── latest_jpeg ──► mmap ──► Flask MJPEG ──► Browser
         │                   20FPS / 640px / 旋转90°                  (命名共享内存, 不写盘)
         └──────────────► [Recognition Thread] ── YuNet(640) ──► SFace深度特征 ──► Gallery匹配 ──► 多帧确认 ──► 打卡/捕获
                            1-3FPS / 身份缓存 / 低频识别
依赖：
    harvesters / genicam / cv2 / numpy（希沃 Python3.8 已装）
用法：
    from camera_manager import CameraManager
    CameraManager().run()   # 阻塞运行，Ctrl+C 优雅退出
"""
import os
import sys
import time
import json
import re
import glob
import logging
import threading
import collections
import datetime
import http.server
import socketserver

os.environ["PATH"] = r"C:\Program Files\HuarayTech\MV Viewer\Runtime\x64;" + os.environ.get("PATH", "")

import numpy as np
import cv2

# ---------------- 配置（集中管理） ----------------
CAMERA_TARGET_FPS = 30        # 相机目标帧率（硬件支持时尝试设置）
PREVIEW_FPS = 30              # 预览编码目标帧率
PREVIEW_WIDTH = 416           # 预览宽度(双核极限平衡画质与流畅)
PREVIEW_JPEG_QUALITY = 64     # 预览 JPEG 质量
RECOGNITION_FPS = 2           # 识别目标帧率(SFace比LBPH快，2fps足够打卡且给preview让算力)
DETECTION_MAX_WIDTH = 416     # YuNet 检测最大宽度（SFace依赖5点landmark，320太低影响小脸对齐质量）

FACE_SIZE = 112
CONF_THRESHOLD = 100          # LBPH confidence（fallback 用）
MIN_DETECT_SCORE = 0.5
SAME_PERSON_COOLDOWN = 300    # 秒，同人重复打卡冷却
CAPTURE_COOLDOWN = 8          # 秒，同人捕获冷却
PREVIEW_JPEG_MMAP = ""  # 已弃用
INTERNAL_HTTP_PORT = 18080  # 内部流服务端口
MMAP_SIZE = 1 * 1024 * 1024   # 保留常量
LAST_RECOG_INTERVAL = 1.5     # 秒，识别结果写入冷却

# SFace 深度人脸识别配置
SFACE_COSINE_THRESHOLD = 0.45   # SFace cosine 相似度阈值（现场统计：0.45时异人误识别率0.49%）
SFACE_L2_THRESHOLD = 1.128      # SFace L2 距离阈值（官方推荐，越小越像）
SFACE_MATCH_MARGIN = 0.05       # best-second 最小间隔，防止"勉强最像"误识别
MULTI_FRAME_CONFIRM = 3         # 多帧确认帧数（连续N帧识别同一人才确认）
IDENTITY_CACHE_TTL = 3          # 身份缓存 TTL（秒），同一人脸特征缓存结果避免重复计算（调试期降低以观察实时识别）
GALLERY_REBUILD_INTERVAL = 3600  # Gallery 重建间隔（秒），检测到新照片自动重建

BASE = r"C:\RoboMasterDashboard"
LIB = os.path.join(BASE, "face_library")
CTI = r"C:\Program Files\HuarayTech\MV Viewer\Runtime\x64\MVProducerU3V.cti"
YUNET = os.path.join(LIB, "models", "face_detection_yunet.onnx")
SFACE_MODEL = os.path.join(LIB, "models", "face_recognition_sface_2021dec.onnx")
MODEL = os.path.join(LIB, "face_model.yml")
NAMES = os.path.join(LIB, "face_names.txt")
PHOTO_DIR = os.path.join(LIB, "photos")
GALLERY_FILE = os.path.join(LIB, "face_gallery.npz")
DATA_DIR = os.path.join(BASE, "data")
LOG_DIR = os.path.join(BASE, "logs")
LAST_RECOG = os.path.join(LIB, "last_recognition.json")
FRAME_LIVE = os.path.join(LIB, "frame_live.jpg")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "face_checkin.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("face_checkin")


# ---------------- FPS 滑动统计 ----------------
class FPSCounter:
    """最近 window 秒内的滑动 FPS 统计。"""

    def __init__(self, window=2.0):
        self.window = window
        self.ts = collections.deque()
        self.lock = threading.Lock()

    def tick(self):
        now = time.time()
        with self.lock:
            self.ts.append(now)
            while self.ts and now - self.ts[0] > self.window:
                self.ts.popleft()

    def fps(self):
        with self.lock:
            n = len(self.ts)
            if n < 2:
                return 0.0
            span = self.ts[-1] - self.ts[0]
            return round(n / span, 1) if span > 0 else 0.0


# ---------------- 中文标签渲染（cv2.putText 不支持中文，用 PIL） ----------------
_FONT = None


def _get_font(size=18):
    global _FONT
    if _FONT is None:
        try:
            from PIL import ImageFont
            for f in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
                      r"C:\Windows\Fonts\simsun.ttc"]:
                if os.path.exists(f):
                    _FONT = ImageFont.truetype(f, size)
                    break
            if _FONT is None:
                _FONT = ImageFont.load_default()
        except Exception:
            _FONT = "fallback"
    return _FONT if isinstance(_FONT, object) and _FONT != "fallback" else None


def _draw_cn_labels(preview, labels):
    """用 PIL 在 BGR numpy 帧上画中文姓名标签。labels: [(x, y, h, text, color_bgr)]。"""
    try:
        from PIL import Image, ImageDraw
        font = _get_font()
        if font is None:
            return False
        hh, ww = preview.shape[:2]
        for (x, y, h, text, color) in labels:
            try:
                bbox = font.getbbox(text)
                tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
                ty = y - th - 8 if y - th - 8 > 0 else y + h + 4
                pad = 4
                x0, y0 = x, ty
                x1, y1 = x + tw + 2 * pad, ty + th + 2 * pad
                if x0 < 0 or y0 < 0 or x1 > ww or y1 > hh:
                    continue
                roi = preview[y0:y1, x0:x1].copy()
                pil = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
                d = ImageDraw.Draw(pil)
                d.rectangle([0, 0, x1 - x0 - 1, y1 - y0 - 1],
                            fill=(int(color[2]), int(color[1]), int(color[0])))
                d.text((pad, pad), text, font=font, fill=(255, 255, 255))
                roi[:] = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
                preview[y0:y1, x0:x1] = roi
            except Exception:
                continue
        return True
    except Exception:
        return False


# ---------------- 线程优先级辅助 ----------------
import ctypes as _ct
def _set_thread_prio(prio):
    try:
        _ct.windll.kernel32.SetThreadPriority(_ct.windll.kernel32.GetCurrentThread(), prio)
    except Exception:
        pass
PRIO_ABOVE = 1
PRIO_NORMAL = 0
PRIO_BELOW = -1
def _set_thread_affinity(mask):
    try:
        _ct.windll.kernel32.SetThreadAffinityMask(_ct.windll.kernel32.GetCurrentThread(), mask)
    except Exception:
        pass

# ---------------- 内部流状态 + HTTP 服务 ----------------
_STATE_LOCK = threading.Lock()
_STATE = {"seq": 0, "jpeg": b"", "ts": 0.0,
          "capture_fps": 0.0, "preview_fps": 0.0, "recognition_fps": 0.0,
          "connected": False}


class _CamHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path == "/stream":
                self._stream()
            elif path == "/status":
                self._status()
            elif path == "/frame":
                self._frame()
            else:
                self.send_error(404)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        last_seq = -1
        while True:
            with _STATE_LOCK:
                seq = _STATE["seq"]
                jpeg = _STATE["jpeg"]
            if jpeg and seq != last_seq:
                last_seq = seq
                try:
                    self.wfile.write(b"--frame\r\n"
                                     b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
                    self.wfile.flush()
                except Exception:
                    return
            else:
                time.sleep(0.02)

    def _status(self):
        with _STATE_LOCK:
            payload = json.dumps({
                "connected": _STATE["connected"],
                "capture_fps": _STATE["capture_fps"],
                "preview_fps": _STATE["preview_fps"],
                "recognition_fps": _STATE["recognition_fps"],
                "ts": _STATE["ts"],
                "frameTime": datetime.datetime.fromtimestamp(_STATE["ts"]).strftime("%H:%M:%S")
                if _STATE["ts"] else None,
            }, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _frame(self):
        with _STATE_LOCK:
            jpeg = _STATE["jpeg"]
        if not jpeg:
            self.send_response(204)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(jpeg)

    def log_message(self, *a):
        pass


def _publish(jpeg, ts, c_fps, p_fps, r_fps, connected):
    with _STATE_LOCK:
        _STATE["seq"] += 1
        _STATE["jpeg"] = jpeg
        _STATE["ts"] = ts
        _STATE["capture_fps"] = c_fps
        _STATE["preview_fps"] = p_fps
        _STATE["recognition_fps"] = r_fps
        _STATE["connected"] = connected


_internal_http = None


def _start_internal_http():
    global _internal_http
    try:
        httpd = socketserver.ThreadingTCPServer(("127.0.0.1", INTERNAL_HTTP_PORT), _CamHandler)
        httpd.daemon_threads = True
        t = threading.Thread(target=httpd.serve_forever, name="internal-http", daemon=True)
        t.start()
        _internal_http = httpd
        log.info("内部流服务已启动: http://127.0.0.1:%d", INTERNAL_HTTP_PORT)
    except Exception as e:
        log.warning("内部流服务启动失败(不影响采集/识别): %s", e)


# ---------------- SFace 深度人脸 Gallery 向量库 ----------------
class FaceGallery:
    """SFace 深度特征向量库：每人一个或多个 128 维特征向量。
    支持从 photos/ 目录构建，缓存到 .npz 文件，自动检测新照片重建。"""

    def __init__(self):
        self.names = []           # 人名列表
        self.vectors = []         # 对应特征向量列表（每人可能多个）
        self.name_to_idx = {}     # 人名 -> vectors 中的起始索引
        self._lock = threading.Lock()
        self._last_mtime = 0.0
        self._last_rebuild = 0.0

    def _photo_mtime(self):
        """获取 photos 目录最新修改时间（用于检测新照片）。"""
        try:
            if not os.path.isdir(PHOTO_DIR):
                return 0.0
            latest = 0.0
            for f in glob.glob(os.path.join(PHOTO_DIR, "*.jpg")) + glob.glob(os.path.join(PHOTO_DIR, "*.png")):
                try:
                    m = os.path.getmtime(f)
                    if m > latest:
                        latest = m
                except Exception:
                    pass
            return latest
        except Exception:
            return 0.0

    def _person_of(self, filename):
        """从文件名提取人名：姓名.jpg / 姓名_1.jpg / 姓名-2.jpg -> 姓名。"""
        base = os.path.splitext(os.path.basename(filename))[0]
        m = re.match(r'^(.*?)[_\-\s]?(\d+)$', base)
        return m.group(1) if m else base

    def build(self, sface, detector, force=False):
        """从 photos/ 目录构建 Gallery。force=True 强制重建。"""
        with self._lock:
            now = time.time()
            mtime = self._photo_mtime()
            # 检查是否需要重建
            if not force and self.vectors and (now - self._last_rebuild < GALLERY_REBUILD_INTERVAL) and mtime <= self._last_mtime:
                return len(self.names)
            # 尝试从缓存加载
            if not force and os.path.exists(GALLERY_FILE) and os.path.getmtime(GALLERY_FILE) >= mtime:
                try:
                    data = np.load(GALLERY_FILE, allow_pickle=True)
                    self.names = list(data["names"])
                    # 强制转换为 float32（旧缓存可能是 object 类型，会导致 sface.match 报错）
                    self.vectors = [np.ascontiguousarray(v, dtype=np.float32).flatten() for v in data["vectors"]]
                    self.name_to_idx = {}
                    for i, n in enumerate(self.names):
                        if n not in self.name_to_idx:
                            self.name_to_idx[n] = i
                    self._last_mtime = mtime
                    self._last_rebuild = now
                    log.info("Gallery 从缓存加载: %d 人, %d 特征", len(set(self.names)), len(self.vectors))
                    return len(set(self.names))
                except Exception as e:
                    log.warning("Gallery 缓存加载失败，重新构建: %s", e)

            # 从 photos 目录构建
            files = sorted(glob.glob(os.path.join(PHOTO_DIR, "*.jpg")) +
                           glob.glob(os.path.join(PHOTO_DIR, "*.png")))
            if not files:
                log.warning("photos 目录无照片，Gallery 为空")
                return 0

            name_list = []
            for f in files:
                p = self._person_of(f)
                if p not in name_list:
                    name_list.append(p)

            vectors = []
            names = []
            no_face = []
            for f in files:
                name = self._person_of(f)
                try:
                    img = cv2.imdecode(np.fromfile(f, dtype=np.uint8), cv2.IMREAD_COLOR)
                except Exception:
                    continue
                if img is None:
                    continue
                h, w = img.shape[:2]
                if max(h, w) > 1400:
                    s = 1400.0 / max(h, w)
                    img = cv2.resize(img, (int(w * s), int(h * s)))
                detector.setInputSize((img.shape[1], img.shape[0]))
                ret, faces = detector.detect(img)
                if faces is None or len(faces) == 0:
                    no_face.append(os.path.basename(f))
                    continue
                # 取最大的脸
                face_raw = max(faces, key=lambda r: r[2] * r[3])
                try:
                    aligned = sface.alignCrop(img, face_raw)
                    feat = sface.feature(aligned)
                    vectors.append(feat.flatten())
                    names.append(name)
                except Exception as e:
                    log.warning("提取特征失败 %s: %s", os.path.basename(f), e)
                    continue

            self.names = names
            self.vectors = vectors
            self.name_to_idx = {}
            for i, n in enumerate(names):
                if n not in self.name_to_idx:
                    self.name_to_idx[n] = i
            self._last_mtime = mtime
            self._last_rebuild = now

            # 保存缓存（vectors 必须是 float32，否则 sface.match 报 object type 错误）
            try:
                np.savez(GALLERY_FILE,
                         names=np.array(names, dtype=object),
                         vectors=np.array(vectors, dtype=np.float32))
            except Exception as e:
                log.warning("Gallery 缓存保存失败: %s", e)

            if no_face:
                log.warning("以下照片未检测到人脸(已跳过): %s", ", ".join(no_face[:10]))
            log.info("Gallery 构建完成: %d 人, %d 特征向量", len(set(names)), len(vectors))
            return len(set(names))

    def match(self, feat, sface):
        """匹配特征向量，返回 (best_name, best_score, recognized, top5_list)。
        使用 cosine 相似度，必须同时满足：
          1. best_score >= SFACE_COSINE_THRESHOLD
          2. best_score - second_score >= SFACE_MATCH_MARGIN
        否则返回 recognized=False（宁可拒识，不要把A认成B）。
        top5_list = [(name, score), ...] 按 score 降序。"""
        with self._lock:
            if not self.vectors:
                return None, 0.0, False, []
            # 对每个人取最大相似度
            person_scores = {}
            match_errors = 0
            feat_f32 = np.ascontiguousarray(feat, dtype=np.float32).reshape(1, -1)
            for i, v in enumerate(self.vectors):
                try:
                    v_f32 = np.ascontiguousarray(v, dtype=np.float32).reshape(1, -1)
                    score = float(sface.match(feat_f32, v_f32, cv2.FaceRecognizerSF_FR_COSINE))
                except Exception as _e:
                    match_errors += 1
                    if match_errors <= 3:
                        log.warning("sface.match error i=%d: %s | feat_shape=%s vec_shape=%s",
                                    i, _e, getattr(feat, 'shape', None), getattr(v, 'shape', None))
                    continue
                name = self.names[i]
                if name not in person_scores or score > person_scores[name]:
                    person_scores[name] = score
            if not person_scores:
                log.warning("gallery.match: all %d vectors failed, feat_shape=%s",
                            len(self.vectors), getattr(feat, 'shape', None))
                return None, 0.0, False, []
            # Top-5 排序
            sorted_persons = sorted(person_scores.items(), key=lambda x: x[1], reverse=True)
            top5 = [(n, round(s, 3)) for n, s in sorted_persons[:5]]
            best_name, best_score = sorted_persons[0]
            second_score = sorted_persons[1][1] if len(sorted_persons) > 1 else 0.0
            margin = best_score - second_score
            # 双重条件：阈值 + margin
            recognized = (best_name is not None
                          and best_score >= SFACE_COSINE_THRESHOLD
                          and margin >= SFACE_MATCH_MARGIN)
            return best_name, round(best_score, 3), recognized, top5


# ---------------- 多帧确认器 ----------------
class MultiFrameConfirmer:
    """多帧确认：同一个人脸位置连续 N 帧识别为同一人才确认身份。
    用 bbox 中心位置作为临时 face_id。"""

    def __init__(self, n=MULTI_FRAME_CONFIRM):
        self.n = n
        self.history = {}  # {face_id: [name, name, ...]}
        self.confirmed = {}  # {face_id: (name, score)}
        self._last_clean = 0.0

    def _clean(self):
        """清理超过 5 秒未更新的 face_id。"""
        now = time.time()
        if now - self._last_clean < 2.0:
            return
        self._last_clean = now
        expired = [fid for fid, (_, ts) in self.confirmed.items() if now - ts > 5.0]
        for fid in expired:
            self.confirmed.pop(fid, None)
            self.history.pop(fid, None)

    def confirm(self, face_id, name, score):
        """添加一帧识别结果，返回 (confirmed_name, confirmed_score, is_new_confirm)。
        如果未确认，返回 (None, 0, False)。"""
        self._clean()
        if face_id not in self.history:
            self.history[face_id] = []
        self.history[face_id].append(name)
        if len(self.history[face_id]) > self.n:
            self.history[face_id].pop(0)
        # 检查最近 N 帧是否全部为同一人
        recent = self.history[face_id][-self.n:]
        if len(recent) >= self.n and all(n == recent[0] for n in recent) and recent[0] is not None:
            confirmed_name = recent[0]
            # 检查是否是新确认
            is_new = face_id not in self.confirmed or self.confirmed[face_id][0] != confirmed_name
            self.confirmed[face_id] = (confirmed_name, time.time())
            return confirmed_name, score, is_new
        return None, 0.0, False


# ---------------- 身份缓存（基于人脸位置） ----------------
class IdentityCache:
    """身份缓存：同一位置的人脸在 TTL 内直接返回缓存结果，避免重复 SFace 计算。
    用 bbox 中心位置和大小作为 key。"""

    def __init__(self, ttl=IDENTITY_CACHE_TTL):
        self.ttl = ttl
        self.cache = {}  # {key: (name, score, recognized, timestamp)}

    def _make_key(self, box):
        x, y, w, h = [int(v) for v in box[:4]]
        cx, cy = x + w // 2, y + h // 2
        # 位置量化到 20px 网格，大小量化到 10px
        return (cx // 20, cy // 20, w // 10, h // 10)

    def get(self, box):
        key = self._make_key(box)
        if key in self.cache:
            name, score, recognized, ts = self.cache[key]
            if time.time() - ts < self.ttl:
                return name, score, recognized
            else:
                del self.cache[key]
        return None

    def set(self, box, name, score, recognized):
        key = self._make_key(box)
        self.cache[key] = (name, score, recognized, time.time())
        # 清理过期缓存
        now = time.time()
        expired = [k for k, (_, _, _, ts) in self.cache.items() if now - ts > self.ttl * 2]
        for k in expired:
            del self.cache[k]


# ---------------- 人脸库 / 打卡 / 捕获 ----------------
def load_recognizer():
    """加载 LBPH 识别器（fallback）。"""
    try:
        if not os.path.exists(MODEL) or not os.path.exists(NAMES):
            return None, []
        rec = cv2.face.LBPHFaceRecognizer_create()
        rec.read(MODEL)
        with open(NAMES, "r", encoding="utf-8") as f:
            names = [x.strip() for x in f.read().splitlines() if x.strip()]
        return rec, names
    except Exception as e:
        log.error("load LBPH recognizer failed: %s", e)
        return None, []


def load_sface():
    """加载 SFace 深度人脸识别器。失败返回 None。"""
    try:
        if not os.path.exists(SFACE_MODEL):
            log.warning("SFace 模型不存在: %s", SFACE_MODEL)
            return None
        sface = cv2.FaceRecognizerSF_create(SFACE_MODEL, "")
        log.info("SFace 深度人脸识别器加载成功")
        return sface
    except Exception as e:
        log.error("SFace 加载失败(将回退 LBPH): %s", e)
        return None


def read_checkin():
    today = datetime.date.today().strftime("%Y%m%d")
    path = os.path.join(DATA_DIR, "face_checkin_%s.json" % today)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("names", [])), path
    except Exception:
        return set(), path


def write_checkin(names, path):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"date": datetime.date.today().strftime("%Y-%m-%d"), "names": sorted(names)},
                      f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error("write checkin failed: %s", e)


def detect_faces(img, detector):
    """仅检测人脸，返回 YuNet 原始输出列表（含关键点，供 SFace alignCrop 使用）。"""
    h, w = img.shape[:2]
    scale = min(1.0, float(DETECTION_MAX_WIDTH) / float(max(w, 1)))
    dw = max(1, int(w * scale)); dh = max(1, int(h * scale))
    if scale < 1.0:
        detect_img = cv2.resize(img, (dw, dh))
    else:
        detect_img = img
    detector.setInputSize((dw, dh))
    ret, faces = detector.detect(detect_img)
    if faces is None:
        return [], 1.0
    # 映射回原始帧坐标
    inv = 1.0 / scale
    result = []
    for f in faces:
        if f[14] < MIN_DETECT_SCORE:
            continue
        f2 = f.copy()
        f2[0] *= inv; f2[1] *= inv; f2[2] *= inv; f2[3] *= inv
        # 关键点也映射
        for i in range(4, 14):
            f2[i] *= inv
        result.append(f2)
    return result, inv


def detect_and_recognize_sface(img, detector, sface, gallery, id_cache, confirmer):
    """SFace 深度识别主流程：检测 -> 对齐 -> 特征 -> Gallery匹配 -> 身份缓存 -> 多帧确认。
    返回 [(name, score, box_orig, recognized)]，box 为 (x, y, w, h)。"""
    results = []
    faces, _ = detect_faces(img, detector)
    if not faces:
        return results
    for f in faces:
        x, y, w, h = [int(v) for v in f[:4]]
        box = (x, y, w, h)
        # 1. 身份缓存命中
        cached = id_cache.get(box)
        if cached is not None:
            name, score, recognized = cached
            results.append((name if recognized else "不在数据库中", score, box, recognized))
            continue
        # 2. SFace 对齐 + 特征提取
        try:
            aligned = sface.alignCrop(img, f)
            feat = sface.feature(aligned)
        except Exception as e:
            log.warning("SFace feature failed: %s", e)
            results.append(("不在数据库中", 0.0, box, False))
            continue
        # 3. Gallery 匹配（双重条件：threshold + margin）
        name, score, recognized, top5 = gallery.match(feat, sface)
        # 4. 多帧确认（仅对识别为成员的人脸）
        if recognized and name:
            face_id = (x // 30, y // 30, w // 20, h // 20)
            confirmed_name, conf_score, is_new = confirmer.confirm(face_id, name, score)
            if confirmed_name:
                name = confirmed_name
                score = conf_score
                recognized = True
            else:
                # 未确认，暂不标记为成员（避免误识别打卡）
                recognized = False
                name = "识别中..."
        # 5. 写入身份缓存
        id_cache.set(box, name if recognized else None, score, recognized)
        # 6. Debug: 打印 Top-5（所有检测到人脸的情况都输出，方便诊断低分原因）
        if top5:
            top5_str = ", ".join("%s:%.3f" % (n, s) for n, s in top5[:3])
            margin_val = top5[0][1] - top5[1][1] if len(top5) > 1 else 0
            log.info("识别 %s | bbox=%dx%d | best=%s(%.3f) margin=%.3f | Top3: %s | %s",
                     "PASS" if recognized else "REJECT",
                     w, h, name if recognized else top5[0][0],
                     score, margin_val, top5_str,
                     "已确认" if recognized else "未达阈值/margin")
        results.append((name if recognized else "不在数据库中", score, box, recognized))
    return results


def detect_and_recognize_lbph(img, detector, rec, names, threshold=CONF_THRESHOLD):
    """LBPH 识别（fallback）。"""
    results = []
    h, w = img.shape[:2]
    scale = min(1.0, float(DETECTION_MAX_WIDTH) / float(max(w, 1)))
    dw = max(1, int(w * scale)); dh = max(1, int(h * scale))
    if scale < 1.0:
        detect_img = cv2.resize(img, (dw, dh))
    else:
        detect_img = img
    detector.setInputSize((dw, dh))
    ret, faces = detector.detect(detect_img)
    if faces is None:
        return results
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    inv = 1.0 / scale
    for f in faces:
        if f[14] < MIN_DETECT_SCORE:
            continue
        x, y, fw, fh = [int(v) for v in f[:4]]
        ox = max(0, int(x * inv)); oy = max(0, int(y * inv))
        ow = min(w - ox, int(fw * inv)); oh = min(h - oy, int(fh * inv))
        face = gray[oy:oy + oh, ox:ox + ow]
        if face.size == 0:
            continue
        face = cv2.resize(face, (FACE_SIZE, FACE_SIZE))
        face = cv2.equalizeHist(face)
        try:
            idx, conf = rec.predict(face)
        except Exception:
            results.append(("不在数据库中", 999.0, (ox, oy, ow, oh), False))
            continue
        if 0 <= idx < len(names) and conf <= threshold:
            results.append((names[idx], round(float(conf), 1), (ox, oy, ow, oh), True))
        else:
            results.append(("不在数据库中", round(float(conf), 1), (ox, oy, ow, oh), False))
    return results


# ---------------- 相机管理 ----------------
class CameraManager:
    def __init__(self):
        self.running = threading.Event()
        self.running.set()

        # 相机状态
        self.latest_frame = None
        self.latest_ts = 0.0
        self.frame_lock = threading.Lock()
        self.connected = False
        self.last_error = None

        # 相机信息
        self.camera_info = {}

        # 识别线程共享的最新人脸框
        self._boxes = []
        self._boxes_lock = threading.Lock()

        # 识别结果共享
        self._recog_pending = None

        # FPS 统计
        self.fps_capture = FPSCounter()
        self.fps_preview = FPSCounter()
        self.fps_recognition = FPSCounter()

        # 相机/识别器
        self._ia = None
        self._h = None
        self._rec = None       # LBPH (fallback)
        self._names = []
        self._sface = None     # SFace (主)
        self._gallery = None   # SFace Gallery
        self._id_cache = None  # 身份缓存
        self._confirmer = None # 多帧确认
        self._detector = None
        self._use_sface = False

        # 线程句柄
        self._threads = []

        # 低频兼容写 frame_live.jpg
        self._last_frame_live = 0.0

    # ---------- 共享访问 ----------
    def get_latest_frame(self):
        with self.frame_lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def set_boxes(self, boxes):
        with self._boxes_lock:
            self._boxes = list(boxes)

    def get_boxes(self):
        with self._boxes_lock:
            return list(self._boxes)

    # ---------- Harvester ----------
    def _init_camera(self):
        from harvesters.core import Harvester
        h = Harvester()
        h.add_file(CTI)
        h.update()
        if not h.device_info_list:
            raise RuntimeError("未找到相机设备")
        ia = h.create(0)
        ia.remote_device.node_map.TriggerMode.value = "Off"
        nm = ia.remote_device.node_map
        info = {}
        try:
            info["width"] = nm.Width.value
            info["height"] = nm.Height.value
        except Exception:
            pass
        try:
            info["pixel_format"] = str(nm.PixelFormat.value)
        except Exception:
            pass
        try:
            info["exposure_us"] = nm.ExposureTime.value
        except Exception:
            info["exposure_us"] = None
        try:
            en = getattr(nm, "AcquisitionFrameRateEnable", None)
            if en is not None and hasattr(en, "value"):
                en.value = True
            fr = getattr(nm, "AcquisitionFrameRate", None)
            if fr is not None and hasattr(fr, "value"):
                fr.value = CAMERA_TARGET_FPS
                info["fps_configured"] = fr.value
            elif hasattr(nm, "AcquisitionFrameRateAbs") and hasattr(nm.AcquisitionFrameRateAbs, "value"):
                nm.AcquisitionFrameRateAbs.value = CAMERA_TARGET_FPS
                info["fps_configured"] = nm.AcquisitionFrameRateAbs.value
        except Exception as e:
            log.warning("AcquisitionFrameRate 设置失败(忽略): %s", e)
        try:
            ia.start()
        except Exception:
            ia.start_acquisition()
        self._h = h
        self._ia = ia
        self.camera_info = info
        log.info("相机已连接: %s", info)

    def _grab_frame(self):
        ia = self._ia
        if ia is None:
            return None
        with ia.fetch_buffer(timeout=8) as buf:
            comp = buf.payload.components[0]
            w = int(comp.width); h = int(comp.height)
            fmt = comp.data_format
            arr = np.array(comp.data)
            if fmt == "Mono8":
                return cv2.cvtColor(arr.reshape(h, w), cv2.COLOR_GRAY2BGR)
            if fmt in ("RGB8", "BGR8"):
                return arr.reshape(h, w, 3)
            if fmt == "BayerRG8":
                return cv2.cvtColor(arr.reshape(h, w), cv2.COLOR_BayerRG2BGR)
            if fmt == "BayerBG8":
                return cv2.cvtColor(arr.reshape(h, w), cv2.COLOR_BayerBG2BGR)
            if fmt == "BayerGR8":
                return cv2.cvtColor(arr.reshape(h, w), cv2.COLOR_BayerGR2BGR)
            if fmt == "BayerGB8":
                return cv2.cvtColor(arr.reshape(h, w), cv2.COLOR_BayerGB2BGR)
            return arr.reshape(h, w, 3) if arr.ndim == 3 else cv2.cvtColor(arr.reshape(h, w), cv2.COLOR_GRAY2BGR)

    # ---------- 采集线程 ----------
    def capture_loop(self):
        _set_thread_prio(PRIO_NORMAL)
        log.info("capture thread started")
        while self.running.is_set():
            try:
                img = self._grab_frame()
                if img is None:
                    time.sleep(0.01)
                    continue
                with self.frame_lock:
                    self.latest_frame = img.copy()
                    self.latest_ts = time.time()
                self.connected = True
                self.last_error = None
                self.fps_capture.tick()
            except Exception as e:
                self.connected = False
                self.last_error = str(e)
                log.warning("capture error: %s (相机可能断开，2s 后重试)", e)
                time.sleep(2.0)
        log.info("capture thread stopped")

    # ---------- 预览线程 ----------
    def preview_loop(self):
        _set_thread_prio(PRIO_ABOVE)
        log.info("preview thread started")
        _prof = {}
        _prof_last = time.time()
        def _acc(k, dt_ms):
            _prof.setdefault(k, []).append(dt_ms)
        while self.running.is_set():
            start = time.perf_counter()
            frame = self.get_latest_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            try:
                hh, ww = frame.shape[:2]
                scale = PREVIEW_WIDTH / max(ww, 1)
                if scale < 1.0:
                    preview = cv2.resize(frame, (int(ww * scale), int(hh * scale)))
                else:
                    preview = frame
                _acc("resize", (time.perf_counter() - start) * 1000.0)
                preview = cv2.rotate(preview, cv2.ROTATE_90_CLOCKWISE)
                _k = np.array([[-0.1, -0.1, -0.1], [-0.1, 1.8, -0.1], [-0.1, -0.1, -0.1]], dtype=np.float32)
                preview = cv2.filter2D(preview, -1, _k)
                _acc("rotate", (time.perf_counter() - start) * 1000.0)
                label_items = []
                for name, conf, box, recognized in self.get_boxes():
                    x, y, w, h = [int(v) for v in box]
                    x = int(x * scale); y = int(y * scale)
                    w = int(w * scale); h = int(h * scale)
                    color = (30, 111, 240) if recognized else (30, 170, 250)
                    label = name if recognized else "不在数据库中"
                    cv2.rectangle(preview, (x, y), (x + w, y + h), color, 2)
                    label_items.append((x, y, h, label, color))
                _acc("boxes", (time.perf_counter() - start) * 1000.0)
                self._label_cnt = getattr(self, '_label_cnt', 0) + 1
                if label_items and self._label_cnt % 4 == 0:
                    _draw_cn_labels(preview, label_items)
                _acc("pil", (time.perf_counter() - start) * 1000.0)
                ok, jpeg = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, PREVIEW_JPEG_QUALITY])
                if not ok:
                    continue
                _acc("enc", (time.perf_counter() - start) * 1000.0)
                _publish(jpeg.tobytes(), self.latest_ts if self.latest_ts else time.time(),
                         self.fps_capture.fps(), self.fps_preview.fps(), self.fps_recognition.fps(),
                         self.connected)
                now = time.time()
                if now - self._last_frame_live >= 1.0:
                    self._last_frame_live = now
                    try:
                        jpeg.tofile(FRAME_LIVE)
                    except Exception:
                        pass
                _acc("pub", (time.perf_counter() - start) * 1000.0)
                self.fps_preview.tick()
                if now - _prof_last >= 5.0:
                    _prof_last = now
                    def _md(k):
                        v = _prof.get(k)
                        return round(sum(v) / len(v), 2) if v else 0.0
                    log.info("PROF preview resize=%.2f rotate=%.2f boxes=%.2f pil=%.2f enc=%.2f pub=%.2f total=%.2fms fps=%.1f",
                             _md("resize"), _md("rotate"), _md("boxes"), _md("pil"), _md("enc"), _md("pub"), _md("total"), self.fps_preview.fps())
                    _prof = {}
            except Exception as e:
                import traceback as _tb
                log.warning("preview error: %s\n%s", e, _tb.format_exc())
            elapsed = time.perf_counter() - start
            _acc("total", elapsed * 1000.0)
            sleep_t = max(0.0, (1.0 / PREVIEW_FPS) - elapsed)
            time.sleep(sleep_t)
        log.info("preview thread stopped")

    # ---------- 识别线程 ----------
    def _write_last_recognition(self, name, status, conf=None):
        now = time.time()
        if now - getattr(self, "_last_recogn_written", 0.0) < LAST_RECOG_INTERVAL:
            return
        self._last_recogn_written = now
        try:
            data = {"name": name, "time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "status": status, "conf": conf}
            tmp = LAST_RECOG + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, LAST_RECOG)
        except Exception as e:
            log.warning("write last recognition failed: %s", e)

    def recognition_loop(self):
        _set_thread_prio(PRIO_BELOW)
        mode = "SFace深度特征" if self._use_sface else "LBPH(fallback)"
        log.info("recognition thread started, 模式=%s, 名单 %d 人", mode, len(self._names))
        last_seen = {}
        last_capture = {}
        while self.running.is_set():
            start = time.perf_counter()
            frame = self.get_latest_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            try:
                checked, path = read_checkin()
                rot = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                # 优先使用 SFace，失败回退 LBPH
                if self._use_sface and self._sface is not None and self._gallery is not None:
                    # 自动检测新照片并重建 Gallery
                    self._gallery.build(self._sface, self._detector, force=False)
                    results = detect_and_recognize_sface(rot, self._detector, self._sface,
                                                           self._gallery, self._id_cache, self._confirmer)
                else:
                    results = detect_and_recognize_lbph(rot, self._detector, self._rec, self._names)
                self.set_boxes(results)
                now = time.time()
                any_member = False
                for name, conf, box, recognized in results:
                    # 分类捕获
                    last_c = last_capture.get(name, 0.0)
                    if now - last_c >= CAPTURE_COOLDOWN:
                        self._save_capture(rot, box, name)
                        last_capture[name] = now
                    if not recognized:
                        continue
                    any_member = True
                    last = last_seen.get(name, 0)
                    if now - last < SAME_PERSON_COOLDOWN:
                        continue
                    if name in checked:
                        last_seen[name] = now
                        continue
                    checked.add(name)
                    write_checkin(checked, path)
                    last_seen[name] = now
                    log.info("已打卡: %s (score=%.3f)", name, conf)
                    self._write_last_recognition(name, "checked", conf)
                if results and not any_member:
                    self._write_last_recognition("不在数据库中", "stranger")
                elif any_member:
                    name0 = next((r[0] for r in results if r[3]), "成员")
                    self._write_last_recognition(name0, "seen")
                self.fps_recognition.tick()
            except Exception as e:
                import traceback as _tb
                log.warning("recognition error: %s\n%s", e, _tb.format_exc())
            elapsed = time.perf_counter() - start
            sleep_t = max(0.0, (1.0 / RECOGNITION_FPS) - elapsed)
            time.sleep(sleep_t)
        log.info("recognition thread stopped")

    def _save_capture(self, img, box, name):
        try:
            x, y, w, h = [int(v) for v in box]
            pad = int(max(w, h) * 0.15)
            x0 = max(0, x - pad); y0 = max(0, y - pad)
            x1 = min(img.shape[1], x + w + pad); y1 = min(img.shape[0], y + h + pad)
            face_img = img[y0:y1, x0:x1]
            if face_img.size == 0:
                return
            folder = os.path.join(LIB, "captures", str(name))
            os.makedirs(folder, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            cv2.imencode(".jpg", face_img, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tofile(
                os.path.join(folder, "%s.jpg" % ts))
        except Exception as e:
            log.warning("save face capture failed: %s", e)

    # ---------- 生命周期 ----------
    def start(self):
        # 初始化 YuNet 检测器
        self._detector = cv2.FaceDetectorYN_create(YUNET, "", (320, 320), 0.6, 0.3, 5000)

        # 优先加载 SFace 深度识别器
        self._sface = load_sface()
        if self._sface is not None:
            self._gallery = FaceGallery()
            self._id_cache = IdentityCache()
            self._confirmer = MultiFrameConfirmer(n=MULTI_FRAME_CONFIRM)
            n = self._gallery.build(self._sface, self._detector, force=False)
            self._names = list(set(self._gallery.names)) if self._gallery.names else []
            self._use_sface = True
            log.info("SFace 模式启用: Gallery %d 人", n)
        else:
            # 回退 LBPH
            self._rec, self._names = load_recognizer()
            if self._rec is None:
                raise RuntimeError("识别模型加载失败(SFace和LBPH均不可用)")
            self._use_sface = False
            log.info("SFace 不可用，回退 LBPH 模式: %d 人", len(self._names))

        # 初始化相机
        self._init_camera()
        # 启动内部 HTTP 流服务
        _start_internal_http()
        # 启动线程
        self._threads = [
            threading.Thread(target=self.capture_loop, name="capture", daemon=True),
            threading.Thread(target=self.preview_loop, name="preview", daemon=True),
            threading.Thread(target=self.recognition_loop, name="recognition", daemon=True),
        ]
        for t in self._threads:
            t.start()
        log.info("CameraManager 已启动：采集/预览/识别 三线程, 模式=%s",
                 "SFace" if self._use_sface else "LBPH")

    def stop(self):
        log.info("CameraManager 停止中…")
        self.running.clear()
        for t in self._threads:
            t.join(timeout=5)
        global _internal_http
        if _internal_http is not None:
            try:
                _internal_http.shutdown()
            except Exception:
                pass
            _internal_http = None
        try:
            if self._ia is not None:
                self._ia.stop(); self._ia.destroy()
        except Exception:
            pass
        if self._h is not None:
            try:
                self._h.reset()
            except Exception:
                pass
        log.info("CameraManager 已停止，Harvester 已释放")

    def run(self):
        self.start()
        try:
            while self.running.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            log.info("收到中断信号")
        finally:
            self.stop()
