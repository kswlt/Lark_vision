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
         └──────────────► [Recognition Thread] ── YuNet(640) ──► LBPH ──► 打卡/捕获 ──► last_recognition.json
                            5FPS / 自适应 sleep
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
PREVIEW_FPS = 20              # 预览编码目标帧率
PREVIEW_WIDTH = 640           # 预览宽度
PREVIEW_JPEG_QUALITY = 70     # 预览 JPEG 质量
RECOGNITION_FPS = 5           # 识别目标帧率
DETECTION_MAX_WIDTH = 640     # YuNet 检测最大宽度（检测缩放，避免全分辨率）

FACE_SIZE = 112
CONF_THRESHOLD = 70           # LBPH confidence（越小越像）
MIN_DETECT_SCORE = 0.5
SAME_PERSON_COOLDOWN = 300    # 秒，同人重复打卡冷却
CAPTURE_COOLDOWN = 8          # 秒，同人捕获冷却
PREVIEW_JPEG_MMAP = ""  # 已弃用（原 mmap 方案，Session 隔离/权限问题，改内部 HTTP）
INTERNAL_HTTP_PORT = 18080  # 内部流服务端口（Flask 代理 /api/camera/stream）
MMAP_SIZE = 1 * 1024 * 1024   # 保留常量（兼容引用）
LAST_RECOG_INTERVAL = 1.5     # 秒，识别结果写入冷却

BASE = r"C:\RoboMasterDashboard"
LIB = os.path.join(BASE, "face_library")
CTI = r"C:\Program Files\HuarayTech\MV Viewer\Runtime\x64\MVProducerU3V.cti"
YUNET = os.path.join(LIB, "models", "face_detection_yunet.onnx")
MODEL = os.path.join(LIB, "face_model.yml")
NAMES = os.path.join(LIB, "face_names.txt")
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


# ---------------- 内部流状态 + HTTP 服务（跨 Session 无权限问题，Flask 代理） ----------------
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
                except Exception:  # noqa: BLE001
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

    def log_message(self, *a):  # 静默访问日志
        pass


def _publish(jpeg, ts, c_fps, p_fps, r_fps, connected):
    """预览线程发布最新帧 + 指标到内部状态。"""
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
    """启动内部 HTTP 流服务（127.0.0.1:18080），daemon 线程，失败不致命。"""
    global _internal_http
    try:
        httpd = socketserver.ThreadingTCPServer(("127.0.0.1", INTERNAL_HTTP_PORT), _CamHandler)
        httpd.daemon_threads = True
        t = threading.Thread(target=httpd.serve_forever, name="internal-http", daemon=True)
        t.start()
        _internal_http = httpd
        log.info("内部流服务已启动: http://127.0.0.1:%d", INTERNAL_HTTP_PORT)
    except Exception as e:  # noqa: BLE001
        log.warning("内部流服务启动失败(不影响采集/识别): %s", e)


# ---------------- 人脸库 / 打卡 / 捕获（识别线程使用） ----------------
def load_recognizer():
    try:
        if not os.path.exists(MODEL) or not os.path.exists(NAMES):
            log.warning("人脸模型不存在，请先运行 train_face.py")
            return None, []
        rec = cv2.face.LBPHFaceRecognizer_create()
        rec.read(MODEL)
        with open(NAMES, "r", encoding="utf-8") as f:
            names = [x.strip() for x in f.read().splitlines() if x.strip()]
        return rec, names
    except Exception as e:  # noqa: BLE001
        log.error("load recognizer failed: %s", e)
        return None, []


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
    except Exception as e:  # noqa: BLE001
        log.error("write checkin failed: %s", e)


