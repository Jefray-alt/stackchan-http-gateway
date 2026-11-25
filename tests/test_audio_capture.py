import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from stackchan_http_gateway.audio_capture import save_pcm_wav


PCM = b"\x01\x00\xff\x7f\x00\x80" * 640


class AudioCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / "captures"

    def test_creates_directory_and_saves_exact_pcm_with_expected_format(self):
        path = save_pcm_wav(PCM, self.directory)

        self.assertEqual(path.parent, self.directory)
        self.assertEqual(path.suffix, ".wav")
        self.assertEqual(list(self.directory.iterdir()), [path])
        with wave.open(str(path), "rb") as recording:
            self.assertEqual(recording.getnchannels(), 1)
            self.assertEqual(recording.getsampwidth(), 2)
            self.assertEqual(recording.getframerate(), 16_000)
            self.assertEqual(recording.getnframes(), len(PCM) // 2)
            self.assertEqual(recording.readframes(recording.getnframes()), PCM)

    def test_multiple_captures_have_unique_paths_and_preserve_previous_audio(self):
        first = save_pcm_wav(PCM, self.directory)
        original = first.read_bytes()
        second = save_pcm_wav(PCM[::-1], self.directory)

        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), original)
        self.assertEqual(set(self.directory.iterdir()), {first, second})

    def test_write_failure_removes_temporary_file(self):
        with patch.object(wave.Wave_write, "writeframes", side_effect=OSError("write failed")):
            with self.assertRaisesRegex(OSError, "write failed"):
                save_pcm_wav(PCM, self.directory)

        self.assertEqual(list(self.directory.iterdir()), [])

    def test_wave_close_failure_removes_temporary_file(self):
        original_close = wave.Wave_write.close

        def fail_close(recording):
            was_open = recording._file is not None
            original_close(recording)
            if was_open:
                raise OSError("close failed")

        with patch.object(wave.Wave_write, "close", fail_close):
            with self.assertRaisesRegex(OSError, "close failed"):
                save_pcm_wav(PCM, self.directory)

        self.assertEqual(list(self.directory.iterdir()), [])

    def test_publication_happens_after_successful_close(self):
        import os

        original_link = os.link

        def publish(source, destination):
            self.assertEqual(list(self.directory.glob("*.wav")), [])
            with wave.open(str(source), "rb") as recording:
                self.assertEqual(recording.readframes(len(PCM) // 2), PCM)
            original_link(source, destination)

        with patch("stackchan_http_gateway.audio_capture.os.link", side_effect=publish):
            save_pcm_wav(PCM, self.directory)

    def test_publication_failure_removes_temporary_file(self):
        with patch("stackchan_http_gateway.audio_capture.os.link", side_effect=OSError("link failed")):
            with self.assertRaisesRegex(OSError, "link failed"):
                save_pcm_wav(PCM, self.directory)

        self.assertEqual(list(self.directory.iterdir()), [])

    def test_existing_destination_is_never_overwritten(self):
        self.directory.mkdir()
        existing = self.directory / "existing.wav"
        existing.write_bytes(b"previous recording")

        with patch("stackchan_http_gateway.audio_capture.Path.with_suffix", return_value=existing):
            with self.assertRaises(FileExistsError):
                save_pcm_wav(PCM, self.directory)

        self.assertEqual(existing.read_bytes(), b"previous recording")
        self.assertEqual(list(self.directory.iterdir()), [existing])
