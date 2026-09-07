# -*- coding: utf-8 -*-
"""
大屏展示的精选文档列表（直接配置 doc_id，无需文件夹授权）。

添加文档方法：
1. 打开飞书文档，复制浏览器地址栏链接
2. 链接格式：https://idf6jvjjmj.feishu.cn/docx/XXXXXXXXXX
3. 把 XXXXXXXXXX 填到 token 字段，name 填文档标题，type 填 docx（新版文档）或 doc（旧版）

注意：文档需要设置为「组织内获得链接的人可阅读」，否则应用身份无法读取。
"""

FEATURED_DOCS = [
    {
        "token": "IHDCdjR8IoI5FYxAx4fcsXIcn1b",
        "name": "冯永兴26RMUC参赛总结",
        "type": "docx",
    },
    # 在这里添加更多文档，格式同上：
    # {
    #     "token": "你的文档token",
    #     "name": "文档标题",
    #     "type": "docx",
    # },
]
