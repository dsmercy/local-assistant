import json
from typing import Any

from src.tools.base import ToolCall


class ToolCallParser:
    """Detects and parses a complete Ollama tool-call JSON block from accumulated tokens."""

    def parse(self, accumulated: str) -> ToolCall | None:
        """Return a ToolCall if *accumulated* is a valid tool-call JSON, else None."""
        text = accumulated.strip()
        if not text:
            return None
        try:
            data: Any = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        name = data.get("name")
        arguments = data.get("arguments")
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return None
        return ToolCall(tool_name=name, arguments=arguments)
