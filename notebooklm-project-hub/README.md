# NotebookLM Project Hub runtime

Pinned runtime for the ChatGPT remote MCP proof using `notebooklm-py` 0.8.3.

Required Railway variables:

- `NOTEBOOKLM_MASTER_TOKEN_JSON` — full contents of `master_token.json` (secret; never commit).
- `NOTEBOOKLM_MCP_OAUTH_PASSWORD` — random password >=16 chars.
- `NOTEBOOKLM_MCP_OAUTH_BASE_URL` — bare public Railway origin, no `/mcp`.
- `NOTEBOOKLM_MCP_PUBLIC_URL` — same bare public origin.
- `NOTEBOOKLM_MCP_OAUTH_STATE_PATH=/data/oauth/oauth_state.json`
- `NOTEBOOKLM_HOME=/data`
- `NOTEBOOKLM_PROFILE=server`
- `NOTEBOOKLM_MCP_ALLOW_EXTERNAL_BIND=1`

The Railway service must mount a persistent volume at `/data/oauth` so ChatGPT OAuth clients/tokens survive redeploys and sleep/wake cycles.

Do not store Google credentials in GitHub.
