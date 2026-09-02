# -*- coding: utf-8 -*-
"""
完整 Mock 任务数据（飞书未配置时使用）。
- 组别固定：算法/电控/机械/运营
- 兵种固定：重装/步兵1/步兵2/哨兵/工程/雷达/飞镖；运营任务可 robot=None
- 不含"英雄"、"通用"、"视觉"
- 日期相对"今天"生成，保证 Dashboard 任何时候打开都有真实感
"""
from datetime import date, timedelta

# (userId, name, group)
OWNERS = [
    ("u001", "林越", "算法"),
    ("u002", "王一凡", "算法"),
    ("u003", "陈宇", "算法"),
    ("u004", "赵天", "电控"),
    ("u005", "孙浩", "电控"),
    ("u006", "周洋", "电控"),
    ("u007", "吴凯", "机械"),
    ("u008", "郑磊", "机械"),
    ("u009", "钱进", "机械"),
    ("u010", "何琪", "运营"),
    ("u011", "沈月", "运营"),
    ("u012", "韩雪", "运营"),
    ("u013", "高远", "算法"),
    ("u014", "唐明", "电控"),
]

OWNER_BY_ID = {uid: (name, grp) for uid, name, grp in OWNERS}

# 字段说明：
#   (task_id, group, robot, title, owner_id, priority, due_offset, blocked, update_days, update_text, done)
#   due_offset: 相对今天的天数（负=已过截止，正=未来）
#   update_days: 距离最近一次更新多少天
#   done: True 表示已完成（有实际完成日期）
TASKS_SPEC = [
    # ---- 算法 ----
    ("ALG-001", "算法", "哨兵", "迁移导航从 x86 架构到 ARM 架构实体机部署，为下一阶段哨兵导航做技术预研", "u003", "important_urgent", -4, False, 0, "ARM 环境已完成基础部署，正在处理导航依赖和底盘硬件接口适配", False),
    ("ALG-002", "算法", "重装", "重装自瞄高速目标跟踪，解决远距离小目标跳变问题", "u001", "important_urgent", 2, False, 1, "重新训练跟踪网络，遮挡场景 mAP 提升到 0.82", False),
    ("ALG-003", "算法", "哨兵", "哨兵定位漂移修正，优化里程计与感知融合权重", "u013", "important", -1, False, 2, "里程计标定完成，漂移量从 3% 降到 1.5%", False),
    ("ALG-004", "算法", "雷达", "雷达多目标跟踪与反小陀螺预判算法", "u002", "important", 5, False, 0, "小陀螺周期辨识已接入，预判命中率 78%", False),
    ("ALG-005", "算法", "步兵1", "步兵弹道模型标定，摩擦轮一致性修正", "u013", "important", 3, False, 4, "样本采集完成，待跑回归", False),
    ("ALG-006", "算法", "重装", "重装装甲板识别与反遮挡策略", "u001", "normal", 9, False, 3, "新增装甲板模板，识别帧率 60fps", False),
    ("ALG-007", "算法", "哨兵", "哨兵能量机关识别与击打决策", "u002", "important_urgent", 7, True, 1, "能量机关流程阻塞，等待雷达提供目标优先级数据", False),
    ("ALG-008", "算法", "雷达", "雷达目标丢失重捕与轨迹外推", "u003", "important", -2, False, 1, "重捕逻辑完成，单目标丢失后 0.3s 内恢复", False),
    ("ALG-009", "算法", "步兵2", "步兵2 自瞄抗遮挡与弹道补偿", "u013", "important", 6, False, 2, "抗遮挡模块已合并，待整车上电实测", False),
    ("ALG-010", "算法", "重装", "重装云台坐标系外参标定工具链", "u001", "normal", 12, False, 5, "标定脚本完成，待现场复测", False),
    ("ALG-011", "算法", "飞镖", "飞镖落点预测模型", "u002", "normal", 14, False, 3, "初步模型已训练，误差 ±25cm", False),
    ("ALG-012", "算法", "哨兵", "哨兵场地语义建图与导航避障", "u003", "important_urgent", -3, False, 0, "建图节点已跑通，避障参数还在调", False),

    # ---- 电控 ----
    ("ELE-001", "电控", "重装", "重装 CAN 全链路验证，排查丢包问题", "u004", "important_urgent", -2, True, 0, "CAN 总线负载过高导致丢包，正在评估提高波特率方案", False),
    ("ELE-002", "电控", "步兵1", "步兵1 底盘控制与运动学调试", "u005", "important", 4, False, 1, "底盘运动学已通，转向手感待调", False),
    ("ELE-003", "电控", "步兵2", "步兵2 腿控调参与功率控制", "u006", "important", -1, False, 2, "腿控参数第二版，起步抖动已缓解", False),
    ("ELE-004", "电控", "工程", "工程机械臂控制与夹取动作", "u014", "important_urgent", 1, False, 0, "机械臂规划已通，夹爪开合测试中", False),
    ("ELE-005", "电控", "哨兵", "哨兵功率控制与云台随动", "u005", "important", 6, False, 3, "功率闭环已接入，待联调", False),
    ("ELE-006", "电控", "重装", "重装双枪管发射与连发控制", "u004", "important_urgent", -5, False, 1, "双枪管切换逻辑完成，弹道一致性待测", False),
    ("ELE-007", "电控", "步兵2", "步兵2 整车上电与系统自检", "u006", "important", -4, False, 0, "整车上电完成，自检通过，进入联调", False),
    ("ELE-008", "电控", "雷达", "雷达伺服跟踪控制", "u014", "normal", 10, False, 4, "伺服 PID 已调，跟踪稳定", False),
    ("ELE-009", "电控", "工程", "工程麦克纳姆底盘控制", "u005", "important", 8, False, 2, "底盘四向运动测试通过", False),
    ("ELE-010", "电控", "飞镖", "飞镖发射控制与校准", "u006", "normal", 15, False, 6, "发射控制板焊接完成，待上电", False),
    ("ELE-011", "电控", "哨兵", "哨兵底盘差速与自主巡逻", "u004", "important", -3, False, 2, "差速模型已实现，巡逻逻辑待优化", False),
    ("ELE-012", "电控", "步兵1", "步兵1 超级电容与能量管理", "u014", "normal", 11, False, 7, "电容充放电测试完成，待集成", False),
    ("ELE-013", "电控", "重装", "重装云台电机控制与回中", "u006", "important_urgent", -2, True, 1, "云台电机异常发热，阻塞排故中", False),
    ("ELE-014", "电控", "工程", "工程气动夹爪电磁阀控制", "u005", "important", 5, False, 1, "气路已通，电磁阀响应正常", False),

    # ---- 机械 ----
    ("MEC-001", "机械", "重装", "重装云台减重设计，目标减重 20%", "u007", "important", 3, False, 2, "新方案已出图，碳板件待切割", False),
    ("MEC-002", "机械", "重装", "重装发射机构优化与供弹可靠性", "u008", "important_urgent", -3, True, 0, "供弹卡弹问题阻塞，需重新设计拨盘", False),
    ("MEC-003", "机械", "步兵1", "步兵1 防撞结构与悬挂", "u009", "important", 7, False, 1, "防撞支架已装车，减震待验证", False),
    ("MEC-004", "机械", "工程", "工程夹取机构设计与装配", "u007", "important_urgent", 2, False, 0, "夹爪装配完成，正在标定开合行程", False),
    ("MEC-005", "机械", "飞镖", "飞镖机构加工与减阻外壳", "u008", "important", 9, False, 3, "外壳 3D 打印完成，正在打磨", False),
    ("MEC-006", "机械", "哨兵", "哨兵悬挂系统与云台护甲", "u009", "normal", 13, False, 5, "悬挂方案确定，零件下单中", False),
    ("MEC-007", "机械", "步兵2", "步兵2 摩擦轮与拨盘调试", "u007", "important", -1, False, 2, "摩擦轮打滑率偏高，更换胶圈测试", False),
    ("MEC-008", "机械", "重装", "重装碳纤维板切割与轻量化", "u008", "normal", 16, False, 4, "板材已到货，安排机加工", False),
    ("MEC-009", "机械", "雷达", "雷达支架与旋转机构", "u009", "normal", 18, False, 8, "支架安装完成", False),
    ("MEC-010", "机械", "工程", "工程抬升机构设计与限位", "u007", "important", 4, False, 1, "抬升机构装配完成，限位开关待接", False),
    ("MEC-011", "机械", "步兵1", "步兵1 拨盘与弹仓设计", "u008", "normal", 12, False, 6, "弹仓图纸完成，待加工", False),
    ("MEC-012", "机械", "重装", "重装底盘护板与整机装配", "u009", "important", -2, False, 1, "护板装好，等待电控上电联调", False),

    # ---- 运营 ----
    ("OPS-001", "运营", None, "联盟赛报名与参赛资料整理", "u010", "important_urgent", 6, False, 0, "报名表已提交，等待组委会审核", False),
    ("OPS-002", "运营", None, "新队员纳新与培训材料", "u011", "important", 10, False, 2, "纳新推文已发布，报名 12 人", False),
    ("OPS-003", "运营", None, "物资采购与物料清单核对", "u012", "important", 4, False, 1, "第三批物料已到，正在清点", False),
    ("OPS-004", "运营", None, "出征资料与随队物资准备", "u010", "important_urgent", -2, False, 1, "随队物资清单已出，待采购补齐", False),
    ("OPS-005", "运营", None, "队伍宣传视频与赛场物料", "u011", "normal", 15, False, 3, "宣传片脚本完成，待拍摄", False),
    ("OPS-006", "运营", None, "赞助商对接与赞助权益落地", "u012", "important", 8, False, 2, "赞助合同已签，等待物料制作", False),
    ("OPS-007", "运营", None, "场地协调与训练排期", "u010", "normal", 5, False, 4, "本周场地已排好", False),
    ("OPS-008", "运营", None, "队服与周边定制", "u011", "normal", 20, False, 9, "样衣确认中", False),

    # ---- 补充混排 ----
    ("ALG-013", "算法", "重装", "重装反小陀螺目标模型训练", "u002", "important", -4, False, 1, "负样本扩充完成，模型迭代中", False),
    ("ELE-015", "电控", "步兵2", "步兵2 遥控与图传链路联调", "u006", "normal", 7, False, 3, "图传延时 80ms，待优化", False),
    ("MEC-013", "机械", "工程", "工程机械臂末端工具换装", "u007", "normal", 19, False, 7, "末端快拆方案确定", False),
    ("OPS-009", "运营", None, "参赛队名与队徽物料", "u011", "normal", 11, False, 6, "队徽已定稿", False),
    ("ALG-014", "算法", "雷达", "雷达与自瞄数据回传协议", "u003", "important", 2, False, 1, "协议 v2 已联调通过", False),
    ("ELE-016", "电控", "重装", "重装整车上电与整车线束", "u004", "important_urgent", -6, True, 0, "线束整理阻塞，接口定义未最终确定", False),
    ("MEC-014", "机械", "哨兵", "哨兵云台护甲轻量化", "u009", "normal", 22, False, 5, "护甲方案迭代中", False),
]

