import asyncio
import json

import httpx
import pytest
import respx

from src.ollama.client import OllamaClient
from src.ollama.exceptions import OllamaUnavailableError
from src.ollama.options import OllamaOptions
from src.ollama.types import ChatMessage

ENDPOINT = "http://localhost:11434"

OPTIONS = OllamaOptions(
    endpoint=ENDPOINT,
    model_name="qwen2.5-coder:7b",
    timeout_seconds=10,
)


def _tags_response(model_name: str = "qwen2.5-coder:7b") -> dict:
    return {"models": [{"name": model_name}]}


def _chat_response(content: str) -> dict:
    return {"message": {"role": "assistant", "content": content}, "done": True}


# ── is_ready ─────────────────────────────────────────────────────────────────


@respx.mock
async def test_is_ready_returns_true_when_server_ok_and_model_present() -> None:
    respx.get(f"{ENDPOINT}/api/tags").mock(
        return_value=httpx.Response(200, json=_tags_response())
    )
    client = OllamaClient(OPTIONS)
    assert await client.is_ready() is True


@respx.mock
async def test_is_ready_returns_false_when_server_unreachable() -> None:
    respx.get(f"{ENDPOINT}/api/tags").mock(side_effect=httpx.ConnectError("down"))
    client = OllamaClient(OPTIONS)
    assert await client.is_ready() is False


@respx.mock
async def test_is_ready_returns_false_when_model_not_in_response() -> None:
    respx.get(f"{ENDPOINT}/api/tags").mock(
        return_value=httpx.Response(200, json=_tags_response("llama3:8b"))
    )
    client = OllamaClient(OPTIONS)
    assert await client.is_ready() is False


# ── stream_chat ───────────────────────────────────────────────────────────────


@respx.mock
async def test_stream_chat_yields_tokens_in_order() -> None:
    respx.post(f"{ENDPOINT}/api/chat").mock(
        return_value=httpx.Response(200, json=_chat_response("Hello world!"))
    )
    client = OllamaClient(OPTIONS)
    messages = [ChatMessage(role="user", content="hi")]
    tokens = [t async for t in client.stream_chat(messages)]
    assert tokens == ["Hello world!"]


@respx.mock
async def test_stream_chat_raises_ollama_unavailable_on_non_2xx() -> None:
    respx.post(f"{ENDPOINT}/api/chat").mock(
        return_value=httpx.Response(503, content=b"service unavailable")
    )
    client = OllamaClient(OPTIONS)
    messages = [ChatMessage(role="user", content="hi")]
    with pytest.raises(OllamaUnavailableError, match="503"):
        async for _ in client.stream_chat(messages):
            pass


@respx.mock
async def test_stream_chat_raises_ollama_unavailable_on_timeout() -> None:
    respx.post(f"{ENDPOINT}/api/chat").mock(
        side_effect=httpx.TimeoutException("timed out")
    )
    client = OllamaClient(OPTIONS)
    messages = [ChatMessage(role="user", content="hi")]
    with pytest.raises(OllamaUnavailableError, match="timed out"):
        async for _ in client.stream_chat(messages):
            pass


@respx.mock
async def test_stream_chat_propagates_cancellation() -> None:
    async def _slow(_: httpx.Request) -> httpx.Response:
        await asyncio.sleep(10)
        return httpx.Response(200)

    respx.post(f"{ENDPOINT}/api/chat").mock(side_effect=_slow)
    client = OllamaClient(OPTIONS)
    messages = [ChatMessage(role="user", content="hi")]

    gen = client.stream_chat(messages)
    task = asyncio.create_task(gen.__anext__())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
