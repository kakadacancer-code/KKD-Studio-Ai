# KKD Studio AI — local build verification

The local checks used FFmpeg and cached NLLB-200 600M and MMS Khmer weights. Model inference was run with HF_HUB_OFFLINE=1.

| Test | Result |
| --- | --- |
| Backend Python `compileall` | Passed |
| FastAPI application import / registered routes | Passed |
| Offline API and media regression checks | Passed, including interruption in a simulated 24-chunk transcription and resume |
| Synthetic Chinese-source MP4 upload, editing, SRT generation | Passed |
| Resumable multi-chunk import | Passed |
| Real MP4 export with absolute-position **synthetic test** voice | Passed |
| Confirm original audio track is absent in rendered export | Passed |
| Khmer Unicode validation, checkpoint behavior and cancellation | Passed |
| TypeScript source transpilation syntax | Passed (13 source files) |
| Frontend production build | Passed with the installed npm dependencies |
| Two-hour MP4 with three imported Chinese cues | Passed using real 600M translation, MMS voices and FFmpeg. Verified audible signal at the beginning, middle and end of the 7,200-second export |
| Full inference through real Whisper + NLLB + MMS model weights | **Not verified:** weights are not bundled; first-time model downloads and runtime resources required |
| Three-hour real movie throughput / hardware benchmark | **Not verified:** duration guard and chunking implemented but not stress-tested |

Do not treat mocked-test dialogue or synthetic WAVs as proof of actual transcription, Khmer translation quality, or natural-sounding TTS.
