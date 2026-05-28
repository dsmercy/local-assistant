# Phase 01 — Ollama Client

## Phase goal
Implement and test an async, streaming Ollama HTTP client backed by httpx.
All downstream components depend on this — it must be solid before Phase 02.

## Entry criteria
- [ ] Phase 00 exit gates passed
- [ ] `pytest -x && ruff check . && mypy src/` all green

## Active standards
§7 Python code quality · §8 Error handling · §9 Logging · §10 Performance · §19 Agent runtime config

## Implementation

### Step 1.1 — OllamaOptions

**File:** `src/ollama/options.py`
```python
from pydantic_settings import BaseSettings

class OllamaOptions(BaseSettings):
    """Ollama server configuration loaded from environment variables."""

    endpoint: str = "http://localhost:11434"
    model_name: str = "qwen2.5-coder:7b"
    timeout_seconds: int = 120

    model_config = {"env_prefix": "OLLAMA_"}
```

### Step 1.2 — Domain types

**File:** `src/ollama/types.py`
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ChatMessage:
    role: str   # "system" | "user" | "assistant" | "tool"
    content: str

@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters_schema: dict  # JSON Schema dict
```

### Step 1.3 — Custom exceptions

**File:** `src/ollama/exceptions.py`
```python
class OllamaError(Exception):
    """Base class for Ollama client errors."""

class OllamaUnavailableError(OllamaError):
    """Raised when Ollama server is unreachable or returns a non-2xx status."""

class OllamaModelNotFoundError(OllamaError):
    """Raised when the requested model is not available."""
```

### Step 1.4 — OllamaClient

**File:** `src/ollama/client.py`

Rules:
- Use `httpx.AsyncClient` — never `requests`
- `stream_chat`: POST `/api/chat`, `stream=true` → yield decoded text tokens
- `is_ready`: GET `/api/tags` with 3s timeout → bool (never raises)
- Apply `timeout_seconds` from options on the shared `AsyncClient`
- Wrap `httpx.TimeoutException` → `OllamaUnavailableError`
- Wrap non-2xx responses → `OllamaUnavailableError` with status + body
- Log at `debug` level only: never log message contents or token values
- Accept and propagate `asyncio.CancelledError` from the caller

```python
from collections.abc import AsyncIterator
from typing import Protocol

class OllamaClientProtocol(Protocol):
    async def is_ready(self) -> bool: ...
    def stream_chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> AsyncIterator[str]: ...
```

### Step 1.5 — Unit tests

**File:** `tests/ollama/test_client.py`

Use `respx` to mock HTTP — no real network calls.

| Scenario | Expected |
|---|---|
| `is_ready` — server 200 + model in JSON | `True` |
| `is_ready` — server unreachable | `False` (no exception) |
| `is_ready` — 200 but model absent | `False` |
| `stream_chat` — streams tokens | yields each token string in order |
| `stream_chat` — non-2xx response | raises `OllamaUnavailableError` |
| `stream_chat` — timeout | raises `OllamaUnavailableError` |
| `stream_chat` — cancellation | `asyncio.CancelledError` propagated |

## Validation gate
```bash
pytest tests/ollama/ -v && ruff check src/ollama/ && mypy src/ollama/
```

## Exit criteria
- [ ] All tests green
- [ ] `is_ready` never raises — always returns `bool`
- [ ] Token streaming uses `async for` — never buffers full response
- [ ] No message content logged at any level
- [ ] `mypy src/ollama/` passes with `strict = true`

## What not to do
- Do not implement tool handlers (Phase 02)
- Do not implement the agent loop (Phase 03)
- Do not add retry logic here — that belongs in AgentLoop
