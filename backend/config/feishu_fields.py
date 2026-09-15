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

# 受控词表 / 组别 / 兵种 / 优先级：统一从队伍配置（team.yaml）读取，
# 未创建 team.yaml 时使用内置默认值（与 team.example.yaml 一致）。
# 其他队伍 clone 后修改 backend/config/team.yaml 即可，无需改动 Python 代码。
from config.team_config import (  # noqa: E402
    ALLOWED_GROUPS,
    ALLOWED_ROBOTS,
    GROUP_ALIASES,
    GROUP_PREFIXES,
    PRIORITY_MAP,
    ROBOT_ALIASES,
    TEAM_NAME,
)

__all__ = [
    "ALLOWED_GROUPS",
    "ALLOWED_ROBOTS",
    "FEISHU_FIELDS",
    "FEISHU_WORKTIME_FIELDS",
    "GROUP_ALIASES",
    "GROUP_PREFIXES",
    "PRIORITY_MAP",
    "ROBOT_ALIASES",
    "TEAM_NAME",
]
