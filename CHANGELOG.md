# Changelog

本项目的所有重要变更都会记录在此文件中。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [1.0.0] - 2026-09

首个开源版本。RM CONTROL（Adam RoboMaster Team）正式对外发布，其他 RM 战队 clone 后改配置即可运行。

### 跨平台部署（Windows + Ubuntu）
- 新增 `scripts/setup.ps1` / `setup.sh`、`start.ps1` / `start.sh`、`stop.ps1` / `stop.sh`，自动定位项目根、使用 `.venv`、PID 精确管理。
- 前端 build 输出统一到仓库根 `dist/`（`vite.config.ts` `outDir: '../dist'`），不再需要手工 copy。
- 全部路径使用相对路径 + `os.path.join`，无 `C:\Users\...` / `/home/...` 硬编码。
- Linux 长期运行示例：`examples/deployment/systemd/rm-control.service.example`。
- CI matrix：Ubuntu + Windows × Python 3.11/3.12，并在每个平台实际启动后端 curl `/api/health` 做 smoke test。

### 开源工程化改造
- 开源文件：LICENSE（MIT）、CONTRIBUTING.md、SECURITY.md、CHANGELOG.md。
- GitHub Actions CI：前端 lint/test/build + 后端 ruff/pytest/compileall/smoke，不依赖真实飞书/相机/Secret。
- 后端测试套件 `backend/tests/`（41 个用例：字段归一化、聚合、数据源模式、缓存回退、health、admin 鉴权、Feishu client 重试）。
- 前端测试：Vitest（API client 超时/错误、日期与任务状态工具函数）。
- 前端工程化：ESLint 9（flat config）+ Prettier + Vitest 2。
- 统一队伍配置：`backend/config/team.example.yaml` 与 `GET /api/meta`。
- 可选摄像头依赖拆分：`requirements.txt` + `requirements-camera.txt`；摄像头模块拆分为 `backend/integrations/camera/`。

### 修复
- `.env` 路径不一致：统一从 `backend/.env` 加载，README/.gitignore/启动方式同步。
- logger 未定义导致异常分支二次报错。
- 飞书失败自动回退 Mock 的危险逻辑 → 改为显式 `DATA_SOURCE` 模式 + stale/degraded 标记。
- `/api/health` 增加飞书状态、上次成功同步时间、缓存年龄、stale。
- 空值日名单导致 `ZeroDivisionError`。
- 修改状态的 API 由 GET 改为 POST，并整理到 `/api/admin/*`（Bearer 鉴权）。
- Feishu client 重试策略：仅对 ConnectionError/Timeout/429/5xx 重试，指数退避 + jitter，全部请求带 timeout。
- 前端自动刷新：主数据 30s、工时/考勤 5min、标签页隐藏暂停；stale 时显示"正在显示缓存数据"。

### 安全
- `/api/camera/*` 与 `/api/attendance/face-latest` 增加 `CAMERA_PUBLIC` / `VIEWER_TOKEN` 鉴权（兼容 MJPEG query token）。
- `/api/docs/content` 增加白名单校验，只允许 `FEATURED_DOCS` 内的 doc_id。
- HTTP 状态码修正：管理接口错误返回 502/503，dist 未构建返回 503，doc 越权返回 403。
- 工作树中的敏感文件（installers/*.exe、真实名单、真实文档 Token、日志、备份内容）已从 Git 索引移除（git rm --cached），由 .gitignore 兜底。
- 部署脚本不再命令行传 SSH 密码、不再 `taskkill /f /im python.exe`，改为 PID 文件 + SSH Key。

### 历史版本
- 内部版本：飞书多维表格任务看板 + 工时/劳模榜 + 值日 + 摄像头人脸签到（希沃 Win7 部署）。
