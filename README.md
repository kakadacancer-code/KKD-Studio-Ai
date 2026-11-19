# KKD Studio AI

**Offline Chinese → Khmer movie translation and AI dubbing**  
A local-first React + FastAPI application for Ubuntu. Import a film, transcribe Mandarin, translate into editable Khmer subtitles, synthesize Khmer dialogue and export an MP4 with voices aligned to their original dialogue timestamps.

> A two-hour test MP4 with imported Chinese subtitles was translated, voiced and exported offline using the 600M translator and Khmer MMS. This check used three lines spaced across the timeline. Throughput and translation accuracy on dialogue-heavy films depend on the material and hardware.

## Features in this build

- **Modern dark UI:** dashboard, saved projects, chunked video importer, translation editor, voice studio, export center, model manager, diagnostics.
- **Upload:** MP4/MOV/MKV/AVI/WEBM; resumable 8 MB upload chunks; 10 GB maximum. Local 3-hour duration validation. Public direct media URLs accepted without cookies/DRM/redirects.
- **Chinese transcription:** Faster-Whisper on CPU, choosing tiny/base/small/medium; 5-minute processing chunks with persisted completion checkpoints and timestamps. Results editable.
- **Translation:** Local NLLB-200 600M or 1.3B translates Chinese into Khmer. Common standalone greetings use fixed Khmer equivalents. Speaker turns within a subtitle are handled separately. Empty, mixed-script output and incomplete translations are flagged for review.
- **Voice generation:** local Meta MMS-TTS Khmer; individual saved WAVs; per-segment voice speed; duration overrun detection; preview, regenerate and resume incomplete segments.
- **Critical alignment rule:** PCM audio timeline begins each voice at its saved `start` timestamp (sample-accurate to 1/22,050 second); additional clips *do not slide later in time*. Overlong speech is flagged rather than silently cut.
- **Export:** FFmpeg renders H.264/AAC MP4 with only the newly assembled Khmer voice track, no original film audio. Fast/balanced/high quality, original/480p/720p/1080p. Preview and download from browser; separate Khmer or Chinese SRT export.
- **Persistence:** SQLite + per-project media folders, one worker at a time to reduce laptop resource contention, real progress records, job cancellation between tasks/while FFmpeg is encoding, interrupted-job detection and resumable completed chunks/segments.
- **Diagnostics and errors:** FFmpeg availability, RAM, CPU, model availability; no invented translations, generated audio or export success.

## 1. Requirements (Ubuntu 24.04)

Use a computer with **8 GB RAM minimum** (16 GB strongly recommended for NLLB + other AI models), several GB of free disk space, and internet access for the **initial model downloads only**. A CPU-only laptop is supported but can be slow for long films.

```bash
sudo apt update
sudo apt install -y ffmpeg python3 python3-venv python3-pip build-essential
node --version    # requires Node 20+
npm --version
ffmpeg -version
```

If Node is missing or too old, install a supported version using `nvm` and select Node 22 LTS. Some AI libraries may not yet support the newest Python version; Python 3.11 or 3.12 is recommended.

## 2. Install dependencies

Extract the ZIP and open a terminal in the root folder:

```bash
cd kkd-studio-ai
chmod +x scripts/setup-ubuntu.sh start.sh
./scripts/setup-ubuntu.sh
```

The setup script creates `backend/.venv`, installs **CPU PyTorch**, the FastAPI + local AI dependencies, and `frontend/node_modules`. It downloads *software packages*, but not the Hugging Face model checkpoints (those are selected inside the app).

