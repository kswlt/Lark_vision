"""
摄像头模块基础设施：环境变量化配置、日志、FPS 统计、线程优先级辅助。

所有机器相关路径均通过环境变量 / backend/.env 配置，不再硬编码开发者电脑路径：
- APP_DATA_DIR       数据目录（打卡记录等），默认 ~/.lark_vision
- FACE_LIBRARY_DIR   人脸库目录（photos/models/face_names.txt 等），默认 <APP_DATA_DIR>/face_library
- CAMERA_CTI_PATH    华睿相机 GenICam 描述文件（.cti）绝对路径；为空表示未配置华睿相机
- CAMERA_ENABLED     是否启用摄像头模块（true/false），未安装 cv2/harvesters 时 Dashboard 照常运行
"""
import collections
import logging
import os
import sys
import threading
import time

# ---------------- 环境变量化配置 ----------------
APP_DATA_DIR = os.environ.get(
    "APP_DATA_DIR", os.path.join(os.path.expanduser("~"), ".lark_vision")
)
FACE_LIBRARY_DIR = os.environ.get(
    "FACE_LIBRARY_DIR", os.path.join(APP_DATA_DIR, "face_library")
)
LIB = FACE_LIBRARY_DIR  # 兼容旧代码引用（人脸库根目录）
CAMERA_CTI_PATH = os.environ.get("CAMERA_CTI_PATH", "").strip()
CAMERA_ENABLED = os.environ.get("CAMERA_ENABLED", "false").strip().lower() in (
    "1", "true", "yes", "on"
)

# 采集 / 预览 / 识别 参数（可环境变量覆盖，默认值保持当前调优结果）
CAMERA_TARGET_FPS = int(os.environ.get("CAMERA_TARGET_FPS", "30"))
PREVIEW_FPS = int(os.environ.get("PREVIEW_FPS", "30"))
PREVIEW_WIDTH = int(os.environ.get("PREVIEW_WIDTH", "640"))
PREVIEW_JPEG_QUALITY = int(os.environ.get("PREVIEW_JPEG_QUALITY", "80"))
RECOGNITION_FPS = int(os.environ.get("RECOGNITION_FPS", "2"))
DETECTION_MAX_WIDTH = int(os.environ.get("DETECTION_MAX_WIDTH", "640"))

FACE_SIZE = 112
CONF_THRESHOLD = 100  # LBPH confidence（fallback 用）
MIN_DETECT_SCORE = 0.5
SAME_PERSON_COOLDOWN = 300  # 秒，同人重复打卡冷却
CAPTURE_COOLDOWN = 8  # 秒，同人捕获冷却
INTERNAL_HTTP_PORT = int(os.environ.get("CAMERA_INTERNAL_PORT", "18080"))
LAST_RECOG_INTERVAL = 1.5  # 秒，识别结果写入冷却

# SFace 深度人脸识别配置
SFACE_COSINE_THRESHOLD = float(os.environ.get("SFACE_COSINE_THRESHOLD", "0.45"))
SFACE_L2_THRESHOLD = 1.128  # 保留：L2 距离阈值（当前使用 cosine，越大越像）
SFACE_MATCH_MARGIN = float(os.environ.get("SFACE_MATCH_MARGIN", "0.05"))
MULTI_FRAME_CONFIRM = int(os.environ.get("MULTI_FRAME_CONFIRM", "3"))
IDENTITY_CACHE_TTL = int(os.environ.get("IDENTITY_CACHE_TTL", "3"))
GALLERY_REBUILD_INTERVAL = 3600  # Gallery 重建间隔（秒）

# 派生路径
MODELS_DIR = os.path.join(FACE_LIBRARY_DIR, "models")
YUNET = os.path.join(MODELS_DIR, "face_detection_yunet.onnx")
SFACE_MODEL = os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")
MODEL = os.path.join(FACE_LIBRARY_DIR, "face_model.yml")
NAMES = os.path.join(FACE_LIBRARY_DIR, "face_names.txt")
PHOTO_DIR = os.path.join(FACE_LIBRARY_DIR, "photos")
GALLERY_FILE = os.path.join(FACE_LIBRARY_DIR, "face_gallery.npz")
DATA_DIR = os.path.join(APP_DATA_DIR, "data")
LOG_DIR = os.path.join(APP_DATA_DIR, "logs")
LAST_RECOG = os.path.join(FACE_LIBRARY_DIR, "last_recognition.json")
FRAME_LIVE = os.path.join(FACE_LIBRARY_DIR, "frame_live.jpg")

# 华睿 SDK：若配置了 CTI 路径，将其 Runtime 目录加入 PATH（DLL 依赖）
if CAMERA_CTI_PATH and os.path.isdir(os.path.dirname(CAMERA_CTI_PATH)):
    os.environ["PATH"] = os.path.dirname(CAMERA_CTI_PATH) + os.pathsep + os.environ.get("PATH", "")

# ---------------- 日志 ----------------
os.makedirs(LOG_DIR, exist_ok=True)
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


# ---------------- 线程优先级辅助（Windows） ----------------
import ctypes as _ct  # noqa: E402


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
