from pathlib import PurePosixPath
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ...services.home_orchestrator import AI_SERVICE_BASE_URL

router = APIRouter(prefix="/audio", tags=["Audio"])


def _validate_tts_filename(filename: str) -> str:
    path = PurePosixPath(filename)
    if filename != path.name or "\\" in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TTS audio filename")
    if path.suffix.lower() not in {".mp3", ".wav", ".ogg", ".webm"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported TTS audio type")
    return filename


@router.get("/tts/{filename}")
async def proxy_tts_audio(filename: str):
    safe_filename = _validate_tts_filename(filename)
    upstream_url = f"{AI_SERVICE_BASE_URL}/internal/v1/tts/audio/{quote(safe_filename)}"
    client = httpx.AsyncClient(timeout=30.0)
    try:
        upstream = await client.send(client.build_request("GET", upstream_url), stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI TTS audio service unavailable: {exc}",
        ) from exc

    if upstream.status_code == status.HTTP_404_NOT_FOUND:
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TTS audio not found")

    if upstream.status_code >= 400:
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI TTS audio proxy failed")

    async def body():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(
        body(),
        media_type=upstream.headers.get("content-type") or "audio/wav",
        headers={"Cache-Control": "private, max-age=600"},
    )
