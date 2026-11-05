# Vercel cloud deployment

The web application runs as Next.js on Vercel. Its server-only API gateway resumes one named, persistent Vercel Sandbox and forwards requests to the Python/FastAPI backend inside it. SQLite metadata, LangGraph checkpoints, Qdrant collections, uploads, memory and artifacts live in the Sandbox filesystem. Automatic snapshots preserve that filesystem between sessions. Processes restart on resume; interrupted runs are marked ERROR and require a fresh approval.

The Sandbox is `testforge-production` in the linked Vercel project. It uses one vCPU, five-minute sessions, persistence enabled, no snapshot expiration, and retention of the latest snapshot. This uses Vercel Sandbox (beta) compute and snapshot storage, which are billed according to the account plan. Do not delete the Sandbox or its retained snapshot if you need its data.

All web deployments require Vercel Authentication. This remains a single-owner academic workspace, not a multi-tenant public SaaS. The Sandbox port independently requires a random backend credential. API/provider secrets are configured in Vercel environment variables and are never embedded in the client bundle or Git history.

Required production variables:

- `NVIDIA_API_KEY`
- `NVIDIA_CHAT_MODEL`
- `NVIDIA_EMBED_MODEL`
- `TESTFORGE_BACKEND_TOKEN` (random high-entropy shared credential for the gateway and backend)

Deploy with Node.js 24 and `vercel deploy --prod`. The configured build command creates a server-only backend source archive and runs `next build`. The archive excludes environment files, local databases, logs, dependencies and test artifacts. The Sandbox installs the pinned Python dependencies in a Python 3.12 environment and installs the audited Vitest adapter.

Cloud browser folder/ZIP uploads are limited to 3 MB per request by the gateway. Typed local paths are disabled: a cloud server cannot read a visitor's filesystem. Use folder selection or ZIP upload. The local application and its configured local-directory mode remain available through `./scripts/start-local.sh`.

The original local development/build scripts remain supported. `npm run build:vercel` is the separate cloud build. Persistent resources belong to the Vercel account, independently of this computer.
