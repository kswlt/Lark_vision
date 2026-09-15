"""
华睿工业相机采集（厂商 SDK 封装）。
通过 CAMERA_CTI_PATH 环境变量指定 GenICam 描述文件；
未配置 CTI 时抛错提示，不静默失败。
"""

import cv2
import numpy as np

from .base import CAMERA_CTI_PATH, CAMERA_TARGET_FPS, log


def camera_configured():
    """是否已配置华睿相机（CAMERA_CTI_PATH）。"""
    return bool(CAMERA_CTI_PATH)


class HuarayCamera:
    """华睿相机封装：连接、参数设置、抓帧（Bayer/灰度 -> BGR）。"""

    def __init__(self):
        self._ia = None
        self._h = None
        self.info = {}

    def connect(self):
        """连接并配置相机。失败抛 RuntimeError（明确错误，不静默）。"""
        if not CAMERA_CTI_PATH:
            raise RuntimeError(
                "未配置 CAMERA_CTI_PATH（华睿相机 GenICam 描述文件 .cti 的绝对路径），无法连接相机"
            )
        try:
            from harvesters.core import Harvester
        except ImportError as e:  # pragma: no cover - 依赖未安装
            raise RuntimeError(
                "未安装相机 SDK 依赖 harvesters/genicam，请参考 README「摄像头可选功能」安装；"
                f"（原始错误: {e}）"
            ) from None
        import os

        if not os.path.exists(CAMERA_CTI_PATH):
            raise RuntimeError(f"CAMERA_CTI_PATH 不存在: {CAMERA_CTI_PATH}")

        h = Harvester()
        h.add_file(CAMERA_CTI_PATH)
        h.update()
        if not h.device_info_list:
            h.reset()
            raise RuntimeError(f"未找到相机设备（已加载 {CAMERA_CTI_PATH}）")
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
        self.info = info
        log.info("相机已连接: %s", info)
        return ia

    def grab(self):
        """抓取一帧并转为 BGR。失败返回 None（由调用方决定重试策略）。"""
        ia = self._ia
        if ia is None:
            return None
        try:
            with ia.fetch_buffer(timeout=8) as buf:
                comp = buf.payload.components[0]
                w = int(comp.width)
                h = int(comp.height)
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
        except Exception as e:
            log.warning("fetch_buffer 异常: %s", e)
            return None

    def release(self):
        """释放相机与 Harvester。"""
        try:
            if self._ia is not None:
                self._ia.stop()
                self._ia.destroy()
        except Exception:
            pass
        if self._h is not None:
            try:
                self._h.reset()
            except Exception:
                pass
        self._ia = None
        self._h = None
