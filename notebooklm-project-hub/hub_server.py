from __future__ import annotations

import asyncio
import json
import os
import secrets
import tempfile
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response

from notebooklm import NotebookLMClient, SlideDeckFormat, SlideDeckLength
from notebooklm.mcp._auth import build_auth, get_configured_token
from notebooklm.mcp._filelink import DOWNLOAD_TTL, FileLinkError, FileLinkSigner
from notebooklm.mcp._oauth import build_oauth_provider, get_oauth_config

PROFILE = os.environ.get("NOTEBOOKLM_PROFILE", "server")
REGISTRY_PATH = Path(os.environ.get("PROJECT_HUB_REGISTRY", "/data/oauth/project_hub_registry.json"))
PUBLIC_URL = (os.environ.get("NOTEBOOKLM_MCP_PUBLIC_URL") or os.environ.get("NOTEBOOKLM_MCP_OAUTH_BASE_URL") or "").rstrip("/")
PORT = int(os.environ.get("PORT", "8080"))

_registry_lock = asyncio.Lock()
_signer = FileLinkSigner(secrets.token_bytes(32))


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if hasattr(value, "value"):
        try:
            return _jsonable(value.value)
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return {k: _jsonable(v) for k, v in vars(value).items() if not k.startswith("_")}
    return str(value)


def _load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"version": 1, "projects": {}}
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("projects"), dict):
            raise ValueError("invalid registry shape")
        return data
    except Exception:
        raise RuntimeError(f"Project Hub registry is invalid: {REGISTRY_PATH}")


def _save_registry(data: dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, REGISTRY_PATH)


@asynccontextmanager
async def _client():
    async with NotebookLMClient.from_storage(profile=PROFILE) as client:
        yield client


async def _resolve_notebook(client: NotebookLMClient, ref: str):
    notebooks = await client.notebooks.list()
    needle = ref.strip().casefold()
    exact = [n for n in notebooks if n.id.casefold() == needle or n.title.strip().casefold() == needle]
    if len(exact) == 1:
        return exact[0]
    prefix = [n for n in notebooks if n.id.casefold().startswith(needle)]
    if len(prefix) == 1:
        return prefix[0]
    title_prefix = [n for n in notebooks if n.title.strip().casefold().startswith(needle)]
    if len(title_prefix) == 1:
        return title_prefix[0]
    matches = exact or prefix or title_prefix
    if len(matches) > 1:
        raise ValueError(f"Notebook reference is ambiguous: {ref!r}")
    raise ValueError(f"Notebook not found: {ref!r}")


async def _resolve_project(client: NotebookLMClient, project: str):
    data = _load_registry()
    entry = data["projects"].get(project)
    if entry is None:
        nb = await _resolve_notebook(client, project)
        return nb, None
    nb = await _resolve_notebook(client, entry["notebook_id"])
    return nb, entry


def _source_row(source: Any) -> dict[str, Any]:
    return {
        "id": getattr(source, "id", None),
        "title": getattr(source, "title", None),
        "kind": _jsonable(getattr(source, "kind", None)),
        "status": _jsonable(getattr(source, "status_str", None) or getattr(source, "status", None)),
        "drive_status": _jsonable(getattr(source, "drive_status_str", None) or getattr(source, "drive_status", None)),
        "created_at": _jsonable(getattr(source, "created_at", None)),
    }


def _artifact_row(artifact: Any, include_visual_assets: bool = True) -> dict[str, Any]:
    row = {
        "id": artifact.id,
        "title": artifact.title,
        "kind": _jsonable(artifact.kind),
        "status": getattr(artifact, "status_str", None) or _jsonable(artifact.status),
        "created_at": _jsonable(getattr(artifact, "created_at", None)),
        "url": getattr(artifact, "url", None),
        "generation_prompt": getattr(artifact, "generation_prompt", None),
        "source_ids": list(getattr(artifact, "source_ids", ()) or ()),
    }
    if include_visual_assets and getattr(artifact, "slides", None):
        assets = []
        for index, slide in enumerate(artifact.slides, start=1):
            text = slide.text or ""
            assets.append({
                "slide": index,
                "image_url": slide.image_url,
                "width": slide.width,
                "height": slide.height,
                "alt_text": slide.alt_text,
                "text": text,
                "text_chars": len(text),
                "visual_candidate": bool(slide.image_url) and len(text) <= 900,
            })
        row["visual_assets"] = assets
    return row


def _auth_provider():
    token = get_configured_token()
    oauth_config = get_oauth_config(profile=PROFILE)
    oauth = build_oauth_provider(oauth_config) if oauth_config else None
    if token is None and oauth is None:
        raise RuntimeError("Project Hub refuses external HTTP startup without MCP bearer or OAuth auth")
    return build_auth(token, oauth)


