from src.ollama.types import ToolDefinition
from src.tools.base import ToolHandler


class ToolNotFoundException(Exception):
    """Raised when a requested tool name is not registered."""


class ToolDepthExceededError(Exception):
    """Raised when recursive tool-call depth exceeds the configured limit."""


class ToolRegistry:
    """Maps tool names to handlers and tracks call depth."""

    def __init__(self, handlers: list[ToolHandler], max_depth: int = 10) -> None:
        self._handlers: dict[str, ToolHandler] = {h.name: h for h in handlers}
        self._max_depth = max_depth
        self._depth = 0

    def resolve(self, name: str) -> ToolHandler:
        """Return the handler for *name*, or raise ToolNotFoundException."""
        if name not in self._handlers:
            raise ToolNotFoundException(f"Tool '{name}' is not registered.")
        return self._handlers[name]

    def increment_depth(self) -> None:
        """Increment the call depth counter, raising if the limit is exceeded."""
        self._depth += 1
        if self._depth > self._max_depth:
            raise ToolDepthExceededError(
                f"Tool call depth exceeded the limit of {self._max_depth}."
            )

    def reset_depth(self) -> None:
        self._depth = 0

    @property
    def definitions(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name=h.name,
                description=h.description,
                parameters_schema=h.parameters_schema,
            )
            for h in self._handlers.values()
        ]
