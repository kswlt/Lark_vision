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
    # ===== 26赛季 =====
    {"token": "IHDCdjR8IoI5FYxAx4fcsXIcn1b", "name": "冯永兴26RMUC参赛总结", "type": "docx"},
    # ===== 24赛季联盟赛总结 =====
    {"token": "UAWbdRLuNoKiEDxsZOZc0IS7nFE", "name": "曹育萌联盟赛总结", "type": "docx"},
    {"token": "FI7Yd4vBEo5tTDxD1xNcdlEKnub", "name": "陈彦霖联盟赛参赛总结", "type": "docx"},
    {"token": "M4pRdBnGCodvn8x0NvecpEidnGb", "name": "代宝山参赛总结", "type": "docx"},
    {"token": "Hn6odxbZ5oAXHFx4lnRcr5ncnge", "name": "龚学超云参赛总结", "type": "docx"},
    {"token": "TfyodWt0zo6YmFxshD9cUi1HnOb", "name": "何德欢参赛总结", "type": "docx"},
    {"token": "IZtldSNKooKWgFxuD7vcYWEcnQA", "name": "黄秋潭参赛总结", "type": "docx"},
    {"token": "FOpRdO9t6od0LVxlY6RcTPnFnod", "name": "黄子健参赛总结", "type": "docx"},
    {"token": "OLFIdjJdJotHfSx0ELoc8U4rnad", "name": "李希瑞云参赛总结", "type": "docx"},
    {"token": "HFjSdz1IYovlC2xxscVcNgl9n1c", "name": "廖明辉总结", "type": "docx"},
    {"token": "HOKTdViqto34kZxcFzscefycnJf", "name": "吕宇浩参赛总结", "type": "docx"},
    {"token": "RE8ndCZSuoLxE3xe5ZPcIHkTnIb", "name": "吕长斌联盟赛参赛总结", "type": "docx"},
    {"token": "XlZidVNfZoSY30xpbinc190Qnkd", "name": "马志恒参赛总结", "type": "docx"},
    {"token": "HMkKdJhYYoZehOxuwGzcw4oKnvh", "name": "聂博章参赛总结", "type": "docx"},
    {"token": "QOOedLxS7ocT9lxvESucwlEHnAA", "name": "任钰珏参赛总结", "type": "docx"},
    {"token": "BH01dYNoroxbvpxzvLCceiHGnRh", "name": "史静波参赛总结", "type": "docx"},
    {"token": "AAoJd1Vr6or5nUxi5AlcvYNWnjh", "name": "魏甜甜参赛总结", "type": "docx"},
    {"token": "ODRddognko9DPHxgO5ocQ2hSnoc", "name": "尹燕玺联盟赛参赛总结", "type": "docx"},
    {"token": "FjF8dSNJIoSTKixr0DYcTdHynQg", "name": "于顺磊参赛总结", "type": "docx"},
    {"token": "PQV1dNGvJobwN7xhxNMcZc0Bnbh", "name": "詹明宇总结", "type": "docx"},
    {"token": "IGstdySD5op26dxSCxlczC0YnA6", "name": "张晟祥参赛总结", "type": "docx"},
    {"token": "FsIIdYAQRoXbaSxXBXDcVdVrnhc", "name": "张政宇参赛总结", "type": "docx"},
    # ===== 24赛季分区赛总结 =====
    {"token": "AP7ydlpbCoD1ofx3Jvkcf19Xnyb", "name": "尹燕玺分区赛参赛总结", "type": "docx"},
    {"token": "RYxadb6WcoLr2Oxb4RFcX1k4nQg", "name": "分区赛总结", "type": "docx"},
    {"token": "N7jyd6f2koddW4xavnacVBTcnDh", "name": "任钰珏分区赛总结", "type": "docx"},
    {"token": "DJYfdwL6GoRTyfxp1j1c0eajnde", "name": "马志恒分区赛总结", "type": "docx"},
    {"token": "RcRNdvIpxo9NBKxqwL0cAH5SnFb", "name": "詹明宇分区赛总结", "type": "docx"},
    {"token": "Dntjdtc2KoGa5lxuDmncUKLXnsc", "name": "代宝山分区赛总结", "type": "docx"},
    {"token": "L0U0dyQbGoaSqJxfAy4cWe3anKe", "name": "龚学超分区赛总结", "type": "docx"},
    {"token": "CUBgde3ywohQtyxQ9TAcxp8Rntc", "name": "何德欢分区赛总结", "type": "docx"},
    {"token": "WNq4d1C7po1tRMxuTxcc5rfcnOg", "name": "黄秋潭分区赛总结", "type": "docx"},
    {"token": "LfLJdLb1wou4LIxP58icMqdLnQf", "name": "李昊泽分区赛总结", "type": "docx"},
    {"token": "NTb5dPdtBo5uwBxJdCxcz4fsnwh", "name": "马佳琨运营组教训规划与建议", "type": "docx"},
    {"token": "GAkDdEGaAoBpSvxPCTacyUQsnOb", "name": "史静波分区赛总结", "type": "docx"},
    {"token": "JbAPdvbNyoDMMrxcZdWctRXTnVg", "name": "魏甜甜分区赛总结", "type": "docx"},
    {"token": "O09ndxaycoe1zOx9531ccUw4nig", "name": "于顺磊分区赛总结", "type": "docx"},
    {"token": "VJKrdEk8Fos51TxHxklcFCmCnwh", "name": "张晟祥分区赛总结", "type": "docx"},
    {"token": "EkAHdsRKAoLGJMxto40cqdNinvd", "name": "黄子健分区赛总结", "type": "docx"},
    {"token": "YdVDdyBnioole7xv3FPctaZlnob", "name": "吕长斌分区赛总结", "type": "docx"},
    {"token": "FCEVd8RMCoc5tgx4prlcoRWZn0P", "name": "张政宇分区赛总结", "type": "docx"},
    {"token": "Jp0qdP4AEoRIHoxunOncq2d2nQd", "name": "陈彦霖分区赛总结", "type": "docx"},
    {"token": "I7W6dS92nodpTrx1xA1cfabGnhc", "name": "李希瑞分区赛总结", "type": "docx"},
    {"token": "CrMWd0OvxoSPwpxZ0RDcitgOnKc", "name": "刘相果分区赛总结", "type": "docx"},
    # ===== 24赛季复活赛/国赛总结 =====
    {"token": "KiuQdZ2E4oDLBwxQBt4cIyijnIf", "name": "陈彦霖复活赛参赛总结", "type": "docx"},
    {"token": "PVbvdQQYJoWJ2pxZUKAcuMGBnvc", "name": "代宝山复活赛参赛总结", "type": "docx"},
    {"token": "BvWzdQNhLo90WBx86JjcT9eInMI", "name": "龚学超复活赛参赛总结", "type": "docx"},
    {"token": "S1vwdVwSboLuCpxTwcgcAzQ6nfe", "name": "何德欢复活赛参赛总结", "type": "docx"},
    {"token": "YhXRdkQ6To6Ug3xiO8ocxMJKn6f", "name": "胡延坤复活赛参赛总结", "type": "docx"},
    {"token": "JUqLdLa7Dog07UxvORPcJAfDn4f", "name": "黄秋潭复活赛参赛总结", "type": "docx"},
    {"token": "XfJDdJdBooSrIIxlCflceueonmW", "name": "黄子健复活赛参赛总结", "type": "docx"},
    {"token": "SsyrdT4PqoP2FpxP9o2cn5iunAg", "name": "姜志齐复活赛参赛总结", "type": "docx"},
    {"token": "Ez0pdbXzfoInVdxOGE4cVBRwnaf", "name": "李海鹏复活赛参赛总结", "type": "docx"},
    {"token": "EO0ydWbYXotelgxcc0ScYLlHnxb", "name": "李希瑞复活赛参赛总结", "type": "docx"},
    {"token": "B2WEd4S1goFhfjxxlFecksFEnJd", "name": "梁一博复活赛参赛总结", "type": "docx"},
    {"token": "Ide4dQleDobyDdxGp3fc4GkWnTe", "name": "刘浙赛季总结", "type": "docx"},
    {"token": "QlOSd3J1eopmnwxjt2ncaNKFnqh", "name": "吕长斌复活赛参赛总结", "type": "docx"},
    {"token": "H0kgdMBhfohRwyxI6a3cjkpHnjf", "name": "马志恒复活赛参赛总结", "type": "docx"},
    {"token": "DtZodHOEgod5AVx03xTc3uw3nDd", "name": "毛蕊复活赛参赛总结", "type": "docx"},
    {"token": "M54bdYJZuoTCnNxcpV7cGzHUnSc", "name": "聂博章复活赛参赛总结", "type": "docx"},
    {"token": "XEo0dmu0vo3psrx7CvKc4LHknIh", "name": "任钰珏复活赛参赛总结", "type": "docx"},
    {"token": "DMShdN9Xko2hprxRn53cMRIinjf", "name": "史静波复活赛参赛总结", "type": "docx"},
    {"token": "COc7dC1kwoajgLxfUFrcjYVZnrc", "name": "魏甜甜复活赛参赛总结", "type": "docx"},
    {"token": "XoNQdnPoFoqyu3xnLDvcPr29nne", "name": "魏轩复活赛参赛总结", "type": "docx"},
]
