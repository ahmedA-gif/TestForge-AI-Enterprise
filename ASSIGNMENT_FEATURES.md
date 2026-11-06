# TestForge AI Enterprise — assignment mapping

This mapping follows the supplied implementation blueprint. The original instructor scenario/rubric was not supplied, so exact rubric compliance cannot be certified.

| Requirement area | Implementation and demonstration |
|---|---|
| One primary agent | Python LangGraph StateGraph; NVIDIA Nemotron model selects analysis, planning and explanation paths. |
| Short-term memory | SQLite-backed LangGraph checkpoints keyed by project and thread. Follow up in the same Agent conversation to refer to earlier messages, plans and results. |
| Long-term memory | Explicit project preferences stored separately in SQLite. Save a preferred suite, start a new session, then ask for the preference. It survives new threads; users can delete it in Memory. |
| Retrieval grounding | NVIDIA embeddings, Qdrant vectors, document chunks with source IDs, line ranges and clickable citations. Index documents, then ask a requirement question. |
| Tool integration | Official MCP stdio server discovers audited suites and runs approved executions. |
| Human approval | Single-use approval bound to project/suite/snapshot with five-minute validity. Execution requires explicit review. |
| Evidence and release | Real Pytest/Vitest results, JUnit cases/logs, deterministic GO/NO-GO/insufficient-evidence gate, PDF/ZIP exports. The demo intentionally contains an expired-coupon failure. |
| Local projects | Directory snapshot on local backend; folder/ZIP upload locally or on cloud. Actual inventory, charts, test-file discovery, Python/JSON parsing findings. Reimport after source edits. Imported tests are not executed. |
| Usability and visualization | Guided steps, source findings, interactive language/run charts; optional 3D map, paused initially, unmounted when closed. |

## Technology
React 19, TypeScript, Next.js 16, Tailwind CSS 4 and Lucide; FastAPI/Pydantic; Python/LangGraph; NVIDIA chat and embeddings; Qdrant; SQLite; MCP; Pytest/Vitest; ReportLab; Vercel Functions gateway and persistent Sandbox snapshots. Local development also supports Vinext/Vite.

## Running without development overhead
Use `./scripts/start-local-production.sh` from the checkout. It builds the optimized UI, starts the loopback Python backend, and serves the app at http://localhost:5173. Stop any older local server before starting. Development/HMR remains available with `./scripts/start-local.sh`.

## Boundaries
This is an academic owner workspace. Team RBAC, arbitrary imported-code execution, public GitHub imports and additional language analyzers remain roadmap work. No claim of zero possible defects, measured code coverage or full enterprise compliance is made.
