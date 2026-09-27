# NotebookLM Project Hub runtime

Compact project-oriented MCP facade over `notebooklm-py` 0.8.3.

## Public tool surface

The runtime intentionally exposes seven project-level operations:

1. `project_list` — notebooks/projects and optional source health.
2. `project_link` — stable project alias → NotebookLM notebook.
3. `project_sync` — inspect and refresh refreshable sources.
4. `project_analyze` — grounded chat with source references.
5. `project_research` — start/status/import web research.
6. `project_create_presentation` — start/status NotebookLM slide-deck generation.
7. `project_artifact` — list/download artifacts and expose rendered slide images as reusable visual assets.

NotebookLM-generated decks are **source material**, not the final Hilex template. A downstream Hilex bridge may reuse strong diagrams/illustrations while preserving the immutable Hilex corporate shell.

For slide decks, `project_artifact(action="list")` returns `visual_assets[]` with NotebookLM's rendered slide image URL, dimensions, alt text, extracted text, and a lightweight `visual_candidate` flag. This makes it possible to inspect/crop/reuse valuable visual material instead of discarding the NotebookLM design work.

`project_artifact(action="download", output_format="pptx"|"pdf")` mints a short-lived signed `/hub/files/...` URL; artifact bytes stay outside the MCP JSON channel.

## Persistent state

Project aliases are stored at `/data/oauth/project_hub_registry.json`, on the same persistent Railway volume used for OAuth state. No Google credentials are stored in GitHub.

## Required Railway variables

- `NOTEBOOKLM_MASTER_TOKEN_JSON` or `NOTEBOOKLM_MASTER_TOKEN_B64` — master token payload (secret; never commit).
- `NOTEBOOKLM_MCP_OAUTH_PASSWORD` — random password >=16 chars.
- `NOTEBOOKLM_MCP_OAUTH_BASE_URL` — bare public Railway origin, no `/mcp`.
- `NOTEBOOKLM_MCP_PUBLIC_URL` — same bare public origin.
- `NOTEBOOKLM_MCP_OAUTH_STATE_PATH=/data/oauth/oauth_state.json`
- `NOTEBOOKLM_HOME=/data`
- `NOTEBOOKLM_PROFILE=server`
- `NOTEBOOKLM_MCP_ALLOW_EXTERNAL_BIND=1`
- `PROJECT_HUB_REGISTRY=/data/oauth/project_hub_registry.json`

The Railway service must mount a persistent volume at `/data/oauth` so OAuth state and project aliases survive redeploys and sleep/wake cycles.
