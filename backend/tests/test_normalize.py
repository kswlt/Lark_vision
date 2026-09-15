"""飞书字段 normalization 测试：空字段、错误类型、受控词别名、日期格式。"""
from datetime import date, timedelta

from services.feishu.normalize import (
    normalize_date,
    normalize_field,
    normalize_group,
    normalize_priority,
    normalize_robot,
    normalize_task,
)


def test_normalize_field_variants():
    assert normalize_field(None) == ""
    assert normalize_field("  任务  ") == "任务"
    assert normalize_field(True) == ""
    assert normalize_field(123) == "123"
    assert normalize_field([{"text": "a"}, {"text": "b"}]) == "ab"
    assert normalize_field({"text": "x"}) == "x"
    assert normalize_field(["raw"]) == "raw"


def test_normalize_date_variants():
    assert normalize_date(None) is None
    assert normalize_date("") is None
    # 毫秒时间戳
    ts = int((date(2026, 9, 1).toordinal() - date(1970, 1, 1).toordinal()) * 86400 * 1000)
    assert normalize_date(ts) == "2026-09-01"
    # 字符串截取日期部分
    assert normalize_date("2026-09-01 12:30") == "2026-09-01"
    assert normalize_date("2026-09-01") == "2026-09-01"
    assert normalize_date("bad") is None


def test_normalize_aliases():
    # 受控词来自 team_config 默认值（视觉->算法；英雄->重装；工程->重装；通用->None）
    assert normalize_group("视觉") == "算法"
    assert normalize_group("算法") == "算法"
    assert normalize_group("") is None
    assert normalize_robot("英雄") == "重装"
    assert normalize_robot("工程") == "重装"
    assert normalize_robot("步兵1") == "步兵"
    assert normalize_robot("通用") is None
    assert normalize_priority("超紧急限时") == "super_urgent"
    assert normalize_priority("未知值") == "normal"


def _rec(**kw):
    fields = {
        "任务是什么（通俗详细写，严禁用ai）": "写测试用例",
        "编号": "T-01",
        "组别": "算法",
        "兵种": "哨兵",
        "重要紧急程度": "重要",
        "任务执行人": [{"id": "u1", "name": "张三", "avatar_url": "http://a"}],
        "预计完成日期": (date.today() + timedelta(days=3)).isoformat(),
        "是否延期": "✅正常",
        "最新进展记录（要求每天下班前更新）": "进行中",
        "最近更新时间": date.today().isoformat(),
        "进展": "开发中",
        "阻塞": False,
    }
    fields.update(kw)
    return {"record_id": "rec123", "fields": fields}


def test_normalize_task_full():
    t = normalize_task(_rec())
    assert t["id"] == "T-01"
    assert t["title"] == "写测试用例"
    assert t["group"] == "算法"
    assert t["robot"] == "哨兵"
    assert t["priority"] == "important"
    assert t["ownerId"] == "u1"
    assert t["ownerName"] == "张三"
    assert t["ownerAvatarUrl"] == "http://a"
    assert not t["overdue"]
    assert t["blocked"] is False
    assert t["latestUpdate"] == "进行中"
    assert t["latestUpdateTime"] == date.today().isoformat()


def test_normalize_task_empty_fields():
    """飞书字段缺失/为 None 时不能抛异常。"""
    t = normalize_task({"record_id": "rec1", "fields": {}})
    assert t["id"]  # 回退 record_id
    assert t["title"] == ""
    assert t["group"] is None
    assert t["robot"] is None
    assert t["priority"] == "normal"
    assert t["ownerId"] is None
    assert t["dueDate"] is None
    assert t["overdue"] is False


def test_normalize_task_wrong_field_types():
    """飞书字段类型变化（如日期是字符串、人员是字符串）时不能崩溃。"""
    t = normalize_task(_rec(预计完成日期="不是日期", 任务执行人="张三", 是否延期=True, 阻塞="yes"))
    assert t["dueDate"] is None
    assert t["ownerId"] is None
    assert t["overdue"] is True  # bool 标记
    assert t["blocked"] is False  # 非 bool -> False


def test_normalize_task_overdue_by_date():
    """无人工标记时，未完成且已过截止 -> overdue=True。"""
    past = (date.today() - timedelta(days=2)).isoformat()
    t = normalize_task(_rec(预计完成日期=past, 是否延期=""))
    assert t["overdue"] is True
    assert t["overdueDays"] == 2


def test_normalize_task_id_fallback():
    """纯数字编号不可作为唯一 id，应回退 record_id。"""
    t = normalize_task(_rec(编号="1"))
    assert t["id"] == "rec123"
