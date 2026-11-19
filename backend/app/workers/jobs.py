"""Sequential, persistent local worker with checkpointed AI processing."""
from __future__ import annotations
import math
import os
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from sqlalchemy import func
from ..database import SessionLocal, Job, Segment, Project, Export, TranscribedChunk, PROJECTS_DIR
from ..services import inference
from ..services.media import make_srt
from ..services.rendering import create_timeline, encode_video
from ..services.utils import AppError

executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='kkd-ai')
_launch_lock = Lock()


def log_job(jid, *, done=None, total=None, failed=None, message=None, status=None, error=None, output=None):
    with SessionLocal() as db:
        job = db.get(Job, jid)
        if job is None:
            return
        for key, val in {'done':done,'total':total,'failed':failed,'message':message,'status':status,'error':error,'output':output}.items():
            if val is not None:
                setattr(job, key, val)
        db.commit()


def check_cancel(jid):
    with SessionLocal() as db:
        job = db.get(Job, jid)
        if job and job.status == 'cancel_requested':
            raise AppError('Job cancelled')


def launch(kind: str, project_id: str | None, options: dict | None = None) -> Job:
    if kind not in ('dub_movie','transcribe','translate','voices','export','download_model'):
        raise AppError('Unsupported job')
    with _launch_lock, SessionLocal() as db:
        if project_id:
            active = db.query(Job).filter(Job.project_id == project_id, Job.status.in_(['queued','running','cancel_requested'])).first()
            if active:
                raise AppError(f'A job is already running for this project ({active.kind})')
        job = Job(id=str(uuid.uuid4()), kind=kind, project_id=project_id, status='queued', message='Waiting for worker')
        db.add(job)
        db.commit()
        job_id = job.id
    executor.submit(worker, job_id, options or {})
    return job


def worker(jid: str, options: dict):
    kind = None
    try:
        with SessionLocal() as db:
            job = db.get(Job, jid)
            kind, project_id = job.kind, job.project_id
            if job.status == 'cancel_requested':
                raise AppError('Job cancelled before starting')
        log_job(jid, status='running', message='Starting local worker')
        functions = {'dub_movie': do_dub_movie, 'transcribe': do_transcribe,'translate': do_translate,'voices': do_voices,'export': do_export, 'download_model': do_download}
        functions[kind](jid, project_id, options)
        with SessionLocal() as db:
            job = db.get(Job, jid)
            if job.status == 'cancel_requested':
                raise AppError('Job cancelled')
            result = 'completed_with_errors' if job.failed else 'completed'
            message = (job.message if kind == 'dub_movie' else f'{job.kind.title()} finished' + (f' ({job.failed} failed)' if job.failed else ''))
        log_job(jid, status=result, message=message)
    except Exception as exc:
        text = str(exc)
        log_job(jid, status='cancelled' if 'cancelled' in text.lower() else 'failed', message='Processing stopped', error=text[:2000])
    finally:
        if kind in ('transcribe', 'translate', 'voices', 'dub_movie'):
            for name in (f"whisper-{options.get('model', 'base')}", options.get('translator', 'nllb'), 'voice'):
                inference.release_model(name)


def do_dub_movie(jid, pid, options):
    with SessionLocal() as db:
        has_rows = db.query(Segment.id).filter_by(project_id=pid).first()
        has_checkpoints = db.query(TranscribedChunk).filter_by(project_id=pid).first()
        previous_asr = db.query(Job).filter_by(project_id=pid, kind='transcribe').order_by(Job.created_at.desc()).first()
    # Imported subtitles are a complete source. Partially transcribed films must
    # finish recognition before progressing, including projects from older versions.
    if not has_rows or has_checkpoints or (previous_asr and previous_asr.status != 'completed'):
        do_transcribe(jid, pid, options)
    check_cancel(jid)
    do_translate(jid, pid, options)
    check_cancel(jid)
    do_voices(jid, pid, {**options, 'fit_window': True})
    with SessionLocal() as db:
        rows = db.query(Segment).filter_by(project_id=pid)
        translations = rows.filter(Segment.translation_status != 'translated').count()
        voices = rows.filter(Segment.translation_status == 'translated', Segment.voice_status != 'ready').count()
        issues = translations + voices
        db.get(Project, pid).status = 'needs_review' if issues else 'voiced'
        db.commit()
    log_job(jid, failed=issues, message=(f'Review {translations} translation(s) and {voices} voice clip(s), then resume dubbing.' if issues else 'Khmer voices are ready for export.'))


