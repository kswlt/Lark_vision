"""
【兼容层】摄像头 / 人脸识别模块。

真实实现已拆分到 backend/integrations/camera/（结构见下），本文件保留旧模块名，
供 camera_checkin.py 等历史代码直接 import，对外 API 完全兼容：

    backend/integrations/camera/
        __init__.py      对外公开 API 汇总
        base.py          环境变量化配置 / 日志 / FPS 统计 / 线程工具
        huaray.py        华睿相机采集（厂商 SDK 封装）
        gallery.py       SFace 人脸向量库
        recognition.py   人脸检测 / SFace / LBPH / 多帧确认 / 身份缓存
        preview.py       内部 MJPEG 流服务
        manager.py       CameraManager（采集/预览/识别 三线程调度）

所有机器相关路径均通过环境变量 / backend/.env 配置（APP_DATA_DIR、
FACE_LIBRARY_DIR、CAMERA_CTI_PATH、CAMERA_ENABLED），不再硬编码开发者电脑路径。

用法：
    from camera_manager import CameraManager
    CameraManager().run()
"""
import os

# 支持希沃等旧部署：从 backend/.env 读取相机/人脸库路径配置
_BACKEND = os.path.dirname(os.path.abspath(__file__))
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_BACKEND, ".env"), override=False)
except Exception:  # pragma: no cover - dotenv 为可选依赖
    pass

from integrations.camera import (  # noqa: F401, E402
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
    CameraManager,
    FaceGallery,
    FPSCounter,
    HuarayCamera,
    IdentityCache,
    MultiFrameConfirmer,
    camera_configured,
    detect_and_recognize_lbph,
    detect_and_recognize_sface,
    detect_faces,
    load_recognizer,
    load_sface,
    log,
    publish,
    read_checkin,
    start_internal_http,
    stop_internal_http,
    write_checkin,
)
