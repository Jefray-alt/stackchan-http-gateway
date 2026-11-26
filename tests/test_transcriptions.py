import asyncio
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import httpx
from starlette.requests import ClientDisconnect

from stackchan_http_gateway.main import create_app


PCM = b"\x01\x00\xff\x7f\x00\x80" * 640
ENDPOINT = "/v1/transcriptions"
MEDIA = {"Content-Type": "application/octet-stream"}


class TranscriptionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / "captures"
        self.enterContext(patch.dict(os.environ, STACKCHAN_CAPTURE_DIR=str(self.directory)))
        self.app = create_app()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test"
        )
        self.addAsyncCleanup(self.client.aclose)

    async def upload(self, content=PCM):
        return await self.client.post(ENDPOINT, headers=MEDIA, content=content)

    def assert_no_capture(self):
        self.assertEqual(list(self.directory.glob("*")), [])

    async def test_acknowledges_saved_audio_and_logs_request_metadata(self):
        with self.assertLogs("uvicorn.error.capture", level="INFO") as logs:
            response = await self.upload()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Audio saved (test only)")
        self.assertEqual(response.headers["content-type"], "text/plain; charset=utf-8")
        self.assertEqual(response.headers["content-length"], str(len(response.content)))
        path, = self.directory.iterdir()
        self.assertIn(path.name, logs.output[0])
        for value in ("POST /v1/transcriptions", "pcm_bytes=3840", "duration_seconds=0.120"):
            self.assertIn(value, logs.output[0])

    async def test_requires_octet_stream(self):
        for media in (None, "text/plain", "application/json"):
            headers = {"Content-Type": media} if media else {}
            response = await self.client.post(ENDPOINT, headers=headers, content=PCM)
            self.assertEqual(response.status_code, 415)
        self.assert_no_capture()

    async def test_capture_is_disabled_without_configuration(self):
        with patch.dict(os.environ, STACKCHAN_CAPTURE_DIR=""):
            app = create_app()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            response = await client.post(ENDPOINT, headers=MEDIA, content=PCM)
        self.assertEqual(response.status_code, 503)
        self.assert_no_capture()

    async def test_invalid_length_releases_slot(self):
        for size in (0, 3_838, 3_841):
            response = await self.upload(b"\x00" * size)
            self.assertEqual(response.status_code, 400)
            self.assert_no_capture()
        self.assertEqual((await self.upload()).status_code, 200)

    async def test_busy_and_cancellation_release_slot_without_saving(self):
        waiting = asyncio.Event()

        async def body():
            yield PCM
            waiting.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(self.upload(body()))
        await asyncio.wait_for(waiting.wait(), 1)
        self.assertEqual((await self.upload()).status_code, 503)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assert_no_capture()
        self.assertEqual((await self.upload()).status_code, 200)

    async def test_disconnect_releases_slot_without_saving(self):
        async def body():
            yield PCM
            raise ClientDisconnect()

        self.assertEqual((await self.upload(body())).status_code, 400)
        self.assert_no_capture()
        self.assertEqual((await self.upload()).status_code, 200)

    async def test_write_failure_cleans_files_and_releases_slot(self):
        with patch.object(wave.Wave_write, "writeframes", side_effect=OSError("disk failed")):
            with self.assertLogs("uvicorn.error.capture", level="ERROR"):
                response = await self.upload()
        self.assertEqual(response.status_code, 500)
        self.assert_no_capture()
        self.assertEqual((await self.upload()).status_code, 200)


if __name__ == "__main__":
    unittest.main()
