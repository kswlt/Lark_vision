# -*- coding: utf-8 -*-
"""
希沃端人脸打卡服务（常驻）。
- 华睿大华 A5131CU210 USB3 相机取流（harvesters + MVProducerU3V.cti）
- YuNet 人脸检测 + LBPH 识别
- 识别到已训练成员 -> 写入当日打卡记录 data/face_checkin_YYYYMMDD.json
- 每人每天只记一次；5 分钟内同人不重复识别
用法:
  单帧测试: python camera_checkin.py --once
  常驻运行: python camera_checkin.py
"""
import os
import sys
import time
import json
import logging
import argparse
import datetime

os.environ["PATH"] = r"C:\Program Files\HuarayTech\MV Viewer\Runtime\x64;" + os.environ.get("PATH", "")

import numpy as np
import cv2

BASE = r"C:\RoboMasterDashboard"
LIB = os.path.join(BASE, "face_library")
CTI = r"C:\Program Files\HuarayTech\MV Viewer\Runtime\x64\MVProducerU3V.cti"
YUNET = os.path.join(LIB, "models", "face_detection_yunet.onnx")
MODEL = os.path.join(LIB, "face_model.yml")
NAMES = os.path.join(LIB, "face_names.txt")
DATA_DIR = os.path.join(BASE, "data")
LOG_DIR = os.path.join(BASE, "logs")

FACE_SIZE = 112
CONF_THRESHOLD = 70        # LBPH confidence 阈值（越小越像）
MIN_DETECT_SCORE = 0.7
DETECT_INTERVAL = 1.2      # 秒，取流间隔
SAME_PERSON_COOLDOWN = 300 # 秒，同人重复识别冷却

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "face_checkin.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("face_checkin")


def load_recognizer():
    """加载 LBPH 模型 + 姓名表；失败返回 None。"""
    try:
        if not os.path.exists(MODEL) or not os.path.exists(NAMES):
            log.warning("人脸模型不存在，请先运行 train_face.py")
            return None, []
        rec = cv2.face.LBPHFaceRecognizer_create()
        rec.read(MODEL)
        with open(NAMES, "r", encoding="utf-8") as f:
            names = [x.strip() for x in f.read().splitlines() if x.strip()]
        return rec, names
    except Exception as e:
        log.error("load recognizer failed: %s", e)
        return None, []


def read_checkin():
    """读今日打卡记录 -> set(names)"""
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


def grab_frame(ia):
    """抓一帧 -> BGR 图像 or None"""
    try:
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
            return arr.reshape(h, w, 3) if arr.ndim == 3 else cv2.cvtColor(arr.reshape(h, w), cv2.COLOR_GRAY2BGR)
    except Exception as e:
        log.warning("grab frame failed: %s", e)
        return None


def detect_and_recognize(img, detector, rec, names, threshold=CONF_THRESHOLD):
    """返回 [(name, confidence, bbox)]"""
    results = []
    h, w = img.shape[:2]
    detector.setInputSize((w, h))
    ret, faces = detector.detect(img)
    if faces is None:
        return results
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    for f in faces:
        if f[14] < MIN_DETECT_SCORE:
            continue
        x, y, fw, fh = [int(v) for v in f[:4]]
        x = max(0, x); y = max(0, y)
        face = gray[y:y+fh, x:x+fw]
        if face.size == 0:
            continue
        face = cv2.resize(face, (FACE_SIZE, FACE_SIZE))
        face = cv2.equalizeHist(face)
        try:
            idx, conf = rec.predict(face)
        except Exception as e:
            log.warning("predict err: %s", e)
            continue
        name = names[idx] if 0 <= idx < len(names) else "未知"
        results.append((name, round(float(conf), 1), (x, y, fw, fh)))
    return results


def run_once(detector, rec, names, ia):
    """单帧测试模式：识别画面中所有人脸并打印。"""
    img = grab_frame(ia)
    if img is None:
        print("NO_FRAME")
        return
    cv2.imencode('.jpg', img)[1].tofile(os.path.join(LIB, "frame_live.jpg"))
    results = detect_and_recognize(img, detector, rec, names)
    if results:
        for name, conf, box in results:
            print("FACE %s conf=%s box=%s" % (name, conf, box))
    else:
        print("NO_FACE_DETECTED")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="单帧测试")
    args = ap.parse_args()

    rec, names = load_recognizer()
    if rec is None:
        return 1
    detector = cv2.FaceDetectorYN_create(YUNET, "", (320, 320), 0.6, 0.3, 5000)

    from harvesters.core import Harvester
    h = Harvester()
    h.add_file(CTI)
    h.update()
    if not h.device_info_list:
        log.error("未找到相机设备")
        return 1
    ia = h.create(0)
    try:
        # 连续采集
        try:
            ia.remote_device.node_map.TriggerMode.value = "Off"
        except Exception:
            pass
        ia.start()

        if args.once:
            run_once(detector, rec, names, ia)
            return 0

        log.info("人脸打卡服务启动，识别名单 %d 人", len(names))
        last_seen = {}  # name -> timestamp
        while True:
            checked, path = read_checkin()
            img = grab_frame(ia)
            if img is None:
                time.sleep(DETECT_INTERVAL)
                continue
            # 保存实时画面帧（供前端相机小窗口轮询）
            try:
                hh, ww = img.shape[:2]
                scale = 640.0 / max(ww, 1)
                if scale < 1.0:
                    small = cv2.resize(img, (int(ww * scale), int(hh * scale)))
                else:
                    small = img
                cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tofile(
                    os.path.join(LIB, "frame_live.jpg")
                )
            except Exception as e:  # noqa: BLE001
                log.warning("save frame failed: %s", e)
            results = detect_and_recognize(img, detector, rec, names)
            now = time.time()
            for name, conf, box in results:
                if conf > CONF_THRESHOLD:
                    log.debug("低置信 %s conf=%s", name, conf)
                    continue
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
            time.sleep(DETECT_INTERVAL)
    except KeyboardInterrupt:
        log.info("服务停止")
    except Exception as e:
        log.error("service error: %s", e)
        import traceback; traceback.print_exc()
        return 1
    finally:
        try:
            ia.stop(); ia.destroy()
        except Exception:
            pass
        h.reset()
    return 0


if __name__ == "__main__":
    sys.exit(main())