def detect_and_recognize(img, detector, rec, names, threshold=CONF_THRESHOLD):
    """检测+识别。返回 [(name, conf, box_orig, recognized)]，box 为原始帧坐标。
    YuNet 在缩放图上检测，bbox 映射回原始帧。"""
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
        # 映射回原始帧坐标
        ox = max(0, int(x * inv)); oy = max(0, int(y * inv))
        ow = min(w - ox, int(fw * inv)); oh = min(h - oy, int(fh * inv))
        face = gray[oy:oy + oh, ox:ox + ow]
        if face.size == 0:
            continue
        face = cv2.resize(face, (FACE_SIZE, FACE_SIZE))
        face = cv2.equalizeHist(face)
        try:
            idx, conf = rec.predict(face)
        except Exception as e:  # noqa: BLE001
            log.warning("predict err: %s", e)
            results.append(("陌生人", 999.0, (ox, oy, ow, oh), False))
            continue
        if 0 <= idx < len(names) and conf <= threshold:
            results.append((names[idx], round(float(conf), 1), (ox, oy, ow, oh), True))
        else:
            results.append(("陌生人", round(float(conf), 1), (ox, oy, ow, oh), False))
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

        # 识别线程共享的最新人脸框（原始帧坐标）
        self._boxes = []
        self._boxes_lock = threading.Lock()

        # 识别结果共享（供写 last_recognition.json，避免识别线程高频 IO）
        self._recog_pending = None  # (name, status, conf)

        # FPS 统计
        self.fps_capture = FPSCounter()
        self.fps_preview = FPSCounter()
        self.fps_recognition = FPSCounter()

        # 相机/识别器
        self._ia = None
        self._h = None
        self._rec = None
        self._names = []
        self._detector = None

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
        """初始化 Harvester + 相机，配置自由运行 + 尝试 30FPS。"""
        from harvesters.core import Harvester
        h = Harvester()
        h.add_file(CTI)
        h.update()
        if not h.device_info_list:
            raise RuntimeError("未找到相机设备")
        ia = h.create(0)
        ia.remote_device.node_map.TriggerMode.value = "Off"
        # 读取/尝试设置硬件 FPS
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
        except Exception as e:  # noqa: BLE001
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
        """从相机抓一帧 -> BGR or None（仅采集线程调用）。"""
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
            except Exception as e:  # noqa: BLE001
                self.connected = False
                self.last_error = str(e)
                log.warning("capture error: %s (相机可能断开，2s 后重试)", e)
                time.sleep(2.0)
        log.info("capture thread stopped")

    # ---------- 预览线程 ----------
    def preview_loop(self):
        log.info("preview thread started")
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
                # 先旋转到显示方向（与 UI 一致，右旋 90°）
                preview = cv2.rotate(preview, cv2.ROTATE_90_CLOCKWISE)
                # 画人脸框（识别线程在旋转后帧检测，坐标与显示坐标系一致，直接 *scale）
                for name, conf, box, recognized in self.get_boxes():
                    x, y, w, h = [int(v) for v in box]
                    x = int(x * scale); y = int(y * scale)
                    w = int(w * scale); h = int(h * scale)
                    color = (30, 111, 240) if recognized else (30, 170, 250)  # BGR 蓝/黄
                    label = name if recognized else "陌生人"
                    cv2.rectangle(preview, (x, y), (x + w, y + h), color, 2)
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    ty = y - 4 if y - 4 > th + 4 else y + h + th + 4
                    cv2.rectangle(preview, (x, ty - th - 4), (x + tw + 6, ty + 2), color, -1)
                    cv2.putText(preview, label, (x + 3, ty - 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                ok, jpeg = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, PREVIEW_JPEG_QUALITY])
                if not ok:
                    continue
                # 发布到内部状态（内存共享，无磁盘 IO；Flask 通过内部 HTTP 代理）
                _publish(jpeg.tobytes(), self.latest_ts if self.latest_ts else time.time(),
                         self.fps_capture.fps(), self.fps_preview.fps(), self.fps_recognition.fps(),
                         self.connected)
                # 低频兼容写 frame_live.jpg（1 秒一次）
                now = time.time()
                if now - self._last_frame_live >= 1.0:
                    self._last_frame_live = now
                    try:
                        cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, PREVIEW_JPEG_QUALITY])[1].tofile(FRAME_LIVE)
                    except Exception:  # noqa: BLE001
                        pass
                self.fps_preview.tick()
            except Exception as e:  # noqa: BLE001
                import traceback as _tb
                log.warning("preview error: %s\n%s", e, _tb.format_exc())
            elapsed = time.perf_counter() - start
            sleep_t = max(0.0, (1.0 / PREVIEW_FPS) - elapsed)
            time.sleep(sleep_t)
        log.info("preview thread stopped")

    # ---------- 识别线程 ----------
    def _write_last_recognition(self, name, status, conf=None):
        """低频写 last_recognition.json（1.5s 冷却）。"""
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
        except Exception as e:  # noqa: BLE001
            log.warning("write last recognition failed: %s", e)

    def recognition_loop(self):
        log.info("recognition thread started, 名单 %d 人", len(self._names))
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
                # 识别在右旋 90° 的帧上进行：人脸正立，YuNet/LBPH 检测与识别效果最佳；
                # 返回框为显示坐标系，预览画框可直接对齐（方向永远正确）。
                rot = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                results = detect_and_recognize(rot, self._detector, self._rec, self._names)
                # 共享人脸框供预览画框
                self.set_boxes(results)
                now = time.time()
                any_member = False
                for name, conf, box, recognized in results:
                    # 分类捕获：名单内按姓名存文件夹，陌生人存"陌生人"文件夹（8s 冷却）
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
                    log.info("已打卡: %s (conf=%.1f)", name, conf)
                    self._write_last_recognition(name, "checked", conf)
                if results and not any_member:
                    self._write_last_recognition("陌生人", "stranger")
                elif any_member:
                    name0 = next((r[0] for r in results if r[3]), "成员")
                    self._write_last_recognition(name0, "seen")
                self.fps_recognition.tick()
            except Exception as e:  # noqa: BLE001
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
        except Exception as e:  # noqa: BLE001
            log.warning("save face capture failed: %s", e)

    # ---------- 生命周期 ----------
    def start(self):
        # 初始化识别器
        self._rec, self._names = load_recognizer()
        if self._rec is None:
            raise RuntimeError("识别模型加载失败")
        self._detector = cv2.FaceDetectorYN_create(YUNET, "", (320, 320), 0.6, 0.3, 5000)
        # 初始化相机
        self._init_camera()
        # 启动内部 HTTP 流服务（Flask 代理用）
        _start_internal_http()
        # 启动线程
        self._threads = [
            threading.Thread(target=self.capture_loop, name="capture", daemon=True),
            threading.Thread(target=self.preview_loop, name="preview", daemon=True),
            threading.Thread(target=self.recognition_loop, name="recognition", daemon=True),
        ]
        for t in self._threads:
            t.start()
        log.info("CameraManager 已启动：采集/预览/识别 三线程")

    def stop(self):
        log.info("CameraManager 停止中…")
        self.running.clear()
        for t in self._threads:
            t.join(timeout=5)
        global _internal_http
        if _internal_http is not None:
            try:
                _internal_http.shutdown()
            except Exception:  # noqa: BLE001
                pass
            _internal_http = None
        try:
            if self._ia is not None:
                self._ia.stop(); self._ia.destroy()
        except Exception:  # noqa: BLE001
            pass
        if self._h is not None:
            try:
                self._h.reset()
            except Exception:  # noqa: BLE001
                pass
        log.info("CameraManager 已停止，Harvester 已释放")

    def run(self):
        """阻塞运行：start + 等待中断信号。"""
        self.start()
        try:
            while self.running.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            log.info("收到中断信号")
        finally:
            self.stop()
