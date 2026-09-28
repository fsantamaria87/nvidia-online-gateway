from __future__ import annotations

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import hub_server as hub
from memory_curator import register_memory_tool
from notebooklm.mcp._filelink import DOWNLOAD_TTL, FileLinkError


_original_artifact_row = hub._artifact_row


def _artifact_row_with_proxy(artifact, include_visual_assets: bool = True):
    row = _original_artifact_row(artifact, include_visual_assets=include_visual_assets)
    if include_visual_assets and hub.PUBLIC_URL:
        for visual in row.get("visual_assets", []):
            image_url = visual.get("image_url")
            if isinstance(image_url, str) and image_url.startswith("https://"):
                token = hub._signer.sign({"op": "hubimg", "url": image_url}, DOWNLOAD_TTL)
                visual["image_proxy_url"] = f"{hub.PUBLIC_URL}/hub/images/{token}"
                visual["proxy_expires_in_seconds"] = DOWNLOAD_TTL
    return row


hub._artifact_row = _artifact_row_with_proxy


@hub.mcp.custom_route("/hub/images/{token}", methods=["GET"])
async def hub_image_proxy(request: Request) -> Response:
    token = request.path_params["token"]
    try:
        payload = hub._signer.verify(token, op="hubimg")
    except FileLinkError:
        return JSONResponse({"error": "invalid_or_expired_link"}, status_code=403)

    image_url = payload.get("url")
    if not isinstance(image_url, str) or not image_url.startswith(
        "https://lh3.googleusercontent.com/notebooklm/"
    ):
        return JSONResponse({"error": "invalid_image_source"}, status_code=403)

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(image_url)
            response.raise_for_status()
    except Exception as exc:
        return JSONResponse({"error": "image_proxy_failed", "detail": str(exc)}, status_code=502)

    media_type = response.headers.get("content-type") or "image/png"
    return Response(
        content=response.content,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer"},
    )


# Register the Memory Curator after the compact core tools are defined. This is
# deliberately a separate tool because persisting project memory is a stateful
# action and should be explicit/auditable rather than hidden inside project_sync.
register_memory_tool(hub.mcp, hub)


def main() -> None:
    hub.main()


if __name__ == "__main__":
    main()
