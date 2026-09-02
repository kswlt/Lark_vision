# RoboMaster Team Adam · 进度管理 Web 系统（RM CONTROL）

RoboMaster 战队 Adam 的进度管理控制台。运行在实验室希沃白板（Windows 7）上，
用于白板长期展示：谁在做什么、哪些任务延期、哪些重要紧急、哪些久未更新、
各技术组最近在干什么、比赛节点还剩多少时间、谁本周投入时间最多。

- **本机访问**：http://localhost:8080
- **局域网（希沃）**：http://192.168.53.117:8080

---

## 一、整体架构

```
浏览器（希沃/手机/笔记本）
      │
      ▼
   Waitress（Win7, TCP 8080）
      ├── /        → React 静态站点（frontend 构建产物 dist/）
      └── /api/*   → Flask API
                        │
                        ├── 飞书多维表格（任务数据，唯一 Source of Truth）
                        ├── 飞书通讯录（人员头像，12h 缓存）
                        └── 飞书工时/考勤（劳模榜，可选）
```

**为什么 Win7 用 React 静态 + Flask：**
- 希沃是比赛现场设备，稳定优先，不升级 Windows、不装 Docker/WSL2/现代 Node。
- React + Vite 的构建在开发电脑完成，生成 `dist/`，Win7 只需要 Python 3.8 即可运行网页服务。
- 生产服务用 **Waitress**（生产级 WSGI 服务器），不用 Flask 自带开发服务器。

---

## 二、目录结构

```
C:\RoboMasterDashboard
├─ backend\                 Flask 后端（在希沃上运行）
│  ├─ app.py                入口：/api/* + 静态站点 + Waitress 启动
│  ├─ requirements.txt      依赖（已锁定兼容 Win7 + Python 3.8）
│  ├─ config\feishu_fields.py   飞书字段映射、受控词表（视觉→算法、英雄→重装、通用→无）
│  ├─ data\mock_tasks.py    完整 Mock 任务数据（飞书未配置时使用）
│  ├─ data\mock_worktime.py Mock 工时数据（含异常样例）
│  ├─ services\
│  │  ├─ aggregates.py      Dashboard/Groups/Robots/Matrix/Leaderboard/People 聚合
│  │  ├─ sources.py         数据源选择（飞书/ Mock）+ 缓存
│  │  └─ feishu\            token / client / bitable / users / normalize / worktime
│  └─ .env                  飞书配置（不入 Git，自行填写）
├─ frontend\                React + TypeScript 源码（开发电脑，不上运行）
├─ dist\                    Vite production build（Flask 直接伺服）
├─ config\                  运行时配置（如 python.cmd，由 setup 生成）
├─ logs\                    app.log / error.log
├─ scripts\
│  ├─ setup_win7.bat        希沃一键安装：装依赖/防火墙/开机自启/启动
│  ├─ start.bat / stop.bat  启停
│  ├─ firewall_win7.bat     防火墙最小规则（只放行 TCP 8080）
│  ├─ build_bundle.ps1      生成本地部署包 zip（离线/U盘）
│  └─ deploy.ps1            远程自动部署（需 SSH）
└─ README.md
```

---

## 三、本地前端开发（开发电脑）

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 （/api 代理到 :5000）
npm run build        # 产出 frontend/dist
```

- 关键配置 `frontend/src/config/season.ts`：赛季节点日期（完整形态/联盟赛/区域赛），只改这里。
- 关键配置 `frontend/src/config/constants.ts`：组别/兵种/优先级。

## 四、后端开发/测试（开发电脑）

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python app.py --dev      # Flask dev server，http://localhost:5000
```

接口验证：
```bash
curl http://localhost:5000/api/health
curl http://localhost:5000/api/tasks
curl http://localhost:5000/api/dashboard
curl http://localhost:5000/api/groups
curl http://localhost:5000/api/robots
curl http://localhost:5000/api/worktime/leaderboard?range=week
curl http://localhost:5000/api/people
```

