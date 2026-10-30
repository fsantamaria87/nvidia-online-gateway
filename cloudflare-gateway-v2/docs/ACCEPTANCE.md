# NVIDIA Gateway v2.1 OAuth — Acceptance & Cutover Gate

## Evidence status (2026-10-30 UTC)
| Gate | State | Evidence / limitation |
|---|---|---|
| Source recovery, branch and rollback | PASS | Old main preserved; PR #5 legacy candidate, PR #6 OAuth RC2 draft |
| 3 original tool schemas | PASS local | Original `initialize` + `tools/list` returns exactly three tools |
| Node SDK + dependencies | PASS CI | npm install, JavaScript check |
| Unit/privacy/budget/fallback/model routes | PASS 27/27 | Synthetic tests including balanced model change |
| Cloudflare authorization Worker bundle | PASS CI | Wrangler dry-run only, no deployment |
| Cloudflare resource Worker bundle | PASS CI | Wrangler dry-run only, no deployment |
| OAuth metadata and S256 PKCE | PASS local | Local Wrangler `/.well-known/oauth-authorization-server` |
| OAuth anonymous access rejection | PASS local | Protected `/mcp` returns 401 |
| Static bearer compatibility | PASS local | Legacy candidate 401/403 and 3 tools |
| Source artifact | PASS | Github Actions reproducible ZIP, no real secrets |
| Cloudflare account authorized | BLOCKED | No connected Cloudflare account/session in current environment |
| GitHub OAuth App and secrets | NOT_RUN | Must be configured privately in owning accounts |
| Real OAuth approval + callback | NOT_RUN | Requires browser user authorization |
| Live NVIDIA API/model/quota | NOT_RUN | API key not available through connected tools |
| ChatGPT plugin rebound to new server | NOT_RUN | Previous registered App remains connected to Railway |
| Codex MCP linkage | NOT_RUN | Requires explicit separate client connection |
| Railway retirement | NOT_RUN | Preserve other Railway services, especially LibroVerse |

GitHub CI green run: https://github.com/fsantamaria87/nvidia-online-gateway/actions/runs/41004644504

**PASS source/local != repaired production.** Production gate requires explicit remote `nvidia_infer` (SYNTHETIC) status=OK, then `nvidia_review` + `nvidia_generate_evalset` and actual ChatGPT MCP tool call. Never publish an anonymous endpoint backed by NVIDIA credits. Never expose credentials in GitHub, ChatGPT, source ZIP or screen captures.

**Primary deploy workflow:** `oauth-auth-server/README.md`; deploy auth Worker then resource Worker using `wrangler.oauth.toml`, NOT `wrangler.toml`.

**Protection of existing services:** never remove the NVIDIA/NotebookLM Railway projects, nvidia-status-page, or libroverse-cloud-free volume before production cutover and backups.
