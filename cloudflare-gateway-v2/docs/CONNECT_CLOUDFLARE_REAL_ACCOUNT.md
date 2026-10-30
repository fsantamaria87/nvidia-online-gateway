# NVIDIA Gateway v2.1 RC2 — next deployment gates (Cloudflare account verified)

**Status:** Cloudflare account accessible in a delegated browser profile. This is a real existing account, not simulated. The two Workers **are not deployed** yet. This runbook is for the already prepared GitHub branch `migration/nvidia-cloudflare-oauth-v2-rc2` in `fsantamaria87/nvidia-online-gateway`. GitHub PR #6 remains DRAFT.

## Completed in account

- Cloudflare Worker subdomain: `francisco-santamaria-b.workers.dev`.
- Worker KV namespace `nvidia-gateway-oauth-kv` created on free plan: `817a7f9bd83842979cb8d99e1dcc45fe`.
- Actual Cloudflare configuration files are safely committed (only public metadata): `wrangler.oauth.toml` and `oauth-auth-server/wrangler.toml`.
- Numeric GitHub owner ID fixed in both configs; this ID is a public identifier, not a credential.
- Synthetic CI / dry-run checks are separate from true production acceptance.

## Gate A — grant Cloudflare GitHub integration (requires owner action)

Cloudflare dashboard -> Workers & Pages -> Create Application -> Connect GitHub.

When redirected to GitHub, sign in as repository owner. For **Cloudflare Workers and Pages** GitHub App, choose **Only select repositories**, and allow **only `fsantamaria87/nvidia-online-gateway`**. Do NOT authorize all repositories. This installation is a CI/CD integration and **not** the GitHub OAuth login app used to authenticate user access to NVIDIA. After installing, return to Cloudflare and verify the repo appears in the picker.

## Gate B — create OAuth authority Worker first

Using Cloudflare Workers Builds GitHub import:
- GitHub repo: `fsantamaria87/nvidia-online-gateway`
- Branch: `migration/nvidia-cloudflare-oauth-v2-rc2` (do NOT select main)
- Worker name: `nvidia-gateway-oauth-auth`
- **Root directory:** `cloudflare-gateway-v2`
- **Build command:** `npm install --no-audit --no-fund` (if required)
- **Deploy command:** `npx wrangler deploy --config oauth-auth-server/wrangler.toml`
- Expected public worker URL: `https://nvidia-gateway-oauth-auth.francisco-santamaria-b.workers.dev`

Verify build/deploy succeeded and the runtime has `OAUTH_KV` bound. Until authenticated GitHub OAuth app secrets exist, `/authorize` should return `503`. The authorization metadata endpoint may be available before the login flow; that does not prove provider readiness.

## Gate C — OAuth GitHub login app (distinct from the Cloudflare GitHub CI integration)

GitHub user Settings -> Developer settings -> OAuth Apps -> New OAuth App. Use unique name `NVIDIA Gateway Private Authorization`; homepage may be the Cloudflare OAuth auth Worker. OAuth callback:
`https://nvidia-gateway-oauth-auth.francisco-santamaria-b.workers.dev/callback`.
Do NOT use the GitHub App "Cloudflare Workers and Pages" for this step; it is unrelated and does not issue user-login OAuth tokens for our own server.

In **the auth Worker** -> Settings -> Variables and Secrets, configure:
- Secret `GITHUB_CLIENT_ID` with the OAuth App client ID (client ID may be public; keeping it in a secret is fine).
- Secret `GITHUB_CLIENT_SECRET` with the generated OAuth App client secret. This must **never** enter GitHub source or ChatGPT transcripts.

`ISSUER`, `MCP_SERVER_URL`, and `ALLOWED_GITHUB_ID` are already specified as nonsecret vars via Wrangler. KV is preconfigured. Do not add GitHub tokens or passwords. Do not grant repo-write scope to the user-login OAuth App (only `read:user` requested by code).

## Gate D — create protected resource Worker second

Using same GitHub repo and the **same branch and root directory** create a second Worker:
- Name: `nvidia-online-gateway-oauth-v2`
- **Root directory:** `cloudflare-gateway-v2`
- **Deploy command:** `npx wrangler deploy --config wrangler.oauth.toml`
- Expected URL: `https://nvidia-online-gateway-oauth-v2.francisco-santamaria-b.workers.dev/mcp`

In **this resource Worker only**, set secret `NVIDIA_API_KEY` (NVIDIA Build/Nemotron API key). Do not paste into chat, ZIP, browser automation instructions, GitHub, CI logs, or any screenshot. Confirm Cloudflare service binding `AUTH_SERVER` points to `nvidia-gateway-oauth-auth`.

Before real use, set provider quota/rate/spend safeguards; client-provided budget fields do not constitute distributed rate limiting.

## Gate E — acceptance (end-to-end)

1. Authority `/.well-known/oauth-authorization-server` must advertise S256 PKCE and valid issuer, authorization and token endpoints.
2. Unauthenticated resource `POST /mcp` must reject with OAuth Bearer 401 plus protected resource metadata.
3. OAuth sign-in and consent must work in a real browser; wrong account must receive denial.
4. Authenticated tools/list must return **exactly three**: `nvidia_infer`, `nvidia_review`, `nvidia_generate_evalset`.
5. Real provider `nvidia_infer` call on **SYNTHETIC** task yields `status=OK` and correct output; verify errors for invalid key/model/quota; then `nvidia_review` and evalset.
6. Point ChatGPT custom MCP to **new OAuth resource** URL and verify an actual call from the live ChatGPT tool. Codex may require separate app connection/approval.
7. Only after all end-to-end gates pass, mark final and consider legacy Railway retirement. **Never delete `libroverse-cloud-free` or any shared persistent volume.**

If any required UI asks for a paid subscription or account-wide GitHub permissions, stop and request explicit approval. Preserve draft PR and stable branch until successful release.
