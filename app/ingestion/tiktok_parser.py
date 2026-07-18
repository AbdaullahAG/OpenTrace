def parse_tiktok_export(payload: dict) -> dict:
    return {"source": "tiktok", "items": payload.get("items", [])}
