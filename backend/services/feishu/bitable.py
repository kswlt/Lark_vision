"""
多维表格记录读取（分页）。
接口：GET /open-apis/bitable/v1/apps/:app_token/tables/:table_id/records
单页最多 500 行，支持 page_token 翻页。
"""


def list_records(client, app_token, table_id, page_size=500, max_pages=20):
    records = []
    page_token = None
    pages = 0
    while True:
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        data = client.get(
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            params=params,
        )
        records.extend(data.get("items") or [])
        pages += 1
        if not data.get("has_more") or not data.get("page_token") or pages >= max_pages:
            break
        page_token = data.get("page_token")
    return records
