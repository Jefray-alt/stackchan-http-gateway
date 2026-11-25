# Receive streamed CoreS3 audio

## Outcome

Point `france-stackchan-cfw` at this gateway and prove that an idle tap sends
playable microphone audio over the LAN. Use a WAV file as the first slice's
verification artifact.

## Scope and decisions

OpenAI transcription is deferred to the second slice. It will use the same
completed audio input and return the transcript to the firmware. Legacy
fixed-length uploads are outside the first slice.

### Firmware contract

The [firmware upload code](https://github.com/Jefray-alt/france-stackchan-cfw/blob/main/src/TranscriptionUpload.cpp)
sends an HTTP/1.1 chunked `POST /v1/transcriptions` with
`Content-Type: application/octet-stream`. The payload is signed 16-bit
little-endian PCM at 16 kHz, mono. The device sends 640 PCM bytes per frame.
Read the decoded body incrementally through FastAPI. ASGI body segments can
split or combine device frames, so validate the total byte count and preserve
the bytes in order.

The firmware ends a valid recording with the final HTTP chunk. If a quiet tap
or capture failure causes it to close before that chunk, discard the upload.
Preserve the [current test backend's limits](https://github.com/Jefray-alt/france-stackchan-cfw/blob/main/backend/README.md)
for chunked uploads: at least 3,840 bytes, an even total, at most 1,920,000
bytes (60 seconds), a five-second body idle limit, and a 65-second total body
deadline. Reject oversized uploads as soon as they cross the limit.

After a successful save, return HTTP 200 with `text/plain; charset=utf-8` and
an explicit byte `Content-Length`. Use `Audio saved (test only)` as the body
so the firmware's `Transcript:` log can confirm it received the acknowledgment.
The server log should associate that request with its WAV filename, PCM byte
count, and duration.

## Tasks and commit chunks

### T1. Capture streamed CoreS3 audio as WAV

- Outcome — Receive a recording from the CoreS3 and save it as a playable WAV.
- Acceptance — A complete upload produces one WAV and a firmware-compatible
  acknowledgment. Failed or canceled uploads leave no capture.

#### T1.1. Receive and validate streamed PCM

- Outcome — Add an internal receiver that accumulates the decoded audio in a
  bounded buffer and applies the firmware contract's byte and deadline limits.
- Depends on — None.
- Acceptance and checks — Exercise normal completion across arbitrary segment
  boundaries, early disconnect, invalid size, and idle and total deadlines.
  Return PCM to the caller only after a complete, valid upload.
- Proposed commit — `feat: validate streamed cores3 pcm`
- Status — Planned.

#### T1.2. Save completed PCM as WAV

- Outcome — Add a writer that takes validated PCM and an explicit capture
  directory. Write to a unique temporary file and publish the final `.wav`
  after a successful write.
- Depends on — None. The writer can be verified with a PCM fixture.
- Acceptance and checks — Reopen the WAV and verify its format and audio
  bytes. Verify that a write failure leaves neither a published recording
  nor a temporary file.
- Proposed commit — `feat: save completed cores3 audio as wav`
- Status — Planned.

#### T1.3. Wire the firmware endpoint to capture storage

- Outcome — Add `POST /v1/transcriptions`, connect the receiver and WAV writer,
  and return the device acknowledgment after the file is saved. Admit one
  request through finalization and return 503 if busy. Document how to enable
  capture outside Git and delete the recordings after verification.
- Depends on — T1.1 and T1.2.
- Acceptance and checks — Verify the response matches the firmware contract,
  unsupported media is rejected, and a failed or interrupted request leaves
  no capture and frees the upload slot. Run the HTTP checks below.
- Proposed commit — `feat: expose cores3 audio capture endpoint`
- Status — Planned.

## End-to-end verification

- Send known PCM to a running gateway over a real HTTP/1.1 chunked connection
  in multiple writes. Reopen the saved WAV and compare its PCM bytes with the
  fixture. Confirm the header reports one channel, two bytes per sample, and
  a sample rate of 16,000 Hz. Confirm that the acknowledgment and WAV appear
  only after the final HTTP chunk.
- Close a second connection without a final chunk. Verify that it leaves no
  WAV or temporary file. Check that empty, odd, undersized, and oversized
  bodies and stalled uploads leave no recording, and that a valid upload can
  follow a failed one.
- Bind the gateway to the server's trusted LAN IPv4 address for the device
  check. Point the firmware's `ROBOT_TRANSCRIPTION_BASE_URL` at
  `http://<server-lan-ip>:8000`. Tap while idle, say a known phrase, then pause
  until capture ends. Expect `Transcript: Audio saved (test only)` in Serial
  and one WAV on the server. Play it back and check that the full phrase is
  audible at normal speed. Repeat with a quiet tap and verify that no new
  WAV appears.

## Completion record

Implementation commits and verification results are pending.
