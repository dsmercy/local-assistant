# Phase 06 — Full Test Suite & Coverage Checklist

> Reference: `agent-instructions/phases/phase-06-testing.md`
> No new features in this phase — tests and coverage only.

---

## Coverage targets

Run:
```bash
pytest --cov=src --cov-report=term-missing --cov-report=html
```

Then open `htmlcov/index.html` and verify:

| Module | Required | Actual |
|---|---|---|
| `src/workspace/context.py` — `is_path_safe` | **100%** | ___ |
| `src/tools/run_command.py` — allow-list | **100%** | ___ |
| `src/tools/read_file.py` — path safety | **100%** | ___ |
| `src/tools/write_file.py` — atomic write | **100%** | ___ |
| `src/agent/loop.py` — depth + stuck | **100%** | ___ |
| `src/ollama/client.py` | **90%+** | ___ |
| `src/rag/context_builder.py` | **90%+** | ___ |
| **Overall** | **≥ 80%** | ___ |

- [ ] All modules meet or exceed their targets

---

## Security regression tests

```bash
pytest tests/security/ -v
```

### Path traversal (all file tools)
- [ ] `test_read_file_rejects_dotdot_traversal[../../etc/passwd]` — PASSED
- [ ] `test_read_file_rejects_absolute_path[/etc/passwd]` — PASSED
- [ ] `test_read_file_rejects_null_byte[file\x00.py]` — PASSED
- [ ] `test_write_file_rejects_dotdot_traversal` — PASSED
- [ ] `test_list_files_rejects_directory_outside_root` — PASSED
- [ ] `test_search_files_rejects_directory_outside_root` — PASSED

### Command allow-list
- [ ] `test_run_command_rejects_rm` — PASSED
- [ ] `test_run_command_rejects_bash` — PASSED
- [ ] `test_run_command_rejects_curl` — PASSED
- [ ] `test_run_command_rejects_powershell` — PASSED
- [ ] `test_run_command_rejects_shell_injection[pytest; rm -rf /]` — PASSED
- [ ] `test_run_command_rejects_shell_injection[dotnet && rm -rf /]` — PASSED

### Prompt injection
- [ ] `test_agent_does_not_execute_instructions_in_tool_output` — PASSED
- [ ] `test_agent_does_not_execute_instructions_in_file_contents` — PASSED

---

## Idempotency tests

```bash
pytest tests/rag/test_ingest.py::test_ingest_twice_does_not_duplicate_chunks -v
```

- [ ] Test passes — second ingest does not double the chunk count

---

## Cancellation & timeout tests

```bash
pytest -k "cancellation or timeout" -v
```

- [ ] All cancellation tests pass (one per async tool/client method)
- [ ] `RunCommandTool` timeout test passes

---

## Full suite run

```bash
pytest --tb=short -q
```

- [ ] 0 failures
- [ ] 0 errors
- [ ] 0 skipped (all tests run)

---

## Code quality final check

```bash
ruff check .
mypy src/
```

- [ ] `ruff` → 0 errors across the entire codebase
- [ ] `mypy` → `Success: no issues found` across entire `src/`

---

## Phase 06 EXIT GATE ✓

- [ ] `pytest --cov=src --cov-fail-under=80` exits 0
- [ ] All security regression tests pass (path traversal, allow-list, injection)
- [ ] All cancellation and timeout tests pass
- [ ] Idempotency test passes
- [ ] Overall coverage ≥ 80%
- [ ] `is_path_safe` coverage = 100%
- [ ] Allow-list coverage = 100%
- [ ] `ruff` and `mypy` both completely clean
- [ ] No production code changed in this phase (confirmed by `git diff src/` showing only test additions)
