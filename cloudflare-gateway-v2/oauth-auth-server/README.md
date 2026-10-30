# OAuth 2.1 resource protection for ChatGPT + Codex

The previous RC used a static Bearer secret. That works for custom MCP clients but does **not** complete the user OAuth flow expected by ChatGPT custom plugins. This two-Worker alternative follows Cloudflare Workers OAuth Provider and OpenAI OAuth 2.1 guidance.

## Components
1. `oauth-auth-server/src/index.js`: OAuthAuthorizationServer, PKCE, consent, upstream GitHub login with allowlisted numeric GitHub ID, KV-bound grants, token exchange. GitHub's token is **never stored in MCP props**.
2. `src/oauth-index.js`: OAuthResourceServer, protected resource metadata, resource-bound access token validation over Worker service binding, scope check, owner check; existing three tools.
3. Existing `src/index.js` remains as a protected static-bearer test/roll-back path. Deploy `wrangler.oauth.toml` for ChatGPT, **never the static-bearer Worker as an anonymous public service**.

## Account setup (user action; no keys in chat)
- Log into Cloudflare, select Workers Free if eligible; configure a workers.dev subdomain. Check free-tier and NVIDIA quotas.
- Create a GitHub OAuth App for this private instance, with callback URL `https://nvidia-gateway-oauth-auth.<subdomain>.workers.dev/callback`.
- Obtain `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` from GitHub OAuth App; set as Cloudflare Worker secrets. Set `ALLOWED_GITHUB_ID` to your numeric GitHub account ID as secret, never username.
- Configure `NVIDIA_API_KEY` on **resource Worker** through Cloudflare secrets. This is not a ChatGPT API key.
- `npx wrangler kv namespace create OAUTH_KV`; paste only KV namespace ID into auth Worker configuration (not secret).
- Copy `oauth-auth-server/wrangler.example.toml` to `oauth-auth-server/wrangler.toml`; replace placeholders, deploy auth Worker **first**: `npx wrangler deploy -c oauth-auth-server/wrangler.toml`.
- Copy `wrangler.oauth.example.toml` to `wrangler.oauth.toml`; replace placeholders, deploy resource Worker **second**: `npx wrangler deploy -c wrangler.oauth.toml`.
- In ChatGPT Plugins > Add custom MCP server, use HTTPS resource URL with `/mcp` and OAuth, authorize through GitHub account and consent. ChatGPT may require a user click to approve. Repeat in Codex if tools/permissions differ.
- Verify unauthenticated 401 + resource metadata, OAuth discovery/PKCE with GitHub login, tools/list (3), actual SYNTHETIC NVIDIA response; no production declaration before that.

## Guardrails
- The GitHub account is checked by immutable numeric ID, not username. Consent page uses HTML escaping, secure one-time consent handle and upstream state binding from official library.
- Configure `offline_access` and sign in again if tokens expire. Do not bypass consent or allow open anonymous resource access.
- **Never expose NVIDIA_API_KEY, OAuth client secret, bearer token, or GitHub access token** to chat, GitHub or screenshots.
- Preserve Railway LibroVerse service and volume. Do not delete any Railway resources while migration is unverified.

Evidence: https://developers.cloudflare.com/agents/model-context-protocol/protocol/authorization/
and https://developers.openai.com/plugins/build/auth
