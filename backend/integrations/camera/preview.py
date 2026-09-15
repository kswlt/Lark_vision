"""
内部 MJPEG 预览流服务（127.0.0.1:CAMERA_INTERNAL_PORT）。
- /stream  multipart/x-mixed-replace 推流
- /status  JSON 状态
- /frame   单帧 JPEG
供 Flask /api/camera/* 代理到浏览器，避免跨 Session 权限问题。
"""
import datetime
import http.server
import json
import socketserver
import threading
import time

from .base import INTERNAL_HTTP_PORT, log

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


def publish(jpeg, ts, c_fps, p_fps, r_fps, connected):
    with _STATE_LOCK:
        _STATE["seq"] += 1
        _STATE["jpeg"] = jpeg
        _STATE["ts"] = ts
        _STATE["capture_fps"] = c_fps
        _STATE["preview_fps"] = p_fps
        _STATE["recognition_fps"] = r_fps
        _STATE["connected"] = connected


_internal_http = None


def start_internal_http():
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


def stop_internal_http():
    global _internal_http
    if _internal_http is not None:
        try:
            _internal_http.shutdown()
        except Exception:
            pass
        _internal_http = None
