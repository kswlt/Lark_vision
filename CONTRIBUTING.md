# 参与贡献

感谢你愿意为这个项目贡献代码！本项目是一个面向 RoboMaster 战队实验室的轻量 Dashboard，
目标是"简单可维护"，请保持这个基调。

## 开发前

1. 阅读 [README](./README.md) 的「快速启动」与「开发方式」。
2. 认领 issue 或先开 issue 说明你要改什么，避免重复劳动。
3. 保持改动范围最小：不要顺手重构无关代码。

## 分支与提交

- 从 `main` 切功能分支：`git checkout -b feat/xxx`
- 提交信息使用清晰的中文或英文描述，例如 `fix: 飞书字段缺失时不再回退 Mock`。
- 合入前先 rebase main，保持历史线性（**禁止 force push 到公共分支**）。

## 代码规范

- **后端（Python 3.8+）**
  - 运行 `ruff check backend`，保持零错误。
  - 新逻辑必须配套 `backend/tests/` 测试，运行 `pytest backend`。
  - 不改动既有接口语义；如需变更，先讨论。
- **前端（TypeScript + React）**
  - 运行 `npm run lint` 与 `npm run test`，保持全绿。
  - `npm run build` 必须通过。
  - 提交前可用 `npm run format` 格式化新增文件。

## 配置约定

- 不要把真实飞书 Token、战队名单、成员照片提交进仓库。
- 新增可配置项时：写到 `backend/.env.example` 与 `backend/config/team.example.yaml`，
  代码里给合理默认值，README 同步说明。
- 摄像头/人脸识别是**可选功能**，缺少 cv2 等依赖时 Dashboard 必须照常启动。

## 测试

- CI 已在 [.github/workflows/ci.yml](./.github/workflows/ci.yml) 中配置，
  不依赖真实飞书账号、真实相机或任何 Secret。
- 本地运行全部检查：

```bash
# 后端
python -m compileall backend
ruff check backend
pytest backend

# 前端
cd frontend
npm ci --legacy-peer-deps
npm run lint
npm run test
npm run build
```

## 提 PR

PR 描述请包含：改动目的、改动内容、验证方式（跑过哪些命令 / 在什么环境验证过）。
涉及相机、希沃端等硬件相关改动，请注明「已在真机验证」或「需要真机验证」。
