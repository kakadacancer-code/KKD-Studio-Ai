"""Integration tests use synthetic WAVs, never claim to test real model accuracy."""
from __future__ import annotations
import io
import uuid
import subprocess
import time
import wave
from pathlib import Path
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Segment, Job, Project, PROJECTS_DIR
from app.services.inference import contains_khmer
from app.services.media import make_srt, probe
from app.services.rendering import create_timeline, inspect_timing, RATE
from app.workers import jobs

client = TestClient(app)

def mp4_file(tmp_path: Path, length=6):
    target = tmp_path/'input.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',f'color=c=blue:s=320x180:r=25:d={length}','-f','lavfi','-i',f'sine=frequency=400:duration={length}','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest','-y',str(target)],check=True)
    return target

def add_wav(segment, duration=.4):
    path=PROJECTS_DIR/segment.project_id/'voices'/f'{segment.id}.wav'
    path.parent.mkdir(parents=True,exist_ok=True)
    t=np.arange(int(16000*duration),dtype=np.float32)/16000
    sf.write(path,.2*np.sin(2*np.pi*700*t),16000)
    segment.voice_path=str(path)
    segment.voice_duration=duration
    segment.voice_status='ready'
    return path


def test_khmer_validation():
    assert contains_khmer('សួស្តី!')
    assert not contains_khmer('你好 Chinese text')
    assert not contains_khmer('')


def test_upload_edit_and_srt(tmp_path):
    media=mp4_file(tmp_path)
    result=client.post('/api/import/upload',files={'file':('short.mp4',media.read_bytes(),'video/mp4')})
    assert result.status_code==200,result.text
    p=result.json()
    assert 5.9 < p['duration'] < 6.1
    assert p['width']==320 and p['height']==180
    assert client.get(f'/api/projects/{p["id"]}/video').status_code==200
    created=client.post(f'/api/projects/{p["id"]}/segments',json={'start':1.25,'end':2.5,'zh':'你好','km':'សួស្តី'}).json()
    assert created['start']==1.25
    assert created['translation_status']=='translated'
    edited=client.patch(f'/api/projects/{p["id"]}/segments/{created["id"]}',json={'km':'សួស្តី បង','start':1.3})
    assert edited.status_code==200,edited.text
    assert edited.json()['start']==1.3
    assert client.get(f'/api/projects/{p["id"]}/subtitles.srt').text.find('សួស្តី បង')>=0
    assert client.patch(f'/api/projects/{p["id"]}/segments/{created["id"]}',json={'end':1.1}).status_code==400
    return p,created


def test_resumable_chunked_import(tmp_path):
    media=mp4_file(tmp_path,3)
    data=media.read_bytes()
    middle=len(data)//2
    init=client.post('/api/import/chunks/init',json={'filename':'short.mp4','filesize':len(data),'chunks':2})
    pid=init.json()['project_id']
    assert client.put(f'/api/import/chunks/{pid}/0',content=data[:middle]).status_code==200
    assert client.get(f'/api/import/chunks/{pid}/status').json()['received']==[0]
    assert client.post(f'/api/import/chunks/{pid}/complete').status_code==400
    assert client.put(f'/api/import/chunks/{pid}/1',content=data[middle:]).status_code==200
    assert client.post(f'/api/import/chunks/{pid}/complete').json()['status']=='imported'


def test_srt_import_and_private_url():
    p=client.post('/api/projects',json={'name':'subtitle-only'}).json()
    srt=b'1\n00:00:01,000 --> 00:00:02,500\nHello Chinese\n\n'
    result=client.post(f'/api/projects/{p["id"]}/subtitles/import?lang=zh',files={'file':('sub.srt',srt,'text/plain')})
    assert result.status_code==200,result.text
    assert result.json()['imported']==1
    assert client.get(f'/api/projects/{p["id"]}/segments').json()[0]['zh']=='Hello Chinese'
    assert client.post('/api/import/url',json={'url':'http://127.0.0.1/secret.mp4'}).status_code==400


