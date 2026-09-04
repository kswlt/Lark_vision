# -*- coding: utf-8 -*-
"""
飞书多维表格字段集中配置。
业务代码不得到处写死"任务是什么（通俗详细写，严禁用ai）"等中文字段名。
所有字段名在此维护，改动只需改这里。
"""

FEISHU_FIELDS = {
    "id": "编号",
    "title": "任务是什么（通俗详细写，严禁用ai）",
    "overdue": "是否延期",
    "actual_finish_date": "实际完成日期",
    "latest_update": "最新进展记录（要求每天下班前更新）",
    "priority": "重要紧急程度",
    "group": "组别",
    "robot": "兵种",
    "owner": "任务执行人",
    "due_date": "预计完成日期",
    "dependency": "依赖任务",
    "blocked": "阻塞",
    "status": "进展",
    # 可选字段：若表格中存在"最近更新时间"字段（日期/时间类型），用于计算"久未更新"
    "latest_update_time": "最近更新时间",
    # 可选字段：若表格中存在"进展历史"字段（文本），用于 Task Drawer 历史信息
    "history": "进展历史",
}

# 打卡/工时表字段（来源 B：飞书多维表格记录工作时间）
FEISHU_WORKTIME_FIELDS = {
    "user": "打卡人员",
    "date": "日期",
    "check_in": "上班打卡",
    "check_out": "下班打卡",
    "duration": "工作时长(分钟)",
}

# 受控词表：飞书里历史遗留叫法统一映射到正式名称
GROUP_ALIASES = {
    "视觉": "算法",
    "视觉组": "算法",
    "Vision": "算法",
    "Visual": "算法",
    "vision": "算法",
    "视觉算法": "算法",
}

ROBOT_ALIASES = {
    "英雄": "重装",
    "hero": "重装",
    "Hero": "重装",
    # "通用" 兵种被禁止：任何情况下都不应落到"通用"
    "通用": None,
}

ALLOWED_GROUPS = ("算法", "电控", "机械", "运营")
ALLOWED_ROBOTS = ("重装", "步兵1", "步兵2", "哨兵", "工程", "雷达", "飞镖")

PRIORITY_MAP = {
    "超紧急限时": "super_urgent",
    "重要紧急": "important_urgent",
    "紧急": "important_urgent",
    "重要": "important",
    "重要不紧急": "important",
    "紧急不重要": "important",
    "一般": "normal",
    "普通": "normal",
    "不紧急不重要": "normal",
    "低": "normal",
}
