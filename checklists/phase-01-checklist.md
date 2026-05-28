# Phase 01 — OllamaClient Checklist

> Reference: `agent-instructions/phases/phase-01-ollama-client.md`

---

## Files created

```bash
find src/ollama tests/ollama -type f | sort
```

- [ ] `src/ollama/__init__.py`
- [ ] `src/ollama/options.py` — `OllamaOptions(BaseSettings)`
- [ ] `src/ollama/types.py` — `ChatMessage`, `ToolDefinition` frozen dataclasses
- [ ] `src/ollama/exceptions.py` — `OllamaError`, `OllamaUnavailableError`, `OllamaModelNotFoundError`
- [ ] `src/ollama/client.py` — `OllamaClientProtocol` (Protocol), `OllamaClient`
- [ ] `tests/ollama/__init__.py`
- [ ] `tests/ollama/test_client.py`

---

## Code review checklist

Open `src/ollama/client.py` and verify:

- [ ] Uses `httpx.AsyncClient` — no `import requests` anywhere
- [ ] `is_ready()` return type is `bool` — no `raise` in the `except` block
- [ ] `stream_chat()` uses `async for` and `yield` — no `.collect()` or list buffer
- [ ] `OllamaOptions` is injected — no hardcoded `"http://localhost:11434"` in client
- [ ] No message content or token values are logged (only path/model at `DEBUG`)
- [ ] `CancelledError` is not caught — it propagates to the caller

---

## Unit tests

```bash
pytest tests/ollama/ -v
```

Verify each test name appears and passes:

- [ ] `test_is_ready_returns_true_when_server_ok_and_model_present`
- [ ] `test_is_ready_returns_false_when_server_unreachable`
- [ ] `test_is_ready_returns_false_when_model_not_in_response`
- [ ] `test_stream_chat_yields_tokens_in_order`
- [ ] `test_stream_chat_raises_ollama_unavailable_on_non_2xx`
- [ ] `test_stream_chat_raises_ollama_unavailable_on_timeout`
- [ ] `test_stream_chat_propagates_cancellation`

All 7 tests must show `PASSED`.

---

## Quality gate

```bash
ruff check src/ollama/ tests/ollama/
mypy src/ollama/
pytest tests/ollama/ --tb=short
```

- [ ] `ruff` → 0 errors
- [ ] `mypy` → `Success: no issues found`
- [ ] `pytest` → 7 passed, 0 failed

---

## Phase 01 EXIT GATE ✓

- [ ] All 7 unit tests pass
- [ ] `is_ready()` confirmed never-raises (test proves it)
- [ ] Token streaming confirmed never-buffers (test proves it)
- [ ] No message content logged at any level (code review confirms)
- [ ] `ruff` and `mypy` both clean
