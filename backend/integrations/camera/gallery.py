"""
SFace 深度人脸 Gallery 向量库：每人一个或多个 128 维特征向量。
支持从 photos/ 目录构建，缓存到 .npz 文件，自动检测新照片重建。
"""
import glob
import os
import re
import threading
import time

import cv2
import numpy as np

from .base import (
    GALLERY_FILE,
    GALLERY_REBUILD_INTERVAL,
    PHOTO_DIR,
    SFACE_COSINE_THRESHOLD,
    SFACE_MATCH_MARGIN,
    log,
)

logger = log


class FaceGallery:
    """SFace 深度特征向量库：每人一个或多个 128 维特征向量。
    支持从 photos/ 目录构建，缓存到 .npz 文件，自动检测新照片重建。"""

    def __init__(self):
        self.names = []           # 人名列表
        self.vectors = []         # 对应特征向量列表（每人可能多个）
        self.name_to_idx = {}     # 人名 -> vectors 中的起始索引
        self._lock = threading.Lock()
        self._last_mtime = 0.0
        self._last_rebuild = 0.0

    def _photo_mtime(self):
        """获取 photos 目录最新修改时间（用于检测新照片）。"""
        try:
            if not os.path.isdir(PHOTO_DIR):
                return 0.0
            latest = 0.0
            for f in glob.glob(os.path.join(PHOTO_DIR, "*.jpg")) + glob.glob(os.path.join(PHOTO_DIR, "*.png")):
                try:
                    m = os.path.getmtime(f)
                    latest = max(latest, m)
                except Exception:
                    pass
            return latest
        except Exception:
            return 0.0

    def _person_of(self, filename):
        """从文件名提取人名：姓名.jpg / 姓名_1.jpg / 姓名-2.jpg -> 姓名。"""
        base = os.path.splitext(os.path.basename(filename))[0]
        m = re.match(r'^(.*?)[_\-\s]?(\d+)$', base)
        return m.group(1) if m else base

    def build(self, sface, detector, force=False):
        """从 photos/ 目录构建 Gallery。force=True 强制重建。"""
        with self._lock:
            now = time.time()
            mtime = self._photo_mtime()
            # 检查是否需要重建
            if not force and self.vectors and (now - self._last_rebuild < GALLERY_REBUILD_INTERVAL) and mtime <= self._last_mtime:
                return len(self.names)
            # 尝试从缓存加载
            if not force and os.path.exists(GALLERY_FILE) and os.path.getmtime(GALLERY_FILE) >= mtime:
                try:
                    data = np.load(GALLERY_FILE, allow_pickle=True)
                    self.names = list(data["names"])
                    # 强制转换为 float32（旧缓存可能是 object 类型，会导致 sface.match 报错）
                    self.vectors = [np.ascontiguousarray(v, dtype=np.float32).flatten() for v in data["vectors"]]
                    self.name_to_idx = {}
                    for i, n in enumerate(self.names):
                        if n not in self.name_to_idx:
                            self.name_to_idx[n] = i
                    self._last_mtime = mtime
                    self._last_rebuild = now
                    log.info("Gallery 从缓存加载: %d 人, %d 特征", len(set(self.names)), len(self.vectors))
                    return len(set(self.names))
                except Exception as e:
                    log.warning("Gallery 缓存加载失败，重新构建: %s", e)

            # 从 photos 目录构建
            files = sorted(glob.glob(os.path.join(PHOTO_DIR, "*.jpg")) +
                           glob.glob(os.path.join(PHOTO_DIR, "*.png")))
            if not files:
                log.warning("photos 目录无照片，Gallery 为空")
                return 0

            name_list = []
            for f in files:
                p = self._person_of(f)
                if p not in name_list:
                    name_list.append(p)

            vectors = []
            names = []
            no_face = []
            for f in files:
                name = self._person_of(f)
                try:
                    img = cv2.imdecode(np.fromfile(f, dtype=np.uint8), cv2.IMREAD_COLOR)
                except Exception:
                    continue
                if img is None:
                    continue
                h, w = img.shape[:2]
                if max(h, w) > 1400:
                    s = 1400.0 / max(h, w)
                    img = cv2.resize(img, (int(w * s), int(h * s)))
                detector.setInputSize((img.shape[1], img.shape[0]))
                ret, faces = detector.detect(img)
                if faces is None or len(faces) == 0:
                    no_face.append(os.path.basename(f))
                    continue
                # 取最大的脸
                face_raw = max(faces, key=lambda r: r[2] * r[3])
                try:
                    aligned = sface.alignCrop(img, face_raw)
                    feat = sface.feature(aligned)
                    vectors.append(feat.flatten())
                    names.append(name)
                except Exception as e:
                    log.warning("提取特征失败 %s: %s", os.path.basename(f), e)
                    continue

            self.names = names
            self.vectors = vectors
            self.name_to_idx = {}
            for i, n in enumerate(names):
                if n not in self.name_to_idx:
                    self.name_to_idx[n] = i
            self._last_mtime = mtime
            self._last_rebuild = now

            # 保存缓存（vectors 必须是 float32，否则 sface.match 报 object type 错误）
            try:
                np.savez(GALLERY_FILE,
                         names=np.array(names, dtype=object),
                         vectors=np.array(vectors, dtype=np.float32))
            except Exception as e:
                log.warning("Gallery 缓存保存失败: %s", e)

            if no_face:
                log.warning("以下照片未检测到人脸(已跳过): %s", ", ".join(no_face[:10]))
            log.info("Gallery 构建完成: %d 人, %d 特征向量", len(set(names)), len(vectors))
            return len(set(names))

    def match(self, feat, sface):
        """匹配特征向量，返回 (best_name, best_score, recognized, top5_list)。
        使用 cosine 相似度，必须同时满足：
          1. best_score >= SFACE_COSINE_THRESHOLD
          2. best_score - second_score >= SFACE_MATCH_MARGIN
        否则返回 recognized=False（宁可拒识，不要把A认成B）。
        top5_list = [(name, score), ...] 按 score 降序。"""
        with self._lock:
            if not self.vectors:
                return None, 0.0, False, []
            # 对每个人取最大相似度
            person_scores = {}
            match_errors = 0
            feat_f32 = np.ascontiguousarray(feat, dtype=np.float32).reshape(1, -1)
            for i, v in enumerate(self.vectors):
                try:
                    v_f32 = np.ascontiguousarray(v, dtype=np.float32).reshape(1, -1)
                    score = float(sface.match(feat_f32, v_f32, cv2.FaceRecognizerSF_FR_COSINE))
                except Exception as _e:
                    match_errors += 1
                    if match_errors <= 3:
                        log.warning("sface.match error i=%d: %s | feat_shape=%s vec_shape=%s",
                                    i, _e, getattr(feat, 'shape', None), getattr(v, 'shape', None))
                    continue
                name = self.names[i]
                if name not in person_scores or score > person_scores[name]:
                    person_scores[name] = score
            if not person_scores:
                log.warning("gallery.match: all %d vectors failed, feat_shape=%s",
                            len(self.vectors), getattr(feat, 'shape', None))
                return None, 0.0, False, []
            # Top-5 排序
            sorted_persons = sorted(person_scores.items(), key=lambda x: x[1], reverse=True)
            top5 = [(n, round(s, 3)) for n, s in sorted_persons[:5]]
            best_name, best_score = sorted_persons[0]
            second_score = sorted_persons[1][1] if len(sorted_persons) > 1 else 0.0
            margin = best_score - second_score
            # 双重条件：阈值 + margin
            recognized = (best_name is not None
                          and best_score >= SFACE_COSINE_THRESHOLD
                          and margin >= SFACE_MATCH_MARGIN)
            return best_name, round(best_score, 3), recognized, top5