mcp = FastMCP(
    name="NotebookLM Project Hub",
    instructions=(
        "Compact project-oriented NotebookLM gateway. Prefer the seven project_* tools. "
        "Presentation artifacts expose NotebookLM-rendered slide images as visual assets so a downstream "
        "Hilex bridge can reuse strong diagrams/illustrations without adopting NotebookLM's slide shell."
    ),
    auth=_auth_provider(),
)


@mcp.tool
async def project_list(include_sources: bool = False) -> dict[str, Any]:
    """List linked projects plus available NotebookLM notebooks. Optionally include source health."""
    async with _client() as client:
        notebooks = await client.notebooks.list()
        registry = _load_registry()
        linked_by_id = {v["notebook_id"]: k for k, v in registry["projects"].items()}
        rows = []
        for nb in notebooks:
            row = {
                "project": linked_by_id.get(nb.id),
                "notebook_id": nb.id,
                "title": nb.title,
                "created_at": _jsonable(getattr(nb, "created_at", None)),
                "linked": nb.id in linked_by_id,
            }
            if include_sources:
                sources = await client.sources.list(nb.id)
                row["sources"] = [_source_row(s) for s in sources]
            rows.append(row)
        return {"projects": rows, "linked_count": len(registry["projects"]), "notebook_count": len(rows)}


@mcp.tool
async def project_link(project: str, notebook: str) -> dict[str, Any]:
    """Link a stable project name to an existing NotebookLM notebook. This does not modify notebook content."""
    async with _client() as client:
        nb = await _resolve_notebook(client, notebook)
        async with _registry_lock:
            data = _load_registry()
            data["projects"][project] = {
                "notebook_id": nb.id,
                "notebook_title": nb.title,
                "linked_at": datetime.utcnow().isoformat() + "Z",
            }
            _save_registry(data)
        return {"status": "linked", "project": project, "notebook_id": nb.id, "notebook_title": nb.title}


@mcp.tool
async def project_sync(project: str, refresh: bool = True) -> dict[str, Any]:
    """Inspect a project's NotebookLM sources and optionally refresh refreshable URL/Drive sources."""
    async with _client() as client:
        nb, _ = await _resolve_project(client, project)
        sources = await client.sources.list(nb.id)
        refreshed, skipped, failed = [], [], []
        if refresh:
            for source in sources:
                kind = str(_jsonable(getattr(source, "kind", ""))).lower()
                if kind not in {"url", "web_page", "drive", "google_drive", "youtube"}:
                    skipped.append({"id": source.id, "title": source.title, "reason": f"non-refreshable kind: {kind}"})
                    continue
                try:
                    await client.sources.refresh(nb.id, source.id)
                    refreshed.append({"id": source.id, "title": source.title})
                except Exception as exc:
                    failed.append({"id": source.id, "title": source.title, "error": str(exc)})
            sources = await client.sources.list(nb.id)
        return {
            "project": project,
            "notebook_id": nb.id,
            "notebook_title": nb.title,
            "refresh_requested": refresh,
            "refreshed": refreshed,
            "skipped": skipped,
            "failed": failed,
            "sources": [_source_row(s) for s in sources],
        }


@mcp.tool
async def project_analyze(project: str, question: str, source_ids: list[str] | None = None) -> dict[str, Any]:
    """Ask a grounded question against a project's NotebookLM sources and return source references."""
    async with _client() as client:
        nb, _ = await _resolve_project(client, project)
        result = await client.chat.ask(nb.id, question, source_ids=source_ids)
        return {
            "project": project,
            "notebook_id": nb.id,
            "answer": result.answer,
            "conversation_id": getattr(result, "conversation_id", None),
            "references": _jsonable(getattr(result, "references", [])),
        }


@mcp.tool
async def project_research(
    project: str,
    action: Literal["start", "status", "import"] = "start",
    query: str | None = None,
    task_id: str | None = None,
    mode: Literal["fast", "deep"] = "fast",
    cited_only: bool = False,
    max_sources: int | None = None,
) -> dict[str, Any]:
    """Start, inspect, or import NotebookLM web research without exposing low-level research tools."""
    async with _client() as client:
        nb, _ = await _resolve_project(client, project)
        if action == "start":
            if not query:
                raise ValueError("query is required when action='start'")
            result = await client.research.start(nb.id, query, source="web", mode=mode)
            return {"project": project, "notebook_id": nb.id, "action": action, "task_id": result.task_id, "status": _jsonable(getattr(result, "status", None))}
        if not task_id:
            raise ValueError("task_id is required for status/import")
        if action == "status":
            result = await client.research.poll(nb.id, task_id=task_id)
            return {"project": project, "notebook_id": nb.id, "action": action, "result": _jsonable(result)}
        polled = await client.research.poll(nb.id, task_id=task_id)
        if str(_jsonable(polled.status)).lower() != "completed":
            raise ValueError(f"Research task is not completed: {polled.status}")
        selected = list(polled.sources)
        if cited_only:
            selection = client.research.select_cited_sources(selected, polled.report or "")
            selected = list(selection.sources)
        if max_sources is not None:
            selected = selected[: max(0, max_sources)]
        result = await client.research.import_sources(nb.id, task_id, selected)
        return {"project": project, "notebook_id": nb.id, "action": action, "selected_count": len(selected), "result": _jsonable(result)}


