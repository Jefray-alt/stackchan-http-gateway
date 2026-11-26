# Stack Chan HTTP Gateway

A small FastAPI service that receives streamed CoreS3 microphone audio and
saves it as WAV for verification. Transcription is deferred; the firmware
receives a test acknowledgment after the recording is saved.

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
| `POST` | `/v1/transcriptions` | Saves completed PCM as WAV when capture is enabled. |

The capture endpoint supports the firmware's HTTP/1.1 chunked upload with
`Content-Type: application/octet-stream`: signed 16-bit little-endian PCM,
16,000 Hz, mono. It accepts 3,840–1,920,000 bytes in complete two-byte samples,
with a five-second body idle limit and a 65-second total body deadline.
It saves only after normal body completion, then returns HTTP 200,
`text/plain; charset=utf-8`, an explicit byte `Content-Length`, and exactly
`Audio saved (test only)`.

Invalid lengths return 400, oversized uploads 413, expired body deadlines 408,
and unsupported media 415. Disabled or busy capture returns 503; storage
failures return 500. Incomplete uploads are discarded, and failed uploads
leave no WAV or temporary file. One upload is admitted per process through
synchronous file finalization; another upload receives 503 while it is busy.

## Capture on the LAN

Capture is disabled unless `STACKCHAN_CAPTURE_DIR` is set at startup. Use an
absolute directory outside this repository; the server creates it as needed.
Replace `192.168.1.10` with the server's trusted LAN IPv4 address and run one
process:

```sh
STACKCHAN_CAPTURE_DIR="$HOME/stackchan-captures" \
  uv run uvicorn stackchan_http_gateway.main:app --host 192.168.1.10 --port 8000 --workers 1
```

Point the firmware's `ROBOT_TRANSCRIPTION_BASE_URL` at
`http://192.168.1.10:8000`. Tap while idle, say a known phrase, and pause until
capture ends. Expect `Transcript: Audio saved (test only)` in Serial. The
server logs the request, WAV filename, PCM byte count, and duration without
logging the audio. Play the WAV and verify the full phrase at normal speed;
repeat with a quiet tap and check that no new recording appears. Delete the
WAV recordings from the capture directory after verification.

Automated checks use a known PCM fixture over real HTTP/1.1 chunked sockets:

```sh
uv run python -m unittest discover -s tests -v
```

These checks cover HTTP completion and WAV content. CoreS3 microphone capture
and audible phrase playback still require the device check above.

## Project layout

- `src/stackchan_http_gateway/main.py`: configures capture and mounts the API
  routers.
- `src/stackchan_http_gateway/api/main.py`: mounts API feature routers under
  `/api`.
- `src/stackchan_http_gateway/api/transcription/`: transcription route module.
- `src/stackchan_http_gateway/api/transcriptions.py`: firmware capture endpoint.
- `docs/`: development workflow and planning documentation.

## Codex workflow

The project rules are in [AGENTS.md](AGENTS.md), and the shared implementation
and review protocol is in [docs/agent-workflow.md](docs/agent-workflow.md).
Codex roles are configured in `.codex/agents/`. Reload Codex after changing
role configuration if the roles are not available.
