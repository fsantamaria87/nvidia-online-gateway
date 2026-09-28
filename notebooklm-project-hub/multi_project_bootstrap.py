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
PAYLOAD_ENV = "MULTI_PROJECT_BOOTSTRAP_B64"
_registry_lock = asyncio.Lock()


def load_payload() -> list[dict[str, Any]]:
    raw = os.environ.get(PAYLOAD_ENV, "").strip()
    if not raw:
        raise RuntimeError(f"{PAYLOAD_ENV} is required")
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        payload = json.loads(decoded)
    except Exception as exc:
        raise RuntimeError(f"Invalid {PAYLOAD_ENV}: {exc}") from exc
    projects = payload.get("projects") if isinstance(payload, dict) else None
    if not isinstance(projects, list) or not projects:
        raise RuntimeError("Bootstrap payload requires a non-empty projects array")
    for project in projects:
        if not isinstance(project, dict) or not project.get("project") or not project.get("notebook_title"):
            raise RuntimeError("Each project requires project and notebook_title")
        sources = project.get("sources")
        if not isinstance(sources, list) or not sources:
            raise RuntimeError(f"Project {project.get('project')} requires sources")
        for item in sources:
            if not isinstance(item, dict) or not item.get("title") or not item.get("content"):
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
            "bootstrap": "multi-project-bootstrap-v1",
        }
        tmp = REGISTRY_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, REGISTRY_PATH)


async def bootstrap_one(payload: dict[str, Any]) -> dict[str, Any]:
    project = payload["project"].strip()
    title = payload["notebook_title"].strip()
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
        for source in payload["sources"]:
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
    projects = load_payload()
    results = await asyncio.gather(*(bootstrap_one(p) for p in projects), return_exceptions=True)
    rendered = []
    failed = False
    for project, result in zip(projects, results):
        if isinstance(result, Exception):
            failed = True
            rendered.append({"status": "error", "project": project.get("project"), "error": str(result)})
        else:
            rendered.append(result)
    print(json.dumps({"kind": "multi_project_bootstrap", "results": rendered}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
