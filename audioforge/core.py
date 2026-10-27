"""Motor local: downloads MP3/MP4/WAV, Demucs, Whisper e histórico."""

from __future__ import annotations

import json
import os
import re
import signal
import queue
import time
import shutil
import subprocess
import sys
import threading
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse


DATA_DIR = Path(os.environ.get("AUDIOFORGE_HOME", str(Path.home() / "Downloads" / "AudioForge-Local"))).expanduser()
HISTORY_FILE = DATA_DIR / "historico.json"
ALLOWED_EXTENSIONS = {
    ".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma",
    ".mp4", ".mkv", ".mov", ".webm", ".avi", ".mpeg", ".mpg", ".m4v",
}
StatusCallback = Callable[[str], None]
_lock = threading.Lock()


class AudioForgeError(Exception):
    """Falha esperada que pode ser mostrada na interface."""

class ProcessingCancelled(AudioForgeError):
    """O usuário solicitou cancelamento; não gravar resultado no histórico."""

_job_context = threading.local()

def _check_cancel():
    event = getattr(_job_context, 'cancel_event', None)
    if event is not None and event.is_set():
        raise ProcessingCancelled('Processamento cancelado pelo usuário.')

def _bitrate() -> int:
    return getattr(_job_context, 'mp3_bitrate', 192)

def _height() -> int | None:
    return getattr(_job_context, 'video_height', None)


def slug(text: str, max_length: int = 70) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9._ -]", "", text).strip(" ._-")
    return re.sub(r"[\s_]+", "-", text)[:max_length].strip("-.") or "audio"


def validate_source(url: str, local_file: str | None) -> tuple[str, str]:
    url = (url or "").strip()
    if bool(url) == bool(local_file):
        raise AudioForgeError("Informe um link OU selecione um arquivo (não os dois).")
    if url:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise AudioForgeError("Informe um link HTTP/HTTPS válido.")
        # Apenas links do YouTube na v0.1; outros links podem exigir cookies,
        # sessões ou autorizações específicas que não são tratadas aqui.
        host = (parsed.hostname or "").lower()
        accepted = host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}
        if not accepted:
            raise AudioForgeError("Nesta versão, a entrada por URL aceita links do YouTube. Para outros serviços, envie um arquivo local.")
        return "url", url
    file = Path(str(local_file))
    if not file.is_file():
        raise AudioForgeError("O arquivo selecionado não existe mais. Envie novamente.")
    if file.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise AudioForgeError(f"Formato não suportado: {file.suffix}. Envie áudio ou vídeo comum.")
    return "arquivo", str(file)


def run_command(command: list[str], status: StatusCallback, *, cwd: Path | None = None) -> None:
    """Acompanha stdout sem bloquear; cancelamento encerra subprocessos filhos.

    FFmpeg/Demucs herdam grupo de processo próprio no Linux, permitindo encerrar
    conversões longas sem matar o servidor do aplicativo.
    """
    _check_cancel()
    try:
        proc = subprocess.Popen(
            command, cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', bufsize=1,
            stdin=subprocess.DEVNULL, start_new_session=(os.name == 'posix'),
        )
    except FileNotFoundError as exc:
        raise AudioForgeError(f'Dependência não encontrada: {command[0]}. Execute o instalador.') from exc
    lines: queue.Queue[str] = queue.Queue()
    last_lines: list[str] = []
    def drain():
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                lines.put(line)
        finally:
            proc.stdout.close()
    reader = threading.Thread(target=drain, name='ffmpeg-log', daemon=True)
    reader.start()
    try:
        while proc.poll() is None or not lines.empty() or reader.is_alive():
            if getattr(_job_context, 'cancel_event', None) is not None and _job_context.cancel_event.is_set():
                if os.name == 'posix':
                    os.killpg(proc.pid, signal.SIGTERM)
                else:
                    proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    if os.name == 'posix':
                        os.killpg(proc.pid, signal.SIGKILL)
                    else:
                        proc.kill()
                    proc.wait(timeout=3)
                raise ProcessingCancelled('Operação cancelada.')
            try: line = lines.get(timeout=0.15).strip()
            except queue.Empty: continue
            if line:
                last_lines.append(line)
                last_lines[:] = last_lines[-15:]
                if any(word in line.lower() for word in ('error','warning','track','100%','download','model')):
                    status(line[:210])
        code = proc.wait()
        _check_cancel()
        if code:
            raise AudioForgeError('Processo externo falhou. Detalhes: ' + ' | '.join(last_lines[-4:])[-550:])
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()