---

## 五、远程部署到希沃（Win7）

### 方式 A：远程自动部署（SSH 可用时）
```powershell
cd C:\Users\Admin\Desktop\飞书可视化\RoboMasterDashboard
.\scripts\deploy.ps1 -Host 192.168.53.117 -User Administrator -Password 你的密码
```
脚本会：前端 build → 上传 dist/backend/scripts → 远端装依赖 → 重启 → 健康检查。

### 方式 B：离线部署（U盘/共享文件夹，推荐当 SSH 不可用时）
```powershell
.\scripts\build_bundle.ps1          # 生成 C:\RoboMasterDashboard_deploy.zip
```
把 zip 拷贝到希沃，解压到 `C:\RoboMasterDashboard`，**右键管理员运行** `scripts\setup_win7.bat`。
setup 会自动：检测 Python → 装依赖 → 记录 Python 路径 → 防火墙 → 开机自启 → 启动。

---

## 六、Win7 Python 环境

- 要求 **Python 3.8.x**（3.8.10 官方安装包支持 Win7）。
- 安装时勾选 "Add python.exe to PATH"。
- 依赖已锁定（requirements.txt，均兼容 Python 3.8）：
  - Flask==2.3.3
  - waitress==3.0.0
  - requests==2.31.0
  - python-dotenv==1.0.1

## 七、启动后端（希沃生产）

```bat
C:\RoboMasterDashboard\scripts\start.bat
```
内部执行：`python backend\app.py` → **Waitress 监听 0.0.0.0:8080**，同时伺服 `dist/` 与 `/api/*`。

---

## 八、飞书配置

1. 开放平台创建企业自建应用，开启权限：
   - 多维表格：查看、评论、编辑和管理多维表格
   - 通讯录：获取用户基本信息 / 通讯录只读
   - （劳模榜若用考勤）考勤：导出打卡数据
2. 把应用加入多维表格协作者（应用本身需有文档权限）。
3. 填写 `backend\.env`（由 `.env.example` 复制）：
   ```
   FEISHU_APP_ID=
   FEISHU_APP_SECRET=
   FEISHU_APP_TOKEN=
   FEISHU_TABLE_ID=
   FEISHU_WORKTIME_APP_TOKEN=
   FEISHU_WORKTIME_TABLE_ID=
   FEISHU_WORKTIME_SOURCE=mock   # bitable | attendance | mock
   PORT=8080
   HOST=0.0.0.0
   ```
4. 重启服务。首页左下角 / 右上角会从 `MOCK DATA` 变为 `FEISHU LIVE`。

> `.env` 绝不允许提交到 Git；App Secret 只存在于希沃的 `backend\.env`。

---

## 九、任务表字段（飞书多维表格）

字段名在 `backend/config/feishu_fields.py` 集中配置：

| 前端字段 | 飞书字段名 | 类型 |
|---|---|---|
| 编号 | 编号 | 文本 |
| 任务 | 任务是什么（通俗详细写，严禁用ai） | 文本 |
| 是否延期 | 是否延期 | 勾选 |
| 实际完成日期 | 实际完成日期 | 日期 |
| 最新进展 | 最新进展记录（要求每天更新） | 文本 |
| 重要紧急程度 | 重要紧急程度 | 单选 |
| 组别 | 组别 | 单选 |
| 兵种 | 兵种 | 单选 |
| 负责人 | 负责人 | 人员 |
| 计划完成日期 | 计划完成日期 | 日期 |
| 依赖任务 | 依赖任务 | 文本 |
| 阻塞 | 阻塞 | 勾选 |
| （可选）最近更新时间 | 最近更新时间 | 日期 |
| （可选）进展历史 | 进展历史 | 文本 |

**受控词（系统自动清洗，界面绝不出现）：**
- `视觉 / 视觉组 / Vision / Visual` → 一律显示为 **算法**
- `英雄 / hero` → 一律显示为 **重装**
- `通用` 兵种 → 视为 **未指定**（不伪造"通用"兵种）

