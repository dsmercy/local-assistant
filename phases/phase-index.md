# Phase Prompt Index

<!--
  Each phase file is injected on top of coding-agent-system-prompt.md.
  Load: BASE_SYSTEM_PROMPT + phases/phase-XX-name.md (one at a time)
  Complete every exit gate before moving to the next phase.
-->

## Phase map

| # | File | Goal | Stack |
|---|---|---|---|
| 00 | `phase-00-scaffold.md` | Project layout, venv, pyproject.toml | Python toolchain |
| 01 | `phase-01-ollama-client.md` | Async OllamaClient with streaming | httpx, asyncio |
| 02 | `phase-02-tools.md` | All five ToolHandler implementations | pathlib, asyncio, subprocess |
| 03 | `phase-03-agent-loop.md` | AgentLoop: stream → detect → execute → loop | LangChain, asyncio |
| 04 | `phase-04-rag-pipeline.md` | ChromaDB ingestion + retrieval + context builder | LangChain, ChromaDB |
| 05 | `phase-05-continue-dev.md` | Continue.dev config + FastAPI SSE server | FastAPI, Continue.dev |
| 06 | `phase-06-testing.md` | Full pytest suite, security regression, coverage | pytest, respx |
| 07 | `phase-07-finetune.md` | Unsloth LoRA fine-tuning + GGUF → Ollama import | Unsloth, trl |

## Global rules (every phase)

- Run `pytest -x && ruff check . && mypy src/` after every implementation step
- Never proceed to the next phase until all exit gates pass
- Never implement code from a future phase speculatively
- All public functions must have full type annotations and docstrings

## How to load a phase prompt

```python
# context_builder.py
BASE  = Path("coding-agent-system-prompt.md").read_text()
PHASE = Path(f"phases/phase-{phase_number:02d}-{phase_name}.md").read_text()
system_prompt = BASE + "\n\n---\n\n" + PHASE
```
