# Blueprint implementation map

This map distinguishes the P0 academic product from the blueprint's future commercial roadmap. Nothing in the PDF is treated as permission to execute uploaded customer code or as evidence that an example run occurred.

| Blueprint section | Implementation and proof |
| --- | --- |
| 01-03 executive, rubric, users | Academic scope and synthetic-scenario caveat in README and UI; real evidence exported from the control plane. |
| 04 eight screens | Overview/import, repository, knowledge, agent, approvals, runs and release views; additional memory/configuration views. |
| 05 full workflow | ZIP/demo import → inventory → hosted embedding index → cited retrieval → single-agent plan → exact approval → MCP execution → normalized result → bounded replan → deterministic report. |
| 06 technology | React + TypeScript + Tailwind/shadcn-ready component system; Vinext compatibility runtime; FastAPI/Pydantic; LangGraph; NVIDIA; Qdrant; SQLite; official MCP 2.3; Pytest/Vitest; ReportLab. Custom interface primitives provide the specified visual design. |
| 07 architecture | README Mermaid diagram; `services/api.py`, `agent.py`, `rag.py`, `mcp_client.py`, `mcp_server.py`, `runner.py`. |
| 08 multi-language | Extension/manifest inventory, Python AST symbols, audited Python/TypeScript fixture execution. Other languages are discovered only; no execution adapter is advertised. |
| 09 ingestion | 10 MB compressed, 25 MB unpacked, 2 MB/file, 1,000 files, depth 15; traversal/absolute/backslash/symlink/duplicate destination checks; secret-like files and dependency directories excluded. Imported code is analysis only. |
| 10 intelligence | Stable file hash inventory, language counts, source/test paths and Python symbols. Profiles persisted as SQLite JSON and included in the evidence export. Tree-sitter remains P1. |
| 11 RAG | `knowledge/demo/D1…D6`, source revisions, line-window chunks, NVIDIA embeddings, observed vector dimension validation, per-project Qdrant collections and top-5 cosine retrieval. |
| 12 memory | LangGraph SQLite checkpoint history scoped by project/thread; separate SQLite preference table; explicit preference writes; UI inspect/delete; new-thread recall. |
| 13 single agent | One compiled StateGraph. Chat pauses with a pending approval record; the explicit approval endpoint resumes an execution-mode graph invocation. Two diagnostic replans maximum per thread. |
| 14 prompt | Stable system policy; JSON decision envelope; backend intent/suite validation. User/repository text cannot grant execution. LLM explanations remain distinguishable from deterministic verdicts. |
| 15 MCP v2 | Five official SDK v2 tools over stdio; actual discovery and call trace captured for each execution. MCP is not replaced by a REST test route. |
| 16 approval | Single-use, five-minute, project/suite/snapshot approval; current fingerprint checked twice; atomic consume; duplicate API submission returns existing run. |
| 17 runners | Fixed Pytest/Vitest command arrays; no shell interpolation; restricted child environment; process-group timeout; real XML parsing; distinct PASS/FAIL/ERROR/TIMEOUT/BLOCKED/PENDING/RUNNING states. |
| 18 security | Trusted fixtures only, upload analysis only, local origin restriction, loopback binding, no arbitrary shell tool, no source writes by model, credential filtering. Hardened customer-code sandboxes are explicitly P2. |
| 19 storage | SQLite record store for projects/plans/runs/audit/doc indexes/traces, approval table and separate memory table; checkpoint DB; local Qdrant; original artifact directory. Schemas initialized idempotently. |
| 20 APIs | Import, project inventory, indexing, retrieval, chat, plans, approve/reject, runs, artifacts, memory, report PDF, ZIP export. Queued background execution with polling. FastAPI OpenAPI at port 8010 `/docs`. |
| 21 release policy | Failure blocks release. Errors/timeouts/missing required evidence prevent GO. Both required suites must pass. Pass rate is not labeled code coverage. |
| 22 synthetic example | Intentional expired-coupon defect in Python; independent pending-submission TypeScript suite. Actual results produced by execution, never copied from illustrative PDF counts. |
| 23 platform validation | `tests/system/test_platform.py` covers approval bypass, changed snapshot, crash/timeout, ZIP attacks, gates, memory, actual MCP and measured XML. Live smoke checks actual hosted APIs and complete evidence flow. |
| 24 repository/environment | Modular `services/`, `fixtures/`, `knowledge/`, `tests/`, scripts, ignored `.env`, `.env.example`, Python lock and npm lock. |
| 25-26 submission/demo | README demo script, architecture, prompt rationale, repeatable tests, proof bundle export, actual sample PDF and logs. |
| 27-29 commercial roadmap | Visible future-work labels for teams, private repositories, extra adapters, sandbox pools, CI/CD, billing, governance, SLOs and commercial security review. No certification or universal testing claim. |
| 30 sources | Supplied 31-page blueprint is the design input; official NVIDIA/MCP documentation used to validate current API contracts. Instructor scenario pack remains unavailable. |

## Actual acceptance evidence

The checked-in test suite is independent from the intentionally failing customer fixture. See `output/qa/system-tests.xml` for measured platform test status, `logs/` for live provider/agent/retrieval/MCP results, and `output/pdf/testforge-release-report.pdf` for the reproducible release artifact. These paths are populated by verification rather than illustrative seed results.

## Deliberate deviations

- UI routes are view URLs (`/?view=…`) within one client workspace rather than separate multi-tenant application routes. Backend business routes follow the blueprint API shape.
- SQLite stores some records as typed-at-boundary JSON instead of a separate relational table for every proposed commercial entity. Approvals and cross-thread memory have dedicated transactional tables.
- Short demo documents are whole-section chunks; larger text uses overlapping line windows instead of a tokenizer dependency.
- The TypeScript demo models checkout submission state rather than a deployed React storefront; the fixture remains synthetic and independently testable.
- This is local single-user software. Public hosting requires deploying the Python backend and restricted runner separately. No publicly hosted UI is claimed to provide unavailable Python execution.

## Local directory and appearance update

The import screen now supports browser folder selection and a typed local directory. `services/projects.py` confines backend reads to configured allowed roots, rejects symlink escapes, skips hardlinks/secrets/dependencies, enforces quotas, and copies accepted files into a separate analysis snapshot. Loopback and browser origin/host checks protect the local-only endpoint. These imports never enable arbitrary execution.

The interface uses low-opacity fills and backdrop blur over a visible desktop wallpaper, with neo-brutalist borders, lime controls and offset shadows. Panel opacity and active-project selection persist locally.

## Data-driven interactive views

The overview renders a draggable, zoomable 3D projection of actual project associations plus clickable composition and test-history charts. Category labels, source counts, suite names, requirement totals, example prompts and traceability follow the selected project. Imported projects no longer inherit the demo's six requirement IDs. No execution data is fabricated for charts. Decorative window controls and prominent opaque fingerprint labels have been removed; approval fingerprints remain immutable backend provenance.
