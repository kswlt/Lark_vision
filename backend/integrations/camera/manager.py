"""
CameraManager：华睿工业相机多线程管理（采集 / 预览 / 识别 解耦）。

架构：
    Harvester(仅采集线程持有)
         │  fetch_buffer (相机自由运行，目标 30FPS)
         ▼
    [Camera Capture Thread] ── latest_frame (内存缓存, 锁保护) ──┐
         │                                                       │
         ├──────────────► [Preview Encoder Thread] ── latest_jpeg ──► 内部HTTP MJPEG ──► Flask ──► Browser
         │                   30FPS / 640px / 旋转90°
         └──────────────► [Recognition Thread] ── YuNet(640) ──► SFace深度特征 ──► Gallery匹配 ──► 多帧确认 ──► 打卡/捕获
                            1-3FPS / 身份缓存 / 低频识别

依赖（可选）：harvesters / genicam / cv2 / numpy（见 requirements-camera.txt）。
用法：
    from integrations.camera import CameraManager
    CameraManager().run()   # 阻塞运行，Ctrl+C 优雅退出
"""
import datetime
import json
import os
import threading
import time

import cv2
import numpy as np

from .base import (
    CAPTURE_COOLDOWN,
    FRAME_LIVE,
    LAST_RECOG,
    LAST_RECOG_INTERVAL,
    LIB,  # 兼容：人脸库根目录
    MULTI_FRAME_CONFIRM,
    PREVIEW_FPS,
    PREVIEW_JPEG_QUALITY,
    PREVIEW_WIDTH,
    PRIO_ABOVE,
    PRIO_BELOW,
    PRIO_NORMAL,
    RECOGNITION_FPS,
    SAME_PERSON_COOLDOWN,
    YUNET,
    FPSCounter,
    _set_thread_prio,
    log,
)
from .gallery import FaceGallery
from .huaray import HuarayCamera
from .preview import publish, start_internal_http, stop_internal_http
from .recognition import (
    IdentityCache,
    MultiFrameConfirmer,
    _draw_cn_labels,
    detect_and_recognize_lbph,
    detect_and_recognize_sface,
    load_recognizer,
    load_sface,
    read_checkin,
    write_checkin,
)


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
        self._cam = None       # HuarayCamera 封装
        self._ia = None        # 兼容旧引用（camera_checkin.run_once 使用）
        self._h = None         # 兼容旧引用
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

    # ---------- 相机（兼容 _init_camera / _grab_frame 旧签名） ----------
    def _init_camera(self):
        """连接相机（失败时抛明确错误，由调用方决定是否终止）。"""
        self._cam = HuarayCamera()
        self._ia = self._cam.connect()
        self._h = self._cam._h
        self.camera_info = self._cam.info
        self.connected = True

    def _grab_frame(self):
        """抓取一帧 BGR。相机未连接返回 None。"""
        if self._cam is None:
            return None
        return self._cam.grab()

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
                for name, _conf, box, recognized in self.get_boxes():
                    x, y, w, h = [int(v) for v in box]
                    x = int(x * scale)
                    y = int(y * scale)
                    w = int(w * scale)
                    h = int(h * scale)
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
                publish(jpeg.tobytes(), self.latest_ts if self.latest_ts else time.time(),
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

                    def _md(k, prof=_prof):
                        v = prof.get(k)
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
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(img.shape[1], x + w + pad)
            y1 = min(img.shape[0], y + h + pad)
            face_img = img[y0:y1, x0:x1]
            if face_img.size == 0:
                return
            folder = os.path.join(LIB, "captures", str(name))
            os.makedirs(folder, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            cv2.imencode(".jpg", face_img, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tofile(
                os.path.join(folder, f"{ts}.jpg"))
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
        start_internal_http()
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
        stop_internal_http()
        if self._cam is not None:
            self._cam.release()
        self._ia = None
        self._h = None
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
