# Changelog

本项目的所有重要变更都会记录在此文件中。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 开源工程化改造（2026-09）

#### 新增
- 开源文件：LICENSE（MIT）、CONTRIBUTING.md、SECURITY.md、CHANGELOG.md。
- GitHub Actions CI：`.github/workflows/ci.yml`（前端 lint/test/build + 后端 ruff/pytest/compileall，不依赖真实飞书/相机/Secret）。
- 后端测试套件 `backend/tests/`（41 个用例：字段归一化、聚合、数据源模式、缓存回退、health、admin 鉴权、Feishu client 重试）。
- 前端测试：Vitest（API client 超时/错误、日期与任务状态工具函数）。
- 前端工程化：ESLint 9（flat config）+ Prettier + Vitest 2。
- 统一队伍配置：`backend/config/team.example.yaml` 与 `GET /api/meta`。
- 可选摄像头依赖拆分：`requirements.txt` + `requirements-camera.txt`；摄像头模块拆分为 `backend/integrations/camera/`。

#### 修复
- `.env` 路径不一致：统一从 `backend/.env` 加载，README/.gitignore/启动方式同步。
- logger 未定义导致异常分支二次报错。
- 飞书失败自动回退 Mock 的危险逻辑 → 改为显式 `DATA_SOURCE` 模式 + stale/degraded 标记。
- `/api/health` 增加飞书状态、上次成功同步时间、缓存年龄、stale。
- 空值日名单导致 `ZeroDivisionError`。
- 修改状态的 API 由 GET 改为 POST，并整理到 `/api/admin/*`（Bearer 鉴权）。
- Feishu client 重试策略：仅对 ConnectionError/Timeout/429/5xx 重试，指数退避 + jitter，全部请求带 timeout。
- 前端自动刷新：主数据 30s、工时/考勤 5min、标签页隐藏暂停；stale 时显示"正在显示缓存数据"。

#### 安全
- 工作树中的敏感文件（installers/*.exe、真实名单、真实文档 Token、日志、备份内容）已从 Git 索引移除（git rm --cached），由 .gitignore 兜底。
- 部署脚本不再命令行传 SSH 密码、不再 `taskkill /f /im python.exe`，改为 PID 文件 + SSH Key。

## [1.0.0] - 2026-09

- 初始版本：飞书多维表格任务看板 + 工时/劳模榜 + 值日 + 摄像头人脸签到（希沃 Win7 部署）。
