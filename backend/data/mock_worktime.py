# -*- coding: utf-8 -*-
"""
Mock 打卡/工时数据：为每个成员生成最近约 35 天的上下班记录。
含少量异常记录（未打卡/负时间/超长）用于验证异常清洗逻辑。
"""
import random
from datetime import date, timedelta

from .mock_tasks import OWNERS

random.seed(20260901)


def build_mock_worktime(days=35):
    today = date.today()
    records = []
    for uid, name, grp in OWNERS:
        # 每个人有个体化的上班倾向（小时）与工作时长
        base_in = random.randint(9, 11)
        base_dur = random.randint(300, 480)
        for i in range(days):
            d = today - timedelta(days=i)
            wd = d.weekday()
            # 周末一半成员来实验室
            if wd >= 5 and random.random() < 0.5:
                continue
            # 偶发缺勤
            if random.random() < 0.08:
                continue
            in_hour = base_in + random.randint(-1, 1)
            in_min = random.randint(0, 59)
            dur = base_dur + random.randint(-40, 60)
            out_hour = (in_hour * 60 + in_min + dur) // 60
            out_min = (in_hour * 60 + in_min + dur) % 60

            cin = "%02d:%02d:%02d" % (in_hour, in_min, random.randint(0, 59))
            cout = "%02d:%02d:%02d" % (out_hour, out_min, random.randint(0, 59))

            # 异常注入（会触发 clean_record 丢弃，不进榜）
            roll = random.random()
            if roll < 0.03:
                cout = None  # 没下班打卡
            elif roll < 0.045:
                dur = -random.randint(1, 30)  # 负时间
            elif roll < 0.055:
                dur = 18 * 60 + 30  # 异常超长
            elif roll < 0.065:
                uid = None  # 空 user

            records.append({
                "userId": uid,
                "userName": name,
                "group": grp,
                "date": d.isoformat(),
                "checkInTime": cin,
                "checkOutTime": cout,
                "durationMinutes": dur if cout else None,
                "avatarUrl": None,
            })
    return records
