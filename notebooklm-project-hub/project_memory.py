from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MEMORY_ROOT = Path(os.environ.get("PROJECT_HUB_MEMORY_ROOT", "/data/oauth/project-memory"))
MEMORY_SOURCE_TITLE = "PROJECT_MEMORY.md — Activity & Decision Log"
_memory_lock = asyncio.Lock()


def _path(project: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in project.strip())
    if not safe:
        raise ValueError("project is required")
    return MEMORY_ROOT / f"{safe}.json"


def load_memory(project: str) -> dict[str, Any]:
    path = _path(project)
    if not path.exists():
        return {"version": 1, "project": project, "entries": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise RuntimeError(f"Project memory is invalid: {path}")
    return data


def render_markdown(project: str, data: dict[str, Any]) -> str:
    lines = [
        f"# PROJECT MEMORY — {project}",
        "",
        "This source is the curated operational memory for this project.",
        "It records activity, decisions, evidence and next steps. Newer entries do not silently invalidate source-of-truth documents.",
        "",
    ]
    entries = list(data.get("entries", []))
    if not entries:
        lines.append("No memory entries recorded yet.")
        return "\n".join(lines)
    for entry in reversed(entries):
        lines.extend([
            f"## {entry['occurred_at']} — {entry.get('title') or 'Project update'}",
            "",
            f"- Activity: {entry.get('activity') or '—'}",
            f"- Decision: {entry.get('decision') or '—'}",
            f"- Result: {entry.get('result') or '—'}",
            f"- Next step: {entry.get('next_step') or '—'}",
            f"- Evidence: {entry.get('evidence') or '—'}",
            f"- Tags: {', '.join(entry.get('tags') or []) or '—'}",
            "",
        ])
    return "\n".join(lines)


async def append_memory(
    project: str,
    *,
    title: str | None = None,
    activity: str | None = None,
    decision: str | None = None,
    result: str | None = None,
    next_step: str | None = None,
    evidence: str | None = None,
    tags: list[str] | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    if not any([title, activity, decision, result, next_step, evidence, tags]):
        raise ValueError("At least one memory field is required")
    async with _memory_lock:
        data = load_memory(project)
        entry = {
            "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
            "title": title,
            "activity": activity,
            "decision": decision,
            "result": result,
            "next_step": next_step,
            "evidence": evidence,
            "tags": tags or [],
        }
        data["entries"].append(entry)
        MEMORY_ROOT.mkdir(parents=True, exist_ok=True)
        path = _path(project)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
        return {"entry": entry, "entry_count": len(data["entries"]), "markdown": render_markdown(project, data)}


async def sync_memory_source(client: Any, notebook_id: str, project: str) -> dict[str, Any]:
    data = load_memory(project)
    markdown = render_markdown(project, data)
    sources = await client.sources.list(notebook_id)
    matches = [s for s in sources if str(getattr(s, "title", "")).strip().casefold() == MEMORY_SOURCE_TITLE.casefold()]
    for source in matches:
        await client.sources.delete(notebook_id, source.id)
    created = await client.sources.add_text(notebook_id, MEMORY_SOURCE_TITLE, markdown)
    return {
        "status": "synced",
        "source_title": MEMORY_SOURCE_TITLE,
        "source_id": getattr(created, "id", None),
        "entry_count": len(data.get("entries", [])),
        "replaced_sources": len(matches),
    }
