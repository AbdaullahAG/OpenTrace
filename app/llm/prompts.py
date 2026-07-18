def build_summary_prompt(history: list[dict]) -> str:
    return f"Summarize the following feed history: {history[:3]}"
