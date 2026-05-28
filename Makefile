.PHONY: all setup serve ingest test check coverage pull-models finetune clean

# ── Setup ──────────────────────────────────────────────────────────────────
setup:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	cp -n .env.example .env || true
	@echo "\nSetup complete. Activate: source .venv/bin/activate"

pull-models:
	ollama pull qwen2.5-coder:14b
	ollama pull nomic-embed-text
	ollama pull llava:13b
	@echo "\nAll models ready."

# ── Development ────────────────────────────────────────────────────────────
serve:
	uvicorn src.main:app --host 127.0.0.1 --port 8765 --reload

ingest:
	python scripts/ingest.py

# ── Quality ────────────────────────────────────────────────────────────────
check:
	ruff check .
	mypy src/

test:
	pytest -x --cov=src --cov-report=term-missing

coverage:
	pytest --cov=src --cov-report=html --cov-fail-under=80
	@echo "\nOpen: htmlcov/index.html"

all: check test

# ── Phase shortcuts ────────────────────────────────────────────────────────
phase-00:
	@echo "Phase 00: check checklists/phase-00-checklist.md"
	@make check
phase-01:
	pytest tests/ollama/ -v && ruff check src/ollama/ && mypy src/ollama/
phase-02:
	pytest tests/workspace/ tests/tools/ tests/security/ -v && ruff check src/tools/ src/workspace/ && mypy src/tools/ src/workspace/
phase-03:
	pytest tests/agent/ -v && ruff check src/agent/ && mypy src/agent/
phase-04:
	pytest tests/rag/ -v && ruff check src/rag/ && mypy src/rag/
phase-05:
	pytest tests/test_server.py -v && ruff check src/main.py && mypy src/main.py
phase-06:
	pytest --cov=src --cov-fail-under=80 -v && ruff check . && mypy src/
phase-07:
	@echo "Phase 07: run python scripts/finetune.py manually"

# ── Fine-tuning ────────────────────────────────────────────────────────────
finetune:
	python scripts/finetune.py

# ── Cleanup ────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ | xargs rm -rf 2>/dev/null || true
	find . -type d -name .mypy_cache | xargs rm -rf 2>/dev/null || true
	find . -type d -name .ruff_cache | xargs rm -rf 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov .coverage dist build *.egg-info 2>/dev/null || true
	@echo "Clean complete"
