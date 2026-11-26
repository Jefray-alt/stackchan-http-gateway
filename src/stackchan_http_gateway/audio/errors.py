class AudioReceiveError(Exception):
    """The PCM body cannot be accepted."""


class InvalidPcmError(AudioReceiveError):
    """The completed body is too short or is not sample aligned."""


class PcmTooLargeError(AudioReceiveError):
    """The body exceeded the maximum PCM byte count."""


class AudioReceiveTimeoutError(AudioReceiveError):
    """The body exceeded its idle limit or total deadline."""
