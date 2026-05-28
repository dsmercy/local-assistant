# Phase 00 — Project Scaffold & Toolchain

## Phase goal
Produce a clean, runnable project skeleton with virtual environment, pyproject.toml,
folder structure, and all dependencies pinned. No implementation code yet.

## Entry criteria
- [ ] Python 3.11+ installed: `python --version`
- [ ] Ollama installed and running: `ollama list`
- [ ] Git repo initialised with `.gitignore` excluding `.venv/`, `__pycache__/`, `*.pyc`

## Tasks

### Task 0.1 — Create project layout
```bash
mkdir local-ai-copilot && cd local-ai-copilot
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

mkdir -p src/{agent,tools,ollama,rag,workspace} tests/{agent,tools,rag,workspace} phases
touch src/__init__.py
touch src/{agent,tools,ollama,rag,workspace}/__init__.py
```

### Task 0.2 — pyproject.toml
```toml
[project]
name = "local-ai-copilot"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "langchain>=0.3",
    "langchain-ollama>=0.2",
    "langchain-community>=0.3",
    "langchain-core>=0.3",
    "chromadb>=0.5",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "httpx>=0.27",
    "structlog>=24.1",
    "aiofiles>=23.2",
    "tenacity>=8.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "ruff>=0.4",
    "mypy>=1.10",
    "pytest-cov>=5.0",
]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "UP", "B", "SIM", "ANN"]
ignore = ["ANN101"]

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

```bash
pip install -e ".[dev]"
```

### Task 0.3 — Environment config (.env)
```bash
# .env  (never commit — add to .gitignore)
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL_NAME=qwen2.5-coder:7b
OLLAMA_TIMEOUT_SECONDS=120
AGENT_MAX_TOOL_CALL_DEPTH=10
AGENT_STUCK_DETECTION_WINDOW=3
```

### Task 0.4 — Pull required models
```bash
ollama pull qwen2.5-coder:7b
ollama pull llava:13b
ollama pull nomic-embed-text
ollama list   # verify all three present
```

### Task 0.5 — Confirm toolchain
```bash
ruff check src/        # expect: no issues
mypy src/              # expect: success (no files yet — that's fine)
pytest                 # expect: no tests collected
```

## Exit criteria
- [ ] `pip install -e ".[dev]"` completes without errors
- [ ] `ruff check src/` passes
- [ ] `pytest` exits 0 (zero tests, zero failures)
- [ ] `.env` present and in `.gitignore`
- [ ] All three Ollama models pulled and listed

## What not to do
- Do not write any implementation code
- Do not commit `.env` or `.venv/`
- Do not add packages beyond the list above