def convert_to_wav(source: Path, destination: Path, status: StatusCallback) -> None:
    if shutil.which("ffmpeg") is None:
        raise AudioForgeError("FFmpeg não foi encontrado. Rode ./install.sh para instalá-lo.")
    if source.suffix.lower() == ".wav":
        shutil.copy2(source, destination)
        return
    status("Convertendo áudio para WAV (formato sem perda na exportação)...")
    run_command([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(source),
        "-map", "0:a:0", "-vn", "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(destination),
    ], status)
    if not destination.is_file():
        raise AudioForgeError("O FFmpeg não conseguiu extrair uma faixa de áudio deste arquivo.")


def wav_to_mp3(source: Path, destination: Path, status: StatusCallback) -> None:
    run_command([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(source),
        "-codec:a", "libmp3lame", "-b:a", f"{_bitrate()}k", str(destination),
    ], status)


def download_youtube_audio(url: str, job_dir: Path, status: StatusCallback) -> tuple[Path, str]:
    """Preserva a abordagem fornecida pelo autor: YoutubeDL + FFmpegExtractAudio WAV."""
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise AudioForgeError("yt-dlp não instalado. Execute ./install.sh.") from exc
    if shutil.which("ffmpeg") is None:
        raise AudioForgeError("FFmpeg não encontrado. Execute ./install.sh.")

    last_progress = [-1]

    def progress_hook(data: dict) -> None:
        _check_cancel()
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            loaded = data.get("downloaded_bytes", 0)
            if total:
                percentage = int(loaded / total * 100)
                if percentage // 10 != last_progress[0] // 10:
                    last_progress[0] = percentage
                    status(f"Baixando mídia: {percentage}%")
        elif data.get("status") == "finished":
            status("Download concluído. Extraindo áudio WAV...")

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(job_dir / "original.%(ext)s"),
        "noplaylist": True,
        "overwrites": True,
        "quiet": True,
        "no_warnings": False,
        "retries": 2,
        "fragment_retries": 2,
        "progress_hooks": [progress_hook],
        "socket_timeout": 15,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
    }
    status("Conectando ao YouTube com yt-dlp...")
    try:
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
    except ProcessingCancelled:
        raise
    except Exception as exc:
        raise AudioForgeError(
            "Falha ao obter áudio da URL. O YouTube pode ter restringido o acesso; "
            "verifique o link, atualize o yt-dlp ou envie um arquivo próprio. "
            f"Detalhe: {str(exc)[:250]}"
        ) from exc
    if not info:
        raise AudioForgeError("Não foi possível ler os metadados do vídeo.")
    output = job_dir / "original.wav"
    if not output.is_file():
        matches = list(job_dir.glob("original*.wav"))
        if not matches:
            raise AudioForgeError("O download não gerou WAV. Verifique a instalação do FFmpeg.")
        output = matches[0]
    return output, str(info.get("title") or "Vídeo do YouTube")


VALID_EXPORTS = {"wav", "mp3", "mp4"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".mpeg", ".mpg", ".m4v"}


def normalize_exports(exports: list[str] | None) -> list[str]:
    """Não permite valores inesperados vindos do formulário web."""
    if exports is None:  # Mantém compatibilidade com chamadas da v0.1.0.
        return ["wav"]
    if not isinstance(exports, list) or any(not isinstance(x, str) or x not in VALID_EXPORTS for x in exports):
        raise AudioForgeError("Selecione formatos válidos: WAV, MP3 e/ou MP4.")
    return [fmt for fmt in ("wav", "mp3", "mp4") if fmt in exports]


