#!/bin/sh
set -eu

PROFILE="${NOTEBOOKLM_PROFILE:-server}"
HOME_DIR="${NOTEBOOKLM_HOME:-/data}"
PROFILE_DIR="$HOME_DIR/profiles/$PROFILE"
OAUTH_DIR="$HOME_DIR/oauth"
mkdir -p "$PROFILE_DIR" "$OAUTH_DIR"

umask 077

if [ -n "${NOTEBOOKLM_MASTER_TOKEN_B64:-}" ]; then
  printf '%s' "$NOTEBOOKLM_MASTER_TOKEN_B64" | base64 -d > "$PROFILE_DIR/master_token.json"
elif [ -n "${NOTEBOOKLM_MASTER_TOKEN_JSON:-}" ]; then
  printf '%s' "$NOTEBOOKLM_MASTER_TOKEN_JSON" > "$PROFILE_DIR/master_token.json"
else
  echo "ERROR: configure NOTEBOOKLM_MASTER_TOKEN_B64 (preferred) or NOTEBOOKLM_MASTER_TOKEN_JSON" >&2
  exit 78
fi

chmod 600 "$PROFILE_DIR/master_token.json"
unset NOTEBOOKLM_MASTER_TOKEN_B64 NOTEBOOKLM_MASTER_TOKEN_JSON

python - "$PROFILE_DIR/master_token.json" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
try:
    obj = json.loads(p.read_text(encoding='utf-8'))
except Exception as e:
    print(f"ERROR: invalid master_token payload: {e}", file=sys.stderr)
    raise SystemExit(78)
if not isinstance(obj, dict):
    print("ERROR: master_token payload must be a JSON object", file=sys.stderr)
    raise SystemExit(78)
print("Master token JSON parsed successfully")
PY

notebooklm --profile "$PROFILE" auth refresh >/tmp/notebooklm-auth-refresh.log 2>&1 || {
  echo "WARN: initial NotebookLM auth refresh did not complete; MCP will attempt recovery on use" >&2
  cat /tmp/notebooklm-auth-refresh.log >&2 || true
}

exec notebooklm-mcp \
  --transport http \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --profile "$PROFILE"
