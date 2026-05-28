Load a build phase and begin implementation.

Usage: /phase <number>   e.g. /phase 02

Steps:
1. Read agent-instructions/phases/phase-<number>-*.md as implementation context
2. Read agent-instructions/system-prompt.md as the base standards
3. Open checklists/phase-<number>-checklist.md and work through every item
4. Run the phase validation gate before declaring the phase complete

Available phases:
  00  Scaffold & toolchain
  01  OllamaClient (async streaming)
  02  Tool implementations (5 tools + WorkspaceContext)
  03  AgentLoop (stream → detect → execute → loop)
  04  RAG pipeline (ChromaDB ingest + context builder)
  05  FastAPI SSE server + Continue.dev configuration
  06  Full test suite & coverage ≥ 80%
  07  Unsloth fine-tuning (optional)

$ARGUMENTS
