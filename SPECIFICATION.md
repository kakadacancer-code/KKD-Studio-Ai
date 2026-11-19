# PROJECT: KKD STUDIO AI
## Professional Chinese-to-Khmer Movie Translation & AI Dubbing Platform

Act as a senior full-stack software engineer, AI engineer, UI/UX designer, and video processing specialist.

Build a complete, production-quality local web application named **KKD Studio AI**.

The application must translate Chinese movies into natural Khmer and generate Khmer AI voice dubbing with accurate timing.

The entire application must work without Gemini, OpenAI, Google Cloud, or any paid AI API.

Use downloadable AI models that run locally on Ubuntu Linux.

**IMPORTANT: Build a functional application, not just a beautiful frontend demonstration.**

---

# 1. PROJECT OBJECTIVE

Create an intelligent movie translation and dubbing studio.

Users should be able to:

1. Import Chinese movies.
2. Extract Chinese speech automatically.
3. Convert Chinese speech into Chinese text.
4. Translate the Chinese dialogue into natural Khmer.
5. Generate Khmer AI voices.
6. Synchronize Khmer voices with the original movie.
7. Edit translations and voice timing manually.
8. Preview dubbed movies directly in the browser.
9. Export videos with Khmer AI voices.
10. Save projects and resume work later.

Target supported video lengths:

- 5 minutes
- 15 minutes
- 30 minutes
- 1 hour
- 2 hours
- Up to 3 hours

The application must support long videos through background job processing, chunking, and checkpoint recovery.

---

# 2. TECHNOLOGY STACK

## Frontend

Use:

- React.js
- Vite
- TypeScript
- Tailwind CSS
- Motion for React
- Lucide React
- React Router
- TanStack Query
- Zustand
- Axios
- React Dropzone
- Wavesurfer.js

Use responsive layouts.

Do not use Bootstrap.

Prefer Tailwind utility classes and reusable React components.

## Backend

Use:

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite
- FFmpeg
- FFprobe
- PyTorch
- Hugging Face Transformers
- faster-whisper
- Background job workers

Use WebSockets or Server-Sent Events for real-time processing updates.

All substantial AI inference must run on the backend.

## AI Models

### Chinese speech recognition

Use Faster-Whisper.

Requirements:

- Recognize spoken Mandarin Chinese.
- Support selectable Simplified Chinese transcription.
- Generate timestamps.
- Detect speech segments.
- Support long movie transcription.
- Allow manual correction.
- Use smaller models on slower computers.

### Chinese-to-Khmer translation

Primary model:

facebook/nllb-200-distilled-600M

Source language:

zho_Hans

Target language:

khm_Khmr

Requirements:

- Produce Khmer Unicode text.
- Preserve dialogue meaning.
- Support context-aware translation.
- Maintain original segment identifiers.
- Preserve timing metadata.
- Never replace Khmer translations with Chinese output.
- Do not silently return empty translations.
- Allow retranslation of individual segments.
- Permit manual editing.

Implement translation in manageable batches.

### Khmer AI text-to-speech

Default model:

facebook/mms-tts-khm

Optional advanced model:

muyleanging/VoxPocket-TTS-Khmer

Requirements:

- Generate spoken Khmer.
- Support individual speech segments.
- Save generated audio as WAV files.
- Preview generated speech.
- Regenerate selected segments.
- Allow voice speed adjustments.
- Permit supported voices and styles.
- Do not display unavailable voices as functional options.

Use the simpler MMS model as the initial working baseline.

Make higher-quality models optional because they may need significantly more RAM or GPU memory.

### Audio processing

Use FFmpeg for:

- Audio extraction
- Audio conversion
- Video rendering
- Audio synchronization
- Timing adjustments
- Audio mixing
- Video compression
- Export

Optional:

Use Demucs for separating dialogue from background music and effects.

Do not assume that perfect dialogue removal is possible.

---

# 3. NO API KEY REQUIREMENT

This is a strict requirement.

The application must not require:

- Gemini API
- OpenAI API
- Google Cloud API
- ElevenLabs API
- Paid translation services
- Paid text-to-speech services

Run AI inference locally.

The initial installation may download public AI model weights from Hugging Face.

After installation, previously downloaded models should operate offline.

Show users which models are installed.

Provide a model manager with:

- Model name
- Download status
- Download size
- Installation progress
- Hardware compatibility
- RAM requirements
- GPU requirements
- Remove model option
- Change model option

