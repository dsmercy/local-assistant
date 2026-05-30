from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.main import app, get_agent_loop


# ── Fake agent loop ───────────────────────────────────────────────────────────


class _FakeLoop:
    def __init__(self, tokens):
        self._tokens = tokens

    async def run(self, _message):
        for t in self._tokens:
            yield t


class _ErrorLoop:
    async def run(self, _message):
        raise RuntimeError("simulated failure")
        yield  # makes this an async generator


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _mock_ollama(monkeypatch):
    """Patch OllamaClient so the lifespan health-check passes without Ollama."""
    monkeypatch.setattr("src.main.OllamaClient.is_ready", AsyncMock(return_value=True))
    monkeypatch.setattr("src.main.OllamaClient.aclose", AsyncMock())


@pytest.fixture(autouse=True)
def _default_agent_override():
    """Override get_agent_loop for every test; individual tests may replace it."""
    app.dependency_overrides[get_agent_loop] = lambda: _FakeLoop(["Hello", " world"])
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client(_mock_ollama, _default_agent_override):
    with TestClient(app) as c:
        yield c


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_chat_returns_200_with_sse_content_type(client):
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_chat_streams_tokens_not_buffered(client):
    response = client.post("/chat", json={"message": "hi"})
    content = response.text
    assert "data: Hello\n\n" in content
    assert "data:  world\n\n" in content


def test_chat_returns_400_for_empty_message(client):
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 400


def test_chat_returns_400_for_whitespace_only_message(client):
    response = client.post("/chat", json={"message": "   "})
    assert response.status_code == 400


def test_chat_stream_ends_with_done_sentinel(client):
    response = client.post("/chat", json={"message": "hi"})
    assert "data: [DONE]\n\n" in response.text


def test_server_does_not_expose_traceback_in_sse_stream(client):
    app.dependency_overrides[get_agent_loop] = lambda: _ErrorLoop()
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 200
    assert "Traceback" not in response.text
    assert "data: [DONE]\n\n" in response.text