def media_to_mp3(source: Path, destination: Path, status: StatusCallback) -> None:
    """MP3 192 kbps direto da origem, sem criar WAV intermediário desnecessário."""
    if source.resolve() == destination.resolve():
        return
    if source.suffix.lower() == ".mp3":
        shutil.copy2(source, destination)
    else:
        status(f"Convertendo áudio para MP3 ({_bitrate()} kbps)...")
        run_command([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-i", str(source), "-map", "0:a:0", "-vn", "-c:a", "libmp3lame", "-b:a", f"{_bitrate()}k",
            str(destination),
        ], status)
    if not destination.is_file() or destination.stat().st_size == 0:
        raise AudioForgeError("Não foi possível gerar o MP3. A origem pode não ter áudio.")


def convert_to_mp4(source: Path, destination: Path, status: StatusCallback) -> None:
    """Conserva H.264/AAC quando possível; recodifica mídia incompatível."""
    if source.resolve() == destination.resolve():
        return
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise AudioForgeError("FFmpeg e ffprobe são necessários para converter vídeos.")
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,height", "-of", "json", str(source)],
            capture_output=True, text=True, check=True, timeout=45,
        )
        streams = json.loads(probe.stdout).get("streams", [])
    except (subprocess.SubprocessError, ValueError, OSError) as exc:
        raise AudioForgeError("Não foi possível analisar as faixas de vídeo. Verifique o arquivo original.") from exc
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    if not video_streams:
        raise AudioForgeError("O arquivo não contém vídeo; não é possível gerar MP4.")
    quick_copy = (video_streams[0].get("codec_name") == "h264" and
                  (not audio_streams or audio_streams[0].get("codec_name") == "aac"))
    can_copy_size = (_height() is None or (
        video_streams[0].get('height') is not None and video_streams[0]['height'] <= _height()))
    if quick_copy and can_copy_size:
        status("Gerando MP4 compatível sem recomprimir o vídeo...")
        if source.suffix.lower() == ".mp4":
            shutil.copy2(source, destination)
        else:
            run_command([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(source),
                "-map", "0:v:0", "-map", "0:a:0?", "-c", "copy", "-movflags", "+faststart", str(destination),
            ], status)
    else:
        status("Convertendo vídeo para MP4 H.264/AAC (pode demorar na CPU)...")
        run_command([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(source),
            "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", *(["-vf", f"scale=-2:min(ih\\,{_height()})"] if _height() else []), "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(destination),
        ], status)
    if not destination.is_file() or destination.stat().st_size == 0:
        raise AudioForgeError("Não foi possível gerar o MP4.")


def download_youtube_mp3(url: str, job_dir: Path, status: StatusCallback) -> tuple[Path, str]:
    """Reutiliza o padrão YoutubeDL + FFmpegExtractAudio do script original."""
    return _download_youtube(url, job_dir, "mp3", status)


def download_youtube_mp4(url: str, job_dir: Path, status: StatusCallback) -> tuple[Path, str]:
    """Escolhe fluxos MP4 (preferindo H.264 + M4A) e mescla pelo FFmpeg."""
    return _download_youtube(url, job_dir, "mp4", status)


