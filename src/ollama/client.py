import asyncio
import json
from collections.abc import AsyncIterator
from typing import Protocol

import httpx
import structlog

from src.ollama.exceptions import OllamaUnavailableError
from src.ollama.options import OllamaOptions
from src.ollama.types import ChatMessage, ToolDefinition

logger = structlog.get_logger(__name__)


class OllamaClientProtocol(Protocol):
    async def is_ready(self) -> bool: ...

    def stream_chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> AsyncIterator[str]: ...


class OllamaClient:
    """Async streaming Ollama HTTP client backed by httpx."""

    def __init__(self, options: OllamaOptions | None = None) -> None:
        self._options = options or OllamaOptions()
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(self._options.timeout_seconds)
        )

    async def is_ready(self) -> bool:
        """Return True if Ollama is reachable and the configured model is present."""
        try:
            response = await self._http.get(
                f"{self._options.endpoint}/api/tags",
                timeout=3.0,
            )
            if response.status_code != 200:
                return False
            data = response.json()
            models: list[dict[str, str]] = data.get("models", [])
            return any(
                m.get("name", "").split(":")[0] == self._options.model_name.split(":")[0]
                for m in models
            )
        except Exception:
            return False

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat tokens from Ollama; yields each decoded text token."""
        payload: dict[str, object] = {
            "model": self._options.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters_schema,
                    },
                }
                for t in tools
            ]

        logger.debug("stream_chat_started", model=self._options.model_name)
        try:
            async with self._http.stream(
                "POST",
                f"{self._options.endpoint}/api/chat",
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise OllamaUnavailableError(
                        f"Ollama returned {response.status_code}: {body.decode()}"
                    )
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    msg = chunk.get("message", {})
                    token: str = msg.get("content", "")
                    if token:
                        yield token
                    # Surface tool calls as a serialised JSON token for the agent loop
                    for tc in msg.get("tool_calls") or []:
                        fn = tc.get("function", {})
                        yield json.dumps(
                            {"name": fn.get("name", ""), "arguments": fn.get("arguments", {})},
                            separators=(",", ":"),
                        )
                    if chunk.get("done"):
                        break
        except asyncio.CancelledError:
            raise
        except OllamaUnavailableError:
            raise
        except httpx.TimeoutException as exc:
            raise OllamaUnavailableError("Ollama request timed out") from exc
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(f"HTTP error communicating with Ollama: {exc}") from exc

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "OllamaClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
