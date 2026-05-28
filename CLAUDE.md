# Local AI Copilot — Claude Code Project

<!--
  This file is read automatically by Claude Code at session start.
  It describes the project layout, commands, rules, and how to work phase-by-phase.
-->

## Project overview

A fully local AI coding assistant **built in Python**, designed for a **.NET fullstack
developer** who also uses React, TypeScript, Node.js, and JavaScript.

| What | How |
|---|---|
| Agent infrastructure | Python · Ollama · LangChain · ChromaDB · FastAPI |
| Developer help target | C# · ASP.NET Core · EF Core · React · Node.js · JS |
| Model | `qwen2.5-coder:14b` via Ollama |
| IDE interface | Continue.dev (VS Code) — sole interface |

---

## Folder structure

```
local-ai-copilot/
├── CLAUDE.md                          ← YOU ARE HERE
├── .claude/
│   ├── settings.json                  ← Claude Code permissions
│   └── commands/                      ← Custom /slash commands
├── agent-instructions/                ← ALL agent prompt files (read-only)
│   ├── system-prompt.md               ← Base system prompt (33 sections)
│   └── phases/                        ← Phase-specific prompt injections
│       ├── phase-index.md
│       ├── phase-00-scaffold.md … phase-07-finetune.md
├── checklists/                        ← Phase test checklists
│   ├── phase-00-checklist.md … phase-07-checklist.md
├── src/                               ← Python agent source (built phase by phase)
│   ├── main.py
│   ├── agent/    loop.py · parser.py · options.py · exceptions.py
│   ├── tools/    base.py · registry.py · read_file.py · write_file.py
│   │             list_files.py · search_files.py · run_command.py
│   ├── ollama/   client.py · options.py · types.py · exceptions.py
│   ├── rag/      ingest.py · retriever.py · context_builder.py · options.py
│   └── workspace/context.py
├── tests/
│   ├── agent/ · tools/ · ollama/ · rag/ · workspace/ · security/
├── scripts/
│   ├── ingest.py                      ← Run RAG ingestion
│   └── finetune.py                    ← Unsloth LoRA fine-tuning
├── context_store/
│   ├── instructions/                  ← Drop .md standards files here
│   ├── codebase/                      ← Drop .cs/.py source files here
│   └── samples/                       ← Drop canonical patterns here
├── modelfiles/                        ← Ollama Modelfiles
├── pyproject.toml
├── Makefile
├── .env.example
└── .gitignore
```

---

## How the agent instructions work

The agent is guided by two layers loaded at query time:

```python
# src/rag/context_builder.py
BASE_PROMPT  = Path("agent-instructions/system-prompt.md").read_text()
PHASE_PROMPT = Path(f"agent-instructions/phases/phase-{n:02d}-{name}.md").read_text()
system_prompt = BASE_PROMPT + "\n\n---\n\n" + PHASE_PROMPT
```

**Do not edit files in `agent-instructions/`** — they are prompt definitions,
not source code. Claude Code writes to `src/`, `tests/`, and `scripts/` only.

---

## Common commands

```bash
make setup        # create venv + install dependencies
make pull-models  # ollama pull qwen2.5-coder:14b + nomic-embed-text + llava:13b
make ingest       # index context_store/ into ChromaDB
make serve        # start FastAPI agent server on localhost:8765
make test         # pytest -x --cov=src
make check        # ruff check . && mypy src/
make all          # check + test
```

---

## Phase-by-phase build workflow

Work through phases in order. Each phase has:
- A **prompt file** in `agent-instructions/phases/` — load it for implementation context
- A **checklist** in `checklists/` — verify every item before moving to the next phase

| Phase | Prompt file | Checklist | Goal |
|---|---|---|---|
| 00 | `phase-00-scaffold.md` | `phase-00-checklist.md` | Toolchain, venv, pyproject.toml |
| 01 | `phase-01-ollama-client.md` | `phase-01-checklist.md` | Async OllamaClient |
| 02 | `phase-02-tools.md` | `phase-02-checklist.md` | 5 tool handlers + WorkspaceContext |
| 03 | `phase-03-agent-loop.md` | `phase-03-checklist.md` | AgentLoop streaming cycle |
| 04 | `phase-04-rag-pipeline.md` | `phase-04-checklist.md` | ChromaDB ingest + context builder |
| 05 | `phase-05-continue-dev.md` | `phase-05-checklist.md` | FastAPI SSE server + Continue.dev |
| 06 | `phase-06-testing.md` | `phase-06-checklist.md` | Full test suite + coverage ≥ 80% |
| 07 | `phase-07-finetune.md` | `phase-07-checklist.md` | Unsloth fine-tuning (optional) |

**To start a phase, tell Claude Code:**
> "Load `agent-instructions/phases/phase-02-tools.md` and begin Phase 02."

Or use the slash command: `/phase 02`

---

## Architecture rules (Claude Code must enforce these)

- `agent-instructions/` is **read-only** — never generate code inside it
- `checklists/` is **read-only** — never modify checklists during a phase
- `src/workspace/context.py` is the **only** place `is_path_safe()` lives
- `src/main.py` is the **composition root only** — no business logic
- All config via `pydantic_settings.BaseSettings` + `.env` — never hardcoded
- All HTTP via `httpx.AsyncClient` — never `requests` in async code
- `run_command` allow-list: `pytest`, `ruff`, `mypy`, `black`, `pip`, `dotnet`, `npm`, `npx`, `node`, `tsc`, `vitest`, `eslint`

---

## Validation commands (run after every change)

```bash
# Minimum gate — must pass before committing any step
pytest -x && ruff check . && mypy src/

# Full gate — must pass before closing a phase
pytest --cov=src --cov-fail-under=80 && ruff check . && mypy src/
```

---

## Folders Claude Code must never read

```
.venv/   __pycache__/   chroma_db/   lora_output/   *.gguf
node_modules/   dist/   build/   .git/   *.lock   coverage/
```
