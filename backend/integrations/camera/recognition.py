"""
人脸识别逻辑：模型加载（SFace / LBPH fallback）、人脸检测（YuNet）、
识别（SFace 深度特征 / LBPH）、多帧确认、身份缓存、打卡读写、中文标签绘制。
"""
import datetime
import json
import os
import time

import cv2
import numpy as np

from .base import (
    CONF_THRESHOLD,
    DATA_DIR,
    DETECTION_MAX_WIDTH,
    FACE_SIZE,
    IDENTITY_CACHE_TTL,
    MIN_DETECT_SCORE,
    MODEL,
    MULTI_FRAME_CONFIRM,
    NAMES,
    SFACE_MODEL,
    log,
)

# ---------------- 中文标签渲染（cv2.putText 不支持中文，用 PIL） ----------------
_FONT = None


def _get_font(size=18):
    global _FONT
    if _FONT is None:
        try:
            from PIL import ImageFont
            for f in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttc",
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
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
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


# ---------------- 模型加载 ----------------
def load_recognizer():
    """加载 LBPH 识别器（fallback）。"""
    try:
        if not os.path.exists(MODEL) or not os.path.exists(NAMES):
            return None, []
        rec = cv2.face.LBPHFaceRecognizer_create()
        rec.read(MODEL)
        with open(NAMES, encoding="utf-8") as f:
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


# ---------------- 打卡记录读写 ----------------
def read_checkin():
    today = datetime.date.today().strftime("%Y%m%d")
    path = os.path.join(DATA_DIR, f"face_checkin_{today}.json")
    try:
        with open(path, encoding="utf-8") as f:
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


# ---------------- 人脸检测（YuNet） ----------------
def detect_faces(img, detector):
    """仅检测人脸，返回 YuNet 原始输出列表（含关键点，供 SFace alignCrop 使用）。"""
    h, w = img.shape[:2]
    scale = min(1.0, float(DETECTION_MAX_WIDTH) / float(max(w, 1)))
    dw = max(1, int(w * scale))
    dh = max(1, int(h * scale))
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
        f2[0] *= inv
        f2[1] *= inv
        f2[2] *= inv
        f2[3] *= inv
        # 关键点也映射
        for i in range(4, 14):
            f2[i] *= inv
        result.append(f2)
    return result, inv


# ---------------- SFace 识别主流程 ----------------
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
            top5_str = ", ".join(f"{n}:{s:.3f}" for n, s in top5[:3])
            margin_val = top5[0][1] - top5[1][1] if len(top5) > 1 else 0
            log.info("识别 %s | bbox=%dx%d | best=%s(%.3f) margin=%.3f | Top3: %s | %s",
                     "PASS" if recognized else "REJECT",
                     w, h, name if recognized else top5[0][0],
                     score, margin_val, top5_str,
                     "已确认" if recognized else "未达阈值/margin")
        results.append((name if recognized else "不在数据库中", score, box, recognized))
    return results


# ---------------- LBPH 识别（fallback） ----------------
def detect_and_recognize_lbph(img, detector, rec, names, threshold=CONF_THRESHOLD):
    """LBPH 识别（fallback）。"""
    results = []
    h, w = img.shape[:2]
    scale = min(1.0, float(DETECTION_MAX_WIDTH) / float(max(w, 1)))
    dw = max(1, int(w * scale))
    dh = max(1, int(h * scale))
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
        ox = max(0, int(x * inv))
        oy = max(0, int(y * inv))
        ow = min(w - ox, int(fw * inv))
        oh = min(h - oy, int(fh * inv))
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
