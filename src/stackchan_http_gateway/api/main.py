from fastapi import APIRouter
from stackchan_http_gateway.api.transcription import router as transcription_router

router = APIRouter(prefix="/api")
router.include_router(transcription_router)
