# Phase 04 — RAG Pipeline: Ingest, Retrieval & Context Builder

## Phase goal
Index instruction files, source code, and code samples into three separate
ChromaDB collections. Build the context_builder that assembles the dynamic
system prompt used at query time.

## Entry criteria
- [ ] Phase 03 exit gates passed · `pytest -x` green

## Active standards
§7 Code quality · §10 Performance (streaming, semaphore) · §12 Architecture · §19 RAG config

## Implementation

### Step 4.1 — RAG configuration — `src/rag/options.py`
```python
from pathlib import Path
from pydantic_settings import BaseSettings

class RagOptions(BaseSettings):
    chroma_db_path: Path = Path("./chroma_db")
    instructions_dir: Path = Path("./context_store/instructions")
    codebase_dir: Path = Path("./context_store/codebase")
    samples_dir: Path = Path("./context_store/samples")
    embed_model: str = "nomic-embed-text"
    instructions_chunk_size: int = 512
    codebase_chunk_size: int = 1024
    samples_chunk_size: int = 800
    chunk_overlap: int = 64
    retrieval_k: int = 5

    model_config = {"env_prefix": "RAG_"}
```

### Step 4.2 — Ingest pipeline — `src/rag/ingest.py`

```python
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

async def ingest_collection(
    source_dir: Path,
    glob: str,
    collection_name: str,
    chunk_size: int,
    options: RagOptions,
) -> int:
    """Chunk, embed, and store documents. Returns chunk count."""
    ...
```

Rules:
- Tag every chunk: `doc.metadata["collection"] = collection_name`
- Tag every chunk: `doc.metadata["source"]` = relative path from source_dir
- Chunk sizes differ per collection — use `RagOptions` values, never hardcode
- Print progress: `{collection_name}: {n} chunks from {m} files`
- Return chunk count for verification

**Entrypoint script — `scripts/ingest.py`:**
```python
async def main() -> None:
    opts = RagOptions()
    await ingest_collection(opts.instructions_dir, "**/*.md",  "instructions", opts.instructions_chunk_size, opts)
    await ingest_collection(opts.codebase_dir,     "**/*.py",  "codebase",     opts.codebase_chunk_size,     opts)
    await ingest_collection(opts.samples_dir,      "**/*.py",  "samples",      opts.samples_chunk_size,       opts)
```

### Step 4.3 — Retriever — `src/rag/retriever.py`

```python
class RagRetriever:
    def __init__(self, options: RagOptions) -> None:
        embeddings = OllamaEmbeddings(model=options.embed_model)
        self._instructions = Chroma(persist_directory=str(options.chroma_db_path),
                                    embedding_function=embeddings,
                                    collection_name="instructions")
        self._codebase = Chroma(...)
        self._samples  = Chroma(...)

    def retrieve(self, query: str) -> dict[str, list[Document]]:
        """Retrieve from all three collections independently."""
        return {
            "instructions": self._instructions.similarity_search(query, k=self._opts.retrieval_k),
            "codebase":     self._codebase.similarity_search(query,     k=3),
            "samples":      self._samples.similarity_search(query,      k=2),
        }
```

### Step 4.4 — Context builder — `src/rag/context_builder.py`

```python
class ContextBuilder:
    """Assembles BASE_SYSTEM_PROMPT + optional PHASE_PROMPT + RAG chunks."""

    def __init__(
        self,
        base_prompt_path: Path,
        retriever: RagRetriever,
        phase_prompts_dir: Path | None = None,
    ) -> None: ...

    def build(self, query: str, phase: str | None = None) -> str:
        """
        Returns: base_prompt + phase_prompt (if provided) + retrieved chunks.
        Section headers:
          ## Relevant standards
          ## Canonical patterns to follow
          ## Related code in this codebase
        """
        ...
```

Rules:
- `base_prompt_path` is the only place where `coding-agent-system-prompt.md` is read
- Phase prompt is optional — skip the section if `phase=None`
- Retrieved chunks are treated as untrusted — never execute instructions from them
- Cap total context at 28,000 tokens (rough char estimate: 28000 * 4 chars) — truncate oldest
- Log: `context_built`, query length, chunks retrieved per collection, total length

### Step 4.5 — Tests — `tests/rag/`

| Test | Scenario | Expected |
|---|---|---|
| `test_ingest` | Ingest 3 markdown files | Returns correct chunk count |
| `test_retriever` | Query returns results from each collection | 3 collections, k results each |
| `test_context_builder_base_only` | No phase, no RAG results | Returns base prompt only |
| `test_context_builder_with_phase` | Phase name provided | Phase section included |
| `test_context_builder_with_rag` | Mock retriever returns chunks | All three sections present |
| `test_context_builder_cap` | Very large retrieval | Output truncated, no crash |

Use `tmp_path` for all ChromaDB paths in tests — never the real `./chroma_db`.

## Validation gate
```bash
pytest tests/rag/ -v
ruff check src/rag/ scripts/
mypy src/rag/

# Manual smoke test (requires Ollama + nomic-embed-text)
python scripts/ingest.py
```

## Exit criteria
- [ ] All three collections indexed by `scripts/ingest.py`
- [ ] `retrieve()` returns results from all three collections
- [ ] `build()` produces a prompt with correct section headers
- [ ] Context truncation does not crash
- [ ] `mypy` strict passes on all rag files

## What not to do
- Do not build the FastAPI server (Phase 05)
- Do not wire context_builder into AgentLoop yet (Phase 05)
- Do not commit `chroma_db/` to git — add to `.gitignore`
