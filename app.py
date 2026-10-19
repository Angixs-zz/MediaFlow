import os
import re
import uuid
from pathlib import Path
from threading import Thread, Lock
from urllib.parse import urlparse

import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DOWNLOADS = Path(os.environ.get('MEDIAFLOW_DOWNLOAD_DIR', ROOT / 'downloads')).resolve()
DOWNLOADS.mkdir(parents=True, exist_ok=True)
app = FastAPI(title='MediaFlow', version='0.1.0')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
JOBS = {}
LOCK = Lock()
ALLOWED_HOSTS = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be'}

class DownloadRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    mode: str = Field(pattern='^(video|audio)$')
    quality: str = Field(pattern='^(best|1080|720|480)$')

def check_url(value: str):
    p = urlparse(value)
    if p.scheme != 'https' or (p.hostname or '').lower() not in ALLOWED_HOSTS:
        raise HTTPException(400, 'Solo se admiten enlaces HTTPS de YouTube.')
    if p.username or p.password or p.port:
        raise HTTPException(400, 'Enlace no válido.')
    return value

def update(job_id, **fields):
    with LOCK:
        JOBS[job_id].update(fields)

def worker(job_id, req):
    folder = DOWNLOADS / job_id
    folder.mkdir(parents=True, exist_ok=True)
    def progress(data):
        if data.get('status') == 'downloading':
            total = data.get('total_bytes') or data.get('total_bytes_estimate') or 0
            downloaded = data.get('downloaded_bytes') or 0
            update(job_id, status='downloading', progress=round(downloaded / total * 100, 1) if total else 0)
        elif data.get('status') == 'finished':
            update(job_id, status='processing', progress=100)
    limit = {'best': None, '1080': 1080, '720': 720, '480': 480}[req.quality]
    fmt = ('bestaudio/best' if req.mode == 'audio' else (f'bestvideo[height<={limit}]+bestaudio/best[height<={limit}]' if limit else 'bestvideo+bestaudio/best'))
    opts = {
        'format': fmt, 'outtmpl': str(folder / '%(title).180B [%(id)s].%(ext)s'),
        'noplaylist': True, 'progress_hooks': [progress], 'quiet': True,
        'windowsfilenames': True, 'restrictfilenames': False,
        'socket_timeout': 20, 'retries': 3,
    }
    if req.mode == 'audio':
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    else:
        opts['merge_output_format'] = 'mp4'
    try:
        update(job_id, status='downloading')
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([req.url])
        candidates = [p for p in folder.iterdir() if p.is_file() and not p.name.endswith(('.part', '.ytdl'))]
        if not candidates:
            raise RuntimeError('No se encontró el archivo final.')
        file = max(candidates, key=lambda p: p.stat().st_size)
        update(job_id, status='completed', progress=100, filename=file.name)
    except Exception as exc:
        update(job_id, status='failed', error=str(exc)[:350])

@app.get('/')
def home():
    return FileResponse(ROOT / 'static' / 'index.html')

@app.post('/api/download')
def start(req: DownloadRequest):
    check_url(req.url)
    job_id = uuid.uuid4().hex
    with LOCK:
        JOBS[job_id] = {'status': 'queued', 'progress': 0, 'filename': None, 'error': None}
    Thread(target=worker, args=(job_id, req), daemon=True).start()
    return {'job_id': job_id}

@app.get('/api/jobs/{job_id}')
def status(job_id: str):
    with LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(404, 'Trabajo no encontrado.')
        return dict(job)

@app.get('/api/files/{job_id}')
def file(job_id: str):
    with LOCK:
        job = JOBS.get(job_id)
        if not job or job['status'] != 'completed':
            raise HTTPException(404, 'Archivo no disponible.')
        filename = job['filename']
    path = DOWNLOADS / job_id / filename
    if not path.is_file():
        raise HTTPException(404, 'Archivo no encontrado.')
    return FileResponse(path, filename=filename, media_type='application/octet-stream')
