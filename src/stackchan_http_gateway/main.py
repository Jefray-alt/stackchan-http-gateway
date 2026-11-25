from fastapi import FastAPI
from stackchan_http_gateway.api.main import router as api_router

app = FastAPI()

app.include_router(api_router)

@app.get("/health")
def say_hello():
    return {"message": "Ok"}