DONE_SPEC = [
    ("ALG-015", "算法", "雷达", "雷达标定工具链搭建", "u002", "normal", -10, False, 10, "标定工具链已交付", True),
    ("ELE-017", "电控", "步兵1", "步兵1 底盘线束整理", "u005", "normal", -8, False, 9, "线束整理完成，走线规范", True),
    ("MEC-015", "机械", "重装", "重装云台轴承更换", "u008", "normal", -9, False, 8, "轴承更换完成，转动顺滑", True),
    ("OPS-010", "运营", None, "社团注册与年审材料", "u012", "normal", -7, False, 8, "年审材料已提交通过", True),
    ("ALG-016", "算法", "步兵2", "步兵2 弹道初速标定", "u013", "normal", -6, False, 7, "初速标定完成", True),
    ("ELE-018", "电控", "哨兵", "哨兵供电系统测试", "u005", "normal", -5, False, 6, "供电测试通过", True),
    ("MEC-016", "机械", "步兵1", "步兵1 摩擦轮装配", "u007", "normal", -4, False, 5, "摩擦轮装配完成", True),
    ("OPS-011", "运营", None, "实验室 5S 整理", "u010", "normal", -3, False, 4, "5S 检查通过", True),
]


def build_mock_tasks():
    today = date.today()
    tasks = []

    def make(tid, group, robot, title, owner_id, priority, due_offset, blocked, update_days, update_text, done):
        due = today + timedelta(days=due_offset)
        actual = None
        if done:
            actual = (today + timedelta(days=due_offset - 1)).isoformat()
        upd_time = (today - timedelta(days=update_days)).isoformat()
        name, grp = OWNER_BY_ID[owner_id]
        overdue = (due_offset < 0) and not done
        return {
            "id": tid,
            "title": title,
            "group": group,
            "robot": robot,
            "ownerId": owner_id,
            "ownerName": name,
            "ownerAvatarUrl": None,
            "dueDate": due.isoformat(),
            "actualFinishDate": actual,
            "overdue": overdue,
            "overdueDays": abs(due_offset) if (overdue and due_offset < 0) else (0 if overdue else None),
            "priority": priority,
            "latestUpdate": update_text,
            "latestUpdateTime": upd_time,
            "daysSinceUpdate": update_days,
            "dependency": None,
            "blocked": blocked,
            "history": [{"time": upd_time, "text": update_text}],
        }

    for spec in TASKS_SPEC + DONE_SPEC:
        tasks.append(make(*spec))

    # 少量依赖关系，让 Drawer 更真实
    dep_map = {
        "ELE-001": "ALG-002",
        "ALG-007": "ALG-004",
        "MEC-002": "MEC-001",
        "ELE-013": "MEC-001",
        "ELE-016": "MEC-012",
        "ALG-001": "ELE-002",
    }
    for t in tasks:
        if t["id"] in dep_map:
            t["dependency"] = dep_map[t["id"]]

    return tasks
