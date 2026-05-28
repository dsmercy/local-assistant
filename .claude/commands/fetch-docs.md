Fetch Microsoft documentation pages and index them into ChromaDB.

Steps:
1. Install fetch dependencies (first time only): `make fetch-install`
2. Preview what will be fetched: `make fetch-docs-dry`
3. Download and clean all docs: `make fetch-docs`
4. Index into ChromaDB: `make ingest`

Or do steps 3+4 together: `make fetch-and-ingest`

To add a new URL:
1. Add it to `docs-urls.txt`
2. Run `make fetch-and-ingest`

To fetch a single URL interactively:
```bash
python scripts/fetch_docs.py --url https://learn.microsoft.com/en-us/dotnet/...
make ingest
```

After ingestion, the agent will automatically retrieve relevant docs
when you ask about .NET versions, APIs, or migration guidance.