Handle model download and installation errors gracefully.

---

# 4. UI/UX DESIGN DIRECTION

Create an exceptionally clean, modern, attractive, and professional interface.

The design should resemble a premium video editing application combined with a modern AI dashboard.

Take visual inspiration from:

- Linear
- DaVinci Resolve
- Adobe Premiere Pro
- Descript
- Modern professional AI SaaS dashboards

Do not copy their branding or exact interfaces.

The application must feel like a professional creative tool.

## Visual Style

Design theme:

**Modern Dark Creative Studio**

Color palette:

Background: #090B10

Sidebar: #10131B

Cards: #161B25

Border: #252B38

Primary accent: #8B5CF6

Secondary accent: #38BDF8

Main text: #F8FAFC

Muted text: #94A3B8

Success: #22C55E

Warning: #F59E0B

Error: #EF4444

## Typography

Use:

- Inter for English UI
- Noto Sans Khmer for Khmer text
- Clean typography hierarchy
- Clear labels
- Comfortable line spacing

Typography sizes:

- Main heading: 32–40px
- Section heading: 22–26px
- Card heading: 16–18px
- Body text: 14–16px
- Small labels: 12–13px

## Design Requirements

Use:

- Rounded 12–16px cards
- Subtle shadows
- Thin borders
- Balanced whitespace
- Clear icons
- Smooth transitions
- Professional hover states
- Skeleton loading
- Beautiful empty states
- Animated progress indicators
- Accessible contrast
- Responsive layouts
- Custom scrollbars

Avoid:

- Oversized buttons
- Excessive gradients
- Too many colors
- Unnecessary animations
- Cluttered dashboards
- Large blank spaces

## Animations

Use Motion for React.

Include:

- Smooth page transitions
- Sidebar animations
- Card hover animations
- Button interactions
- Dialog transitions
- Progress animations
- Smooth panel resizing
- Elegant notification animations

Keep animations lightweight and professional.

---

# 5. MAIN APPLICATION LAYOUT

Create a professional application shell.

## Left Sidebar

Include:

KKD STUDIO AI logo

Navigation:

- Dashboard
- My Projects
- Import Video
- Translation Studio
- AI Voice Studio
- Video Editor
- Export Center
- Model Manager
- Settings

Bottom section:

- System status
- CPU/GPU usage
- Storage
- About

Sidebar must support collapse and expansion.

## Top Navigation

Include:

- Current page title
- Search
- Notifications
- Processing status
- Settings button

Make the interface visually polished.

---

# 6. DASHBOARD PAGE

Build a modern dashboard.

## Hero Section

Display:

"Bring Chinese Stories to Life in Khmer."

Supporting text:

"Translate, dub, and create Khmer movie experiences with local AI."

Primary button:

"Create New Project"

Secondary button:

"Explore Projects"

Include a small animated waveform visualization.

## Statistics Cards

Display:

- Total projects
- Completed translations
- Generated voice clips
- Total processed video hours

Use real database values.

## Recent Projects

Display project cards with:

- Video thumbnail
- Movie name
- Duration
- Translation progress
- Voice progress
- Status
- Last edited date

Actions:

- Open
- Rename
- Duplicate
- Delete

## System Status

Display:

- Translation model status
- Speech recognition model status
- Voice model status
- CPU usage
- GPU availability
- Active processing jobs

---

# 7. VIDEO IMPORT PAGE

Create a beautiful upload interface.

## Upload Panel

Large drag-and-drop area.

Text:

"Drop your movie here"

Subtext:

"Upload Chinese movies and start translating into Khmer."

Buttons:

"Choose Video"

"Import From URL"

Support:

- MP4
- MOV
- MKV
- AVI
- WEBM

Target files up to 10 GB.

Implement chunked uploads with resume support.

## URL Import

Allow users to provide direct downloadable media URLs.

Support optional public video URL import through a separate, legally compliant downloader module where technically supported.

Do not bypass DRM, authentication, or access controls.

Show:

- Video thumbnail
- Video title
- Duration
- Resolution
- File size

Display an import progress bar.

## Import Settings

Source language:

Chinese (Mandarin)

Target language:

Khmer

Processing mode:

- Fast
- Balanced
- High Accuracy

Audio output:

- Khmer Voice Only
- Khmer Voice + Background Audio

Default to:

**Khmer Voice Only**

---

