from __future__ import annotations

import asyncio
import base64
import inspect
import json
import os
import subprocess
from pathlib import Path


def bootstrap_auth() -> None:
    profile = os.environ.get("NOTEBOOKLM_PROFILE", "server")
    home = Path(os.environ.get("NOTEBOOKLM_HOME", "/data"))
    profile_dir = home / "profiles" / profile
    profile_dir.mkdir(parents=True, exist_ok=True)
    token_path = profile_dir / "master_token.json"

    b64 = os.environ.get("NOTEBOOKLM_MASTER_TOKEN_B64")
    raw = os.environ.get("NOTEBOOKLM_MASTER_TOKEN_JSON")
    if b64:
        token_path.write_bytes(base64.b64decode(b64))
    elif raw:
        token_path.write_text(raw, encoding="utf-8")
    elif not token_path.exists():
        raise FileNotFoundError("NotebookLM master token is unavailable")

    token_path.chmod(0o600)
    subprocess.run(
        ["notebooklm", "--profile", profile, "auth", "refresh"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


bootstrap_auth()
import hub_server as hub

PROJECT = "golden-e2e"
OUTPUT = Path(os.environ.get("GOLDEN_VISUAL_MANIFEST", "/data/oauth/golden_e2e_visual_assets.json"))


async def invoke(tool_obj, **kwargs):
    if inspect.iscoroutinefunction(tool_obj):
        return await tool_obj(**kwargs)
    for attr in ("fn", "func", "function", "handler"):
        fn = getattr(tool_obj, attr, None)
        if inspect.iscoroutinefunction(fn):
            return await fn(**kwargs)
    if callable(tool_obj):
        value = tool_obj(**kwargs)
        if inspect.isawaitable(value):
            return await value
        return value
    raise TypeError(f"Tool object is not directly invokable: {type(tool_obj)!r}")


async def main() -> int:
    result = await invoke(
        hub.project_artifact,
        project=PROJECT,
        action="list",
        artifact_id=None,
        kind="slide_deck",
        output_format="pptx",
        include_visual_assets=True,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts = result.get("artifacts", [])
    assets = [v for a in artifacts for v in a.get("visual_assets", [])]
    candidates = [v for v in assets if v.get("visual_candidate")]
    print("VISUAL_MANIFEST_RESULT=" + json.dumps({
        "status": "PASS",
        "path": str(OUTPUT),
        "artifact_count": len(artifacts),
        "visual_assets": len(assets),
        "visual_candidates": len(candidates),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
