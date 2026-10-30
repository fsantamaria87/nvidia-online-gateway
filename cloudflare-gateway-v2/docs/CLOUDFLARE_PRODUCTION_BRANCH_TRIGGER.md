# Cloudflare production-branch Git trigger — 2026-10-30

This benign tracked documentation commit triggers Cloudflare Workers Builds after changing
the Worker production branch to `migration/nvidia-cloudflare-oauth-v2-rc2`. It does not alter runtime logic, secrets,
provider calls, or the stable `main` branch.

Expected Worker: `nvidia-gateway-oauth-auth`
Expected root: `cloudflare-gateway-v2`
Expected deploy command: `npx wrangler deploy --config oauth-auth-server/wrangler.toml`

**Do not declare deployed on this commit alone.** Confirm Cloudflare build references
this commit, the expected branch, and returns successful deployment and OAuth discovery.
