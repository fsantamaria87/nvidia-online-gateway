from __future__ import annotations

import asyncio
import inspect
import json
import time

import hub_server as hub

NOTEBOOK_TITLE = "MCP Integration Test - 2026-09-27"
PROJECT = "golden-e2e"


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


def record(rows, name, ok, **extra):
    rows.append({"tool": name, "status": "PASS" if ok else "FAIL", **extra})


async def main():
    rows = []
    task_research = None
    task_deck = None

    try:
        r = await invoke(hub.project_list, include_sources=True)
        matches = [p for p in r.get("projects", []) if p.get("title") == NOTEBOOK_TITLE]
        record(rows, "project_list", bool(matches), notebook_count=r.get("notebook_count"), matched=len(matches))
        if not matches:
            raise RuntimeError(f"Synthetic notebook not found: {NOTEBOOK_TITLE}")
    except Exception as exc:
        record(rows, "project_list", False, error=type(exc).__name__)
        print("GOLDEN_E2E_RESULT=" + json.dumps({"overall": "FAIL", "rows": rows}, ensure_ascii=False))
        return 1

    try:
        r = await invoke(hub.project_link, project=PROJECT, notebook=NOTEBOOK_TITLE)
        record(rows, "project_link", r.get("status") == "linked", notebook_id=r.get("notebook_id"))
    except Exception as exc:
        record(rows, "project_link", False, error=type(exc).__name__)

    try:
        r = await invoke(hub.project_sync, project=PROJECT, refresh=False)
        record(rows, "project_sync", not r.get("failed"), source_count=len(r.get("sources", [])), refresh_requested=r.get("refresh_requested"))
    except Exception as exc:
        record(rows, "project_sync", False, error=type(exc).__name__)

    try:
        q = "Según las fuentes del notebook, si una línea produce 100 piezas/h y la demanda es 120 piezas/h, ¿cuál es el déficit y la utilización requerida?"
        r = await invoke(hub.project_analyze, project=PROJECT, question=q, source_ids=None)
        record(rows, "project_analyze", bool(r.get("answer")), reference_count=len(r.get("references", [])))
    except Exception as exc:
        record(rows, "project_analyze", False, error=type(exc).__name__)

    try:
        r = await invoke(hub.project_research, project=PROJECT, action="start", query="industrial capacity utilization demand versus capacity definition", task_id=None, mode="fast", cited_only=False, max_sources=None)
        task_research = r.get("task_id")
        ok = bool(task_research)
        if ok:
            await asyncio.sleep(8)
            s = await invoke(hub.project_research, project=PROJECT, action="status", query=None, task_id=task_research, mode="fast", cited_only=False, max_sources=None)
            status = str(s.get("result", {}).get("status", ""))
            record(rows, "project_research", True, task_id=task_research, observed_status=status or "started")
        else:
            record(rows, "project_research", False, error="missing_task_id")
    except Exception as exc:
        record(rows, "project_research", False, error=type(exc).__name__)

    try:
        instructions = "Golden E2E: crea una presentación breve, ejecutiva y visual del caso sintético de capacidad. Prioriza diagramas e imágenes reutilizables, con poco texto por slide."
        r = await invoke(hub.project_create_presentation, project=PROJECT, action="start", instructions=instructions, task_id=None, source_ids=None, language="es", deck_format="presenter", deck_length="short")
        task_deck = r.get("task_id")
        if not task_deck:
            raise RuntimeError("missing presentation task_id")
        final_status = "started"
        complete = False
        for _ in range(18):
            await asyncio.sleep(10)
            s = await invoke(hub.project_create_presentation, project=PROJECT, action="status", instructions=None, task_id=task_deck, source_ids=None, language="es", deck_format="presenter", deck_length="short")
            result = s.get("result", {})
            final_status = str(result.get("status") or result.get("status_label") or "")
            complete = bool(result.get("is_complete")) or final_status.lower() in {"completed", "complete", "done"}
            if complete:
                break
        record(rows, "project_create_presentation", complete, task_id=task_deck, observed_status=final_status or "unknown")
    except Exception as exc:
        record(rows, "project_create_presentation", False, error=type(exc).__name__)

    try:
        r = await invoke(hub.project_artifact, project=PROJECT, action="list", artifact_id=None, kind="slide_deck", output_format="pptx", include_visual_assets=True)
        arts = r.get("artifacts", [])
        completed = [a for a in arts if str(a.get("status", "")).lower() == "completed"]
        visual_assets = [v for a in arts for v in a.get("visual_assets", [])]
        candidates = [v for v in visual_assets if v.get("visual_candidate")]
        record(rows, "project_artifact:list", bool(arts), artifact_count=len(arts), visual_assets=len(visual_assets), visual_candidates=len(candidates))

        target = (completed[-1] if completed else (arts[-1] if arts else None))
        if target:
            d = await invoke(hub.project_artifact, project=PROJECT, action="download", artifact_id=target.get("id"), kind="slide_deck", output_format="pptx", include_visual_assets=True)
            record(rows, "project_artifact:download", bool(d.get("download_url")), artifact_id=d.get("artifact_id"), expires_in_seconds=d.get("expires_in_seconds"))
        else:
            record(rows, "project_artifact:download", False, error="no_artifact")
    except Exception as exc:
        record(rows, "project_artifact", False, error=type(exc).__name__)

    overall = "PASS" if all(r["status"] == "PASS" for r in rows) else "PARTIAL"
    print("GOLDEN_E2E_RESULT=" + json.dumps({"overall": overall, "rows": rows}, ensure_ascii=False))
    return 0 if overall == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
