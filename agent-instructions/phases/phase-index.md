# Phase Prompt Index

<!--
  Each phase file is injected on top of agent-instructions/system-prompt.md.
  Load order: system-prompt.md  +  phases/phase-XX-name.md (one at a time)
  Complete every exit gate and checklist before moving to the next phase.
-->

## Phase map

| # | File | Goal | Checklist |
|---|---|---|---|
| 00 | `phase-00-scaffold.md` | Repo layout, venv, pyproject.toml | `checklists/phase-00-checklist.md` |
| 01 | `phase-01-ollama-client.md` | Async OllamaClient with streaming | `checklists/phase-01-checklist.md` |
| 02 | `phase-02-tools.md` | 5 ToolHandlers + WorkspaceContext | `checklists/phase-02-checklist.md` |
| 03 | `phase-03-agent-loop.md` | AgentLoop: stream → detect → execute | `checklists/phase-03-checklist.md` |
| 04 | `phase-04-rag-pipeline.md` | ChromaDB ingest + context builder | `checklists/phase-04-checklist.md` |
| 05 | `phase-05-continue-dev.md` | FastAPI SSE server + Continue.dev | `checklists/phase-05-checklist.md` |
| 06 | `phase-06-testing.md` | Full pytest suite + coverage ≥ 80% | `checklists/phase-06-checklist.md` |
| 07 | `phase-07-finetune.md` | Unsloth LoRA fine-tuning (optional) | `checklists/phase-07-checklist.md` |

## Global rules (apply in every phase)

- Run `pytest -x && ruff check . && mypy src/` after every implementation step
- Verify every item in the phase checklist before moving on
- Never implement code from a future phase speculatively
- All public functions must have full type annotations and docstrings
- Agent instruction files (`agent-instructions/`) are read-only — never modify them

## How to load a phase prompt

```python
# src/rag/context_builder.py
BASE  = Path("agent-instructions/system-prompt.md").read_text()
PHASE = Path(f"agent-instructions/phases/phase-{n:02d}-{name}.md").read_text()
system_prompt = BASE + "\n\n---\n\n" + PHASE
```

## Claude Code slash command

```
/phase 02   →  loads phase-02-tools.md and begins implementation
```
