from dataclasses import dataclass


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters_schema: dict  # type: ignore[type-arg]  # JSON Schema dict
