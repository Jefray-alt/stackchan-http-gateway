from fastapi import APIRouter

router = APIRouter(prefix="/transcription", tags=["transcription"])

@router.get("/")
def transcribe():
    return { "message": "hello" }