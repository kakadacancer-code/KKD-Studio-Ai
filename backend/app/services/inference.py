"""Actual on-device speech recognition, NLLB translation and MMS Khmer speech synthesis.

Weights are downloaded once on first use unless downloaded through Model Manager.
No cloud inference APIs, no placeholder text and no fake audio generation.
"""
from __future__ import annotations
import os
import html
import re
import unicodedata
from pathlib import Path
from threading import Lock
import numpy as np
from .utils import AppError
from ..database import MODELS_DIR

TRANS_ID = 'facebook/nllb-200-distilled-600M'
TRANSLATORS = {'nllb': TRANS_ID, 'nllb-large': 'facebook/nllb-200-distilled-1.3B'}
TTS_ID = 'facebook/mms-tts-khm'
_loaded = {}
_lock = Lock()


class ModelLoadError(AppError):
    pass


def contains_khmer(text: str) -> bool:
    return any('\u1780' <= c <= '\u17b3' for c in text)


# Whole utterances only. Substring substitutions can reverse the meaning of dialogue.
DIALOGUE_PHRASES = {
    '你好': 'សួស្តី', '您好': 'ជម្រាបសួរ',
    '早上好': 'អរុណសួស្តី', '晚安': 'រាត្រីសួស្តី',
    '谢谢': 'អរគុណ', '謝謝': 'អរគុណ',
    '非常感谢': 'សូមអរគុណយ៉ាងជ្រាលជ្រៅ', '非常感謝': 'សូមអរគុណយ៉ាងជ្រាលជ្រៅ',
    '对不起': 'សុំទោស', '對不起': 'សុំទោស',
    '再见': 'លាហើយ', '再見': 'លាហើយ',
}


def dialogue_text(text: str) -> str:
    text = re.sub(r'</?(?:i|b|u|font)\b[^>]*>', '', html.unescape(text), flags=re.I)
    return unicodedata.normalize('NFC', text).strip()


def has_chinese(text: str) -> bool:
    return bool(re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002fa1f]', text))


def model_local(identifier: str) -> Path:
    return MODELS_DIR / identifier.replace('/', '--')


def installed_model(identifier: str) -> Path | None:
    path = model_local(identifier)
    def complete(folder):
        vocab = 'vocab.json' if identifier == TTS_ID else 'sentencepiece.bpe.model'
        return ((folder / 'config.json').is_file() and (folder / vocab).is_file()
                and any((folder / name).is_file() for name in ('model.safetensors','pytorch_model.bin')))
    if complete(path):
        return path
    try:
        from huggingface_hub import try_to_load_from_cache
        config = try_to_load_from_cache(identifier, 'config.json')
        if isinstance(config, str) and complete(Path(config).parent):
            return Path(config).parent
    except ImportError:
        pass
    return None


def load_whisper(size: str):
    if size not in ('tiny', 'base', 'small', 'medium'):
        raise AppError('Unknown Whisper model')
    name = f'whisper-{size}'
    with _lock:
        if name not in _loaded:
            try:
                from faster_whisper import WhisperModel
                path = MODELS_DIR / name
                _loaded[name] = WhisperModel(str(path) if (path / 'model.bin').exists() else size, device='cpu', compute_type='int8', download_root=str(MODELS_DIR), local_files_only=os.getenv('HF_HUB_OFFLINE') == '1')
            except Exception as e:
                raise AppError(f'Cannot load Whisper {size}. Install AI requirements and download model: {e}') from e
        return _loaded[name]


def load_translation(engine='nllb'):
    identifier = TRANSLATORS[engine]
    with _lock:
        if engine not in _loaded:
            try:
                import torch
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
                source = str(installed_model(identifier) or identifier)
                tokenizer = AutoTokenizer.from_pretrained(source, src_lang='zho_Hans')
                model = AutoModelForSeq2SeqLM.from_pretrained(source)
                model.eval()
                _loaded[engine] = (tokenizer, model, torch)
            except Exception as e:
                raise ModelLoadError(f'Cannot load NLLB model. Check models and AI dependencies: {e}') from e
        return _loaded[engine]


def translate_batch(texts: list[str], engine='nllb') -> list[str]:
    parts = [[] for _ in texts]
    pending = []
    invalid = set()
    for idx, text in enumerate(texts):
        clean = dialogue_text(text)
        # SRT often marks each speaker in a shared time window with a dash.
        for line in re.split(r'\n\s*[-–—]\s*', clean.lstrip('-–— ')):
            line = line.strip()
            if not has_chinese(line):
                invalid.add(idx)
                continue
            phrase = DIALOGUE_PHRASES.get(line.rstrip('。.!！'))
            if phrase:
                parts[idx].append(phrase)
            else:
                pending.append((idx, len(parts[idx]), line))
                parts[idx].append('')

    if pending:
        tokenizer, model, torch = load_translation(engine)
        try:
            units = []
            for idx, slot, line in pending:
                if idx in invalid:
                    continue
                if len(tokenizer(line).input_ids) <= 512:
                    units.append((idx, slot, line))
                    continue
                # Preserve every clause when an unusually long cue exceeds NLLB's
                # training window. An indivisible oversized clause needs review.
                clauses = list(filter(None, re.split(r'(?<=[。！？!?；;，,])\s*', line)))
                if any(len(tokenizer(clause).input_ids) > 512 for clause in clauses):
                    invalid.add(idx)
                    continue
                units.extend((idx, slot, clause) for clause in clauses)

            for offset in range(0, len(units), 4):
                batch = units[offset:offset + 4]
                inputs = tokenizer([line for _, _, line in batch], return_tensors='pt', padding=True)
                with torch.inference_mode():
                    out = model.generate(**inputs, forced_bos_token_id=tokenizer.convert_tokens_to_ids('khm_Khmr'),
                                         max_new_tokens=512, num_beams=4)
                for (idx, slot, _), tokens in zip(batch, out, strict=True):
                    km = tokenizer.decode(tokens, skip_special_tokens=True).strip()
                    if (not contains_khmer(km) or has_chinese(km)
                            or int(tokens[1:].ne(tokenizer.pad_token_id).sum()) >= 512):
                        invalid.add(idx)
                    else:
                        parts[idx][slot] = (parts[idx][slot] + ' ' + km).strip()
        except Exception as e:
            raise AppError(f'Local NLLB translation failed: {e}') from e
    return ['' if idx in invalid else ' '.join(lines) for idx, lines in enumerate(parts)]


