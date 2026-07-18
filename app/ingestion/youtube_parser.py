def parse_youtube_export(payload: dict) -> dict:
    return {"source": "youtube", "items": payload.get("items", [])}
