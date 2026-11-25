import asyncio
import os
import socket
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import uvicorn

from stackchan_http_gateway.main import create_app


PCM = b"\x01\x00\xff\x7f\x00\x80" * 640


class ChunkedHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / "captures"
        self.enterContext(patch.dict(os.environ, STACKCHAN_CAPTURE_DIR=str(self.directory)))
        self.enterContext(patch("stackchan_http_gateway.audio_receiver._BODY_IDLE_SECONDS", 0.3))
        self.app = create_app()
        self.socket = socket.socket()
        self.socket.bind(("127.0.0.1", 0))
        self.socket.listen()
        self.addCleanup(self.socket.close)
        self.server = uvicorn.Server(uvicorn.Config(
            self.app, log_level="critical", access_log=False, lifespan="off"
        ))
        self.task = asyncio.create_task(self.server.serve(sockets=[self.socket]))
        self.addAsyncCleanup(self.stop_server)
        async with asyncio.timeout(2):
            while not self.server.started:
                await asyncio.sleep(0.01)

    async def stop_server(self):
        self.server.should_exit = True
        await asyncio.wait_for(self.task, 2)

    async def begin(self):
        reader, writer = await asyncio.open_connection(*self.socket.getsockname())
        self.addAsyncCleanup(writer.wait_closed)
        self.addCleanup(writer.close)
        writer.write(b"POST /v1/transcriptions HTTP/1.1\r\nHost: localhost\r\n"
                     b"Content-Type: application/octet-stream\r\n"
                     b"Transfer-Encoding: chunked\r\nConnection: close\r\n\r\n")
        await writer.drain()
        return reader, writer

    async def chunk(self, writer, content):
        wire = f"{len(content):x}\r\n".encode() + content + b"\r\n"
        # Split both framing and PCM across socket writes independently of frames.
        for start, stop in ((0, 1), (1, 7), (7, len(wire))):
            writer.write(wire[start:stop])
            await writer.drain()

    async def response(self, reader):
        data = await asyncio.wait_for(reader.read(), 2)
        headers, separator, body = data.partition(b"\r\n\r\n")
        self.assertTrue(separator, data)
        status = int(headers.split(b" ", 2)[1])
        return status, headers.lower(), body

    async def complete(self, content):
        reader, writer = await self.begin()
        if content:
            await self.chunk(writer, content)
        writer.write(b"0\r\n\r\n")
        await writer.drain()
        return await self.response(reader)

    def assert_no_capture(self):
        self.assertEqual(list(self.directory.glob("*")), [])

    async def test_final_chunk_controls_acknowledgment_and_exact_wav(self):
        reader, writer = await self.begin()
        for part in (PCM[:1], PCM[1:641], PCM[641:2_000], PCM[2_000:]):
            await self.chunk(writer, part)

        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(reader.read(1), 0.05)
        self.assert_no_capture()
        writer.write(b"0\r\n\r\n")
        await writer.drain()
        status, headers, body = await self.response(reader)

        self.assertEqual(status, 200)
        self.assertEqual(body, b"Audio saved (test only)")
        self.assertIn(b"content-type: text/plain; charset=utf-8", headers)
        self.assertIn(b"content-length: 23", headers)
        path, = self.directory.iterdir()
        with wave.open(str(path), "rb") as recording:
            self.assertEqual((recording.getnchannels(), recording.getsampwidth(), recording.getframerate()),
                             (1, 2, 16_000))
            self.assertEqual(recording.readframes(recording.getnframes()), PCM)

    async def test_missing_final_chunk_discards_capture_and_next_upload_works(self):
        reader, writer = await self.begin()
        await self.chunk(writer, PCM)
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(reader.read(1), 0.05)
        writer.close()
        await writer.wait_closed()
        async with asyncio.timeout(1):
            while self.app.state.capture_busy:
                await asyncio.sleep(0.01)
        self.assert_no_capture()
        self.assertEqual((await self.complete(PCM))[0], 200)

    async def test_invalid_oversized_and_stalled_uploads_leave_no_files(self):
        for size in (0, 3_838, 3_841):
            with self.subTest(size=size):
                self.assertEqual((await self.complete(b"\x00" * size))[0], 400)
                self.assert_no_capture()

        reader, writer = await self.begin()
        await self.chunk(writer, b"\x00" * 1_920_001)
        self.assertEqual((await self.response(reader))[0], 413)  # No final chunk.
        self.assert_no_capture()

        reader, writer = await self.begin()
        await self.chunk(writer, PCM)
        self.assertEqual((await self.response(reader))[0], 408)
        self.assert_no_capture()
        self.assertEqual((await self.complete(PCM))[0], 200)


if __name__ == "__main__":
    unittest.main()