**Manual setup** (if the installer fails):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-ai.txt
cd ../frontend
npm install
cd ..
```

If you want to test the UI and API **without heavy AI packages**, install `backend/requirements.txt` instead. Transcription/translation/TTS buttons will fail with *real explanatory errors* until AI dependencies and weights are available; the rest of the application remains usable.

## 3. Start the app

```bash
./start.sh
```

Open:

| Service | URL |
| --- | --- |
| **KKD Studio AI** | **http://localhost:5173** |
| FastAPI | http://localhost:8000 |
| Interactive API docs | http://localhost:8000/docs |

Or run separately in **two terminals**:

```bash
# Terminal 1, from project root:
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
# Terminal 2, from project root:
cd frontend
npm run dev
```

Everything runs locally on 127.0.0.1; **no Gemini, Google Cloud, OpenAI or other paid API key** is used. Google Fonts loaded by the browser are only optional UI fonts; the inference pipeline never sends video or text to Google. For a strictly disconnected machine, replace the font import with local/system fonts and pre-download the model checkpoints.

## 4. Dub a movie in Khmer

In **Translation Studio**, choose a translation model and select **Dub movie in Khmer**. The job transcribes a new movie in five-minute chunks, translates each cue and synthesizes its Khmer voice. If you have a Chinese SRT for the movie, import it first to use its dialogue and timestamps. A two-hour film has 24 transcription chunks. The existing import limits are three hours and 10 GB.

Select the same button after an interruption to resume. Completed chunks (including silence), subtitles and voice clips are saved locally. The job fits speech to each subtitle window up to 1.35× speed and flags overruns. Review flagged lines, then open **Export Center** to save the dubbed MP4. MMS uses one Khmer speaker throughout.

The default 600M model uses less memory. The optional 1.3B checkpoint is a separate download in **Model Manager**. Use **Retry selected** to compare a line, or **Retranslate all** to replace a project's existing Khmer text. Retranslation can replace manual edits. Editing Chinese dialogue marks its existing translation for review and invalidates its voice.

### Run each step separately

1. Open **Model Manager**, and download **Whisper Base**, **NLLB-200 600M** and **MMS Khmer TTS** (one at a time). Model files are cached inside `storage/models/`. If not explicitly downloaded, the first AI run may fetch a model automatically.
2. Select **Import Video** → upload a short, permitted Chinese MP4. Long imports use resumable 8 MB chunks.
3. In **Translation Studio**, select **Extract Chinese Speech**. Faster-Whisper extracts timestamped Chinese segments. You can also import a Chinese `.srt` file instead.
4. Select **Translate missing** to run NLLB locally. Manually review Chinese lines and natural Khmer wording, edit and **Save Changes** where needed.
5. Open **AI Voice Studio** → **Generate All Voices**. MMS synthesizes Khmer WAV clips. The system reports timings that are too long; adjust the translation or speaking speed and regenerate them.
6. Open **Export Center**. Once every clip is valid, select resolution and quality → **Export Khmer Movie**. A newly encoded MP4 appears for playback and download.
7. **Close and restart the studio** at any time. All completed subtitles and generated WAV files persist. Starting the same job again skips work already saved.

Example: if Chinese dialogue starts at **00:00:05.000**, its Khmer voice is inserted at **00:00:05.000**, even if other subtitle timings are changed. Long voices are *not cut or moved silently*.

## 5. Resuming large operations

- **Video uploads:** if a browser upload fails, choose the **same file** again in the importer; the saved project ID and already uploaded chunks are found from browser storage and SQLite. If you clear your browser data, the upload ID cannot be auto-discovered by the UI.
- **Transcription:** successful 5-minute chunks are committed. Re-running transcription skips any completed chunks; the partially processed chunk may repeat.
- **Translation:** only subtitles missing successful Khmer text are processed by default.
- **Voices:** existing WAVs are skipped. Selected clips can be regenerated explicitly.
- **Jobs:** if the server closes abruptly, `running`/`queued` rows become `interrupted`. Relaunch the relevant step to resume.
- **Export:** exports are processed as separate jobs; a failed export can be started again. Existing voice clips and source files are not deleted.

SQLite file: `storage/studio.db`  
Media: `storage/projects/<project-id>/`  
Models: `storage/models/`

## 6. Automated tests

```bash
source backend/.venv/bin/activate
pip install pytest
PYTHONPATH=backend pytest -q tests
```

The tests exercise input validation, chunked upload and resume, subtitle editing, Khmer validation, saved translation checkpoints with a clearly marked **mock model**, PCM timestamp alignment, source soundtrack removal and an actual FFmpeg MP4 render using **synthetic test WAVs**. They **do not establish** the quality of Whisper, NLLB or MMS output; use a short permitted Chinese-language sample for a final manual acceptance test on your hardware.

## 7. Troubleshooting

| Issue | Fix |
| --- | --- |
| `ffmpeg` or `ffprobe` missing | `sudo apt install ffmpeg` then restart backend. |
| `ModuleNotFoundError: transformers` / `faster_whisper` | Activate `.venv`; install `backend/requirements-ai.txt`. |
| Model download fails | Check internet/storage. Retry from Model Manager. Model files are large. |
| Very slow CPU / RAM errors | Use Whisper Tiny or Base; process a short clip first. Close memory-heavy applications. |
| Khmer translation empty, Chinese-only or strange | Failed segment is flagged. Retry selected or correct it manually. NLLB is not infallible. |
| Voice is longer than subtitle | Shorten Khmer sentence, increase segment speed up to 1.35×, or adjust timing manually, then regenerate. |
| No voice / export blocked | Translate missing lines and regenerate all required WAVs; read warnings. |
| `Address already in use` port 8000 | Stop the previous backend process or change port and Vite proxy together. |
| MKV playback unsupported in browser | Use an H.264 MP4 source for preview; MKV can still be ingested by FFmpeg. Final export is MP4. |
| Slow or failed 3-hour export | Ensure sufficient disk space (temporary PCM files + output), CPU time, and permissions; test shorter clips before large renders. |

## 8. Licensing and rights

- NLLB-200 distilled 600M: **CC-BY-NC-4.0**, research-oriented and **not intended for production deployment** by its model card.
- MMS-TTS Khmer: **CC-BY-NC-4.0**.
- These model licenses impose **noncommercial restrictions**. Do not assume this particular baseline is eligible for a monetized YouTube channel or commercial service.
- Only import and publish movies you have the rights/permission to use. Local operation does not grant rights in third-party films.
- Model sources: [NLLB-200 600M](https://huggingface.co/facebook/nllb-200-distilled-600M), [MMS Khmer](https://huggingface.co/facebook/mms-tts-khm), [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## 9. Honest scope / limitations

This is a **working initial implementation**, not all items in the supplied 1,355-line specification. The following still need development:

- Advanced multi-track video editing, waveform dragging, splitting/undo/redo and original-dialogue-safe background sound separation (Demucs not wired up).
- Multi-speaker cloning, expressive emotions, pitch controls and VoxPocket advanced voices (MMS offers one standard Khmer voice).
- Burned-in subtitles, MKV final output, 3-hour full stress-tested rendering, model removal/download percentages, advanced GPU optimization, true offline-bundled UI fonts.
- Automatic import of DRM-protected platform pages, playlists, paywalled sources or videos requiring site logins. These are intentionally not bypassed.
- An unattended, production-grade distributed job queue. Current jobs run in one local thread; progress is polled from SQLite. Interruption recovery works at *chunk* or *completed segment* boundaries, not mid-inference.
- Model weights are **not bundled** in this ZIP, and the exact ASR/translation/TTS full pipeline has **not been benchmarked** against real Chinese films here.

A 3-hour duration ceiling and upload size limit are enforced in code, and long audio is chunked, but a real 3-hour movie should only be attempted after confirming a short end-to-end test succeeds on the intended Ubuntu hardware.

## Structure

```text
kkd-studio-ai/
├── frontend/                 React + Vite + TypeScript + Tailwind UI
│   └── src/
│       ├── components/      Application shell, status UI
│       ├── lib/             Axios client, Zustand preferences
│       └── pages/           Dashboard, Projects, Import, Studio, Voices, Export, Models, Settings
├── backend/
│   ├── app/
│   │   ├── main.py          FastAPI endpoints
│   │   ├── database.py      SQLite + SQLAlchemy models
│   │   ├── workers/jobs.py  Single worker + recovery checkpoints
│   │   └── services/       Speech, translation, TTS, alignment, FFmpeg
│   ├── requirements.txt
│   └── requirements-ai.txt
├── tests/test_core.py       Validated API / media integration tests
├── scripts/setup-ubuntu.sh  CPU-first local installer
├── start.sh                 Starts both servers
├── storage/                 Runtime data (generated)
└── SPECIFICATION.md         Original detailed project prompt
```
