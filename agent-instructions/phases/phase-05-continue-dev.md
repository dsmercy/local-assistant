# Phase 05 — FastAPI Server & Continue.dev Configuration

## Phase goal
Wire all components into a running FastAPI SSE server and configure Continue.dev
to use it as the AI backend. After this phase the agent works end-to-end in VS Code.

## Entry criteria
- [ ] Phase 04 exit gates passed · `pytest -x` green
- [ ] `scripts/ingest.py` has been run and `chroma_db/` is populated

## Active standards
§11 FastAPI standards · §19 Streaming · §20 Security · §23 Human collaboration

## Implementation

### Step 5.1 — Dependency wiring — `src/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify Ollama is ready
    client = OllamaClient(OllamaOptions())
    if not await client.is_ready():
        raise RuntimeError("Ollama is not running. Run 'ollama serve' to start it.")
    yield
    # Shutdown: close HTTP client

app = FastAPI(lifespan=lifespan)

# CORS — localhost only; adjust if your VS Code extension needs a specific origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["vscode-webview://*", "http://localhost:*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)
```

**Dependency factories (use `Depends()` in routes — never instantiate in handlers):**
```python
def get_ollama_options() -> OllamaOptions: return OllamaOptions()
def get_agent_options()  -> AgentOptions:  return AgentOptions()
def get_rag_options()    -> RagOptions:    return RagOptions()

async def get_agent_loop(
    ollama_opts: OllamaOptions = Depends(get_ollama_options),
    agent_opts:  AgentOptions  = Depends(get_agent_options),
    rag_opts:    RagOptions    = Depends(get_rag_options),
) -> AgentLoop:
    retriever = RagRetriever(rag_opts)
    builder   = ContextBuilder(
        base_prompt_path=Path("coding-agent-system-prompt.md"),
        retriever=retriever,
        phase_prompts_dir=Path("phases"),
    )
    ...
```

### Step 5.2 — /chat endpoint (SSE)

```
POST /chat
Body: { "message": str, "phase": str | null }
Response: text/event-stream
```

```python
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    phase: str | None = None

@app.post("/chat")
async def chat(
    request: ChatRequest,
    agent: AgentLoop = Depends(get_agent_loop),
) -> StreamingResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    async def token_stream():
        async for token in agent.run(request.message):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(token_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})
```

Rules:
- Never buffer tokens — yield each immediately
- Write `[DONE]` sentinel as the final SSE event
- Return `HTTPException(400)` for empty message
- Never expose tracebacks in SSE stream — catch exceptions, yield error token, close stream

### Step 5.3 — Run the server

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8765 --reload
```

Add a `Makefile` target:
```makefile
serve:
    uvicorn src.main:app --host 127.0.0.1 --port 8765 --reload

ingest:
    python scripts/ingest.py
```

### Step 5.4 — Continue.dev configuration

**File:** `~/.continue/config.json`

```json
{
  "models": [
    {
      "title": "Local Copilot (Qwen2.5-Coder)",
      "provider": "ollama",
      "model": "qwen2.5-coder:7b",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "Local Vision (LLaVA)",
      "provider": "ollama",
      "model": "llava:13b",
      "apiBase": "http://localhost:11434"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Qwen2.5-Coder Autocomplete",
    "provider": "ollama",
    "model": "qwen2.5-coder:7b",
    "apiBase": "http://localhost:11434"
  },
  "embeddingsProvider": {
    "provider": "ollama",
    "model": "nomic-embed-text",
    "apiBase": "http://localhost:11434"
  },
  "contextProviders": [
    { "name": "code" },
    { "name": "file" },
    { "name": "codebase" },
    { "name": "diff" },
    { "name": "terminal" }
  ],
  "slashCommands": [
    { "name": "edit",    "description": "Apply a targeted code edit" },
    { "name": "comment", "description": "Add docstrings and comments" },
    { "name": "test",    "description": "Generate unit tests" }
  ]
}
```

**Key Continue.dev shortcuts:**

| Action | Shortcut |
|---|---|
| Open chat panel | `Cmd/Ctrl + L` |
| Ask about selected code | Select → `Cmd/Ctrl + L` |
| Inline edit | `Cmd/Ctrl + I` |
| Add file to context | `@file` in chat |
| Search codebase | `@codebase` in chat |
| Switch to LLaVA (vision) | Click model name → select LLaVA |

### Step 5.5 — Integration test

**File:** `tests/test_server.py`

```python
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

def test_chat_streams_tokens():
    async def fake_run(msg):
        for token in ["Hello", " world"]:
            yield token

    with patch("src.main.get_agent_loop") as mock:
        mock.return_value.run = fake_run
        client = TestClient(app)
        response = client.post("/chat", json={"message": "hi"}, stream=True)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

def test_chat_rejects_empty_message():
    client = TestClient(app)
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 400
```

## Validation gate
```bash
pytest tests/test_server.py -v
ruff check src/main.py && mypy src/main.py

# Manual end-to-end
uvicorn src.main:app --host 127.0.0.1 --port 8765 &
curl -N -X POST http://127.0.0.1:8765/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Say hello in one sentence"}'
```

## Exit criteria
- [ ] `POST /chat` streams tokens with `text/event-stream` content type
- [ ] `POST /chat` with empty message returns 400
- [ ] Startup fails clearly if Ollama is not running
- [ ] Continue.dev connects to Ollama, autocomplete works in VS Code
- [ ] `@codebase` in Continue.dev chat uses `nomic-embed-text` embeddings
- [ ] Server does not expose tracebacks in SSE stream

## What not to do
- Do not bind to `0.0.0.0` in production — `127.0.0.1` only
- Do not add authentication beyond CORS (this is a local-only dev tool)
- Do not buffer tokens before writing to the SSE response
- Do not add any new tools or agent features in this phase
