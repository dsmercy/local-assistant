# Phase 05 — FastAPI Server & Continue.dev Checklist

> Reference: `agent-instructions/phases/phase-05-continue-dev.md`

---

## Files created / modified

- [ ] `src/main.py` — full FastAPI app with DI wiring (no longer placeholder)
- [ ] `tests/test_server.py` — server integration tests

---

## DI composition review

Open `src/main.py` and verify:

- [ ] `lifespan` context manager checks Ollama on startup — raises `RuntimeError` if unreachable
- [ ] All services injected via `Depends()` — no service instantiated in route handlers
- [ ] `OllamaOptions`, `AgentOptions`, `RagOptions` loaded from env vars (pydantic-settings)
- [ ] CORS middleware allows only `vscode-webview://*` and `http://localhost:*`
- [ ] Server binds to `127.0.0.1` only — not `0.0.0.0`

---

## /chat endpoint tests

```bash
pytest tests/test_server.py -v
```

- [ ] `test_chat_returns_200_with_sse_content_type` — PASSED
- [ ] `test_chat_streams_tokens_not_buffered` — PASSED
- [ ] `test_chat_returns_400_for_empty_message` — PASSED
- [ ] `test_chat_returns_400_for_whitespace_only_message` — PASSED
- [ ] `test_chat_stream_ends_with_done_sentinel` — PASSED
- [ ] `test_server_does_not_expose_traceback_in_sse_stream` — PASSED

---

## Startup behaviour

```bash
# Test: Ollama NOT running → clear error message
# Stop ollama temporarily: ollama stop  (or kill the process)
uvicorn src.main:app --host 127.0.0.1 --port 8765 2>&1 | head -5
```

- [ ] Error message includes "Ollama is not running" (not a Python traceback)
- [ ] Server exits with non-zero code

```bash
# Test: Ollama running → server starts cleanly
ollama serve &
uvicorn src.main:app --host 127.0.0.1 --port 8765 &
sleep 2
curl -s http://127.0.0.1:8765/docs | grep -q "openapi"
echo "Server responding: $?"
```

- [ ] Server starts without errors
- [ ] `/docs` responds (FastAPI OpenAPI)

---

## End-to-end streaming test (requires Ollama)

```bash
make serve &
sleep 3
curl -N -X POST http://127.0.0.1:8765/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Say the word hello only"}' \
  --max-time 30
```

- [ ] Response shows `data: ` prefixed SSE events
- [ ] Final event is `data: [DONE]`
- [ ] Tokens appear progressively (not all at once after a delay)

---

## Continue.dev configuration

Open VS Code and verify Continue.dev is configured:

```bash
cat ~/.continue/config.json | python3 -m json.tool > /dev/null && echo "Valid JSON"
```

- [ ] `~/.continue/config.json` is valid JSON
- [ ] `models` array contains entry with `"model": "qwen2.5-coder:14b"`
- [ ] `tabAutocompleteModel` is set to `qwen2.5-coder:14b`
- [ ] `embeddingsProvider` model is `nomic-embed-text`
- [ ] `contextProviders` includes `"code"`, `"file"`, `"codebase"`

**Test in VS Code:**
- [ ] Open a `.py` or `.cs` file — autocomplete suggestions appear (may take a few seconds)
- [ ] `Cmd/Ctrl + L` opens the Continue chat panel
- [ ] Type a question in chat — response streams token by token
- [ ] `@codebase` in chat triggers codebase search

---

## Quality gate

```bash
pytest tests/test_server.py --tb=short
ruff check src/main.py
mypy src/main.py
```

- [ ] All server tests pass
- [ ] `ruff` → 0 errors
- [ ] `mypy` → `Success: no issues found`

---

## Phase 05 EXIT GATE ✓

- [ ] `/chat` endpoint streams tokens with `text/event-stream` content type
- [ ] Empty/whitespace message returns HTTP 400
- [ ] Server exits clearly when Ollama is not running
- [ ] Server binds to `127.0.0.1` only
- [ ] Stack traces never appear in SSE stream
- [ ] Continue.dev autocomplete works in VS Code
- [ ] `@codebase` context search works in Continue.dev chat
- [ ] `ruff` and `mypy` both clean
