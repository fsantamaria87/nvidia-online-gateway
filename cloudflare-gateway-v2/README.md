# NVIDIA Online Gateway v2.0.0-rc1 — Cloudflare Workers migration candidate

**State:** SOURCE CANDIDATE / NOT DEPLOYED / NOT CONNECTED. This is not a claim that the old NVIDIA MCP is fixed.

The old `nvidia-online-gateway` was available to ChatGPT as three tools, but the MCP transport returned `404` at its railway.app endpoint. Railway showed the service **offline with no active deployment**. This package is a new **standalone, stateless MCP implementation**, not a way to repair the legacy ChatGPT App by changing only a skill.

## Source and API
- `src/index.js`: MCP remote `/mcp` Worker endpoint, `@modelcontextprotocol/server` v2 + Cloudflare Agents `createMcpHandler`, token authentication. `/health` is a liveness check only; it does not test the provider or prove API readiness.
- `src/core.js`: portable/advisory routing (fast, balanced, deep, auto), synthetic eval set, second-model review, classifier, limited retries and observable fallback, budget classification and provider adapter.
- `test/core.test.js`: offline synthetic tests, no provider credentials needed.
- `wrangler.toml`: `workers.dev` deployment configuration (no secret values).

### Retained callable tools
`nvidia_infer`, `nvidia_review`, and `nvidia_generate_evalset` with the original argument names and guardrails. The tools return `status=OK|ERROR|BYPASSED`, not invented success. `switchyard_active=false` is intentional; this is deterministic routing, not NVIDIA NeMo Switchyard.

## Secrets and security

**Do not deploy with anonymous MCP.** Before configuring the service, requests to `/mcp` fail with 503. After configuration, all `/mcp` methods require an HTTPS bearer token. The Worker checks browser `Origin` against `MCP_ALLOWED_ORIGINS` (empty by default; non-browser clients omit `Origin`). CORS wildcard is disabled. Keys are never embedded in the source or response. Rotate the old NVIDIA key before reusing it in a new platform if it was previously exposed.

- `NVIDIA_API_KEY`: NVIDIA Developer Build API key, configured as a Cloudflare secret.
- `MCP_CLIENT_TOKEN`: randomly generated *distinct* 32+ character token for the MCP client, configured as a Cloudflare secret.
- Optional `NVIDIA_MODEL_FAST`, `NVIDIA_MODEL_BALANCED`, `NVIDIA_MODEL_DEEP`: server-side overrides if NVIDIA's hosted model identifiers change.
- Optional `MCP_ALLOWED_ORIGINS`: exact comma-separated HTTPS browser origins (if you use a browser MCP client).

**Important limitations:** `optional_provider_calls_used` is an advisory value supplied by the caller and **not** a cross-request server-side rate limiter. Each tool invocation permits at most 3 upstream HTTP attempts (including retry/fallback), with tokens limited to 2048 by default. Configure independent provider spending quotas, Cloudflare rate limits, and alerts before production. `data_classification` is provided by the caller and is not a proof that a prompt contains no secrets. Never pass actual Hilex customer or plant data without explicit approval and minimization.

## Deploy when access is authorized

Requires a Cloudflare account and a local/CI environment with Node 22+. `npm` and Wrangler were NOT able to access npm registry in the build sandbox, but GitHub Actions has passed npm install, Wrangler dry-run and authenticated localhost MCP smoke. Remote Worker and NVIDIA integration tests are still required.

```bash
cd nvidia_orchestrator_v2
npm install
npm run check
npm test
npx wrangler login
npx wrangler secret put NVIDIA_API_KEY
npx wrangler secret put MCP_CLIENT_TOKEN
npx wrangler deploy
```

**Before** `wrangler deploy`, generate and securely store the random MCP client token. Set `NVIDIA_API_KEY` and `MCP_CLIENT_TOKEN` for the correct Worker and account. Do not paste them into GitHub, ChatGPT, logs, or shared screenshots. Check whether Cloudflare billing policies and NVIDIA provider quotas fit your free-tier requirement.

Then verify:

1. `GET https://<your-subdomain>.workers.dev/health` returns a liveness status; it does not test NVIDIA.
2. Unauthenticated MCP request returns `401` (when secrets are configured); wrong Origin `403`.
3. Authorized MCP client connects to `https://<your-subdomain>.workers.dev/mcp` with `Authorization: Bearer <MCP_CLIENT_TOKEN>` and sees 3 tools.
4. Real `nvidia_infer` using `SYNTHETIC` returns `status=OK`, valid model and usage; test `nvidia_review` and evalset with synthetic content.
5. Explicit 429, timeout, authentication and invalid JSON failure tests are observed.
6. ChatGPT App/MCP tooling must connect separately and securely; updating our old plugin skill **cannot** point the old registered App to a new endpoint. Codex and ChatGPT may have different MCP availability/authentication constraints.

## Rollback and boundaries

- **Do not touch the notebooklm-project-hub, libroverse-cloud-free, nvidia-status-page, or existing Railway NVIDIA deployment** while staging this candidate.
- Keep main GitHub LKG frozen until the Worker can be built and called by an actual MCP client.
- Cut over clients one by one after real provider tests; only then inventory old consumers and plan retirement of Railway services.

## Source references
- https://developers.cloudflare.com/agents/model-context-protocol/apis/handler-api/
- https://developers.cloudflare.com/agents/model-context-protocol/protocol/authorization/
- https://build.nvidia.com/models?label=Chat&q=nemotron
