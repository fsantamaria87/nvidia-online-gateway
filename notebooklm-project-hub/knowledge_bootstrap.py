from __future__ import annotations

import asyncio
import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from notebooklm import NotebookLMClient

PROFILE = os.environ.get("NOTEBOOKLM_PROFILE", "server")
REGISTRY_PATH = Path(os.environ.get("PROJECT_HUB_REGISTRY", "/data/oauth/project_hub_registry.json"))
PAYLOAD_ENV = "KNOWLEDGE_BOOTSTRAP_B64"
PAYLOAD_FILE = Path(os.environ.get("KNOWLEDGE_BOOTSTRAP_FILE", "/app/knowledge_hubs_payload.json"))
_registry_lock = asyncio.Lock()


def load_payload() -> list[dict[str, Any]]:
    raw = os.environ.get(PAYLOAD_ENV, "").strip()
    try:
        if raw:
            payload = json.loads(base64.b64decode(raw).decode("utf-8"))
        elif PAYLOAD_FILE.exists():
            payload = json.loads(PAYLOAD_FILE.read_text(encoding="utf-8"))
        else:
            raise RuntimeError(f"Provide {PAYLOAD_ENV} or {PAYLOAD_FILE}")
    except Exception as exc:
        raise RuntimeError(f"Invalid knowledge bootstrap payload: {exc}") from exc
    projects = payload.get("projects") if isinstance(payload, dict) else None
    if not isinstance(projects, list) or not projects:
        raise RuntimeError("Bootstrap payload requires non-empty projects array")
    for p in projects:
        if not isinstance(p, dict) or not p.get("project") or not p.get("notebook_title"):
            raise RuntimeError("Each project requires project and notebook_title")
        sources = p.get("sources")
        if not isinstance(sources, list) or not sources:
            raise RuntimeError("Each project requires non-empty sources")
        for s in sources:
            if not isinstance(s, dict) or not s.get("title") or not s.get("content"):
                raise RuntimeError("Each source requires title and content")
    return projects


async def update_registry(project: str, notebook_id: str, notebook_title: str) -> None:
    async with _registry_lock:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        if REGISTRY_PATH.exists():
            data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        else:
            data = {"version": 1, "projects": {}}
        if not isinstance(data, dict):
            data = {"version": 1, "projects": {}}
        data.setdefault("version", 1)
        data.setdefault("projects", {})
        data["projects"][project] = {
            "notebook_id": notebook_id,
            "notebook_title": notebook_title,
            "linked_at": datetime.now(timezone.utc).isoformat(),
            "bootstrap": "knowledge-bootstrap-v1",
        }
        tmp = REGISTRY_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, REGISTRY_PATH)


async def bootstrap_one(spec: dict[str, Any]) -> dict[str, Any]:
    project = spec["project"].strip()
    title = spec["notebook_title"].strip()
    async with NotebookLMClient.from_storage(profile=PROFILE) as client:
        notebooks = await client.notebooks.list()
        matches = [n for n in notebooks if n.title.strip().casefold() == title.casefold()]
        if matches:
            notebook = matches[0]
            created = False
        else:
            notebook = await client.notebooks.create(title)
            created = True
        existing_sources = await client.sources.list(notebook.id)
        existing_titles = {str(s.title).strip().casefold() for s in existing_sources}
        added: list[str] = []
        skipped: list[str] = []
        for source in spec["sources"]:
            source_title = source["title"].strip()
            if source_title.casefold() in existing_titles:
                skipped.append(source_title)
                continue
            await client.sources.add_text(notebook.id, source_title, source["content"])
            existing_titles.add(source_title.casefold())
            added.append(source_title)
        await update_registry(project, notebook.id, notebook.title)
        return {
            "status": "ok",
            "project": project,
            "notebook_id": notebook.id,
            "notebook_title": notebook.title,
            "notebook_created": created,
            "sources_added": added,
            "sources_skipped_existing": skipped,
        }


async def main() -> None:
    specs = load_payload()
    results = await asyncio.gather(*(bootstrap_one(s) for s in specs), return_exceptions=True)
    rendered = []
    failed = False
    for spec, result in zip(specs, results):
        if isinstance(result, Exception):
            failed = True
            rendered.append({"status": "error", "project": spec.get("project"), "error": str(result)})
        else:
            rendered.append(result)
    print(json.dumps({"knowledge_bootstrap": rendered}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
