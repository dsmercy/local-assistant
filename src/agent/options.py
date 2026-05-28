from pydantic_settings import BaseSettings


class AgentOptions(BaseSettings):
    """Agent runtime configuration loaded from environment variables."""

    max_tool_call_depth: int = 10
    stuck_detection_window: int = 3

    model_config = {"env_prefix": "AGENT_"}