def _download_youtube(url: str, job_dir: Path, output_format: str,
                      status: StatusCallback) -> tuple[Path, str]:
    if output_format not in {"mp3", "mp4"}:
        raise AudioForgeError("Formato de download não suportado.")
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise AudioForgeError("yt-dlp não instalado. Execute bash install.sh.") from exc
    if shutil.which("ffmpeg") is None:
        raise AudioForgeError("FFmpeg não encontrado. Execute bash install.sh.")

    last_progress = [-1]

    def progress_hook(data: dict) -> None:
        _check_cancel()
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            if total:
                percent = int(data.get("downloaded_bytes", 0) / total * 100)
                if percent // 10 != last_progress[0] // 10:
                    last_progress[0] = percent
                    status(f"Baixando mídia: {percent}%")
        elif data.get("status") == "finished":
            status("Download concluído; finalizando formato selecionado...")

    options: dict = {
        "outtmpl": str(job_dir / "original.%(ext)s"),
        "noplaylist": True, "overwrites": True, "quiet": True,
        "no_warnings": False, "retries": 2, "fragment_retries": 2,
        "progress_hooks": [progress_hook],
        "socket_timeout": 15,
    }
    if output_format == "mp3":
        options.update({
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": str(_bitrate())}],
        })
    else:
        # Se MP4/H.264 estiver indisponível, ainda tenta streams MP4 compatíveis com o contêiner.
        # Restringimos a extensão: não renomeamos arquivos WEBM arbitrários para .mp4.
        options.update({
            "format": (
                f"bv[ext=mp4][height<={_height()}]+ba[ext=m4a]/b[ext=mp4][height<={_height()}]"
                if _height() else
                "bv[ext=mp4][vcodec^=avc1]+ba[ext=m4a]/b[ext=mp4]/bv[ext=mp4]+ba[ext=m4a]"
            ),
            "merge_output_format": "mp4",
        })
    status(f"Obtendo mídia do YouTube para {output_format.upper()}...")
    try:
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
    except ProcessingCancelled:
        raise
    except Exception as exc:
        raise AudioForgeError(
            "Falha ao obter a mídia. O YouTube pode restringir o acesso ou não oferecer "
            f"um formato MP4 compatível. Atualize o yt-dlp ou envie um arquivo local. Detalhe: {str(exc)[:230]}"
        ) from exc
    if not info:
        raise AudioForgeError("Não foi possível recuperar os metadados do vídeo.")
    outfile = job_dir / f"original.{output_format}"
    if not outfile.is_file() or outfile.stat().st_size == 0:
        raise AudioForgeError(f"O processamento terminou, mas não produziu o arquivo {output_format.upper()} esperado.")
    return outfile, str(info.get("title") or "Vídeo do YouTube")


def separate_audio(source_wav: Path, job_dir: Path, status: StatusCallback) -> tuple[Path, Path, list[Path]]:
    try:
        import demucs  # noqa: F401 — check explícito de dependência
    except ImportError as exc:
        raise AudioForgeError("Demucs não instalado. Execute ./install.sh.") from exc

    model = "htdemucs"
    status("Separando voz e instrumental com Demucs (CPU). Na primeira vez, baixará o modelo...")
    separated = job_dir / "separacao"
    run_command([
        sys.executable, "-m", "demucs", "--two-stems", "vocals", "-n", model,
        "-d", "cpu", "-o", str(separated), str(source_wav),
    ], status)
    result_dir = separated / model / source_wav.stem
    vocal = result_dir / "vocals.wav"
    inst = result_dir / "no_vocals.wav"
    if not vocal.exists() or not inst.exists():
        raise AudioForgeError("O Demucs terminou sem produzir as duas faixas esperadas. Confira o log.")
    vocal_wav = job_dir / "voz.wav"
    inst_wav = job_dir / "instrumental.wav"
    shutil.move(str(vocal), str(vocal_wav))
    shutil.move(str(inst), str(inst_wav))
    shutil.rmtree(separated, ignore_errors=True)
    status("Gerando MP3s para reprodução e download...")
    vocal_mp3 = job_dir / "voz.mp3"
    inst_mp3 = job_dir / "instrumental.mp3"
    wav_to_mp3(vocal_wav, vocal_mp3, status)
    wav_to_mp3(inst_wav, inst_mp3, status)
    return inst_mp3, vocal_mp3, [inst_wav, vocal_wav, inst_mp3, vocal_mp3]


def srt_time(seconds: float) -> str:
    milliseconds = max(0, round(float(seconds) * 1000))
    hrs, remaining = divmod(milliseconds, 3_600_000)
    minutes, remaining = divmod(remaining, 60_000)
    secs, millis = divmod(remaining, 1000)
    return f"{hrs:02}:{minutes:02}:{secs:02},{millis:03}"


