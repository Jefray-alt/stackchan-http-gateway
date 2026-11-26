import asyncio
from collections.abc import AsyncIterable


_MIN_PCM_BYTES = 3_840
_MAX_PCM_BYTES = 1_920_000
_BODY_IDLE_SECONDS = 5.0
_TOTAL_BODY_SECONDS = 65.0


class AudioReceiveError(Exception):
    """The PCM body cannot be accepted."""


class InvalidPcm(AudioReceiveError):
    """The completed body is too short or is not sample aligned."""


class PcmTooLarge(AudioReceiveError):
    """The body exceeded the maximum PCM byte count."""


class AudioReceiveTimeout(AudioReceiveError):
    """The body exceeded its idle limit or total deadline."""


async def receive_pcm(body: AsyncIterable[bytes]) -> bytes:
    """Return bounded PCM only after normal, valid body completion.

    Body read failures, including disconnects and cancellation, propagate to
    the caller without exposing accumulated PCM.
    """
    pcm = bytearray()
    loop = asyncio.get_running_loop()
    total_deadline = loop.time() + _TOTAL_BODY_SECONDS
    iterator = aiter(body)

    while True:
        read_started = loop.time()
        if read_started >= total_deadline:
            raise AudioReceiveTimeout("PCM upload exceeded the total body deadline")

        idle_deadline = read_started + _BODY_IDLE_SECONDS
        deadline = min(idle_deadline, total_deadline)
        reason = "total body deadline" if total_deadline <= idle_deadline else "body idle limit"
        timeout = asyncio.timeout_at(deadline)

        try:
            async with timeout:
                segment = await anext(iterator, None)
        except TimeoutError as error:
            if not timeout.expired():
                raise
            raise AudioReceiveTimeout(f"PCM upload exceeded the {reason}") from error

        # Buffered reads may not yield control for asyncio's timer to fire.
        if loop.time() >= deadline:
            raise AudioReceiveTimeout(f"PCM upload exceeded the {reason}")

        if segment is None:
            break

        if len(pcm) + len(segment) > _MAX_PCM_BYTES:
            raise PcmTooLarge("PCM upload exceeds 1,920,000 bytes")

        pcm.extend(segment)

    if len(pcm) < _MIN_PCM_BYTES or len(pcm) % 2:
        raise InvalidPcm("PCM upload must contain at least 3,840 bytes and complete samples")

    return bytes(pcm)
