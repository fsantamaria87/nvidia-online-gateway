# Dual-worker Cloudflare build trigger — 2026-10-30

Documentation-only push to production branch migration/nvidia-cloudflare-oauth-v2-rc2 after both Cloudflare
GitHub Workers Builds projects are connected. This triggers:
- nvidia-gateway-oauth-auth (wrangler config oauth-auth-server/wrangler.toml)
- nvidia-online-gateway-oauth-v2 (wrangler config wrangler.oauth.toml)

Expect both to build from the same commit and keep their independent service
names. The resource Worker requires AUTH_SERVER Service Binding.
No credentials, real API calls, changes to main or Railway are in this commit.
