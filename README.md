# Local AI Copilot

A fully local AI coding assistant built in **Python**, designed for a **.NET fullstack
developer** who also works with React, TypeScript, Node.js, and JavaScript.
No external API calls. No usage costs. Everything runs on your machine.

## Stack

| Layer | Tech |
|---|---|
| Agent infrastructure | Python 3.11 · FastAPI · LangChain · ChromaDB |
| LLM | Ollama `qwen2.5-coder:14b` |
| Embeddings | `nomic-embed-text` via Ollama |
| Developer help target | C# · ASP.NET Core · EF Core · React · Node.js · JS |
| IDE interface | Continue.dev (VS Code) |

## Quick start

```bash
# 1. Clone & setup
git clone <your-repo> && cd local-ai-copilot
make setup                     # creates .venv + installs deps + copies .env

# 2. Start Ollama and pull models
ollama serve &
make pull-models               # downloads qwen2.5-coder:14b + nomic-embed-text + llava:13b

# 3. Add your context (optional but recommended)
#    Drop .md docs into context_store/instructions/
#    Drop .cs/.py source into context_store/codebase/
#    Drop patterns into context_store/samples/
make ingest

# 4. Start the agent server
make serve

# 5. Open VS Code with Continue.dev
#    Config: see agent-instructions/phases/phase-05-continue-dev.md
```

## Build phases

This project is built incrementally using Claude Code.
Open this repo in Claude Code — `CLAUDE.md` is read automatically.

| Phase | Goal | Checklist |
|---|---|---|
| 00 | Scaffold & toolchain | `checklists/phase-00-checklist.md` |
| 01 | OllamaClient | `checklists/phase-01-checklist.md` |
| 02 | Tool implementations | `checklists/phase-02-checklist.md` |
| 03 | AgentLoop | `checklists/phase-03-checklist.md` |
| 04 | RAG pipeline | `checklists/phase-04-checklist.md` |
| 05 | FastAPI server + Continue.dev | `checklists/phase-05-checklist.md` |
| 06 | Test suite + coverage | `checklists/phase-06-checklist.md` |
| 07 | Fine-tuning (optional) | `checklists/phase-07-checklist.md` |

**To start a phase in Claude Code:** `/phase 00`

## Commands

| Command | Description |
|---|---|
| `make setup` | Create venv + install deps |
| `make pull-models` | Pull all Ollama models |
| `make serve` | Start agent server |
| `make ingest` | Index context_store/ into ChromaDB |
| `make test` | Run pytest with coverage |
| `make check` | ruff + mypy |
| `make all` | check + test |
| `make phase-XX` | Run validation gate for phase XX |

## Agent instructions

All agent prompt files live in `agent-instructions/`:

```
agent-instructions/
├── system-prompt.md          ← 33-section base prompt (loaded every query)
└── phases/
    ├── phase-index.md
    ├── phase-00-scaffold.md … phase-07-finetune.md
```

These are referenced directly by `src/rag/context_builder.py` at query time.
**Do not modify these files** — they are prompt definitions, not source code.
