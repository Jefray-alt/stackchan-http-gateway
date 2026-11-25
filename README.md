# Stack Chan HTTP Gateway

A small FastAPI service that provides an HTTP entry point for Stack Chan. The
current API is a scaffold: it exposes a health response and a placeholder
transcription route.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

## Development

Install the project and its dependencies from the repository root:

```sh
uv sync
```

Start the development server:

```sh
uv run stackchan-http-gateway
```

The server listens on `http://127.0.0.1:8000` and reloads when source files
change. FastAPI's interactive API documentation is available at
`http://127.0.0.1:8000/docs`.

## API

| Method | Path | Current behavior |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"message":"Ok"}`. |
| `GET` | `/api/transcription/` | Returns a placeholder `{"message":"hello"}` response. |

The transcription route does not perform transcription yet.

## Project layout

- `src/stackchan_http_gateway/main.py`: creates the FastAPI app and mounts the
  API router.
- `src/stackchan_http_gateway/api/main.py`: mounts API feature routers under
  `/api`.
- `src/stackchan_http_gateway/api/transcription/`: transcription route module.
- `docs/`: development workflow and planning documentation.

## Codex workflow

The project rules are in [AGENTS.md](AGENTS.md), and the shared implementation
and review protocol is in [docs/agent-workflow.md](docs/agent-workflow.md).
Codex roles are configured in `.codex/agents/`. Reload Codex after changing
role configuration if the roles are not available.
