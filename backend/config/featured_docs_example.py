"""
大屏展示的精选文档列表（示例配置）。

使用方法：
1. 复制为 featured_docs.py（该文件已被 .gitignore 忽略，不会提交到 Git）
2. 打开飞书文档，复制浏览器地址栏链接
3. 链接格式：https://your-tenant.feishu.cn/docx/XXXXXXXXXX
4. 把 XXXXXXXXXX 填到 token 字段，name 填文档标题，type 填 docx（新版文档）或 doc（旧版）

注意：文档需要设置为「组织内获得链接的人可阅读」，否则应用身份无法读取。
注意：真实 doc token 属于内部信息，请勿提交到 Git。
"""

FEATURED_DOCS = [
    # ===== 示例文档（替换为你的真实文档） =====
    {"token": "YOUR_DOC_TOKEN_1", "name": "示例文档一：参赛总结", "type": "docx"},
    {"token": "YOUR_DOC_TOKEN_2", "name": "示例文档二：赛季规划", "type": "docx"},
]
