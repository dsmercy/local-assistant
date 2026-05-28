# Phase 04 — RAG Pipeline Checklist

> Reference: `agent-instructions/phases/phase-04-rag-pipeline.md`

---

## Files created

```bash
find src/rag tests/rag scripts -type f | sort
```

- [ ] `src/rag/options.py` — `RagOptions(BaseSettings)`
- [ ] `src/rag/ingest.py` — `ingest_collection()` async function
- [ ] `src/rag/retriever.py` — `RagRetriever` class
- [ ] `src/rag/context_builder.py` — `ContextBuilder` class
- [ ] `scripts/ingest.py` — runnable ingest script
- [ ] `tests/rag/__init__.py`
- [ ] `tests/rag/test_ingest.py`
- [ ] `tests/rag/test_retriever.py`
- [ ] `tests/rag/test_context_builder.py`

---

## Ingest tests

```bash
pytest tests/rag/test_ingest.py -v
```

- [ ] `test_ingest_returns_correct_chunk_count_for_small_file` — PASSED
- [ ] `test_ingest_tags_each_chunk_with_collection_name` — PASSED
- [ ] `test_ingest_tags_each_chunk_with_relative_source_path` — PASSED
- [ ] `test_ingest_twice_does_not_duplicate_chunks` — PASSED (idempotency)

---

## Retriever tests

```bash
pytest tests/rag/test_retriever.py -v
```

- [ ] `test_retrieve_returns_results_from_all_three_collections` — PASSED
- [ ] `test_retrieve_instructions_uses_separate_collection` — PASSED
- [ ] `test_retrieve_codebase_uses_separate_collection` — PASSED
- [ ] `test_retrieve_samples_uses_separate_collection` — PASSED

---

## ContextBuilder tests

```bash
pytest tests/rag/test_context_builder.py -v
```

- [ ] `test_build_base_only_returns_system_prompt` — PASSED
- [ ] `test_build_with_phase_includes_phase_section` — PASSED
- [ ] `test_build_with_rag_includes_all_three_section_headers` — PASSED
- [ ] `test_build_caps_total_length_and_does_not_crash` — PASSED
- [ ] `test_system_prompt_read_from_agent_instructions_path` — PASSED

---

## Manual ingest smoke test (requires Ollama + nomic-embed-text)

```bash
# Add a test file to context_store
echo "# Test standard\nAlways use type hints." > context_store/instructions/test.md

# Run ingest
python scripts/ingest.py
```

- [ ] Script prints progress: `instructions: N chunks from 1 files`
- [ ] `chroma_db/` directory is created
- [ ] Script exits 0

```bash
# Verify retrieval works
python3 -c "
from src.rag.options import RagOptions
from src.rag.retriever import RagRetriever
opts = RagOptions()
r = RagRetriever(opts)
results = r.retrieve('type hints')
print('instructions:', len(results['instructions']), 'chunks')
print('codebase:', len(results['codebase']), 'chunks')
print('samples:', len(results['samples']), 'chunks')
"
```

- [ ] `instructions: N chunks` (N ≥ 1)
- [ ] No exception raised

---

## ContextBuilder integration check

```bash
python3 -c "
from pathlib import Path
from src.rag.options import RagOptions
from src.rag.retriever import RagRetriever
from src.rag.context_builder import ContextBuilder
opts = RagOptions()
builder = ContextBuilder(
    base_prompt_path=Path('agent-instructions/system-prompt.md'),
    retriever=RagRetriever(opts),
    phase_prompts_dir=Path('agent-instructions/phases'),
)
prompt = builder.build('type hints python', phase='phase-01-ollama-client')
print(f'Prompt length: {len(prompt)} chars')
assert '## Relevant standards' in prompt or len(prompt) > 1000
print('OK')
"
```

- [ ] Prints `Prompt length: XXXX chars` (should be > 5000)
- [ ] Prints `OK`

---

## Quality gate

```bash
pytest tests/rag/ --tb=short
ruff check src/rag/ scripts/
mypy src/rag/
```

- [ ] All tests pass
- [ ] `ruff` → 0 errors
- [ ] `mypy` → `Success: no issues found`

---

## Phase 04 EXIT GATE ✓

- [ ] All ingest, retriever, and context builder tests pass
- [ ] Ingest is idempotent — running twice gives same chunk count
- [ ] `chroma_db/` is in `.gitignore` (confirm: `git check-ignore chroma_db/`)
- [ ] ContextBuilder correctly references `agent-instructions/system-prompt.md`
- [ ] Phase prompts loaded from `agent-instructions/phases/`
- [ ] `ruff` and `mypy` both clean