# 8. TRANSLATION STUDIO

This is one of the most important pages.

Build a professional translation workspace.

## Layout

Left panel:

Video player

Middle panel:

Chinese transcription

Right panel:

Khmer translation editor

Bottom panel:

Timeline

## Video Player

Include:

- Play/Pause
- Seek
- Volume
- Playback speed
- Fullscreen
- Current time
- Video duration
- Subtitle display

Clicking a subtitle should seek the video to its timestamp.

## Translation Editor

Display synchronized Chinese and Khmer subtitles.

Each segment should contain:

- Segment number
- Start time
- End time
- Chinese text
- Khmer translation
- Translation status
- Edit button
- Regenerate translation button

Example:

Segment 001

Start: 00:00:05.000

End: 00:00:08.000

Chinese:
你好，你今天怎么样？

Khmer:
សួស្តី ថ្ងៃនេះអ្នកសុខសប្បាយទេ?

Status:
Translated

## Translation Controls

Include:

- Extract Chinese Speech
- Translate Selected
- Translate All
- Retry Failed
- Save Changes
- Export SRT
- Import SRT

Support processing up to 1,000 subtitle segments per batch.

Internally split the work into smaller resumable jobs.

Do not send all 1,000 segments into one model request.

## Translation Quality Requirements

The system should:

- Preserve meaning
- Use natural Khmer grammar
- Preserve character names
- Handle Chinese idioms appropriately
- Maintain subtitle order
- Avoid duplicated translations
- Detect untranslated segments
- Retry failed segments
- Support user corrections

Add a translation validation system.

Flag suspicious translations for review.

Never fabricate a successful translation status.

---

# 9. AI VOICE STUDIO

Create a premium AI dubbing interface.

## Page Layout

Left:

Voice model and voice settings

Center:

Dialogue list

Right:

Voice preview

Bottom:

Audio waveform timeline

## Voice Settings

Include:

- AI model selection
- Available voice selection
- Speech speed
- Pitch adjustment where supported
- Volume
- Available voice styles
- Audio preview

Possible voice styles when supported:

- Neutral
- Happy
- Sad
- Angry
- Calm
- Dramatic

Hide or disable unsupported features.

## Voice Generation

Buttons:

"Generate Selected"

"Generate All Voices"

"Regenerate Failed"

"Preview Voice"

"Save Audio"

Support at least 1,000 dialogue segments through queued jobs.

Display:

- Total segments
- Completed segments
- Failed segments
- Remaining segments
- Current processing step
- Real processing progress

Save each generated clip immediately.

Do not lose completed clips when a later segment fails.

---

# 10. ACCURATE AUDIO SYNCHRONIZATION

Timing accuracy is a critical requirement.

Every generated Khmer voice clip must use the original dialogue timestamp.

Example:

Chinese dialogue:

Start: 00:00:05.000

End: 00:00:08.000

Khmer voice:

Must start at 00:00:05.000.

Do not shift the entire timeline.

## Synchronization Requirements

- Preserve original segment start times.
- Align voice onset with the selected dialogue start.
- Insert silence only where needed.
- Detect generated audio that exceeds the available duration.
- Allow reasonable time stretching.
- Support manual timing adjustments.
- Show overlapping voice clips.
- Allow regeneration of problematic segments.
- Support waveform-based editing.

Never silently cut off a voice clip.

If a voice is too long:

1. Show a warning.
2. Offer modest speed adjustment.
3. Offer translation shortening.
4. Offer manual timing adjustments.
5. Offer voice regeneration.

The user must be able to resolve synchronization problems.

Use FFmpeg for final alignment and audio assembly.

---

# 11. VIDEO EDITOR

Build a timeline-based editor.

The interface should resemble a lightweight professional video editing studio.

## Main Layout

Top-left:

Media library

Top-center:

Video preview

Top-right:

Properties panel

Bottom:

Multitrack timeline

## Timeline Tracks

Include:

Track 1: Video

Track 2: Original audio

Track 3: Khmer AI voices

Track 4: Subtitles

## Editing Features

- Zoom timeline
- Drag clips
- Trim clips
- Split clips
- Move audio
- Adjust volume
- Mute tracks
- Edit subtitles
- Modify timing
- Play selected ranges
- Undo/redo supported changes
- Save project

## Audio Modes

Mode A:

**Khmer AI Voice Only**

Remove the original audio track from the exported movie.