def load_voice():
    with _lock:
        if 'voice' not in _loaded:
            try:
                import torch
                from transformers import AutoTokenizer, VitsModel
                source = str(installed_model(TTS_ID) or TTS_ID)
                tokenizer = AutoTokenizer.from_pretrained(source)
                model = VitsModel.from_pretrained(source)
                model.eval()
                _loaded['voice'] = (tokenizer, model, torch)
            except Exception as e:
                raise ModelLoadError(f'Cannot load MMS Khmer voice model. Check models and AI dependencies: {e}') from e
        return _loaded['voice']


def synthesize_khmer(text: str, output: Path, speed: float = 1.0, *, window: float | None = None) -> float:
    if not text.strip() or not contains_khmer(text):
        raise AppError('Khmer text is empty or does not contain Khmer Unicode')
    if not 0.75 <= speed <= 1.35:
        raise AppError('Voice speed must be between 0.75× and 1.35×')
    tokenizer, model, torch = load_voice()
    try:
        import soundfile as sf
        inputs = tokenizer(text, return_tensors='pt')
        with torch.inference_mode():
            waveform = model(**inputs).waveform.squeeze().cpu().numpy()
        waveform = np.asarray(waveform, dtype=np.float32)
        if waveform.size == 0 or not np.isfinite(waveform).all():
            raise AppError('Voice model returned no valid audio')
        sample_rate = int(model.config.sampling_rate)
        if window and window > 0 and len(waveform) / sample_rate > window * speed:
            # Small headroom covers the endpoint rounding of FFmpeg's tempo filter.
            speed = min(1.35, len(waveform) / sample_rate / window * 1.02)
        output.parent.mkdir(parents=True, exist_ok=True)
        raw = output.with_name(output.stem + '.raw.wav')
        sf.write(str(raw), waveform, sample_rate)
        if speed == 1:
            raw.replace(output)
        else:
            import subprocess
            adjusted = output.with_suffix('.tempo.wav')
            try:
                subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(raw), '-af', f'atempo={speed}', str(adjusted)], check=True, timeout=240)
                adjusted.replace(output)
            finally:
                adjusted.unlink(missing_ok=True)
                raw.unlink(missing_ok=True)
        data = sf.info(str(output))
        return data.duration
    except AppError:
        raise
    except Exception as e:
        raise AppError(f'Khmer voice generation failed: {e}') from e


def model_catalog() -> list[dict]:
    items = [
        {'id': 'whisper-tiny', 'name': 'Whisper Tiny', 'kind': 'Transcription', 'ram': '~1 GB', 'license': 'MIT'},
        {'id': 'whisper-base', 'name': 'Whisper Base', 'kind': 'Transcription', 'ram': '~1–2 GB', 'license': 'MIT'},
        {'id': 'whisper-small', 'name': 'Whisper Small', 'kind': 'Transcription', 'ram': '~2–4 GB', 'license': 'MIT'},
        {'id': 'nllb', 'name': 'NLLB-200 600M', 'kind': 'Translation', 'ram': '~4–6 GB', 'license': 'CC-BY-NC-4.0'},
        {'id': 'nllb-large', 'name': 'NLLB-200 1.3B', 'kind': 'Translation', 'ram': '~8–12 GB', 'license': 'CC-BY-NC-4.0'},
        {'id': 'mms', 'name': 'MMS Khmer TTS', 'kind': 'Voice generation', 'ram': '~2 GB', 'license': 'CC-BY-NC-4.0'},
    ]
    for item in items:
        if item['id'].startswith('whisper'):
            size = item['id'].split('-')[1]
            target = MODELS_DIR / ('whisper-' + size)
            others = list(MODELS_DIR.glob('models--Systran--faster-whisper-' + size + '*'))
            item['installed'] = (target / 'model.bin').exists() or bool(others)
        else:
            item['installed'] = installed_model(TRANSLATORS.get(item['id'], TTS_ID)) is not None
    return items


def download_model(identifier: str):
    if identifier.startswith('whisper-') and identifier in ('whisper-tiny','whisper-base','whisper-small'):
        from faster_whisper.utils import download_model as download_whisper
        size = identifier.removeprefix('whisper-')
        path = download_whisper(size, output_dir=str(MODELS_DIR / identifier))
        return str(path)
    if identifier in (*TRANSLATORS, 'mms'):
        from huggingface_hub import snapshot_download
        model_id = TRANSLATORS.get(identifier, TTS_ID)
        return snapshot_download(model_id, local_dir=str(model_local(model_id)))
    raise AppError('Unknown model')


def release_model(name: str):
    """Free previous stage's RAM on smaller CPU-only machines."""
    import gc
    with _lock:
        if name not in _loaded:
            return
        _loaded.pop(name, None)
    gc.collect()
