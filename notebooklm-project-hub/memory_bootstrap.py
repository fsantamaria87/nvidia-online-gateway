from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path

from notebooklm import NotebookLMClient
from project_memory import append_memory, sync_memory_source

PROFILE = os.environ.get("NOTEBOOKLM_PROFILE", "server")
REGISTRY_PATH = Path(os.environ.get("PROJECT_HUB_REGISTRY", "/data/oauth/project_hub_registry.json"))
PAYLOAD_ENV = "PROJECT_MEMORY_UPDATE_B64"


def load_payload() -> list[dict]:
    raw = os.environ.get(PAYLOAD_ENV, "").strip()
    if not raw:
        raise RuntimeError(f"{PAYLOAD_ENV} is required")
    payload = json.loads(base64.b64decode(raw).decode("utf-8"))
    updates = payload.get("updates") if isinstance(payload, dict) else None
    if not isinstance(updates, list) or not updates:
        raise RuntimeError("Payload requires a non-empty updates array")
    return updates


def load_registry() -> dict:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("projects"), dict):
        raise RuntimeError("Invalid Project Hub registry")
    return data


async def apply_one(client: NotebookLMClient, registry: dict, update: dict) -> dict:
    project = str(update.get("project") or "").strip()
    if not project:
        raise ValueError("Each update requires project")
    entry = registry["projects"].get(project)
    if not entry:
        raise ValueError(f"Unknown linked project: {project}")
    result = await append_memory(
        project,
        title=update.get("title"),
        activity=update.get("activity"),
        decision=update.get("decision"),
        result=update.get("result"),
        next_step=update.get("next_step"),
        evidence=update.get("evidence"),
        tags=update.get("tags"),
        occurred_at=update.get("occurred_at"),
    )
    sync = await sync_memory_source(client, entry["notebook_id"], project)
    return {"project": project, "entry_count": result["entry_count"], "sync": sync}


async def main() -> None:
    updates = load_payload()
    registry = load_registry()
    async with NotebookLMClient.from_storage(profile=PROFILE) as client:
        results = []
        for update in updates:
            try:
                results.append({"status": "ok", **(await apply_one(client, registry, update))})
            except Exception as exc:
                results.append({"status": "error", "project": update.get("project"), "error": str(exc)})
        print(json.dumps({"kind": "project_memory_update", "results": results}, ensure_ascii=False))
        if any(r["status"] == "error" for r in results):
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
