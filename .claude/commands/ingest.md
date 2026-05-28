Re-index context_store/ into ChromaDB.

Run after adding or changing files in:
  context_store/instructions/   ← .md standards files
  context_store/codebase/       ← .cs / .py source files
  context_store/samples/        ← canonical code patterns

```bash
python scripts/ingest.py
```
