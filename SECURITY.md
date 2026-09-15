# 安全说明（Security Policy）

## 支持的版本

| 版本 | 支持状态 |
| ---- | -------- |
| main 分支 | ✅ 积极维护 |
| 历史 tag | ⚠️ 仅关键安全修复 |

## 报告漏洞

请**不要**在 GitHub issue 中公开安全漏洞细节。请通过邮件联系维护者
（在仓库首页 Contributors 中查看维护者邮箱），或直接开一个标题带 `[SECURITY]`
的私有讨论。

报告请包含：

1. 漏洞类型与影响面；
2. 复现步骤（尽量精简）；
3. 受影响的版本/文件；
4. 你建议的修复方式（可选）。

## 本项目的安全设计

- **飞书凭证只放在 `backend/.env`**（已 gitignore），仓库只提交 `.env.example`。
- **显式数据源模式**：`DATA_SOURCE=feishu` 下飞书请求失败时只返回最近成功缓存并标记
  `stale/degraded`，**绝不自动回退到 Mock 假数据**。
- **管理接口需要鉴权**：`/api/admin/*` 必须携带 `Authorization: Bearer <ADMIN_TOKEN>`，
  普通 Dashboard 读取接口无需登录。
- **敏感数据不入库**：`backend/config/team_roster.json`、`featured_docs.py`、
  `face_library/`、`logs/`、安装器等均被 .gitignore 忽略。
- **摄像头是可选依赖**：未安装 cv2/华睿 SDK 时，Dashboard 以 `camera_enabled=false`
  正常运行，不会因 import 失败而崩溃。

## 部署建议

- 生产环境设置强随机 `ADMIN_TOKEN`，不要使用示例值。
- 定期轮换飞书应用密钥（App Secret）。
- 旧 Win7/希沃部署见 README「Legacy Deployment」，注意系统无安全更新，
  仅限内网使用，不建议暴露公网。
