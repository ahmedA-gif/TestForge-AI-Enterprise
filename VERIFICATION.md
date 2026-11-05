# Verification report

Verified on **6 November 2026 (Asia/Karachi)** against the running local application at http://127.0.0.1:5173.

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| Platform regression tests | **62 passed** | `output/qa/system-tests.xml` |
| TypeScript | Passed | `npm run typecheck` |
| Production build | Passed | `npm run build` |
| Desktop/mobile screens | **19 passed**, no page-wide overflow | `output/qa/browser-verification.json` |
| Browser workflows | **16 check groups passed** | Same JSON; screenshots under `output/qa/verified-*` |
| Browser/server errors | **0 JavaScript exceptions; 0 HTTP 5xx responses** during browser verification | Same JSON |
| NVIDIA embeddings and retrieval | Six documents indexed; actual 2,048-dimensional embeddings; coupon requirement retrieved with D1/D6 citations | `logs/index.json`, `logs/rag_trace.json` |
| NVIDIA agent | Real model request, cited failure explanation and proposed plan | `logs/thread_a.json`, `logs/followup.json`, `logs/llm_trace.json` |
| MCP v2 | Actual stdio discovery and approved execution | `logs/mcp_trace.json` |
| Python demo fixture | **4 passed, 1 intentional failure** | `logs/pytest_run.json`, original JUnit artifacts |
| TypeScript demo fixture | **3 passed** | `logs/vitest_run.json`, original JUnit artifacts |
| Release decision | **NO-GO**, correctly blocked by the intentional coupon defect | `logs/report.json` and current report API |
| Memory | Explicit preference recalled in a new thread; browser preference deletion and transcript download passed | `logs/thread_b.json`; browser verification JSON |
| Imports | ZIP, folder picker and allowed local path passed; secrets excluded; out-of-root paths rejected; source left unchanged | System tests and browser verification JSON |
| Project-specific data | Go/Rust fixture displayed its own inventory and R-42/REQ-207, with no invented runs | Browser and platform tests |
| Charts/3D | Rotate, pause, drag, zoom, reset, select nodes, filter languages/suites and drill into original runs passed | Browser verification JSON |
| Appearance/accessibility | Opacity preference persists; mobile navigation and reduced-motion behavior passed | Browser verification JSON |
| Exports | Valid PDF, evidence ZIP and transcript downloaded | Live and browser checks |
| Credential check | Key absent from source/client bundle; local `.env` mode 0600 | `output/qa/credential-check.json` |

## Defect found and fixed

The release gate accepted suites labeled PASS even when all required tests were skipped. Required suites with skipped tests now normalize to **INCOMPLETE**; skipped, empty or error-containing results cannot produce GO. Six regression cases cover skipped-only, partially skipped, empty, inconsistent-error and runner-normalization scenarios. The skipped-only probe now returns **INSUFFICIENT EVIDENCE**.

## Reproduce

Start the application with `./scripts/start-local.sh`, then run:

```sh
npm run test:system
npm run typecheck
npm run build
npm run test:live
npm run test:browser
```

The browser runner uses an installed Playwright package or this machine's bundled runtime. Override its module path with `TESTFORGE_PLAYWRIGHT_MODULE` if needed. Live and browser checks use the NVIDIA endpoints and run only audited fixtures. Browser verification writes its results even if a check fails.

Temporary repositories created by this verification were removed. Real test-run history and original artifacts are retained for inspection. The duplicate-ZIP-name warning is intentional input for a rejection test.

## Scope

These results verify the implemented single-user local academic MVP. Imported arbitrary repositories remain **analysis-only**. Enterprise roadmap features and hardened multi-tenant execution are not represented as implemented or certified. Passing these checks is not proof that every possible input or production threat has been tested.

## Broader bug audit

The regression suite now contains 62 passing cases. Additional fixes cover:

- Empty/blank specification files and uppercase extensions no longer break document parsing or disappear from detection.
- Corrupt/encrypted/unsupported ZIP entries produce validation errors.
- Invalid or empty model answers and malformed/non-finite embeddings fail cleanly without creating plans or corrupting the working index. Provider connection failures are surfaced as recoverable errors.
- Reindexing builds a new collection before switching the active pointer; failures preserve the previous working index and in-flight retrievals can finish on their original collection.
- Latest release evidence is selected by run start time, so an older run finishing late cannot override a newer run.
- Rejecting a plan is transactional; concurrent approve/reject requests have one winner. Queued runs are bound to their approval identity.
- Abandoned pending/running jobs become ERROR on restart and require fresh authorization.
- SQLite connections close after transactions; same-thread graph requests are serialized to preserve all conversation turns.
- Single-suite replanning stops cleanly when no alternate suite is available.
- Late transcript responses cannot overwrite a new session. Project changes clear stale file filters and dialogs; invalid view URLs fall back to Overview.
- Chart keyboard controls accept both Enter and Space.

The delayed-transcript browser regression passed (`output/qa/session-race.json`). The live smoke harness now waits for concurrent runs to settle before asserting the final report, instead of treating a correctly provisional verdict as an application failure.

The live audit also exposed intermittent model misclassification of an explicit plan request. Clear current-turn plan requests now route deterministically to pending-plan creation; explicit requests not to create a plan remain explanations. Both paths have regression tests. Execution still requires a separate approval.

## Scrolling and usability update

The latest revision passes 62 platform cases, the live NVIDIA/RAG/MCP smoke flow, 19 desktop/mobile screens, 16 browser workflow groups and 11 focused performance/usability checks. The overview provides a next-step guide, on-demand 3D animation, lighter transparent surfaces, compact progress polling and lazy original-run evidence. The focused browser check records zero off-screen SVG animation mutations and no page errors. See `PERFORMANCE.md` and `output/qa/performance-verification.json`. Existing ESLint backlog is documented separately; this is not a claim of a lint-clean repository.