Use only generated Khmer dialogue and silence.

Mode B:

**Khmer AI Voice + Background Audio**

Attempt to preserve background music and effects using source separation.

Explain that source separation may leave artifacts or residual dialogue.

Do not claim perfect audio separation.

---

# 12. VIDEO EXPORT CENTER

Build a dedicated export page.

## Export Settings

Resolution:

- 480p
- 720p
- 1080p
- Original resolution

Format:

- MP4
- MKV

Audio:

- Khmer AI Only
- Khmer AI + Background

Subtitles:

- No subtitles
- Khmer subtitles
- Chinese subtitles
- Download separate SRT file

Quality:

- Fast
- Balanced
- High Quality

## Export Process

Show actual progress through:

1. Validating project
2. Preparing audio
3. Synchronizing voices
4. Rendering video
5. Finalizing output

Allow cancellation.

Allow failed exports to be retried.

Preserve the source media and completed voice clips.

Use streaming or chunk-based processing for long movies.

Avoid loading entire movies into memory.

## Completed Export

Display:

- Video thumbnail
- File name
- Duration
- Resolution
- File size
- Export status

Buttons:

- Play Video
- Open Output Folder
- Download Video
- Export Subtitles

The completed video must be playable inside the browser.

---

# 13. PROJECT PERSISTENCE

Implement reliable project saving.

Use SQLite to store:

- Projects
- Video metadata
- Transcription segments
- Translations
- Voice generation status
- Audio file paths
- Processing jobs
- Export records
- User settings

Save all generated media to organized project directories.

## Resume System

If the application closes during translation or voice generation:

- Preserve completed segments.
- Preserve successful voice clips.
- Save processing checkpoints.
- Detect interrupted jobs on restart.
- Allow users to resume unfinished work.
- Do not restart completed work unnecessarily.

Example:

Total voice clips: 1,000

Completed: 650

Remaining: 350

After reopening:

Display the saved progress.

Button:

"Resume Remaining 350 Clips"

---

# 14. SETTINGS PAGE

Build a beautiful settings interface.

Sections:

General

AI Models

Translation

Audio

Performance

Storage

Appearance

## General Settings

- Application language
- Default output language
- Default export folder
- Autosave

## Model Settings

- Whisper model
- Translation model
- Khmer TTS model
- Installed models
- Download model
- Remove model

## Performance Settings

- CPU/GPU selection
- Batch size
- Maximum worker count
- Model precision where supported
- Memory-saving mode
- Maximum video duration

## Appearance

- Dark mode
- Compact layout
- Animation preferences

---

# 15. BACKEND API

Create real API endpoints.

## Projects

POST /api/projects

GET /api/projects

GET /api/projects/{id}

PATCH /api/projects/{id}

DELETE /api/projects/{id}

## Video Import

POST /api/import/upload

POST /api/import/url

GET /api/import/{job_id}/status

## Transcription

POST /api/projects/{id}/transcribe

GET /api/projects/{id}/segments

PATCH /api/projects/{id}/segments/{segment_id}

## Translation

POST /api/projects/{id}/translate

POST /api/projects/{id}/translate/segment

GET /api/projects/{id}/translation-status

## AI Voice

POST /api/projects/{id}/voices/generate

POST /api/projects/{id}/voices/regenerate

GET /api/projects/{id}/voices

GET /api/projects/{id}/voices/status

## Export

POST /api/projects/{id}/export

GET /api/projects/{id}/export/status

GET /api/projects/{id}/export/result

## System

GET /api/system/status

GET /api/system/models

POST /api/system/models/download

GET /api/system/jobs/{job_id}

Implement proper validation and error handling.

Return meaningful error messages.

Use background workers for expensive jobs.

---

# 16. PERFORMANCE AND LONG VIDEO SUPPORT

The application must handle long movies reliably.

Requirements:

- Support videos up to 3 hours.
- Support uploads up to 10 GB.
- Use chunked processing.
- Process audio without loading entire files into RAM.
- Support CPU inference.
- Support GPU acceleration when available.
- Limit concurrent AI tasks based on available resources.
- Persist processing results.
- Resume failed tasks.
- Avoid duplicate voice generation.
- Clean temporary files safely.
- Log all processing errors.

Provide performance presets.

### Low Resource Mode

Use smaller Whisper models.

Use NLLB 600M.

Use MMS Khmer TTS.

Use low batch sizes.

### High Performance Mode

