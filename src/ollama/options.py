from pydantic_settings import BaseSettings


class OllamaOptions(BaseSettings):
    """Ollama server configuration loaded from environment variables."""

    endpoint: str = "http://localhost:11434"
    model_name: str = "qwen2.5-coder:14b"
    timeout_seconds: int = 120

    model_config = {"env_prefix": "OLLAMA_"}