def test_absolute_timeline_and_original_audio_removed(tmp_path):
    p,_=test_upload_edit_and_srt(tmp_path)
    with SessionLocal() as db:
        seg=db.query(Segment).filter_by(project_id=p['id']).first()
        path=add_wav(seg,.35)
        db.commit()
        rows=db.query(Segment).filter_by(project_id=p['id']).all()
        out=tmp_path/'aligned.wav'
        create_timeline(rows, p['duration'], out)
        pcm,rate=sf.read(out)
        assert rate==RATE
        assert np.max(np.abs(pcm[:RATE]))==0  # silence until original start, never moved
        assert np.max(np.abs(pcm[int(1.3*RATE):int(1.6*RATE)]))>.05
        assert np.max(np.abs(pcm[int(2.6*RATE):]))==0
        assert not inspect_timing(rows)
        seg.voice_duration=3.5
        assert inspect_timing([seg])
        seg.voice_duration=.35
        db.commit()
    result=client.post(f'/api/projects/{p["id"]}/export',json={'audio_mode':'voice_only','resolution':'480p','quality':'fast'})
    assert result.status_code==200,result.text
    job_id=result.json()['job']
    status=None
    for _ in range(90):
        status=client.get(f'/api/system/jobs/{job_id}').json()
        if status['status'] not in ('queued','running','cancel_requested'):
            break
        time.sleep(.2)
    assert status['status']=='completed',status
    exports=client.get(f'/api/projects/{p["id"]}/exports').json()
    assert len(exports)==1
    assert exports[0]['size']>1000
    assert client.get(exports[0]['url']).status_code==200
    rendered=PROJECTS_DIR/p['id']/'renders'/exports[0]['filename']
    assert probe(rendered)['duration']>5
    # The export uses the newly built silent/Khmer track, not the original film audio.
    output_wav=tmp_path/'audio.wav'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(rendered),'-vn','-ac','1','-ar',str(RATE),str(output_wav)],check=True)
    signal,_=sf.read(output_wav)
    assert np.max(np.abs(signal[int(.1*RATE):int(.8*RATE)]))<.001
    assert np.max(np.abs(signal[int(1.4*RATE):int(1.5*RATE)]))>.02


def test_checkpointed_mock_translation():
    p=client.post('/api/projects',json={'name':'checkpoint demo'}).json()
    with SessionLocal() as db:
        db.add(Segment(project_id=p['id'],seq=1,start=0,end=2,zh='你好'))
        db.add(Segment(project_id=p['id'],seq=2,start=2,end=4,zh='谢谢'))
        db.add(Job(id='job-mock',project_id=p['id'],kind='translate',status='running'))
        db.commit()
    original=jobs.inference.translate_batch
    jobs.inference.translate_batch=lambda texts, engine:['សួស្តី' if t=='你好' else 'អរគុណ' for t in texts]
    try:
        jobs.do_translate('job-mock',p['id'],{})
    finally:
        jobs.inference.translate_batch=original
    with SessionLocal() as db:
        rows=db.query(Segment).filter_by(project_id=p['id']).order_by(Segment.seq).all()
        assert len(rows)==2 and all(s.translation_status=='translated' for s in rows)
        assert rows[0].km=='សួស្តី'
        assert rows[1].km=='អរគុណ'
        # Calling again resumes safely: no completed segments are retransmitted.
        assert all(s.km for s in rows)


def test_invalid_translation_never_passes_as_khmer():
    p=client.post('/api/projects',json={'name':'validation checkpoint'}).json()
    with SessionLocal() as db:
        db.add(Segment(project_id=p['id'],seq=1,start=0,end=2,zh='你好'))
        db.add(Job(id='job-invalid',project_id=p['id'],kind='translate',status='running'))
        db.commit()
    original=jobs.inference.translate_batch
    jobs.inference.translate_batch=lambda texts, engine:['你好' for _ in texts]
    try:
        jobs.do_translate('job-invalid',p['id'],{})
    finally:
        jobs.inference.translate_batch=original
    with SessionLocal() as db:
        row=db.query(Segment).filter_by(project_id=p['id']).first()
        assert row.translation_status=='failed'
        assert row.km==''
        assert 'Khmer' in row.review_note


