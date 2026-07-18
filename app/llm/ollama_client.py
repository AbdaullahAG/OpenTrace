import os


class OllamaClient:
    def __init__(self, host: str | None = None, model: str | None = None):
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral")

    def ping(self) -> bool:
        return True
