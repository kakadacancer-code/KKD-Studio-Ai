"""KKD Studio AI local API. All controls use actual persisted data or operations."""
from __future__ import annotations
import ipaddress
import json
import re
import shutil
import socket
import subprocess
import uuid
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Body
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func

from .database import SessionLocal, Project, Segment, Job, Export, TranscribedChunk, PROJECTS_DIR, STORAGE, MODELS_DIR
from .services.media import probe, make_srt, MAX_BYTES, EXTENSIONS
from .services.inference import model_catalog
from .services.utils import AppError
from .workers.jobs import launch

app = FastAPI(title='KKD Studio AI', version='0.1.0', description='Offline Chinese → Khmer subtitling and dubbing studio')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173','http://localhost:5174','http://127.0.0.1:5174'], allow_credentials=False, allow_methods=['*'], allow_headers=['*'])

@app.exception_handler(AppError)
async def business_error(request: Request, exc: AppError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=400, content={'detail':str(exc)})

class NewProject(BaseModel):
    name: str = Field(min_length=1,max_length=220)

class RenameProject(BaseModel):
    name: str = Field(min_length=1,max_length=220)

class SegmentUpdate(BaseModel):
    zh: str | None = None
    km: str | None = None
    start: float | None = Field(default=None,ge=0)
    end: float | None = Field(default=None,gt=0)
    voice_speed: float | None = Field(default=None,ge=0.75,le=1.35)

