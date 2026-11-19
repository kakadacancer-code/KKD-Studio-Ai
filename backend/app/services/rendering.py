"""Disk-backed voice timeline: every clip begins at its absolute source time."""
from __future__ import annotations
import math
import os
import subprocess
import uuid
import wave
from pathlib import Path
import numpy as np
import soundfile as sf
from .utils import AppError

RATE = 22050


def inspect_timing(segments) -> list[dict]:
    issues = []
    for s in segments:
        if s.translation_status in ('failed', 'needs_review'):
            issues.append({'segment_id': s.id, 'message': 'Review the Khmer translation before export'})
        elif s.voice_status not in ('ready', 'timing_warning') or not s.voice_path or not Path(s.voice_path).is_file():
            issues.append({'segment_id': s.id, 'message': 'Missing generated Khmer voice'})
        elif s.voice_duration > s.end - s.start + 0.035:
            issues.append({'segment_id': s.id, 'message': f'Voice is {s.voice_duration:.2f}s, but window is {s.end-s.start:.2f}s. Shorten text or increase speech speed.'})
        elif s.start < 0 or s.end <= s.start:
            issues.append({'segment_id': s.id, 'message': 'Invalid subtitle start/end time'})
    return issues


def create_timeline(segments, duration: float, destination: Path, progress=None):
    """Write silence then mix each generated WAV at exactly round(start * RATE).

    Keeps long films bounded in RAM; only one generated clip and one small chunk
    are loaded at a time. This method never moves neighboring dialogue clips.
    """
    issues = inspect_timing(segments)
    if issues:
        raise AppError(f'{len(issues)} segment(s) require attention before export: {issues[0]["message"]}')
    duration_frames = int(math.ceil(duration * RATE))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        remaining = duration_frames
        zeros = b'\x00' * (RATE * 2 * 5)
        while remaining:
            frames = min(remaining, RATE * 5)
            wav.writeframesraw(zeros[:frames * 2])
            remaining -= frames
        wav.writeframes(b'')

    with destination.open('r+b') as track:
        for i, segment in enumerate(segments, 1):
            data, source_rate = sf.read(segment.voice_path, dtype='float32', always_2d=False)
            if data.ndim == 2:
                data = data.mean(axis=1)
            if source_rate != RATE:
                new_len = int(round(len(data) * RATE / source_rate))
                data = np.interp(np.arange(new_len) * source_rate / RATE, np.arange(len(data)), data).astype(np.float32)
            # Protect against corrupted files, even after validation.
            offset = int(round(segment.start * RATE))
            if offset + len(data) > duration_frames:
                raise AppError(f'Segment {segment.seq} would exceed video duration')
            pcm = np.round(np.clip(data, -1, 1) * 32767).astype('<i2')
            for pos in range(0, len(pcm), RATE * 2):
                piece = pcm[pos:pos + RATE * 2]
                point = 44 + 2 * (offset + pos)  # wave module creates 44-byte PCM header
                track.seek(point)
                old = track.read(2 * len(piece))
                existing = np.frombuffer(old, dtype='<i2').astype(np.int32)
                if len(existing) != len(piece):
                    raise AppError('Output audio file unexpectedly truncated')
                mixed = np.clip(existing + piece.astype(np.int32), -32768, 32767).astype('<i2')
                track.seek(point)
                track.write(mixed.tobytes())
            if progress:
                progress(i, len(segments), f'Aligning voice {i}/{len(segments)}')
    return destination


def encode_video(video: Path, audio: Path, destination: Path, duration: float, resolution='original', quality='balanced', progress=None, cancelled=None):
    if resolution not in ('original','480p','720p','1080p') or quality not in ('fast','balanced','high'):
        raise AppError('Unsupported export setting')
    settings = {'fast': ('ultrafast', '26'), 'balanced': ('veryfast', '22'), 'high': ('medium', '18')}
    preset, crf = settings[quality]
    temp = destination.with_name(f'.export-{uuid.uuid4().hex[:8]}' + destination.suffix)
    cmd = ['ffmpeg', '-hide_banner', '-y', '-loglevel', 'error', '-nostats', '-progress', 'pipe:1', '-i', str(video), '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0']
    if resolution != 'original':
        height = {'480p':480, '720p':720, '1080p':1080}[resolution]
        cmd.extend(['-vf', f'scale=-2:min(ih\\,{height})'])
    cmd.extend(['-c:v','libx264','-preset',preset,'-crf',crf,'-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart','-t',str(duration),str(temp)])
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        for line in proc.stdout:
            if cancelled and cancelled():
                proc.terminate()
                proc.wait(timeout=10)
                raise AppError('Export cancelled')
            if line.startswith('out_time_ms='):
                # ffmpeg labels microseconds as out_time_ms
                try:
                    seconds = int(line.split('=',1)[1]) / 1_000_000
                    if progress:
                        progress(min(0.98, seconds / duration))
                except ValueError:
                    pass
        error = proc.stderr.read()
        code = proc.wait()
        if code:
            raise AppError(f'FFmpeg export failed: {error[-1600:]}')
        if not temp.is_file() or temp.stat().st_size == 0:
            raise AppError('FFmpeg produced no video file')
        temp.replace(destination)
    finally:
        temp.unlink(missing_ok=True)
    return destination
