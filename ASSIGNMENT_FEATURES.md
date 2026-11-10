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
| Local projects | Directory snapshot on local backend; folder/ZIP upload locally or on cloud. Actual inventory, charts, test-file discovery, bundled syntax checks for multiple languages. Reimport after source edits. Imported tests are not executed. |
| Usability and visualization | Guided steps, source findings, interactive language/run charts; optional 3D map, paused initially, unmounted when closed. |

## Technology
React 19, TypeScript, Next.js 16, Tailwind CSS 4 and Lucide; FastAPI/Pydantic; Python, LangChain and LangGraph; NVIDIA chat and embeddings; Qdrant; SQLite; MCP; Pytest/Vitest; ReportLab; Vercel Functions gateway and persistent Sandbox snapshots. Local development also supports Vinext/Vite.

## Running without development overhead
Use `./scripts/start-local-production.sh` from the checkout. It builds the optimized UI, starts the loopback Python backend, and serves the app at http://localhost:5173. Stop any older local server before starting. Development/HMR remains available with `./scripts/start-local.sh`.

## Boundaries
This is an academic owner workspace. Team RBAC, arbitrary imported-code execution, public GitHub imports and additional runtime adapters remain roadmap work. No claim of zero possible defects, measured code coverage or full enterprise compliance is made.

## Parallel review and linked project workflow

The selected project ID stays in each view link. Import a folder once, then use Diagnose for measured findings, Analysis for the specialist team, Knowledge for citations, Approvals for authorization, Test runs for measured results, and Memory for notes and conversation history.

The LangGraph coordinator handles chat and approval routing. Analysis uses LangGraph `Send` to dispatch seven parallel LangChain review chains against a bounded snapshot. Each chain prepares role-specific evidence, calls NVIDIA and validates complete JSON against a Pydantic schema. The collector preserves completed reviews when another branch fails. Each role stores its status, duration, findings and source references. Reviews appear in the project evidence export.

| Specialist | Reasoning method | Job |
|---|---|---|
| Inventory | Structural classification | Map files, languages and structure. |
| Diagnostics | Evidence-led diagnosis | Explain measured syntax findings and propose fixes. |
| Security | Threat modeling | Review supplied source excerpts for risky patterns. |
| Dependency | Compatibility analysis | Review manifests and configuration. |
| Test design | Risk-based test design | Identify missing cases and suggest tests. |
| Knowledge | Source-grounded comparison | Review requirements and citation gaps. |
| Release evidence | Evidence sufficiency assessment | Assess measured evidence and identify gaps. |

Imported projects have an approval-bound source validation suite. It checks file integrity and supported syntax and records JUnit evidence. Runtime Pytest and Vitest execution is available in the audited demo. A read-only specialist review and a measured validation run have separate records and appear separately in the UI.


Readable UTF-8 source can be indexed regardless of extension. Pygments supplies language labels when it recognizes the filename. Tree-sitter and standard-library parsers provide syntax validation for the bundled languages. Each run lists the checks performed on each file. Files without a bundled parser receive file integrity checks and can participate in AI review.