def do_transcribe(jid, pid, options):
    size = options.get('model', 'base')
    log_job(jid, message=f'Loading local Whisper {size} model…')
    model = None
    with SessionLocal() as db:
        project = db.get(Project, pid)
        if not project or not project.filename:
            raise AppError('Import a video first')
        source, duration = Path(project.filename), project.duration
    step_seconds = 300
    chunks = math.ceil(duration / step_seconds)
    log_job(jid, total=chunks, done=0)
    for index in range(chunks):
        check_cancel(jid)
        with SessionLocal() as db:
            if db.get(TranscribedChunk, (pid, index)) or db.query(Segment.id).filter_by(project_id=pid, chunk_index=index).first():
                log_job(jid, done=index+1, message=f'Skipped saved chunk {index+1}/{chunks}')
                continue
        tmp = PROJECTS_DIR / pid / f'transcribe-{index}.wav'
        seconds = min(step_seconds, duration - index * step_seconds)
        cmd = ['ffmpeg', '-hide_banner','-loglevel','error','-y','-ss',str(index * step_seconds),'-i',str(source),'-t',str(seconds),'-vn','-ac','1','-ar','16000',str(tmp)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=300)
            if model is None:
                model = inference.load_whisper(size)
            entries, _ = model.transcribe(str(tmp), language='zh', vad_filter=True, beam_size=5, condition_on_previous_text=False)
            rows = [(max(0, index * step_seconds + float(e.start)), min(duration, index * step_seconds + float(e.end)), e.text.strip()) for e in entries]
            with SessionLocal() as db:
                current = db.query(func.max(Segment.seq)).filter(Segment.project_id == pid).scalar() or 0
                for begin, end, zh in rows:
                    if end > begin and zh:
                        current += 1
                        db.add(Segment(project_id=pid, chunk_index=index, seq=current, start=round(begin,3), end=round(end,3), zh=zh))
                db.add(TranscribedChunk(project_id=pid, chunk_index=index))
                db.commit()
            log_job(jid, done=index+1, message=f'Transcribed chunk {index+1}/{chunks}')
        finally:
            tmp.unlink(missing_ok=True)
    with SessionLocal() as db:
        project = db.get(Project, pid)
        n = db.query(Segment).filter_by(project_id=pid).count()
        project.status = 'transcribed' if n else 'no_speech_found'
        db.commit()
    inference.release_model(f'whisper-{size}')
    if not n:
        raise AppError('Whisper found no Chinese speech. Check the source audio and language.')


def do_translate(jid, pid, options):
    engine = options.get('translator', 'nllb')
    chosen = set(int(x) for x in options.get('segment_ids', []))
    with SessionLocal() as db:
        segments = db.query(Segment).filter_by(project_id=pid).order_by(Segment.start).all()
        pending = [s.id for s in segments if (not chosen or s.id in chosen) and (options.get('overwrite') or not s.km.strip() or s.translation_status in ('failed','needs_review'))]
    log_job(jid, total=len(pending), done=0, message='Translating Chinese dialogue into Khmer…')
    failures = 0
    for offset in range(0, len(pending), 4):
        check_cancel(jid)
        ids = pending[offset:offset+4]
        with SessionLocal() as db:
            rows = db.query(Segment).filter(Segment.id.in_(ids)).order_by(Segment.id).all()
        error = ''
        try:
            texts = inference.translate_batch([s.zh for s in rows], engine)
            if len(texts) != len(rows):
                raise AppError('Translation model returned an unexpected number of results')
        except inference.ModelLoadError:
            raise
        except Exception as exc:
            texts = [''] * len(rows)
            error = str(exc)[:300]

        with SessionLocal() as db:
            for row, candidate in zip(rows, texts):
                # Edits saved while the CPU was translating take precedence.
                unchanged = db.query(Segment).filter_by(id=row.id, zh=row.zh, km=row.km)
                if inference.contains_khmer(candidate) and not inference.has_chinese(candidate):
                    update = dict(km=candidate, translation_status='translated', review_note='')
                    if candidate != row.km:
                        update.update(voice_status='pending', voice_duration=0, voice_path=None)
                else:
                    note = ('Add Chinese dialogue or enter a Khmer translation.'
                            if not inference.has_chinese(inference.dialogue_text(row.zh))
                            else 'Incomplete Khmer translation. Check the source, split long dialogue or edit the Khmer text.')
                    update = dict(translation_status='failed', review_note=error or note,
                                  voice_status='pending', voice_duration=0, voice_path=None)
                changed = unchanged.update(update, synchronize_session=False)
                if changed and update['translation_status'] == 'failed':
                    failures += 1
            db.commit()
        log_job(jid, done=min(offset+len(ids),len(pending)), failed=failures, message=f'Translated {min(offset+len(ids),len(pending))}/{len(pending)}')
    with SessionLocal() as db:
        p = db.get(Project,pid)
        if p:
            p.status = 'translated' if not failures else 'needs_review'
            db.commit()
    inference.release_model(engine)


