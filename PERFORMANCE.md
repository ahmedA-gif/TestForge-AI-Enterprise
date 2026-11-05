# Scrolling and workflow improvements

The overview now gives a concrete next action: index requirements, create a plan, review approval, inspect a running test, or open the report. Its five navigation steps explain the workflow, and the bundled demo explicitly explains its intentional coupon failure. Start analysis opens requirements first. Loading states distinguish cloud startup from an empty project; mobile navigation closes with the backdrop or Escape. Chat scrolls its message container rather than the whole page.

## Rendering changes

- The wallpaper is blurred once on a fixed layer. Scrolling cards keep transparent fills and neo-brutalist borders without individual backdrop filters. Sidebar/modal blur is limited.
- The 3D map starts paused. Play, drag, zoom, node inspection and keyboard rotation remain available. Animation is suspended while scrolling, off-screen or in a hidden tab; reduced-motion settings remain respected.
- Stable callbacks and memoization avoid rebuilding the visualizations on unrelated form changes.

## Data changes

- One `/projects/{id}/workspace` request replaces six initial project-data requests. Activity traces load only in Configuration.
- Initial run history and progress polling return compact summaries. Original assertion bodies, logs and artifacts remain available and load when a run is opened.
- Polling does not overlap, skips hidden tabs, avoids unchanged updates, and refreshes plans/report after a run completes. Session changes no longer reload the entire workspace.

## Verification

`npm run test:performance` writes `output/qa/performance-verification.json` and screenshots. It uses Playwright from a local installation or `TESTFORGE_PLAYWRIGHT_MODULE`/the bundled runtime. It checks animation suspension, initial request counts, navigation, real MCP/Pytest execution, original test-case loading, replanning guidance, chat scrolling and mobile behavior. It creates an explicitly approved audited demo run; it does not call the AI provider. Optional `TESTFORGE_BASELINE_URL` captures the same metrics from an old build.

The initial same-machine comparison captured 3,083 off-screen SVG attribute mutations in 1.2 seconds on commit 15719ef versus zero after the change. The old 1.8-second idle sample used 161 ms of JavaScript and 89 ms of layout; updated samples rounded to zero. These are headless Chromium samples, not a promise about every device or every interaction.

Platform regressions, live NVIDIA/RAG/MCP checks, desktop/mobile browser checks and the production build are also run for this change. Generated XML/JSON under `output/qa/` and live records under `logs/` are the measured evidence.

The repository already had ESLint failures in the original page, visualizations and project-display helper (20 errors in the baseline comparison). This change reduces that count; the new guide has no lint findings. Source typing and production-build checks are evaluated separately from that existing lint backlog.

The macOS Desktop folder denied access during this change. Work was performed in `/Users/macbookpro/testforge-performance-work`, a fresh checkout of the same GitHub repository. The original Desktop checkout and its local databases were not modified.