@mcp.tool
async def project_create_presentation(
    project: str,
    action: Literal["start", "status"] = "start",
    instructions: str | None = None,
    task_id: str | None = None,
    source_ids: list[str] | None = None,
    language: str = "es",
    deck_format: Literal["presenter", "detailed"] = "presenter",
    deck_length: Literal["short", "default"] = "short",
) -> dict[str, Any]:
    """Generate or poll a NotebookLM slide deck. Generated slides are visual/content source material, not the final Hilex shell."""
    async with _client() as client:
        nb, _ = await _resolve_project(client, project)
        if action == "status":
            if not task_id:
                raise ValueError("task_id is required when action='status'")
            status = await client.artifacts.poll_status(nb.id, task_id)
            return {"project": project, "notebook_id": nb.id, "action": action, "result": _jsonable(status)}
        fmt = SlideDeckFormat.PRESENTER_SLIDES if deck_format == "presenter" else SlideDeckFormat.DETAILED_DECK
        length = SlideDeckLength.SHORT if deck_length == "short" else SlideDeckLength.DEFAULT
        status = await client.artifacts.generate_slide_deck(
            nb.id,
            source_ids=source_ids,
            language=language,
            instructions=instructions,
            slide_format=fmt,
            slide_length=length,
        )
        return {"project": project, "notebook_id": nb.id, "action": action, "task_id": status.task_id, "status": _jsonable(getattr(status, "status", None))}


@mcp.tool
async def project_artifact(
    project: str,
    action: Literal["list", "download"] = "list",
    artifact_id: str | None = None,
    kind: Literal["slide_deck", "all"] = "slide_deck",
    output_format: Literal["pptx", "pdf"] = "pptx",
    include_visual_assets: bool = True,
) -> dict[str, Any]:
    """List artifacts or mint a short-lived download URL. Slide decks expose rendered slide-image URLs for visual reuse/extraction."""
    async with _client() as client:
        nb, _ = await _resolve_project(client, project)
        artifacts = await client.artifacts.list_slide_decks(nb.id) if kind == "slide_deck" else await client.artifacts.list(nb.id)
        if action == "list":
            return {"project": project, "notebook_id": nb.id, "artifacts": [_artifact_row(a, include_visual_assets=include_visual_assets) for a in artifacts]}
        if not artifact_id:
            completed = [a for a in artifacts if getattr(a, "is_completed", False) or str(getattr(a, "status_str", "")).lower() == "completed"]
            if not completed:
                raise ValueError("No completed slide deck is available to download")
            artifact_id = completed[-1].id
        if not PUBLIC_URL:
            raise RuntimeError("NOTEBOOKLM_MCP_PUBLIC_URL or NOTEBOOKLM_MCP_OAUTH_BASE_URL is required for remote artifact downloads")
        token = _signer.sign({"op": "hubdl", "nb": nb.id, "artifact": artifact_id, "fmt": output_format}, DOWNLOAD_TTL)
        return {
            "project": project,
            "notebook_id": nb.id,
            "artifact_id": artifact_id,
            "output_format": output_format,
            "download_url": f"{PUBLIC_URL}/hub/files/{token}",
            "expires_in_seconds": DOWNLOAD_TTL,
        }


@mcp.custom_route("/hub/files/{token}", methods=["GET"])
async def hub_download(request: Request) -> Response:
    token = request.path_params["token"]
    try:
        payload = _signer.verify(token, op="hubdl")
    except FileLinkError:
        return JSONResponse({"error": "invalid_or_expired_link"}, status_code=403)
    nb_id = payload.get("nb")
    artifact_id = payload.get("artifact")
    fmt = payload.get("fmt")
    if not isinstance(nb_id, str) or not isinstance(artifact_id, str) or fmt not in {"pptx", "pdf"}:
        return JSONResponse({"error": "invalid_link_payload"}, status_code=403)
    tmpdir = Path(tempfile.mkdtemp(prefix="project-hub-"))
    output = tmpdir / f"notebooklm-{artifact_id}.{fmt}"
    try:
        async with _client() as client:
            await client.artifacts.download_slide_deck(nb_id, str(output), artifact_id=artifact_id, output_format=fmt)
    except Exception as exc:
        return JSONResponse({"error": "download_failed", "detail": str(exc)}, status_code=502)
    return FileResponse(
        output,
        media_type=("application/vnd.openxmlformats-officedocument.presentationml.presentation" if fmt == "pptx" else "application/pdf"),
        filename=output.name,
        headers={"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer"},
    )


def main() -> None:
    mcp.run(transport="http", host="0.0.0.0", port=PORT, stateless_http=True, uvicorn_config={"proxy_headers": False})


if __name__ == "__main__":
    main()
