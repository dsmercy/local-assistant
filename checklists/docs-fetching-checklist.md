# Documentation Fetching & Indexing Checklist

> Run this whenever you add new documentation to the agent's knowledge base.
> This is NOT a build phase — it can be run at any time after Phase 04 is complete.

---

## Step 1 — Install fetch dependencies (first time only)

```bash
make fetch-install
```

Verify:
- [ ] `pip list | grep trafilatura` shows a version
- [ ] `pip list | grep beautifulsoup4` shows a version

---

## Step 2 — Preview output paths (dry run)

```bash
make fetch-docs-dry
```

Verify the output file list makes sense:

- [ ] `.NET Core 3.x` URLs map to `context_store/instructions/dotnet/core-3x/`
- [ ] `.NET 6` URLs map to `context_store/instructions/dotnet/dotnet-6/`
- [ ] `.NET 8` URLs map to `context_store/instructions/dotnet/dotnet-8/`
- [ ] `.NET 10` URLs map to `context_store/instructions/dotnet/dotnet-10/`
- [ ] No URLs are missing or miscategorised

---

## Step 3 — Fetch all documentation

```bash
make fetch-docs
```

For each URL, verify the output line shows:
- [ ] `✓` prefix (not `✗` or `⚠`)
- [ ] Character count > 1,000 (healthy page content)
- [ ] A file path like `context_store/instructions/dotnet/dotnet-8/aspnetcore-8-0.md`

Expected files after fetch:
```
context_store/instructions/dotnet/
├── core-3x/
│   ├── aspnet-core-aspnetcore-3-1.md
│   └── ef-core-3-x.md
├── dotnet-6/
│   ├── aspnet-core-aspnetcore-6-0.md
│   ├── ef-core-6-0-whatsnew.md
│   └── dotnet-core-porting.md
├── dotnet-8/
│   ├── dotnet-8-overview.md
│   ├── aspnet-core-aspnetcore-8-0.md
│   ├── ef-core-8-0-whatsnew.md
│   └── dotnet-core-native-aot.md
└── dotnet-10/
    ├── dotnet-10-overview.md
    ├── aspnet-core-aspnetcore-10-0.md
    └── ef-core-10-0-whatsnew.md
```

- [ ] All 12 files are present: `find context_store/instructions/dotnet -name "*.md" | wc -l` → `12`
- [ ] Files are not empty: `wc -l context_store/instructions/dotnet/**/*.md`

---

## Step 4 — Ingest into ChromaDB

```bash
make ingest
```

Verify:
- [ ] Script prints progress for all 3 collections (`instructions`, `codebase`, `samples`)
- [ ] `instructions` collection shows chunk count increase (the docs were chunked)
- [ ] Script exits 0
- [ ] `chroma_db/` directory is updated (check modified time: `ls -la chroma_db/`)

---

## Step 5 — Verify retrieval

```bash
python3 -c "
from src.rag.options import RagOptions
from src.rag.retriever import RagRetriever

opts = RagOptions()
r = RagRetriever(opts)

queries = [
    'ASP.NET Core minimal API .NET 8',
    'EF Core 8 complex types',
    '.NET 10 new features',
    'CancellationToken async .NET',
    'EF Core migration upgrade',
]

for q in queries:
    results = r.retrieve(q)
    n = len(results['instructions'])
    sources = [d.metadata.get('source', '?')[:60] for d in results['instructions'][:2]]
    print(f'  [{n} chunks] {q}')
    for s in sources:
        print(f'    ← {s}')
    print()
"
```

- [ ] Each query returns ≥ 1 chunk from the `instructions` collection
- [ ] Source URLs in results match `learn.microsoft.com`
- [ ] Version-specific queries (e.g. ".NET 8") return chunks from the correct version folder

---

## Step 6 — Test in Continue.dev

Open VS Code and ask the agent:

- [ ] "What are the new features in .NET 8?" → agent references specific features from the docs
- [ ] "How do I migrate from .NET Core 3.1 to .NET 6?" → agent references the porting guide
- [ ] "What changed in EF Core 10?" → agent references the EF Core 10 whatsnew page
- [ ] Agent responses cite specific API names (not just generic advice)

---

## Adding new documentation

To add more URLs in the future:

1. Add the URL to `docs-urls.txt` (comment `// version` for clarity)
2. Run `make fetch-and-ingest` (fetches + re-indexes in one step)
3. Verify with the retrieval test above

No code changes needed — the pipeline handles everything automatically.

---

## Troubleshooting

**Problem: `✗ HTTP 403` on a URL**
- Microsoft docs occasionally block scrapers; wait a few minutes and retry
- Try `python scripts/fetch_docs.py --url <url>` for a single retry

**Problem: `⚠ Very short content` warning**
- The page may be a landing/index page with little text
- Check the saved `.md` file — if it has < 10 lines, delete it and try again later

**Problem: Chunks not showing in retrieval**
- Confirm `make ingest` ran after `make fetch-docs`
- Confirm the file is in `context_store/instructions/` (not `codebase/` or `samples/`)
- Check chunk size: files with < 200 chars won't produce meaningful chunks
