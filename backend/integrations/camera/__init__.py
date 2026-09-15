"""
摄像头 / 人脸识别模块（可选功能）。

未安装 cv2/harvesters 等依赖时，本包不应导致后端启动失败：
- Dashboard 通过 CAMERA_ENABLED=false 直接禁用摄像头功能；
- 仅当确实需要摄像头时安装 backend/requirements-camera.txt 并配置相机。

对外公开 API（与旧 camera_manager 模块兼容）：
    CameraManager
    LIB / FACE_LIBRARY_DIR / 各类路径常量
    load_recognizer / load_sface
    detect_faces / detect_and_recognize_sface / detect_and_recognize_lbph
    FaceGallery / MultiFrameConfirmer / IdentityCache
    read_checkin / write_checkin / log
    camera_configured
"""
from .base import (  # noqa: F401
    APP_DATA_DIR,
    CAMERA_CTI_PATH,
    CAMERA_ENABLED,
    DATA_DIR,
    DETECTION_MAX_WIDTH,
    FACE_LIBRARY_DIR,
    FRAME_LIVE,
    GALLERY_FILE,
    LAST_RECOG,
    LIB,
    LOG_DIR,
    MODEL,
    MODELS_DIR,
    NAMES,
    PHOTO_DIR,
    PREVIEW_FPS,
    RECOGNITION_FPS,
    SFACE_MODEL,
    YUNET,
    FPSCounter,
    log,
)
from .gallery import FaceGallery  # noqa: F401

# 重导出 camera_configured（供 app.py 判断是否配置了相机）
from .huaray import (
    HuarayCamera,  # noqa: F401
    camera_configured,  # noqa: F401
)
from .manager import CameraManager  # noqa: F401
from .preview import (  # noqa: F401
    publish,
    start_internal_http,
    stop_internal_http,
)
from .recognition import (  # noqa: F401
    IdentityCache,
    MultiFrameConfirmer,
    detect_and_recognize_lbph,
    detect_and_recognize_sface,
    detect_faces,
    load_recognizer,
    load_sface,
    read_checkin,
    write_checkin,
)