def transcribe_audio(source_wav: Path, job_dir: Path, model_name: str, language: str, status: StatusCallback) -> tuple[str, list[Path]]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise AudioForgeError("faster-whisper não instalado. Execute ./install.sh.") from exc
    if model_name not in {"tiny", "base", "small"}:
        raise AudioForgeError("Selecione um modelo de transcrição válido.")
    if language not in {"auto", "pt", "en", "es"}:
        raise AudioForgeError("Selecione um idioma válido.")
    status(f"Carregando Whisper '{model_name}' na CPU. O modelo pode ser baixado na primeira execução...")
    whisper = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=min(4, os.cpu_count() or 2))
    segments, info = whisper.transcribe(
        str(source_wav), beam_size=3, language=None if language == "auto" else language,
        vad_filter=False,
    )
    status(f"Transcrevendo... idioma identificado: {info.language}.")
    text_lines: list[str] = []
    subtitle_chunks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        _check_cancel()
        text = segment.text.strip()
        if not text:
            continue
        text_lines.append(text)
        subtitle_chunks.append(f"{len(subtitle_chunks) + 1}\n{srt_time(segment.start)} --> {srt_time(segment.end)}\n{text}\n")
        if index == 1 or index % 8 == 0:
            status(f"Transcrição em andamento: {index} trechos processados...")
    result = "\n".join(text_lines)
    txt_file = job_dir / "transcricao.txt"
    srt_file = job_dir / "legendas.srt"
    txt_file.write_text(result + ("\n" if result else ""), encoding="utf-8")
    srt_file.write_text("\n".join(subtitle_chunks), encoding="utf-8")
    _check_cancel()
    if not result:
        status("Nenhuma fala foi reconhecida. Os arquivos de transcrição foram gerados vazios.")
    return result, [txt_file, srt_file]


def _read_history() -> list[dict]:
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError, TypeError):
        return []


def read_history() -> list[dict]:
    with _lock:
        return _read_history()


