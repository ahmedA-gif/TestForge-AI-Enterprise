#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -x /Users/macbookpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node ]; then export PATH="/Users/macbookpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH"; fi
export TESTFORGE_NODE="$(command -v node)"
export TESTFORGE_LOCAL_BACKEND=1
npm run build:vercel
.venv/bin/uvicorn services.api:app --host 127.0.0.1 --port 8010 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT INT TERM
node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 5173
