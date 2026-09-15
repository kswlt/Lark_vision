"""
队伍配置加载器（backend/config/team.yaml，可选）。

优先级：
1. 存在 backend/config/team.yaml        -> 以该文件为准（其他队伍改配置即可，不用改代码）
2. 不存在                              -> 使用内置默认值（与 team.example.yaml 一致），
                                         并在日志中给出"复制示例文件"的提示

仓库只提交 team.example.yaml；team.yaml 已被 .gitignore 忽略，不会入库。
注意：team.yaml 中的真实成员/组织信息请勿提交到 Git。
"""
import json
import logging
import os

try:
    import yaml as _yaml  # type: ignore

    HAS_YAML = True
except ImportError:  # pragma: no cover - 未安装 PyYAML 时回退 JSON/默认值
    HAS_YAML = False
    _yaml = None

logger = logging.getLogger("team_config")

_BASE = os.path.dirname(os.path.abspath(__file__))  # backend/config/
_TEAM_YAML = os.path.join(_BASE, "team.yaml")
_TEAM_JSON = os.path.join(_BASE, "team.json")

# 内置默认值（与 team.example.yaml 保持一致，保证未配置时系统照常运行）
DEFAULT_TEAM = {
    "name": "RoboMaster Team",
    "groups": ["算法", "电控", "机械", "运营"],
    "robots": ["重装", "步兵", "哨兵", "雷达", "飞镖"],
    "group_aliases": {
        "视觉": "算法",
        "视觉组": "算法",
        "Vision": "算法",
        "Visual": "算法",
        "vision": "算法",
        "视觉算法": "算法",
    },
    "robot_aliases": {
        "英雄": "重装",
        "hero": "重装",
        "Hero": "重装",
        "步兵1": "步兵",
        "步兵2": "步兵",
        "工程": "重装",
        "通用": None,
    },
    "group_prefixes": {"算法": "ALG", "电控": "ELE", "机械": "MEC", "运营": "OPR"},
    "priority_map": {
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
    },
}


def _deep_merge(default, override):
    """浅层合并：dict 逐键覆盖，list 整体替换（保证别名等 map 可整体覆盖）。"""
    out = dict(default)
    if not isinstance(override, dict):
        return out
    for k, v in override.items():
        out[k] = v
    return out


def load_team_config():
    """加载队伍配置，返回 dict（绝不在导入期抛错，异常时回退默认值并记录日志）。"""
    config = dict(DEFAULT_TEAM)

    path = None
    if os.path.exists(_TEAM_YAML):
        path = _TEAM_YAML
        if not HAS_YAML:
            logger.error(
                "存在 %s 但未安装 PyYAML，请执行 pip install pyyaml 后重启；当前使用内置默认队伍配置",
                _TEAM_YAML,
            )
            return config
        try:
            with open(_TEAM_YAML, encoding="utf-8") as f:
                raw = _yaml.safe_load(f) or {}
        except Exception as e:
            logger.error("读取 team.yaml 失败（%s），当前使用内置默认队伍配置", e)
            return config
    elif os.path.exists(_TEAM_JSON):
        path = _TEAM_JSON
        try:
            with open(_TEAM_JSON, encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            logger.error("读取 team.json 失败（%s），当前使用内置默认队伍配置", e)
            return config
    else:
        logger.warning(
            "未找到队伍配置文件（%s / %s），使用内置默认配置。"
            "如需自定义组别/兵种/别名，请复制 backend/config/team.example.yaml 为 team.yaml",
            _TEAM_YAML,
            _TEAM_JSON,
        )
        return config

    team = raw.get("team") if isinstance(raw, dict) else None
    if isinstance(team, dict):
        config = _deep_merge(config, team)
    else:
        logger.error("team 配置文件缺少 team 节点（%s），使用内置默认配置", path)
    return config


# 模块级单例（进程内只加载一次）
TEAM = load_team_config()

TEAM_NAME = TEAM.get("name", DEFAULT_TEAM["name"])
ALLOWED_GROUPS = tuple(TEAM.get("groups") or DEFAULT_TEAM["groups"])
ALLOWED_ROBOTS = tuple(TEAM.get("robots") or DEFAULT_TEAM["robots"])
GROUP_ALIASES = TEAM.get("group_aliases") or {}
ROBOT_ALIASES = TEAM.get("robot_aliases") or {}
GROUP_PREFIXES = TEAM.get("group_prefixes") or {}
PRIORITY_MAP = TEAM.get("priority_map") or {}
