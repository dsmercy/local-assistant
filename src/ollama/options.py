from pydantic_settings import BaseSettings


class OllamaOptions(BaseSettings):
    """Ollama server configuration loaded from environment variables."""

    endpoint: str = "http://127.0.0.1:11434"
    model_name: str = "qwen2.5-coder:7b"
    timeout_seconds: int = 300

    model_config = {"env_prefix": "OLLAMA_"}
