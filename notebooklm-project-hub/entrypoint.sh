#!/bin/sh
set -eu

PROFILE="${NOTEBOOKLM_PROFILE:-server}"
HOME_DIR="${NOTEBOOKLM_HOME:-/data}"
PROFILE_DIR="$HOME_DIR/profiles/$PROFILE"
OAUTH_DIR="$HOME_DIR/oauth"
mkdir -p "$PROFILE_DIR" "$OAUTH_DIR"

if [ -z "${NOTEBOOKLM_MASTER_TOKEN_JSON:-}" ]; then
  echo "ERROR: NOTEBOOKLM_MASTER_TOKEN_JSON is not configured" >&2
  exit 78
fi

umask 077
printf '%s' "$NOTEBOOKLM_MASTER_TOKEN_JSON" > "$PROFILE_DIR/master_token.json"
chmod 600 "$PROFILE_DIR/master_token.json"
unset NOTEBOOKLM_MASTER_TOKEN_JSON

# On a fresh container, materialize/refresh storage_state.json from the durable master token.
# A transient failure is logged, but the MCP process still starts so its own auth recovery can run.
notebooklm --profile "$PROFILE" auth refresh >/tmp/notebooklm-auth-refresh.log 2>&1 || {
  echo "WARN: initial NotebookLM auth refresh did not complete; MCP will attempt recovery on use" >&2
  cat /tmp/notebooklm-auth-refresh.log >&2 || true
}

exec notebooklm-mcp \
  --transport http \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --profile "$PROFILE"
