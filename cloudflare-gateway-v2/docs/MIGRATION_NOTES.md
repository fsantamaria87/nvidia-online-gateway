# Architecture note

## Before
`ChatGPT → NVIDIA Online Gateway App (3 tools) → dead railway.app MCP probe`.
The source used `@modelcontextprotocol/sdk` v1 with Streamable HTTP at `/mcp`; current ChatGPT connection probes an SSE URL and receives 404. The Railway instance is offline with no active deployment.

## Candidate after
`MCP client → Cloudflare Worker (bearer auth, stateless `/mcp`) → NVIDIA build API`, with profile routing & fallback. The client must be reconfigured to use the new HTTPS endpoint and auth. A new Worker cannot take over the old App ID automatically.

**No browser-only substitution:** Unlike NotebookLM, NVIDIA execution is a programmatic model API with secret keys. A browser automation would not be the recommended durable MCP implementation.

## Pinned conditions
- Public GitHub source is fine because no secrets embedded.
- Library compatibility validated via Cloudflare documentation on 2026-10-29, and CI verified npm install, Worker dry-run and local MCP handshake on 2026-10-29. Remote production and NVIDIA calls are not yet verified.
- SDK v2 Cloudflare Agents requires version compatibility; package uses server 2.4.0 and `agents` 0.32.0. Pin exact resolution in `package-lock.json` when dependencies can install successfully. Do not claim fully reproducible without lockfile.
- Production needs rate limits beyond the stateless local advisory budget, and periodic key rotations.
