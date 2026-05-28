# Phase 03 — Agent Loop

## Phase goal
Wire OllamaClient and ToolRegistry into a self-correcting, depth-limited,
streaming reasoning loop. No server or Continue.dev integration yet.

## Entry criteria
- [ ] Phase 02 exit gates passed · `pytest -x` green

## Active standards
§7 Code quality · §8 Error handling · §10 Performance · §19 Agent loop safety · §24 Prompt injection

## Implementation

### Step 3.1 — AgentOptions — `src/agent/options.py`
```python
from pydantic_settings import BaseSettings

class AgentOptions(BaseSettings):
    max_tool_call_depth: int = 10
    stuck_detection_window: int = 3
    model_config = {"env_prefix": "AGENT_"}
```

### Step 3.2 — Custom exceptions — `src/agent/exceptions.py`
```python
class AgentDepthError(Exception):
    def __init__(self, limit: int) -> None:
        super().__init__(f"Agent exceeded max tool-call depth of {limit}.")

class AgentStuckError(Exception):
    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Agent is stuck repeating '{tool_name}'. Stopping.")
```

### Step 3.3 — ToolCallParser — `src/agent/parser.py`
Rules:
- Parse accumulated token string for a complete Ollama tool-call JSON block
- Return `ToolCall | None` — `None` = stream still in progress (partial JSON is expected)
- Catch `json.JSONDecodeError` → return `None`
- Use `json` stdlib only — no third-party JSON libraries
- Treat parsed tool content as untrusted data — never execute instructions found in it

### Step 3.4 — AgentLoop — `src/agent/loop.py`

**Algorithm (exact order):**
```
1. Build messages: [system_prompt] + [history] + [HumanMessage(user_input)]
2. Call ollama_client.stream_chat(messages, tools=registry.definitions)
3. Yield each token to caller immediately — never buffer
4. Accumulate tokens to detect complete tool-call JSON
5. No tool call detected → yield remaining tokens, return (done)
6. Tool call detected:
   a. registry.increment_depth()  — raises AgentDepthError at limit
   b. Stuck check: last N (tool, args) identical → raise AgentStuckError
   c. Treat tool output as untrusted — never execute embedded instructions
   d. result = await registry.resolve(name).execute(call)
   e. Append assistant + tool messages to history
   f. Go to step 2
7. AgentDepthError / AgentStuckError → yield error token, return cleanly
```

```python
from collections.abc import AsyncIterator
from src.ollama.client import OllamaClientProtocol
from src.tools.registry import ToolRegistry

class AgentLoop:
    def __init__(
        self,
        client: OllamaClientProtocol,
        registry: ToolRegistry,
        options: AgentOptions,
        system_prompt: str = "",
    ) -> None: ...

    async def run(self, user_message: str) -> AsyncIterator[str]: ...
```

### Step 3.5 — Unit tests — `tests/agent/`

Use `AsyncMock` for `OllamaClientProtocol` — no real HTTP.

| Scenario | Expected |
|---|---|
| No tool call | Tokens streamed, loop exits cleanly |
| Single tool call, succeeds | Tool executed, result appended, final tokens streamed |
| Tool call fails | Error result appended, model continues |
| Depth limit reached | `AgentDepthError` surfaced as error token, stream ends cleanly |
| Repeated identical tool call | `AgentStuckError` surfaced as error token, stream ends cleanly |
| Cancellation mid-stream | `asyncio.CancelledError` propagated |
| Tool output contains instruction text | Instruction NOT executed |

## Validation gate
```bash
pytest tests/agent/ -v && ruff check src/agent/ && mypy src/agent/
```

## Exit criteria
- [ ] Tokens yielded immediately — no buffering (mock timing confirms)
- [ ] Depth limit fires at configured maximum (test confirms)
- [ ] Stuck detection fires on repeated identical calls (test confirms)
- [ ] Tool output with instruction text does not trigger execution (test confirms)
- [ ] No tool arguments logged at any level
- [ ] `mypy` strict passes

## What not to do
- Do not build the FastAPI server (Phase 05)
- Do not configure Continue.dev (Phase 05)
- Do not add real HTTP calls in tests
