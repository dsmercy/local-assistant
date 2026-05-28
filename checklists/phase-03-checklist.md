# Phase 03 — AgentLoop Checklist

> Reference: `agent-instructions/phases/phase-03-agent-loop.md`

---

## Files created

```bash
find src/agent tests/agent -type f | sort
```

- [ ] `src/agent/options.py` — `AgentOptions(BaseSettings)`
- [ ] `src/agent/exceptions.py` — `AgentDepthError`, `AgentStuckError`
- [ ] `src/agent/parser.py` — `ToolCallParser`
- [ ] `src/agent/loop.py` — `AgentLoop`
- [ ] `tests/agent/__init__.py`
- [ ] `tests/agent/test_loop.py`
- [ ] `tests/agent/test_parser.py`

---

## Code review checklist

Open `src/agent/loop.py` and verify:

- [ ] `run()` is an `async def` that returns `AsyncIterator[str]` via `yield`
- [ ] Tokens are `yield`-ed immediately inside the streaming loop — no `.append()` + yield-all pattern
- [ ] Depth counter is incremented **before** calling the tool
- [ ] `AgentDepthError` is caught internally → yields a user-facing error token → returns cleanly (does NOT re-raise)
- [ ] `AgentStuckError` is caught internally → yields a user-facing error token → returns cleanly
- [ ] Tool output is appended to conversation history as a `tool` role message — not re-parsed for instructions
- [ ] No tool arguments are logged at any level

---

## ToolCallParser tests

```bash
pytest tests/agent/test_parser.py -v
```

- [ ] `test_returns_none_for_incomplete_json` — PASSED
- [ ] `test_returns_none_for_plain_text_tokens` — PASSED
- [ ] `test_returns_tool_call_for_complete_json_block` — PASSED
- [ ] `test_catches_json_decode_error_returns_none` — PASSED

---

## AgentLoop unit tests

```bash
pytest tests/agent/test_loop.py -v
```

- [ ] `test_no_tool_call_streams_tokens_and_exits_cleanly` — PASSED
- [ ] `test_single_tool_call_executes_and_continues_stream` — PASSED
- [ ] `test_failed_tool_result_appended_model_continues` — PASSED
- [ ] `test_depth_limit_surfaces_as_error_token_stream_ends` — PASSED
- [ ] `test_stuck_detection_surfaces_as_error_token_stream_ends` — PASSED
- [ ] `test_cancellation_propagates_correctly` — PASSED
- [ ] `test_tool_output_with_instruction_text_not_executed` — PASSED

All 7 tests must show `PASSED`.

---

## Behaviour verification

```bash
# Quick manual smoke test (requires Ollama running)
python3 -c "
import asyncio
from src.agent.loop import AgentLoop
from src.agent.options import AgentOptions
from src.tools.registry import ToolRegistry
from src.ollama.client import OllamaClient
from src.ollama.options import OllamaOptions

async def main():
    client = OllamaClient(OllamaOptions())
    if not await client.is_ready():
        print('Ollama not running — skipping live test')
        return
    loop = AgentLoop(client=client, registry=ToolRegistry([]), options=AgentOptions())
    async for token in loop.run('Say hello in one word'):
        print(token, end='', flush=True)
    print()

asyncio.run(main())
"
```

- [ ] Tokens print one by one (streaming, not all at once)
- [ ] No exception raised
- [ ] Loop exits cleanly

---

## Quality gate

```bash
pytest tests/agent/ --tb=short
ruff check src/agent/
mypy src/agent/
```

- [ ] All 11+ tests pass
- [ ] `ruff` → 0 errors
- [ ] `mypy` → `Success: no issues found`

---

## Phase 03 EXIT GATE ✓

- [ ] Tokens stream immediately — confirmed by test
- [ ] Depth limit fires at configured maximum — confirmed by test
- [ ] Stuck detection fires on repeated identical calls — confirmed by test
- [ ] Tool output with instruction text does not cause execution — confirmed by test
- [ ] `AgentDepthError` and `AgentStuckError` surface as tokens, not raised exceptions
- [ ] No tool arguments logged at any level
- [ ] `ruff` and `mypy` both clean
