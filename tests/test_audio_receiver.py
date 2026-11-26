import asyncio
import unittest
from unittest.mock import patch

from starlette.requests import ClientDisconnect

from stackchan_http_gateway.audio.receiver import (
    AudioReceiveTimeout,
    InvalidPcm,
    PcmTooLarge,
    receive_pcm,
)


MIN_PCM = b"\x01\x00" * 1_920
MAX_PCM_BYTES = 1_920_000


async def segments(*parts):
    for part in parts:
        yield part


class AudioReceiverTests(unittest.IsolatedAsyncioTestCase):
    async def test_preserves_pcm_across_split_and_combined_frames(self):
        result = await receive_pcm(
            segments(MIN_PCM[:1], MIN_PCM[1:641], MIN_PCM[641:2_000], MIN_PCM[2_000:])
        )

        self.assertIsInstance(result, bytes)
        self.assertEqual(result, MIN_PCM)

    async def test_waits_for_normal_body_completion(self):
        waiting = asyncio.Event()
        complete = asyncio.Event()

        async def body():
            yield MIN_PCM
            waiting.set()
            await complete.wait()

        task = asyncio.create_task(receive_pcm(body()))
        await waiting.wait()
        self.assertFalse(task.done())

        complete.set()
        self.assertEqual(await task, MIN_PCM)

    async def test_accepts_exact_size_limits(self):
        for size in (len(MIN_PCM), MAX_PCM_BYTES):
            with self.subTest(size=size):
                pcm = b"\x00" * size
                self.assertEqual(await receive_pcm(segments(pcm)), pcm)

    async def test_rejects_empty_short_and_odd_completed_bodies(self):
        for size in (0, 1, 3_838, 3_839, 3_841):
            with self.subTest(size=size):
                with self.assertRaises(InvalidPcm):
                    await receive_pcm(segments(b"\x00" * size))

    async def test_accepts_empty_segments_without_changing_pcm(self):
        self.assertEqual(await receive_pcm(segments(b"", MIN_PCM, b"")), MIN_PCM)

    async def test_rejects_oversize_without_reading_the_rest_of_the_body(self):
        read_after_limit = False

        async def body():
            nonlocal read_after_limit
            yield b"\x00" * MAX_PCM_BYTES
            yield b"\x00"
            read_after_limit = True
            yield b"unread"

        with self.assertRaises(PcmTooLarge):
            await receive_pcm(body())

        self.assertFalse(read_after_limit)

    async def test_rejects_an_oversized_first_segment(self):
        with self.assertRaises(PcmTooLarge):
            await receive_pcm(segments(b"\x00" * (MAX_PCM_BYTES + 1)))

    async def test_disconnect_does_not_return_partial_pcm(self):
        async def body():
            yield MIN_PCM
            raise ClientDisconnect()

        with self.assertRaises(ClientDisconnect):
            await receive_pcm(body())

    async def test_source_failures_propagate_without_partial_pcm(self):
        for error in (OSError("body read failed"), TimeoutError("source failed")):
            with self.subTest(error=error):
                async def body():
                    yield MIN_PCM
                    raise error

                with self.assertRaises(type(error)) as caught:
                    await receive_pcm(body())

                self.assertIs(caught.exception, error)

    async def test_cancellation_reaches_the_pending_body_read(self):
        waiting = asyncio.Event()
        cancelled = asyncio.Event()

        async def body():
            yield MIN_PCM
            waiting.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        task = asyncio.create_task(receive_pcm(body()))
        await waiting.wait()
        task.cancel()

        with self.assertRaises(asyncio.CancelledError):
            await task

        self.assertTrue(cancelled.is_set())

    async def test_idle_timeout_cancels_a_stalled_body_read(self):
        cancelled = asyncio.Event()

        async def body():
            yield MIN_PCM
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        with patch("stackchan_http_gateway.audio.receiver._BODY_IDLE_SECONDS", 0.01):
            with self.assertRaisesRegex(AudioReceiveTimeout, "idle"):
                await receive_pcm(body())

        self.assertTrue(cancelled.is_set())

    async def test_total_timeout_cancels_a_stalled_body_read(self):
        async def body():
            yield MIN_PCM
            await asyncio.Event().wait()

        with patch("stackchan_http_gateway.audio.receiver._TOTAL_BODY_SECONDS", 0.01):
            with self.assertRaisesRegex(AudioReceiveTimeout, "total"):
                await receive_pcm(body())

    async def test_idle_deadline_resets_after_each_segment(self):
        clock = [0.0]

        async def body():
            for part in (MIN_PCM[:1], MIN_PCM[1:], b""):
                clock[0] += 4.0
                yield part
            clock[0] += 4.0

        loop = asyncio.get_running_loop()
        with patch.object(loop, "time", side_effect=lambda: clock[0]):
            self.assertEqual(await receive_pcm(body()), MIN_PCM)

    async def test_total_deadline_includes_immediately_available_segments(self):
        clock = [0.0]

        async def body():
            for _ in range(17):
                clock[0] += 4.0
                yield MIN_PCM

        loop = asyncio.get_running_loop()
        with patch.object(loop, "time", side_effect=lambda: clock[0]):
            with self.assertRaisesRegex(AudioReceiveTimeout, "total"):
                await receive_pcm(body())

    async def test_deadline_applies_to_normal_body_completion(self):
        clock = [0.0]

        async def body():
            yield MIN_PCM
            clock[0] += 5.0

        loop = asyncio.get_running_loop()
        with patch.object(loop, "time", side_effect=lambda: clock[0]):
            with self.assertRaisesRegex(AudioReceiveTimeout, "idle"):
                await receive_pcm(body())


if __name__ == "__main__":
    unittest.main()
