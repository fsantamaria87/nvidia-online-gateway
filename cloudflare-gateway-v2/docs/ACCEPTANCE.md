# Delivery gate — NVIDIA Gateway v2.0.0-rc1

| Gate | Status | Evidence | Action |
|---|---|---|---|
| Legacy ChatGPT MCP calls | FAIL | `nvidia_infer` and `nvidia_review`: `MCP SSE probe returned 404 from railway.app` | Replace endpoint after server is deployed |
| Railway NVIDIA server | OFFLINE | Railway environment status, no active deployment | Preserve for rollback |
| Railway LibroVerse service | OFFLINE | Same Railway environment, volume exists | Do not mutate |
| Source recovered | PASS | Public repo `fsantamaria87/nvidia-online-gateway` server.js v0.5.0 | Original preserved |
| Cloudflare implementation source | PASS (build) | `npm install`, syntax, `wrangler deploy --dry-run` passed in GitHub Actions | Test remote deploy with credentials |
| Offline QA | PASS | 26 synthetic tests, npm test | Preserved in CI |
| JavaScript syntax | PASS | `node --check` | Retest bundled code |
| Auth fail-closed | PASS (unit/static) | Bearer+origin, missing-secret guard, secrets absent from repo | Test deployed endpoint |
| Provider API key valid | NOT_RUN | Railway only exposed *name* `NVIDIA_API_KEY` | Configure new secret privately |
| Cloudflare Worker deployed | NOT_RUN | No connected Cloudflare account/tool/secret | Deploy with approved credentials |
| Local MCP 3 tools listed | PASS (localhost) | `wrangler dev` + authorized `initialize` and `tools/list`; unauthorized 401, invalid Origin 403 | Re-test remote deployment |
| Real NVIDIA inference | NOT_RUN | No working new provider connection | Synthetic end-to-end live test |
| ChatGPT App rebinding | NOT_RUN | Legacy App still points to Railway | Use existing App owner/source or supported custom MCP flow |
| Codex MCP connection | NOT_RUN | Requires Codex host and auth configuration | Test on target host |
| Old Railway cleanup | NOT_RUN | Other services share Railway project and storage | Wait for validated replacement |

**GitHub CI reference:** PR #5, local build + 26 tests + authenticated localhost MCP smoke PASS (run 40996049088). Full NVIDIA provider call and remote ChatGPT integration remain NOT_RUN.

**Acceptance rule:** do not label FINAL or functional until actual authenticated `tools/list`, all three tools and an actual NVIDIA API call return success from deployed Worker. Never claim a passing local mock is production proof.
