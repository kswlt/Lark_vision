# -*- coding: utf-8 -*-
"""
希沃端人脸打卡服务（常驻）——入口。
架构已重构为多线程（见 camera_manager.py）：
    Camera Capture Thread  →  latest_frame(内存)
        ├─ Preview Encoder Thread → mmap → Flask MJPEG → 浏览器
        └─ Recognition Thread     → YuNet → LBPH → 打卡 / 捕获
用法:
    常驻运行: python camera_checkin.py
    单帧测试: python camera_checkin.py --once
"""
import os
import sys
import time
import argparse

os.environ["PATH"] = r"C:\Program Files\HuarayTech\MV Viewer\Runtime\x64;" + os.environ.get("PATH", "")

import cv2

from camera_manager import (
    CameraManager,
    LIB,
    load_recognizer,
    detect_and_recognize,
    log,
)

# 单帧测试模式共用 CameraManager 的相机初始化和抓帧
def run_once():
    from camera_manager import CameraManager as _CM
    cm = _CM()
    try:
        rec, names = load_recognizer()
        if rec is None:
            print("NO_MODEL")
            return 1
        detector = cv2.FaceDetectorYN_create(
            os.path.join(LIB, "models", "face_detection_yunet.onnx"),
            "", (320, 320), 0.6, 0.3, 5000)
        cm._init_camera()
        img = cm._grab_frame()
        if img is None:
            print("NO_FRAME")
            return 1
        cv2.imencode(".jpg", img)[1].tofile(os.path.join(LIB, "frame_live.jpg"))
        results = detect_and_recognize(img, detector, rec, names)
        if results:
            for name, conf, box, rec_ok in results:
                print("FACE %s conf=%s box=%s" % (name, conf, box))
        else:
            print("NO_FACE_DETECTED")
    finally:
        try:
            if cm._ia is not None:
                cm._ia.stop(); cm._ia.destroy()
            if cm._h is not None:
                cm._h.reset()
        except Exception:  # noqa: BLE001
            pass
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="单帧测试")
    args = ap.parse_args()

    if args.once:
        return run_once()

    log.info("人脸打卡服务启动（多线程架构）")
    cm = CameraManager()
    try:
        cm.run()
    except Exception as e:  # noqa: BLE001
        log.error("service error: %s", e)
        import traceback; traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
