from __future__ import annotations
import json
import subprocess
from pathlib import Path
from .utils import AppError

MAX_SECONDS = 10800  # three hours
MAX_BYTES = 10 * 1024**3
EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.webm'}


def probe(path: Path) -> dict:
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], check=True, capture_output=True, text=True, timeout=40)
        metadata = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        raise AppError(f'FFprobe failed or media file is invalid: {e}') from e
    video = next((s for s in metadata.get('streams', []) if s.get('codec_type') == 'video'), None)
    if not video:
        raise AppError('The file has no video track')
    duration = float(metadata.get('format', {}).get('duration') or video.get('duration') or 0)
    if not 0 < duration <= MAX_SECONDS:
        raise AppError('Video duration must be greater than 0 and no longer than 3 hours')
    return {'duration': duration, 'width': int(video.get('width', 0)), 'height': int(video.get('height', 0)), 'file_size': path.stat().st_size}


def srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return f'{h:02}:{m:02}:{s:02},{milli:03}'


def make_srt(segments, lang='km') -> str:
    out = []
    for i, seg in enumerate(segments, 1):
        text = (seg.km if lang == 'km' else seg.zh).strip()
        if not text:
            continue
        out.append(f'{i}\n{srt_timestamp(seg.start)} --> {srt_timestamp(seg.end)}\n{text}\n')
    return '\n'.join(out) + ('\n' if out else '')
