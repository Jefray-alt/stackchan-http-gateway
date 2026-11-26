import os
from pathlib import Path

from fastapi import FastAPI

from stackchan_http_gateway.api.main import router as api_router
from stackchan_http_gateway.api.transcriptions import router as capture_router


def create_app() -> FastAPI:
    app = FastAPI()
    configured_directory = os.environ.get("STACKCHAN_CAPTURE_DIR")
    app.state.capture_directory = (
        Path(configured_directory).expanduser() if configured_directory else None
    )
    app.state.capture_busy = False
    app.include_router(api_router)
    app.include_router(capture_router)

    @app.get("/health")
    def say_hello():
        return {"message": "Ok"}

    return app


app = create_app()
