# Phase 02 — Tool Implementations Checklist

> Reference: `agent-instructions/phases/phase-02-tools.md`
> Implement and test ONE tool at a time. Do not move to the next tool until its tests pass.

---

## WorkspaceContext & base types

Files:
- [ ] `src/workspace/context.py` — `WorkspaceContext`, `PathSafetyError`, `WorkspaceNotFoundError`
- [ ] `src/tools/base.py` — `ToolCall`, `ToolResult` (frozen dataclasses), `ToolHandler` (Protocol)
- [ ] `src/tools/registry.py` — `ToolRegistry`, `ToolNotFoundException`, `ToolDepthExceededError`
- [ ] `tests/workspace/test_context.py`
- [ ] `tests/tools/test_registry.py`

```bash
pytest tests/workspace/ tests/tools/test_registry.py -v
```

WorkspaceContext tests:
- [ ] `test_is_path_safe_returns_true_for_valid_path`
- [ ] `test_is_path_safe_returns_false_for_dotdot_traversal`
- [ ] `test_is_path_safe_returns_false_for_null_byte`
- [ ] `test_is_path_safe_returns_false_for_out_of_root_path`
- [ ] `test_raises_workspace_not_found_when_no_project_file`

ToolRegistry tests:
- [ ] `test_resolve_returns_handler_for_known_tool`
- [ ] `test_resolve_raises_for_unknown_tool`
- [ ] `test_depth_exceeded_raises_after_limit`

---

## Tool 1 — ReadFileTool

- [ ] `src/tools/read_file.py` created
- [ ] `tests/tools/test_read_file.py` created

```bash
pytest tests/tools/test_read_file.py -v
```

- [ ] `test_reads_file_within_workspace` — PASSED
- [ ] `test_raises_path_safety_error_for_dotdot` — PASSED
- [ ] `test_raises_path_safety_error_for_null_byte` — PASSED
- [ ] `test_returns_error_result_when_file_not_found` — PASSED
- [ ] `test_returns_error_result_when_file_exceeds_512kb` — PASSED
- [ ] `test_propagates_cancellation` — PASSED

---

## Tool 2 — ListFilesTool

- [ ] `src/tools/list_files.py` created
- [ ] `tests/tools/test_list_files.py` created

```bash
pytest tests/tools/test_list_files.py -v
```

- [ ] `test_lists_files_in_valid_directory` — PASSED
- [ ] `test_raises_path_safety_error_for_directory_outside_root` — PASSED
- [ ] `test_truncates_at_500_files_with_notice` — PASSED
- [ ] `test_excludes_pycache_and_venv_always` — PASSED
- [ ] `test_respects_gitignore_patterns` — PASSED

---

## Tool 3 — SearchFilesTool

- [ ] `src/tools/search_files.py` created
- [ ] `tests/tools/test_search_files.py` created

```bash
pytest tests/tools/test_search_files.py -v
```

- [ ] `test_literal_match_returns_correct_file_and_line` — PASSED
- [ ] `test_regex_match_returns_correct_file_and_line` — PASSED
- [ ] `test_invalid_regex_returns_error_result` — PASSED
- [ ] `test_no_matches_returns_success_with_no_matches_message` — PASSED
- [ ] `test_truncates_at_200_matches_with_notice` — PASSED
- [ ] `test_raises_path_safety_error_for_outside_root` — PASSED

---

## Tool 4 — WriteFileTool

- [ ] `src/tools/write_file.py` created
- [ ] `tests/tools/test_write_file.py` created

```bash
pytest tests/tools/test_write_file.py -v
```

- [ ] `test_full_file_write_matches_content_exactly` — PASSED
- [ ] `test_line_range_patch_replaces_only_targeted_lines` — PASSED
- [ ] `test_out_of_bounds_range_returns_error_result` — PASSED
- [ ] `test_raises_path_safety_error_for_outside_root` — PASSED
- [ ] `test_missing_parent_directory_returns_error_result` — PASSED
- [ ] `test_atomic_write_leaves_no_partial_file_on_failure` — PASSED

---

## Tool 5 — RunCommandTool

- [ ] `src/tools/run_command.py` created
- [ ] `tests/tools/test_run_command.py` created

```bash
pytest tests/tools/test_run_command.py -v
```

- [ ] `test_allowed_command_returns_success_on_exit_0` — PASSED
- [ ] `test_allowed_command_returns_failure_with_stderr_on_exit_1` — PASSED
- [ ] `test_disallowed_executable_raises_value_error_immediately` — PASSED (e.g. `rm`, `bash`)
- [ ] `test_unknown_subcommand_raises_value_error` — PASSED
- [ ] `test_timeout_returns_error_result` — PASSED
- [ ] `test_propagates_cancellation` — PASSED

---

## Security regression — run after all tools

```bash
pytest tests/security/ -v
```

- [ ] Path traversal `../../etc/passwd` rejected by every file tool
- [ ] Null byte `\x00` in path rejected by every file tool
- [ ] Absolute paths outside workspace root rejected
- [ ] Non-allowed executables (`rm`, `bash`, `curl`, `powershell`) raise `ValueError`

---

## Quality gate

```bash
pytest tests/workspace/ tests/tools/ tests/security/ --tb=short
ruff check src/tools/ src/workspace/
mypy src/tools/ src/workspace/
```

- [ ] All tests pass (≥ 30 tests expected)
- [ ] `ruff` → 0 errors
- [ ] `mypy` → `Success: no issues found`

---

## Phase 02 EXIT GATE ✓

- [ ] All 5 tools implemented and passing their full test suites
- [ ] `PathSafetyError` raised correctly by every file tool (automated)
- [ ] `ValueError` raised by `RunCommandTool` on non-allowed command (automated)
- [ ] `WriteFileTool` atomic write confirmed (test proves no partial file)
- [ ] Security regression tests all green
- [ ] `ruff` and `mypy` both clean