Use larger models where hardware supports them.

Enable supported GPU acceleration.

Use optimized batch sizes.

Use optional higher-quality Khmer TTS.

---

# 17. ERROR HANDLING

Handle common failures:

- FFmpeg missing
- Model not downloaded
- Insufficient disk space
- Out of memory
- Unsupported video
- Invalid download URL
- Failed transcription
- Translation returns empty text
- Invalid Khmer output
- Voice generation returns no audio
- Voice longer than subtitle duration
- Export failure
- Disconnected browser
- Interrupted background job

Display useful error messages.

Provide recovery actions.

Never display a fake success message.

---

# 18. PROJECT STRUCTURE

Use a clean full-stack folder structure.

kkd-studio-ai/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── stores/
│   │   ├── types/
│   │   ├── assets/
│   │   └── App.tsx
│   │
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── transcription.py
│   │   │   ├── translation.py
│   │   │   ├── tts.py
│   │   │   ├── synchronization.py
│   │   │   └── rendering.py
│   │   ├── workers/
│   │   ├── database/
│   │   └── utils/
│   │
│   ├── requirements.txt
│   └── .env.example
│
├── storage/
│   ├── projects/
│   ├── models/
│   ├── audio/
│   └── exports/
│
├── scripts/
├── tests/
└── README.md

Maintain separation between frontend UI, API endpoints, inference engines, and background workers.

---

# 19. REAL FUNCTIONALITY REQUIREMENT

Do not create nonfunctional buttons.

Do not use fake processing results.

Do not claim that a translation was completed unless the model actually generated it.

Every major UI action must connect to a real backend function.

Implement:

- Real video upload
- Real Chinese speech recognition
- Real Chinese-to-Khmer translation
- Real Khmer speech generation
- Real audio synchronization
- Real video export
- Real project persistence

If an advanced feature is not implemented, clearly label it as unavailable rather than pretending it works.

---

# 20. TESTING REQUIREMENTS

Create automated tests for:

- Video import
- Chinese transcription
- Translation model loading
- Chinese-to-Khmer translation
- Khmer Unicode output
- Khmer TTS audio generation
- Timestamp synchronization
- Saving and resuming jobs
- Export creation
- API validation

Also provide an integration test using a short sample video.

Test the complete workflow:

Upload video
→ Extract audio
→ Recognize Chinese
→ Translate to Khmer
→ Generate Khmer voice
→ Synchronize audio
→ Render movie
→ Play exported result

Verify the output exists and contains a usable video stream and expected audio.

Include tests for failed and interrupted jobs.

---

# 21. INSTALLATION

Target environment:

Ubuntu 24.04 LTS

Support running the frontend and backend locally.

Frontend:

http://localhost:5173

Backend:

http://localhost:8000

API documentation:

http://localhost:8000/docs

Provide:

- Installation instructions
- Required system packages
- Python environment setup
- Node.js setup
- FFmpeg installation
- Model installation
- Startup commands
- Troubleshooting instructions

Create a convenient local startup script.

---

# 22. DEVELOPMENT EXECUTION PLAN

Build this application in functional phases.

Phase 1:
Project setup, frontend shell, routing, dashboard, database.

Phase 2:
Video import, preview, metadata extraction, project management.

Phase 3:
Chinese speech recognition and transcript editor.

Phase 4:
Real offline Chinese-to-Khmer translation.

Phase 5:
Real Khmer TTS generation and audio previews.

Phase 6:
Voice synchronization and timeline editing.

Phase 7:
Video rendering, export, and downloads.

Phase 8:
Long-video processing, recovery, optimization, and testing.

Complete and verify each phase before moving to the next.

Do not replace functional implementations with mock data.

Create clean, maintainable, reusable code.

## FINAL GOAL

Deliver a beautiful, modern, powerful, and functional Chinese-to-Khmer AI movie dubbing studio.

It should be easy for beginners to use while providing advanced editing features.

The user should be able to:

1. Open KKD Studio AI in their browser.
2. Upload a Chinese movie.
3. Automatically recognize Chinese dialogue.
4. Translate the dialogue into Khmer.
5. Generate Khmer AI voices.
6. Synchronize the voices with the movie.
7. Preview the dubbed video.
8. Export the final Khmer-dubbed movie.

All core AI processing must work locally without any paid API key.

Prioritize real functionality, accurate timing, understandable Khmer translation, project reliability, and professional interface design.