class SegmentAdd(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    zh: str = ''
    km: str = ''

class MovieOptions(BaseModel):
    model: str = 'base'
    translator: Literal['nllb', 'nllb-large'] = 'nllb'

class AIOptions(MovieOptions):
    segment_ids: list[int] = Field(default_factory=list, max_length=1000)
    overwrite: bool = False

class ExportOptions(BaseModel):
    resolution: str = 'original'
    quality: str = 'balanced'
    audio_mode: str = 'voice_only'

class ModelRequest(BaseModel):
    model_id: str

class URLRequest(BaseModel):
    url: str
    name: str | None = None

class ChunkStart(BaseModel):
    filename: str
    filesize: int = Field(gt=0,le=MAX_BYTES)
    chunks: int = Field(gt=0,le=20000)


def get_project(db, pid: str) -> Project:
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(status_code=404, detail='Project not found')
    return p


def segment_json(seg: Segment):
    return {'id':seg.id,'seq':seg.seq,'start':seg.start,'end':seg.end,'zh':seg.zh,'km':seg.km,'translation_status':seg.translation_status,'voice_status':seg.voice_status,'voice_duration':seg.voice_duration,'voice_speed':seg.voice_speed,'voice_url':f'/api/segments/{seg.id}/voice' if seg.voice_path and Path(seg.voice_path).is_file() else None,'review_note':seg.review_note}


def project_json(p: Project, db=None):
    base = {'id':p.id,'name':p.name,'duration':p.duration,'file_size':p.file_size,'width':p.width,'height':p.height,'status':p.status,'filename':Path(p.filename).name if p.filename else None,'video_url':f'/api/projects/{p.id}/video' if p.filename else None,'created_at':p.created_at,'updated_at':p.updated_at}
    if db:
        segments = db.query(Segment).filter_by(project_id=p.id).all()
        count = len(segments)
        base.update({'segment_count':count,'translated_count':sum(bool(s.km.strip()) for s in segments),'voiced_count':sum(bool(s.voice_path and Path(s.voice_path).is_file()) for s in segments),'warning_count':sum(s.voice_status == 'timing_warning' for s in segments)})
    return base


def finish_upload(p: Project, media: Path, db):
    if not media.is_file() or not media.stat().st_size:
        raise AppError('Upload is empty')
    metadata = probe(media)
    for k,v in metadata.items(): setattr(p,k,v)
    p.filename = str(media)
    p.status = 'imported'
    db.commit()
    return project_json(p,db)

@app.get('/api/health')
def health():
    return {'ok':True,'app':'KKD Studio AI','mode':'local-only'}

@app.get('/api/dashboard')
def dashboard():
    with SessionLocal() as db:
        projects = db.query(Project).order_by(Project.updated_at.desc()).all()
        return {'projects':len(projects),'translations':db.query(Segment).filter(Segment.translation_status=='translated').count(),'voices':db.query(Segment).filter(Segment.voice_path.isnot(None)).count(),'video_hours':round(sum(p.duration for p in projects)/3600,2),'recent': [project_json(p,db) for p in projects[:5]]}

@app.post('/api/projects')
def new_project(payload:NewProject):
    with SessionLocal() as db:
        p = Project(id=str(uuid.uuid4()),name=payload.name.strip(),status='created')
        db.add(p); db.commit()
        (PROJECTS_DIR / p.id).mkdir(parents=True,exist_ok=True)
        return project_json(p,db)

@app.get('/api/projects')
def list_projects():
    with SessionLocal() as db:
        return [project_json(p,db) for p in db.query(Project).order_by(Project.updated_at.desc()).all()]

@app.get('/api/projects/{pid}')
def single_project(pid:str):
    with SessionLocal() as db:
        return project_json(get_project(db,pid),db)

@app.patch('/api/projects/{pid}')
def patch_project(pid:str, payload:RenameProject):
    with SessionLocal() as db:
        p = get_project(db,pid)
        p.name = payload.name.strip()
        db.commit()
        return project_json(p,db)

@app.delete('/api/projects/{pid}')
def delete_project(pid:str):
    with SessionLocal() as db:
        get_project(db,pid)
        if db.query(Job).filter(Job.project_id==pid,Job.status.in_(['queued','running','cancel_requested'])).first():
            raise AppError('Cannot delete a project while a job is active')
        db.query(Export).filter_by(project_id=pid).delete()
        db.query(TranscribedChunk).filter_by(project_id=pid).delete()
        db.query(Job).filter_by(project_id=pid).delete()
        db.delete(db.get(Project,pid)); db.commit()
    shutil.rmtree(PROJECTS_DIR / pid,ignore_errors=True)
    return {'deleted':True}

@app.post('/api/import/upload')
async def upload_video(file:UploadFile=File(...)):
    filename = Path(file.filename or 'video.mp4').name
    if Path(filename).suffix.lower() not in EXTENSIONS:
        raise AppError('Unsupported format. Upload MP4, MKV, MOV, AVI, or WEBM.')
    pid = str(uuid.uuid4())
    folder = PROJECTS_DIR / pid
    folder.mkdir(parents=True,exist_ok=True)
    media = folder / ('source'+Path(filename).suffix.lower())
    with SessionLocal() as db:
        p = Project(id=pid,name=Path(filename).stem[:220],status='uploading')
        db.add(p);db.commit()
        try:
            size = 0
            with media.open('wb') as output:
                while chunk := await file.read(1024*1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise AppError('10 GB upload limit exceeded')
                    output.write(chunk)
            return finish_upload(p,media,db)
        except Exception:
            db.delete(p); db.commit()
            shutil.rmtree(folder,ignore_errors=True)
            raise
        finally:
            await file.close()

@app.post('/api/import/chunks/init')
def begin_chunks(payload:ChunkStart):
    filename = Path(payload.filename).name
    if Path(filename).suffix.lower() not in EXTENSIONS:
        raise AppError('Unsupported video format')
    with SessionLocal() as db:
        p = Project(id=str(uuid.uuid4()),name=Path(filename).stem[:220],status='uploading')
        db.add(p);db.commit()
        (PROJECTS_DIR/p.id/'chunks').mkdir(parents=True,exist_ok=True)
        metadata = {'filename':filename,'filesize':payload.filesize,'chunks':payload.chunks}
        (PROJECTS_DIR/p.id/'upload.json').write_text(json.dumps(metadata))
        return {'project_id':p.id,'chunks':payload.chunks}

@app.get('/api/import/chunks/{pid}/status')
def chunk_status(pid:str):
    with SessionLocal() as db: get_project(db,pid)
    folder = PROJECTS_DIR / pid
    info_file = folder/'upload.json'
    if not info_file.exists(): raise AppError('Not a resumable upload')
    info = json.loads(info_file.read_text())
    return {'received':sorted(int(p.stem) for p in (folder/'chunks').glob('*.part')),'chunks':info['chunks']}

@app.put('/api/import/chunks/{pid}/{index}')
async def send_chunk(pid:str,index:int,request:Request):
    with SessionLocal() as db:
        p = get_project(db,pid)
        if p.status != 'uploading': raise AppError('Upload was already completed')
    folder = PROJECTS_DIR/pid
    info = json.loads((folder/'upload.json').read_text())
    if not 0 <= index < info['chunks']:
        raise AppError('Invalid chunk index')
    part = folder/'chunks'/f'{index}.part'
    tmp = part.with_suffix('.tmp')
    size = 0
    try:
        with tmp.open('wb') as stream:
            async for chunk in request.stream():
                size += len(chunk)
                if size > 16*1024*1024:
                    raise AppError('Chunk must not exceed 16 MB')
                stream.write(chunk)
        tmp.replace(part)
    finally:
        tmp.unlink(missing_ok=True)
    return {'received':index,'bytes':size}

@app.post('/api/import/chunks/{pid}/complete')
def complete_chunks(pid:str):
    with SessionLocal() as db:
        p = get_project(db,pid)
        if p.status != 'uploading': raise AppError('Not uploading')
        folder = PROJECTS_DIR/pid
        info = json.loads((folder/'upload.json').read_text())
        media = folder/('source'+Path(info['filename']).suffix.lower())
        chunks = folder/'chunks'
        if any(not (chunks/f'{i}.part').exists() for i in range(info['chunks'])):
            raise AppError('Some upload chunks are missing. Resume the upload before completing.')
        with media.open('wb') as target:
            for i in range(info['chunks']):
                with (chunks/f'{i}.part').open('rb') as incoming:
                    shutil.copyfileobj(incoming,target,1024*1024)
        if media.stat().st_size != info['filesize']:
            media.unlink(missing_ok=True)
            raise AppError('Final file size does not match uploaded file')
        out = finish_upload(p,media,db)
        shutil.rmtree(chunks,ignore_errors=True)
        (folder/'upload.json').unlink(missing_ok=True)
        return out


def safe_public_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise AppError('Only public http/https direct media URLs are allowed')
    if parsed.port and parsed.port not in (80,443):
        raise AppError('Nonstandard URL ports are not supported')
    try:
        addresses = socket.getaddrinfo(parsed.hostname,parsed.port or (443 if parsed.scheme=='https' else 80),type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise AppError('Private, loopback, or internal URLs are not permitted')
    except socket.gaierror as e:
        raise AppError(f'URL hostname could not be resolved: {e}') from e
    return parsed

@app.post('/api/import/url')
def import_url(payload:URLRequest):
    # Direct, publicly accessible media only. No DRM, cookie, login or redirects.
    parsed = safe_public_url(payload.url)
    ext = Path(parsed.path).suffix.lower()
    if ext not in EXTENSIONS:
        raise AppError('Direct URL must end in a supported video extension. Streaming pages/DRM URLs are not supported.')
    import httpx
    with SessionLocal() as db:
        p = Project(id=str(uuid.uuid4()),name=(payload.name or Path(parsed.path).stem)[:220],status='uploading')
        db.add(p);db.commit()
        folder = PROJECTS_DIR/p.id
        folder.mkdir(parents=True,exist_ok=True)
        target = folder/('source'+ext)
        try:
            with httpx.stream('GET',payload.url,timeout=httpx.Timeout(20,read=60),follow_redirects=False,trust_env=False) as stream:
                if stream.status_code != 200: raise AppError(f'Direct URL download failed ({stream.status_code}); redirects are not supported')
                size=0
                with target.open('wb') as output:
                    for part in stream.iter_bytes(chunk_size=1024*1024):
                        size+=len(part)
                        if size>MAX_BYTES: raise AppError('Remote video exceeds 10 GB')
                        output.write(part)
            return finish_upload(p,target,db)
        except Exception:
            db.delete(p);db.commit();shutil.rmtree(folder,ignore_errors=True)
            raise

@app.get('/api/projects/{pid}/video')
def get_video(pid:str):
    with SessionLocal() as db:
        p=get_project(db,pid)
        if not p.filename or not Path(p.filename).is_file(): raise HTTPException(404,detail='Imported video not found')
        return FileResponse(p.filename, media_type='video/mp4', filename=Path(p.filename).name,content_disposition_type='inline')

@app.get('/api/projects/{pid}/segments')
def list_segments(pid:str):
    with SessionLocal() as db:
        get_project(db,pid)
        return [segment_json(s) for s in db.query(Segment).filter_by(project_id=pid).order_by(Segment.start,Segment.id).all()]

@app.post('/api/projects/{pid}/segments')
def add_segment(pid:str,payload:SegmentAdd):
    with SessionLocal() as db:
        p=get_project(db,pid)
        if payload.end<=payload.start or (p.duration and payload.end>p.duration+0.05): raise AppError('Segment start/end must be within the video')
        seq=(db.query(func.max(Segment.seq)).filter_by(project_id=pid).scalar() or 0)+1
        s=Segment(project_id=pid,chunk_index=-1,seq=seq,start=payload.start,end=payload.end,zh=payload.zh,km=payload.km,translation_status='translated' if payload.km else 'pending')
        db.add(s); db.commit()
        return segment_json(s)

@app.patch('/api/projects/{pid}/segments/{sid}')
def update_segment(pid:str,sid:int,payload:SegmentUpdate):
    with SessionLocal() as db:
        p=get_project(db,pid)
        s=db.get(Segment,sid)
        if not s or s.project_id!=pid: raise HTTPException(404,detail='Segment not found')
        new_start=payload.start if payload.start is not None else s.start
        new_end=payload.end if payload.end is not None else s.end
        if new_end<=new_start or (p.duration and new_end>p.duration+0.05): raise AppError('Invalid segment timing')
        source_changed = payload.zh is not None and payload.zh != s.zh
        translation_changed = payload.km is not None and payload.km != s.km
        invalidates = source_changed
        for field in ('zh','km','start','end','voice_speed'):
            new_value = getattr(payload,field)
            if new_value is not None and new_value != getattr(s,field):
                setattr(s,field,new_value)
                if field in ('km','voice_speed'):
                    invalidates=True
        if source_changed and not translation_changed and s.km:
            s.translation_status='needs_review'
        elif payload.km is not None:
            s.translation_status='translated' if payload.km.strip() else 'pending'
        if invalidates:
            s.voice_path=None; s.voice_duration=0; s.voice_status='pending';s.review_note=''
            if s.translation_status == 'needs_review':
                s.review_note='Chinese dialogue changed. Retry translation or update the Khmer line.'
        elif s.voice_path:
            s.voice_status='timing_warning' if s.voice_duration>s.end-s.start+0.035 else 'ready'
        db.commit()
        return segment_json(s)

@app.delete('/api/projects/{pid}/segments/{sid}')
def delete_segment(pid:str,sid:int):
    with SessionLocal() as db:
        get_project(db,pid)
        s=db.get(Segment,sid)
        if not s or s.project_id!=pid: raise HTTPException(404,detail='Segment not found')
        db.delete(s);db.commit()
        return {'deleted':True}

@app.get('/api/projects/{pid}/subtitles.srt')
def export_srt(pid:str,lang:str='km'):
    if lang not in ('zh','km'): raise AppError('Language must be zh or km')
    with SessionLocal() as db:
        get_project(db,pid)
        rows=db.query(Segment).filter_by(project_id=pid).order_by(Segment.start).all()
        return PlainTextResponse(make_srt(rows,lang), media_type='text/plain; charset=utf-8', headers={'Content-Disposition':f'attachment; filename="{pid}-{lang}.srt"'})

@app.post('/api/projects/{pid}/subtitles/import')
async def import_subtitles(pid:str,file:UploadFile=File(...),lang:str='zh'):
    if lang not in ('zh','km'): raise AppError('Language must be zh or km')
    raw=await file.read(2*1024*1024+1)
    if len(raw)>2*1024*1024: raise AppError('SRT file too large')
    text=raw.decode('utf-8-sig',errors='replace').replace('\r\n','\n')
    pattern=r'(?:^|\n)\s*\d+\s*\n\s*(\d\d:\d\d:\d\d[,\.]\d{3})\s*-->\s*(\d\d:\d\d:\d\d[,\.]\d{3})[^\n]*\n(.*?)(?=\n\s*\d+\s*\n\s*\d\d:\d\d:\d\d|\Z)'
    matches=re.findall(pattern,text,re.S)
    if not matches: raise AppError('No valid SRT entries found')
    def to_sec(stamp):
        h,m,s=stamp.replace(',', '.').split(':')
        return int(h)*3600+int(m)*60+float(s)
    with SessionLocal() as db:
        p=get_project(db,pid)
        # zh import creates new segments; km import fills existing by order.
        current=db.query(Segment).filter_by(project_id=pid).order_by(Segment.start).all()
        if lang=='km' and len(current)!=len(matches):
            raise AppError('Khmer SRT requires the same number of rows as existing Chinese segments')
        for index,(start,end,content) in enumerate(matches):
            begin,finish=to_sec(start),to_sec(end)
            if finish<=begin or (p.duration and finish>p.duration+0.05): raise AppError('Subtitle timing exceeds video duration')
            content=content.strip()
            if lang=='zh':
                db.add(Segment(project_id=pid,chunk_index=-1,seq=len(current)+index+1,start=begin,end=finish,zh=content))
            else:
                s=current[index]
                s.km=content;s.translation_status='translated' if content else 'pending';s.voice_path=None;s.voice_status='pending'
        db.commit()
    return {'imported':len(matches)}

@app.post('/api/projects/{pid}/transcribe')
def transcribe(pid:str,options:AIOptions=Body(default=AIOptions())):
    with SessionLocal() as db:
        p=get_project(db,pid)
        if not p.filename: raise AppError('Import a video first')
    return {'job':launch('transcribe',pid,options.model_dump()).id}

@app.post('/api/projects/{pid}/dub')
def dub_movie(pid:str, options:MovieOptions=Body(default=MovieOptions())):
    with SessionLocal() as db:
        if not get_project(db,pid).filename:
            raise AppError('Import a movie first')
    return {'job':launch('dub_movie',pid,options.model_dump()).id}

@app.post('/api/projects/{pid}/translate')
def translate(pid:str,options:AIOptions=Body(default=AIOptions())):
    with SessionLocal() as db:
        get_project(db,pid)
        if not db.query(Segment).filter_by(project_id=pid).first(): raise AppError('Transcribe or import Chinese subtitles first')
    return {'job':launch('translate',pid,options.model_dump()).id}

@app.post('/api/projects/{pid}/translate/segment')
def translate_one(pid:str, segment_id:int=Body(embed=True), translator:Literal['nllb','nllb-large']=Body(default='nllb')):
    with SessionLocal() as db:
        get_project(db,pid)
        seg=db.get(Segment,segment_id)
        if not seg or seg.project_id!=pid: raise HTTPException(404,detail='Segment not found')
    return {'job':launch('translate',pid,{'segment_ids':[segment_id],'overwrite':True,'translator':translator}).id}

@app.post('/api/projects/{pid}/voices/generate')
def voices(pid:str,options:AIOptions=Body(default=AIOptions())):
    with SessionLocal() as db:
        get_project(db,pid)
        if not db.query(Segment).filter(Segment.project_id==pid,Segment.km!='').first():raise AppError('Translate the dialogue into Khmer first')
    return {'job':launch('voices',pid,options.model_dump()).id}

@app.post('/api/projects/{pid}/voices/regenerate')
def regen_voice(pid:str,segment_id:int=Body(embed=True)):
    with SessionLocal() as db:
        get_project(db,pid)
        seg=db.get(Segment,segment_id)
        if not seg or seg.project_id!=pid:raise HTTPException(404,detail='Segment not found')
    return {'job':launch('voices',pid,{'segment_ids':[segment_id],'overwrite':True}).id}

@app.get('/api/projects/{pid}/voices')
def voices_list(pid:str):
    with SessionLocal() as db:
        get_project(db,pid)
        return [segment_json(s) for s in db.query(Segment).filter_by(project_id=pid).order_by(Segment.start).all()]

@app.get('/api/segments/{sid}/voice')
def play_voice(sid:int):
    with SessionLocal() as db:
        seg=db.get(Segment,sid)
        if not seg or not seg.voice_path or not Path(seg.voice_path).is_file():raise HTTPException(404,detail='Voice not yet generated')
        return FileResponse(seg.voice_path,media_type='audio/wav')

@app.post('/api/projects/{pid}/export')
def export_video(pid:str,options:ExportOptions):
    if options.audio_mode!='voice_only': raise AppError('Background audio separation is not implemented. Khmer Voice Only is currently supported.')
    if options.resolution not in ('original','480p','720p','1080p') or options.quality not in ('fast','balanced','high'):
        raise AppError('Unknown export preset')
    with SessionLocal() as db:
        get_project(db,pid)
    return {'job':launch('export',pid,options.model_dump()).id}

@app.get('/api/projects/{pid}/exports')
def list_exports(pid:str):
    with SessionLocal() as db:
        get_project(db,pid)
        exports=db.query(Export).filter_by(project_id=pid).order_by(Export.created_at.desc()).all()
        return [{'id':e.id,'filename':Path(e.path).name,'size':Path(e.path).stat().st_size if Path(e.path).exists() else 0,'url':f'/api/exports/{e.id}/video','created_at':e.created_at} for e in exports]

@app.get('/api/exports/{eid}/video')
def output_video(eid:str):
    with SessionLocal() as db:
        e=db.get(Export,eid)
        if not e or not Path(e.path).is_file():raise HTTPException(404,detail='Rendered video not found')
        return FileResponse(e.path,media_type='video/mp4',filename=Path(e.path).name,content_disposition_type='inline')

@app.get('/api/system/jobs')
def recent_jobs():
    with SessionLocal() as db:
        return [job_json(j) for j in db.query(Job).order_by(Job.created_at.desc()).limit(20).all()]


def job_json(j):
    return {'id':j.id,'project_id':j.project_id,'kind':j.kind,'status':j.status,'done':j.done,'total':j.total,'failed':j.failed,'message':j.message,'error':j.error,'output':j.output,'created_at':j.created_at}

@app.get('/api/system/jobs/{jid}')
def job_status(jid:str):
    with SessionLocal() as db:
        job=db.get(Job,jid)
        if not job:raise HTTPException(404,detail='Job not found')
        return job_json(job)

@app.post('/api/system/jobs/{jid}/cancel')
def cancel_job(jid:str):
    with SessionLocal() as db:
        job=db.get(Job,jid)
        if not job:raise HTTPException(404,detail='Job not found')
        if job.status in ('running','queued'):
            job.status='cancel_requested';job.message='Cancellation requested';db.commit()
        return job_json(job)

@app.get('/api/system/models')
def models():
    return model_catalog()

@app.post('/api/system/models/download')
def install_model(req:ModelRequest):
    if req.model_id not in ('whisper-tiny','whisper-base','whisper-small','nllb','nllb-large','mms'):
        raise AppError('Unknown model')
    return {'job':launch('download_model',None,{'model_id':req.model_id}).id}

@app.get('/api/system/status')
def system_status():
    stats={'storage_bytes':sum(p.stat().st_size for p in STORAGE.rglob('*') if p.is_file()),'disk_free_bytes':shutil.disk_usage(STORAGE).free,'cpu_percent':None,'ram_percent':None,'gpu':'Not configured','ffmpeg':shutil.which('ffmpeg') is not None,'ffprobe':shutil.which('ffprobe') is not None,'models':model_catalog()}
    try:
        import psutil
        stats['cpu_percent']=psutil.cpu_percent(interval=None)
        stats['ram_percent']=psutil.virtual_memory().percent
    except ImportError:
        pass
    try:
        output=subprocess.run(['nvidia-smi','--query-gpu=name','--format=csv,noheader'],capture_output=True,text=True,timeout=3)
        if output.returncode==0:stats['gpu']=output.stdout.strip()
    except (FileNotFoundError,subprocess.TimeoutExpired):pass
    with SessionLocal() as db:
        stats['active_jobs']=db.query(Job).filter(Job.status.in_(['running','queued','cancel_requested'])).count()
    return stats
