# Phase 00 — Scaffold & Toolchain Checklist

> Run every command exactly as written. Tick each box only when the command output matches.

---

## Pre-flight: system requirements

- [ ] Python 3.11+: `python --version` → shows `3.11.x` or higher
- [ ] Ollama installed: `ollama --version` → shows a version number
- [ ] Git initialised: `git status` → works without error

---

## Step 1 — Virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python --version                 # must still show 3.11+
```

- [ ] `.venv/` directory exists
- [ ] `which python` (or `where python`) points inside `.venv/`

---

## Step 2 — Install dependencies

```bash
pip install -e ".[dev]"
```

- [ ] Command exits with code 0 (no errors)
- [ ] `pip list | grep langchain` shows a version
- [ ] `pip list | grep chromadb` shows a version
- [ ] `pip list | grep pytest` shows a version

---

## Step 3 — Pull Ollama models

```bash
make pull-models
ollama list
```

- [ ] `qwen2.5-coder:14b` appears in `ollama list`
- [ ] `nomic-embed-text` appears in `ollama list`
- [ ] `llava:13b` appears in `ollama list`

---

## Step 4 — Environment config

```bash
cp .env.example .env
cat .env
```

- [ ] `.env` file exists
- [ ] `OLLAMA_MODEL_NAME=qwen2.5-coder:14b` is set
- [ ] `.env` is listed in `.gitignore` (run `git check-ignore .env` → prints `.env`)

---

## Step 5 — Folder structure

```bash
find src -type f | sort
find tests -type f | sort
```

- [ ] `src/__init__.py` exists
- [ ] `src/agent/__init__.py` exists
- [ ] `src/tools/__init__.py` exists
- [ ] `src/ollama/__init__.py` exists
- [ ] `src/rag/__init__.py` exists
- [ ] `src/workspace/__init__.py` exists
- [ ] `src/main.py` exists (placeholder)
- [ ] `tests/__init__.py` and all sub-package `__init__.py` files exist

---

## Step 6 — Quality gate

```bash
ruff check src/
mypy src/
pytest
```

- [ ] `ruff check src/` → `All checks passed.` or `0 errors`
- [ ] `mypy src/` → `Success: no issues found`
- [ ] `pytest` → `0 passed` or `no tests ran`, exit code 0

---

## Phase 00 EXIT GATE ✓

All of the following must be true before starting Phase 01:

- [ ] `python -m pytest` exits 0
- [ ] `ruff check .` exits 0
- [ ] `mypy src/` exits 0
- [ ] `ollama list` shows all 3 models
- [ ] `.env` exists and is in `.gitignore`
- [ ] `chroma_db/` is in `.gitignore`
