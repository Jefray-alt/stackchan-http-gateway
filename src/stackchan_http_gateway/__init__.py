def main() -> None:
    """Run the StackChan HTTP Gateway development server."""
    import uvicorn

    uvicorn.run("stackchan_http_gateway.main:app", host="127.0.0.1", port=8000, reload=True)