def save_history(record: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        entries = _read_history()
        entries = [record] + [entry for entry in entries if entry.get("id") != record["id"]]
        temp = HISTORY_FILE.with_suffix(".json.tmp")
        temp.write_text(json.dumps(entries[:200], ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, HISTORY_FILE)


def history_choices() -> list[tuple[str, str]]:
    return [(f"{item['date']}  ·  {item['title'][:65]}  ·  {item['operations']}", item["id"])
            for item in read_history() if (DATA_DIR / item.get("id", "" )).is_dir()]


def load_history_item(item_id: str | None) -> dict:
    if not item_id or not re.fullmatch(r"[0-9a-f]{12}", item_id):
        raise AudioForgeError("Selecione um item do histórico.")
    entry = next((i for i in read_history() if i.get("id") == item_id), None)
    if entry is None:
        raise AudioForgeError("Item do histórico não encontrado.")
    root = (DATA_DIR / item_id).resolve()
    if not root.is_dir():
        raise AudioForgeError("A pasta deste resultado não existe mais.")
    paths = []
    for name in entry.get("files", []):
        path = (root / name).resolve()
        if path.parent == root and path.is_file():
            paths.append(str(path))
    inst = str(root / "instrumental.mp3") if (root / "instrumental.mp3").exists() else None
    vocal = str(root / "voz.mp3") if (root / "voz.mp3").exists() else None
    original_mp3 = root / "original.mp3"
    original_wav = root / "original.wav"
    original_audio = str(original_mp3 if original_mp3.is_file() else original_wav) if (original_mp3.is_file() or original_wav.is_file()) else None
    original_video = str(root / "original.mp4") if (root / "original.mp4").is_file() else None
    transcript = (root / "transcricao.txt").read_text(encoding="utf-8") if (root / "transcricao.txt").exists() else ""
    return {"title": entry.get("title", "Arquivo"), "files": paths, "original_audio": original_audio,
            "video": original_video, "instrumental": inst, "vocals": vocal,
            "transcript": transcript, "folder": str(root)}


def process(
    url: str,
    local_file: str | None,
    separate: bool,
    transcribe: bool,
    model_name: str,
    language: str,
    status: StatusCallback,
    exports: list[str] | None = None,
    *, cancel_event: threading.Event | None = None,
    mp3_bitrate: int = 192,
    video_height: int | None = None,
) -> dict:
    """Uma entrada, múltiplas saídas. História v0.1 mantida sem migrações."""
    _job_context.cancel_event = cancel_event
    _job_context.mp3_bitrate = int(mp3_bitrate)
    _job_context.video_height = video_height
    _check_cancel()
    mode, input_value = validate_source(url, local_file)
    formats = normalize_exports(exports)
    if not formats and not separate and not transcribe:
        raise AudioForgeError("Marque um formato (MP3, MP4 ou WAV) ou uma operação de IA.")
    if mode == "arquivo" and "mp4" in formats and Path(input_value).suffix.lower() not in VIDEO_EXTENSIONS:
        raise AudioForgeError("MP4 exige uma entrada com vídeo. Desmarque MP4 para arquivos somente de áudio.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    item_id = uuid.uuid4().hex[:12]
    folder = DATA_DIR / item_id
    folder.mkdir(exist_ok=False)

    need_wav = "wav" in formats or separate or transcribe
    wav_path: Path | None = None
    video_path: Path | None = None
    mp3_path: Path | None = None
    files: list[Path] = []
    try:
        if mode == "url":
            if "mp4" in formats:
                source, title = download_youtube_mp4(input_value, folder, status)
                video_path = source
            elif "mp3" in formats and not need_wav:
                source, title = download_youtube_mp3(input_value, folder, status)
                mp3_path = source
            else:
                source, title = download_youtube_audio(input_value, folder, status)
                wav_path = source
        else:
            source = Path(input_value)
            title = source.stem
            status("Preparando arquivo local...")
            if "mp4" in formats:
                video_path = folder / "original.mp4"
                convert_to_mp4(source, video_path, status)
                source = video_path

        _check_cancel()
        if need_wav and wav_path is None:
            wav_path = folder / "original.wav"
            convert_to_wav(source, wav_path, status)
        if "mp3" in formats and mp3_path is None:
            mp3_path = folder / "original.mp3"
            media_to_mp3(wav_path if wav_path else source, mp3_path, status)

        if "mp4" in formats and video_path:
            files.append(video_path)
        if "wav" in formats and wav_path:
            files.append(wav_path)
        if "mp3" in formats and mp3_path:
            files.append(mp3_path)

        instrumental = None
        vocals = None
        transcript = ""
        if separate or transcribe:
            assert wav_path is not None
        _check_cancel()
        if separate:
            instrumental, vocals, extra = separate_audio(wav_path, folder, status)
            files.extend(extra)
        _check_cancel()
        if transcribe:
            transcript, extra = transcribe_audio(wav_path, folder, model_name, language, status)
            files.extend(extra)

        # WAV intermediário pode ocupar centenas de MB. Só guarda se pedido.
        if wav_path and "wav" not in formats and wav_path.is_file():
            wav_path.unlink()
            wav_path = None

        operations = ([fmt.upper() for fmt in formats] +
                      (["Karaokê"] if separate else []) +
                      (["Transcrição"] if transcribe else []))
        record = {
            "id": item_id, "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "title": title, "source": mode, "operations": " + ".join(operations),
            "files": [p.name for p in files],
        }
        _check_cancel()
        save_history(record)
        status("Tudo concluído! Os arquivos estão disponíveis no histórico.")
        return {
            "title": title, "folder": str(folder), "files": [str(p) for p in files],
            "original_audio": str(mp3_path or wav_path) if mp3_path or wav_path else None,
            "video": str(video_path) if video_path else None,
            "instrumental": str(instrumental) if instrumental else None,
            "vocals": str(vocals) if vocals else None, "transcript": transcript,
        }
    except Exception:
        # Preserva pasta incompleta para diagnóstico, sem poluir o histórico.
        raise
    finally:
        _job_context.cancel_event = None
        _job_context.mp3_bitrate = 192
        _job_context.video_height = None