def do_voices(jid, pid, options):
    chosen = set(int(x) for x in options.get('segment_ids', []))
    with SessionLocal() as db:
        query = db.query(Segment).filter_by(project_id=pid)
        if options.get('fit_window'):
            query = query.filter(~Segment.translation_status.in_(['failed','needs_review']))
        rows = query.order_by(Segment.start).all()
        pending = [s.id for s in rows if (not chosen or s.id in chosen) and (options.get('overwrite') or not (s.voice_path and Path(s.voice_path).is_file()))]
    log_job(jid, total=len(pending), done=0, message='Generating Khmer voices…')
    failures = 0
    for i, segment_id in enumerate(pending, 1):
        check_cancel(jid)
        with SessionLocal() as db:
            seg = db.get(Segment, segment_id)
        if seg is None:
            continue
        outfile = PROJECTS_DIR / pid / 'voices' / f'{segment_id}-{jid}.wav'
        window = seg.end - seg.start
        try:
            if seg.translation_status in ('failed','needs_review'):
                raise AppError('Review the Khmer translation before generating this voice.')
            duration = inference.synthesize_khmer(seg.km, outfile, seg.voice_speed,
                                                  window=window if options.get('fit_window') else None)
            overrun = duration > window + 0.035
            note = f'Voice exceeds subtitle window by {duration-window:.2f}s. Shorten translation or increase speech speed.' if overrun else ''
            update = dict(voice_path=str(outfile), voice_duration=duration,
                          voice_status='timing_warning' if overrun else 'ready', review_note=note)
        except inference.ModelLoadError:
            raise
        except Exception as exc:
            update = dict(voice_path=None, voice_duration=0, voice_status='failed', review_note=str(exc)[:350])

        with SessionLocal() as db:
            unchanged = db.query(Segment).filter_by(id=seg.id, zh=seg.zh, km=seg.km, voice_speed=seg.voice_speed,
                                                     start=seg.start, end=seg.end, translation_status=seg.translation_status)
            saved = unchanged.update(update, synchronize_session=False)
            db.commit()
        if not saved or update['voice_status'] == 'failed':
            outfile.unlink(missing_ok=True)
        if saved and update['voice_status'] == 'failed':
            failures += 1
        if saved and seg.voice_path and Path(seg.voice_path).parent == outfile.parent and Path(seg.voice_path) != outfile:
            Path(seg.voice_path).unlink(missing_ok=True)
        log_job(jid, done=i, failed=failures, message=f'Generated voice {i}/{len(pending)}')
    with SessionLocal() as db:
        p = db.get(Project,pid)
        if p:
            p.status = 'voiced' if not failures else 'needs_review'
            db.commit()
    inference.release_model('voice')


def do_export(jid, pid, options):
    from ..services.rendering import inspect_timing
    with SessionLocal() as db:
        p = db.get(Project, pid)
        if not p or not p.filename:
            raise AppError('Project has no imported video')
        segments = db.query(Segment).filter_by(project_id=pid).order_by(Segment.start).all()
        if not segments:
            raise AppError('No dialogue segments; transcribe or import subtitles first')
        issues = inspect_timing(segments)
        if issues:
            raise AppError(f'{len(issues)} voice segment(s) are missing or too long. First problem at segment {issues[0]["segment_id"]}: {issues[0]["message"]}')
        source, duration = Path(p.filename), p.duration
    audio = PROJECTS_DIR / pid / 'renders' / f'voice-{jid}.wav'
    destination = PROJECTS_DIR / pid / 'renders' / f'kkd-khmer-{jid[:8]}.mp4'
    log_job(jid, total=100, done=0, message='Preparing synchronized Khmer voice timeline')
    try:
        create_timeline(segments,duration,audio,progress=lambda done,total,msg: log_job(jid,done=min(20,int(20*done/total)),message=msg))
        check_cancel(jid)
        log_job(jid,done=20,message='Rendering video with Khmer voice only (original soundtrack excluded)')
        encode_video(source,audio,destination,duration,options.get('resolution','original'),options.get('quality','balanced'),progress=lambda fraction: log_job(jid,done=20+int(fraction*79),message=f'Encoding {int(fraction*100)}%'),cancelled=lambda: is_cancelled(jid))
        with SessionLocal() as db:
            db.add(Export(id=str(uuid.uuid4()),project_id=pid,path=str(destination)))
            project = db.get(Project,pid)
            project.status = 'exported'
            db.commit()
        log_job(jid,done=100,output=str(destination),message='Video created')
    finally:
        audio.unlink(missing_ok=True)


def is_cancelled(jid):
    with SessionLocal() as db:
        j = db.get(Job,jid)
        return bool(j and j.status == 'cancel_requested')


def do_download(jid, pid, options):
    which = options.get('model_id')
    log_job(jid, total=1, message=f'Downloading {which}; model files can be large…')
    inference.download_model(which)
    check_cancel(jid)
    log_job(jid,done=1,message='Model downloaded')