组别固定：算法 / 电控 / 机械 / 运营。兵种：重装 / 步兵1 / 步兵2 / 哨兵 / 工程 / 雷达 / 飞镖。

---

## 十、人员头像

- 打卡记录与任务负责人通过 `user_id / open_id` 关联，再调用飞书通讯录 API 取姓名与头像。
- 后端内存缓存，**TTL 12 小时**，避免每次刷新都请求 30 个头像。
- 头像加载失败时前端显示**姓名首字** fallback，不使用随机互联网头像。

## 十一、工时 / 劳模榜

- 数据来源由 `FEISHU_WORKTIME_SOURCE` 决定：
  - `bitable`：从 `FEISHU_WORKTIME_*` 多维表格读上下班打卡记录（推荐）。
  - `attendance`：调用飞书考勤 `user_tasks/query`（需"导出打卡数据"权限）。
  - `mock`：演示数据（飞书未接入时）。
- 异常记录（没下班打卡 / 重复打卡 / 负时间 / 单日 >16h / 跨天 / 空 user）**一律不进榜**，只写日志。
- 按真实打卡工时 `sum(durationMinutes)` 排序，不按任务数量。

---

## 十二、防火墙

只放行 TCP 8080，**不关闭整个防火墙**：
```bat
C:\RoboMasterDashboard\scripts\firewall_win7.bat
```
或手动（Win7 兼容）：
```
netsh advfirewall firewall add rule name="RoboMaster Dashboard" dir=in action=allow protocol=TCP localport=8080
```

## 十三、开机自启

```bat
schtasks /create /tn "RoboMasterDashboard" /tr "C:\RoboMasterDashboard\scripts\start.bat" /sc onstart /ru SYSTEM /rl highest /f
```
开机即启动（SYSTEM 身份，无需密码）。停止任务：`schtasks /end /tn RoboMasterDashboard`。

## 十四、日志

- `logs\app.log`：运行与访问日志。
- `logs\error.log`：错误日志（ERROR 以上）。
- 日志**不会**输出 `FEISHU_APP_SECRET`、`tenant_access_token`、SSH 密码。

---

## 十五、更新程序

1. 改前端 → `cd frontend && npm run build`。
2. 方式 A：`.\scripts\deploy.ps1 ...`（SSH）。
   方式 B：`.\scripts\build_bundle.ps1` 生成 zip，U盘拷贝覆盖 `C:\RoboMasterDashboard`（保留 `backend\.env` 与 `logs\`），运行 `setup_win7.bat` 或直接重启服务。
3. 验证：`http://192.168.53.117:8080/api/health` 返回 200。

## 十六、故障处理

| 现象 | 排查 |
|---|---|
| 网页打不开 | 服务是否在跑（任务管理器找 python）；日志 `logs\app.log`；端口 `netstat -ano \| findstr :8080` |
| 本机通、局域网不通 | 防火墙规则是否添加（firewall_win7.bat）；是否为同一局域网 |
| 显示 MOCK DATA | `backend\.env` 未填或未生效；检查 `FEISHU_APP_ID/SECRET/TOKEN/TABLE_ID` |
| 任务为 0 条 | 飞书应用是否被加为多维表格协作者；字段名是否与 `feishu_fields.py` 一致 |
| 劳模榜为空 | `FEISHU_WORKTIME_SOURCE` 未配置；或考勤/工时表无数据（不会伪造） |
| 头像不显示 | 应用无通讯录权限，前端会显示姓名首字（正常降级） |
| 服务 500 | 看 `logs\error.log`（不含密钥） |
| 端口 8080 被占 | 改 `backend\.env` 的 PORT 并同步防火墙规则 |

---

## 安全说明

- 只监听局域网 `0.0.0.0:8080`，不开放公网。
- `FEISHU_APP_SECRET` 只存在希沃 `backend\.env`，不进前端 JS，不入 Git。
- 日志不含任何密钥 / token / 密码。
