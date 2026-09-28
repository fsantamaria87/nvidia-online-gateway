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
  echo "WARN: initial NotebookLM auth refresh did not complete; Project Hub will attempt recovery on use" >&2
  cat /tmp/notebooklm-auth-refresh.log >&2 || true
}

if [ "${RUN_CAPACITY_BOOTSTRAP:-0}" = "1" ]; then
  python /app/capacity_bootstrap.py
fi

if [ "${RUN_MULTI_PROJECT_BOOTSTRAP:-0}" = "1" ]; then
  python /app/multi_project_bootstrap.py
fi

# One-shot bootstrap for the two next Knowledge Hubs. The implementation uses
# asyncio.gather so production-program and excel-qa are created in parallel.
if [ "${RUN_PROJECT_PAIR_BOOTSTRAP:-0}" = "1" ]; then
  python /app/project_pair_bootstrap.py
fi

if [ "${RUN_GOLDEN_VISUAL_PROBE:-0}" = "1" ]; then
  python /app/visual_manifest_probe.py || echo "WARN: Golden visual manifest probe failed" >&2
fi

unset NOTEBOOKLM_MASTER_TOKEN_B64 NOTEBOOKLM_MASTER_TOKEN_JSON \
  CAPACITY_BOOTSTRAP_B64 RUN_CAPACITY_BOOTSTRAP \
  MULTI_PROJECT_BOOTSTRAP_B64 RUN_MULTI_PROJECT_BOOTSTRAP \
  RUN_PROJECT_PAIR_BOOTSTRAP KNOWLEDGE_BOOTSTRAP_B64

exec python /app/launcher.py
