import asyncio
import json
from collections.abc import AsyncIterator

import structlog

from src.agent.exceptions import AgentDepthError, AgentStuckError
from src.agent.options import AgentOptions
from src.agent.parser import ToolCallParser
from src.ollama.client import OllamaClientProtocol
from src.ollama.types import ChatMessage
from src.tools.base import ToolCall, ToolResult
from src.tools.registry import ToolDepthExceededError, ToolNotFoundException, ToolRegistry

logger = structlog.get_logger(__name__)


class AgentLoop:
    """Self-correcting, depth-limited, streaming reasoning loop."""

    def __init__(
        self,
        client: OllamaClientProtocol,
        registry: ToolRegistry,
        options: AgentOptions,
        system_prompt: str = "",
    ) -> None:
        self._client = client
        self._registry = registry
        self._options = options
        self._system_prompt = system_prompt
        self._parser = ToolCallParser()

    async def run(self, user_message: str) -> AsyncIterator[str]:
        """Stream response tokens, executing tool calls as they are detected."""
        messages: list[ChatMessage] = []
        if self._system_prompt:
            messages.append(ChatMessage(role="system", content=self._system_prompt))
        messages.append(ChatMessage(role="user", content=user_message))

        self._registry.reset_depth()
        recent_sigs: list[str] = []

        while True:
            accumulated = ""

            try:
                async for token in self._client.stream_chat(
                    messages, tools=self._registry.definitions
                ):
                    accumulated += token
                    yield token
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                yield f"\n[Agent error: {exc}]"
                return

            # No tool call in this response — normal completion
            tool_call = self._parser.parse(accumulated)
            if tool_call is None:
                return

            # ── depth check ────────────────────────────────────────────────
            try:
                self._registry.increment_depth()
            except ToolDepthExceededError:
                yield f"\n[Agent error: {AgentDepthError(self._options.max_tool_call_depth)}]"
                return

            # ── stuck detection ─────────────────────────────────────────────
            sig = json.dumps(
                {"n": tool_call.tool_name, "a": tool_call.arguments}, sort_keys=True
            )
            recent_sigs.append(sig)
            window = self._options.stuck_detection_window
            if (
                len(recent_sigs) >= window
                and len(set(recent_sigs[-window:])) == 1
            ):
                yield f"\n[Agent error: {AgentStuckError(tool_call.tool_name)}]"
                return

            # ── execute tool (output is untrusted data, not instructions) ───
            result = await self._execute_tool(tool_call)

            # ── append to history and loop ──────────────────────────────────
            messages.append(ChatMessage(role="assistant", content=accumulated))
            messages.append(ChatMessage(role="tool", content=result.output))

    async def _execute_tool(self, call: ToolCall) -> ToolResult:
        try:
            handler = self._registry.resolve(call.tool_name)
            return await handler.execute(call)
        except ToolNotFoundException as exc:
            logger.debug("tool_not_found", tool=call.tool_name)
            return ToolResult(success=False, output=str(exc), error="tool_not_found")
        except Exception as exc:
            logger.debug("tool_error", tool=call.tool_name, error=str(exc))
            return ToolResult(success=False, output=str(exc), error="tool_error")
