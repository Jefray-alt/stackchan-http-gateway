import os
import tempfile
import wave
from pathlib import Path


def save_pcm_wav(pcm: bytes, capture_directory: Path) -> Path:
    """Save validated mono, 16-bit, 16 kHz PCM and return its WAV path.

    Create the capture directory if needed. Publish only after both the WAV
    writer and underlying file close successfully. A hard link publishes the
    completed file atomically without replacing an existing recording.
    """
    capture_directory.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        mode="wb", prefix="capture-", suffix=".tmp", dir=capture_directory, delete=False
    )
    temporary_path = Path(temporary.name)
    final_path = temporary_path.with_suffix(".wav")
    published = False

    try:
        with temporary as output:
            with wave.open(output, "wb") as recording:
                recording.setnchannels(1)
                recording.setsampwidth(2)
                recording.setframerate(16_000)
                recording.writeframes(pcm)

        os.link(temporary_path, final_path)
        published = True
        temporary_path.unlink()
        return final_path
    except BaseException:
        if published:
            final_path.unlink(missing_ok=True)
        raise
    finally:
        temporary_path.unlink(missing_ok=True)
