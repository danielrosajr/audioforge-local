"""FIFO local de processamento. Um job de cada vez para poupar CPU/RAM.

Estados são protegidos por lock, e cópias de uploads são mantidas até o fim.
A fila em andamento não é restaurada após reiniciar; resultados completos ficam
no histórico normal do AudioForge.
"""
from __future__ import annotations

import re
import shutil
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from audioforge import core


@dataclass
class Job:
    id: str
    title: str
    url: str
    local_file: str | None
    exports: list[str]
    separate: bool
    transcribe: bool
    model: str
    language: str
    mp3_bitrate: int
    video_height: int | None
    state: str = 'aguardando'
    message: str = 'Na fila'
    progress: int | None = None
    created: float = field(default_factory=time.time)
    started: float | None = None
    ended: float | None = None
    result: dict | None = None
    logs: list[str] = field(default_factory=list)
    cancel: threading.Event = field(default_factory=threading.Event, repr=False)
    staging: Path | None = None


class ProcessingQueue:
    MAX_JOBS = 30

    def __init__(self, staging_root: Path | None = None, processor: Callable = core.process):
        self.root = staging_root or (core.DATA_DIR / '.fila-temporaria')
        self.processor = processor
        self._items: dict[str, Job] = {}
        self._pending: deque[str] = deque()
        self._lock = threading.RLock()
        self._signal = threading.Condition(self._lock)
        self._stop = False
        self._worker = threading.Thread(target=self._loop, name='audioforge-fila', daemon=True)
        self._worker.start()

    def enqueue(self, url, local_file, exports, separate, transcribe, model, language,
                mp3_bitrate=192, video_height=None) -> str:
        mode, value = core.validate_source(url, local_file)
        formats = core.normalize_exports(exports)
        if not formats and not separate and not transcribe:
            raise core.AudioForgeError('Selecione pelo menos uma exportação ou ferramenta de IA.')
        if mode == 'arquivo' and 'mp4' in formats and Path(value).suffix.lower() not in core.VIDEO_EXTENSIONS:
            raise core.AudioForgeError('MP4 exige uma entrada com vídeo.')
        if model not in {'tiny','base','small'} or language not in {'auto','pt','en','es'}:
            raise core.AudioForgeError('Opções de transcrição inválidas.')
        bitrate = int(mp3_bitrate)
        if bitrate not in {128,192,320}:
            raise core.AudioForgeError('Qualidade MP3 inválida.')
        height = None if video_height in (None, 'original') else int(video_height)
        if height not in (None,720,1080):
            raise core.AudioForgeError('Qualidade de vídeo inválida.')
        with self._signal:
            busy = sum(job.state in {'aguardando','processando','cancelando'} for job in self._items.values())
            if busy >= self.MAX_JOBS:
                raise core.AudioForgeError('Fila cheia (30 trabalhos). Aguarde ou cancele algum item.')
            id_ = uuid.uuid4().hex[:8]
            staging = None
            saved_file = None
            try:
                if mode == 'arquivo':
                    # A fila precisa de uma cópia estável do arquivo enviado ao Gradio.
                    staging = self.root / id_
                    staging.mkdir(parents=True, exist_ok=False)
                    saved = staging / ('origem' + Path(value).suffix.lower())
                    shutil.copy2(value, saved)
                    saved_file = str(saved)
                job = Job(id_, Path(value).name if mode == 'arquivo' else value[:75],
                          value if mode == 'url' else '', saved_file, formats, bool(separate),
                          bool(transcribe), model, language, bitrate, height, staging=staging)
                self._items[id_] = job
                self._pending.append(id_)
                self._signal.notify()
                return id_
            except Exception:
                if staging:
                    shutil.rmtree(staging, ignore_errors=True)
                raise

    def _log(self, id_: str, message: str):
        with self._lock:
            job = self._items[id_]
            job.message = str(message)[:240]
            job.logs.append(job.message)
            job.logs[:] = job.logs[-60:]
            # Porcentagem exibida apenas quando yt-dlp informa progresso real.
            m = re.search(r'Baixando mídia:\s*(\d+)%', message)
            if m:
                job.progress = min(100, int(m.group(1)))

    def _loop(self):
        while True:
            with self._signal:
                while not self._pending and not self._stop:
                    self._signal.wait()
                if self._stop:
                    return
                id_ = self._pending.popleft()
                job = self._items[id_]
                if job.cancel.is_set():
                    job.state, job.message, job.ended = 'cancelado', 'Cancelado antes de iniciar', time.time()
                    self._cleanup(job)
                    continue
                job.state, job.started, job.message = 'processando', time.time(), 'Iniciando…'
            try:
                result = self.processor(
                    job.url, job.local_file, job.separate, job.transcribe,
                    job.model, job.language, lambda msg: self._log(id_, msg),
                    job.exports, cancel_event=job.cancel,
                    mp3_bitrate=job.mp3_bitrate, video_height=job.video_height,
                )
                if job.cancel.is_set():
                    raise core.ProcessingCancelled('Cancelado após finalizar etapa.')
                with self._lock:
                    job.result, job.state, job.message = result, 'concluído', 'Arquivos prontos'
                    job.progress = 100
            except core.ProcessingCancelled:
                with self._lock:
                    job.state, job.message = 'cancelado', 'Cancelado pelo usuário'
            except Exception as exc:
                with self._lock:
                    if job.cancel.is_set():
                        job.state, job.message = 'cancelado', 'Cancelado pelo usuário'
                    else:
                        job.state, job.message = 'erro', str(exc)[:240]
                    job.logs.append(job.message)
            finally:
                with self._lock:
                    job.ended = time.time()
                self._cleanup(job)

    def _cleanup(self, job: Job):
        if job.staging:
            shutil.rmtree(job.staging, ignore_errors=True)

    def cancel_job(self, id_: str) -> str:
        with self._signal:
            job = self._items.get((id_ or '').strip())
            if not job:
                raise core.AudioForgeError('Selecione um trabalho da fila.')
            if job.state == 'aguardando':
                job.cancel.set()
                try: self._pending.remove(job.id)
                except ValueError: pass
                job.state, job.message, job.ended = 'cancelado', 'Cancelado antes de iniciar', time.time()
                self._cleanup(job)
                return f'Item {job.id} cancelado antes de iniciar.'
            if job.state == 'processando':
                job.state, job.message = 'cancelando', 'Interrompendo com segurança…'
                job.cancel.set()
                return f'Solicitação de cancelamento enviada para {job.id}. Aguarde a etapa encerrar.'
            if job.state == 'cancelando':
                return 'O cancelamento já foi solicitado.'
            return f'Esse item já está {job.state}.'

    def clear_finished(self) -> int:
        with self._lock:
            ids = [k for k,v in self._items.items() if v.state in {'concluído','erro','cancelado'}]
            for k in ids: del self._items[k]
            return len(ids)

    def snapshot(self) -> list[dict]:
        with self._lock:
            jobs = list(self._items.values())
            return [dict(id=j.id, title=j.title, state=j.state, message=j.message,
                         progress=j.progress, created=j.created, started=j.started,
                         ended=j.ended, files=len(j.result.get('files', [])) if j.result else 0)
                    for j in reversed(jobs)]

    def get_result(self, id_: str) -> dict:
        with self._lock:
            job = self._items.get(id_)
            if not job or not job.result:
                raise core.AudioForgeError('Esse trabalho ainda não foi concluído.')
            return dict(job.result)

    def log_for(self, id_: str) -> str:
        with self._lock:
            job = self._items.get(id_)
            return '\n'.join(job.logs[-35:]) if job else ''

    def busy_count(self):
        with self._lock:
            return sum(j.state in {'aguardando', 'processando', 'cancelando'} for j in self._items.values())

    def stop_if_idle(self) -> bool:
        with self._signal:
            if self.busy_count():
                return False
            self._stop = True
            self._signal.notify_all()
            return True
