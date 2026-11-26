import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from starlette.requests import ClientDisconnect

from stackchan_http_gateway.audio.capture import save_pcm_wav
from stackchan_http_gateway.audio.errors import (
    AudioReceiveTimeoutError,
    InvalidPcmError,
    PcmTooLargeError,
)
from stackchan_http_gateway.audio.receiver import receive_pcm


router = APIRouter(tags=["transcription"])
logger = logging.getLogger("uvicorn.error.capture")
_ACKNOWLEDGMENT = b"Audio saved (test only)"


@router.post("/v1/transcriptions", response_class=Response)
async def capture_audio(request: Request) -> Response:
    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != "application/octet-stream":
        raise HTTPException(415, "Expected application/octet-stream")

    state = request.app.state
    if state.capture_directory is None:
        raise HTTPException(503, "Audio capture is disabled")
    if state.capture_busy:
        raise HTTPException(503, "An audio upload is already in progress")

    # No await between admission and setting the per-process upload slot.
    state.capture_busy = True
    try:
        try:
            pcm = await receive_pcm(request.stream())
        except InvalidPcmError as error:
            raise HTTPException(400, str(error)) from error
        except PcmTooLargeError as error:
            raise HTTPException(413, str(error)) from error
        except AudioReceiveTimeoutError as error:
            raise HTTPException(408, str(error)) from error
        except ClientDisconnect as error:
            raise HTTPException(400, "Audio upload disconnected") from error

        # Keep finalization synchronous: cancellation cannot interrupt publication.
        try:
            path = save_pcm_wav(pcm, state.capture_directory)
        except OSError as error:
            logger.exception("Audio capture could not be saved")
            raise HTTPException(500, "Audio capture could not be saved") from error

        logger.info(
            "%s %s client=%s saved=%s pcm_bytes=%d duration_seconds=%.3f",
            request.method, request.url.path, request.client, path.name, len(pcm), len(pcm) / 32_000,
        )
        return Response(
            _ACKNOWLEDGMENT,
            media_type="text/plain",
            headers={"Content-Length": str(len(_ACKNOWLEDGMENT))},
        )
    finally:
        state.capture_busy = False