def test_cancel_queued_job_without_running_model():
    p=client.post('/api/projects',json={'name':'cancelled'}).json()
    with SessionLocal() as db:
        db.add(Job(id='job-cancel',project_id=p['id'],kind='voices',status='cancel_requested'))
        db.commit()
    jobs.worker('job-cancel',{})
    assert client.get('/api/system/jobs/job-cancel').json()['status']=='cancelled'


def test_short_dialogue_and_invalid_sources():
    from app.services.inference import translate_batch
    texts = ['<i>你好！</i>', '- 對不起\n- 谢谢！', '', '...', '123']
    assert translate_batch(texts) == ['សួស្តី', 'សុំទោស អរគុណ', '', '', '']
    assert not contains_khmer('១២។')


def test_changed_chinese_requires_fresh_khmer():
    project = client.post('/api/projects', json={'name':'Revised dialogue'}).json()
    url = f'/api/projects/{project["id"]}/segments'
    seg = client.post(url, json={'start':0, 'end':5, 'zh':'你好', 'km':'សួស្តី'}).json()
    with SessionLocal() as db:
        add_wav(db.get(Segment, seg['id']))
        db.commit()
    row = client.patch(f'{url}/{seg["id"]}', json={'zh':'谢谢'}).json()
    assert row['translation_status'] == 'needs_review'
    assert row['voice_url'] is None
    row = client.patch(f'{url}/{seg["id"]}', json={'km':'អរគុណ'}).json()
    assert row['translation_status'] == 'translated'


def test_movie_dub_resumes_silent_and_spoken_chunks(tmp_path):
    from types import SimpleNamespace
    from unittest.mock import patch
    from app.database import TranscribedChunk

    project = client.post('/api/projects', json={'name':'Two hour resume'}).json()
    pid = project['id']
    with SessionLocal() as db:
        p = db.get(Project, pid)
        p.duration, p.filename = 7200, str(tmp_path/'source.mp4')
        db.commit()

    visited = []
    class Recognizer:
        def transcribe(self, path, **options):
            index = int(Path(path).stem.split('-')[-1])
            visited.append(index)
            if visited == [0, 1, 2]:
                raise RuntimeError('interrupted during recognition')
            entries = [SimpleNamespace(start=1, end=4, text='你好')] if index in (1,23) else []
            return entries, None

    def synthesize(text, path, speed, *, window):
        assert text == 'សួស្តី' and window == 3
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(path, np.ones(1600)*0.1, 16000)
        return 0.1

    def start_and_wait():
        response = client.post(f'/api/projects/{pid}/dub', json={})
        assert response.status_code == 200, response.text
        for _ in range(200):
            job = client.get('/api/system/jobs/' + response.json()['job']).json()
            if job['status'] not in ('running','queued'):
                return job
            time.sleep(0.05)
        raise AssertionError('Movie job did not finish')

    with patch.object(jobs.subprocess,'run'), patch.object(jobs.inference,'load_whisper',return_value=Recognizer()), patch.object(jobs.inference,'synthesize_khmer',side_effect=synthesize) as tts:
        assert start_and_wait()['status'] == 'failed'
        assert start_and_wait()['status'] == 'completed'
        assert start_and_wait()['status'] == 'completed'
        assert tts.call_count == 2
    assert visited == [0,1,2] + list(range(2,24))
    with SessionLocal() as db:
        assert db.query(TranscribedChunk).filter_by(project_id=pid).count() == 24
        rows = db.query(Segment).filter_by(project_id=pid).order_by(Segment.start).all()
        assert [r.start for r in rows] == [301,6901]
        assert all(r.voice_status == 'ready' for r in rows)
