#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then cp .env.example .env; chmod 600 .env; fi
if [ ! -x .venv/bin/python ]; then echo 'Run python3 -m venv .venv and .venv/bin/pip install -r requirements.lock.txt first.'; exit 1; fi
if [ -x /Users/macbookpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node ]; then export PATH="/Users/macbookpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH"; fi
export TESTFORGE_NODE="$(command -v node)"
.venv/bin/uvicorn services.api:app --host 127.0.0.1 --port 8010 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT INT TERM
npm run dev
