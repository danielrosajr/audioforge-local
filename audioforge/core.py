"""Motor local: reaproveita yt-dlp e adiciona Demucs, Whisper e histórico."""

from __future__ import annotations

import json
import os
import re
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
    """Executa comandos sem shell; encaminha mensagens úteis para a GUI."""
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        raise AudioForgeError(f"Dependência não encontrada: {command[0]}. Execute o instalador.") from exc
    last_lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        text = line.strip()
        if text:
            last_lines.append(text)
            if len(last_lines) > 15:
                last_lines.pop(0)
            if any(word in text.lower() for word in ("error", "warning", "track", "100%", "download", "model")):
                status(text[:210])
    code = proc.wait()
    if code != 0:
        raise AudioForgeError("Processo externo falhou. Detalhes: " + " | ".join(last_lines[-4:])[-550:])


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
        "-codec:a", "libmp3lame", "-b:a", "192k", str(destination),
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
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
    }
    status("Conectando ao YouTube com yt-dlp...")
    try:
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
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
    transcript = (root / "transcricao.txt").read_text(encoding="utf-8") if (root / "transcricao.txt").exists() else ""
    return {"title": entry.get("title", "Arquivo"), "files": paths, "instrumental": inst,
            "vocals": vocal, "transcript": transcript, "folder": str(root)}


def process(
    url: str,
    local_file: str | None,
    separate: bool,
    transcribe: bool,
    model_name: str,
    language: str,
    status: StatusCallback,
) -> dict:
    """Executa operações selecionadas e devolve caminhos para exibição no Gradio."""
    mode, input_value = validate_source(url, local_file)
    if not separate and not transcribe:
        status("Nenhuma IA selecionada: será gerado apenas o WAV original.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    item_id = uuid.uuid4().hex[:12]
    folder = DATA_DIR / item_id
    folder.mkdir(exist_ok=False)
    try:
        if mode == "url":
            original_wav, title = download_youtube_audio(input_value, folder, status)
        else:
            source = Path(input_value)
            title = source.stem
            original_wav = folder / "original.wav"
            status("Preparando arquivo local...")
            convert_to_wav(source, original_wav, status)
        files: list[Path] = [original_wav]
        instrumental = None
        vocals = None
        transcript = ""
        if separate:
            instrumental, vocals, extra = separate_audio(original_wav, folder, status)
            files.extend(extra)
        if transcribe:
            transcript, extra = transcribe_audio(original_wav, folder, model_name, language, status)
            files.extend(extra)
        record = {
            "id": item_id,
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "title": title,
            "source": mode,
            "operations": " + ".join((["Karaokê"] if separate else []) + (["Transcrição"] if transcribe else []) + (["WAV"] if not separate and not transcribe else [])),
            "files": [p.name for p in files],
        }
        save_history(record)
        status("Tudo concluído! Arquivos disponíveis para reproduzir e baixar.")
        return {"title": title, "folder": str(folder), "files": [str(p) for p in files],
                "instrumental": str(instrumental) if instrumental else None,
                "vocals": str(vocals) if vocals else None, "transcript": transcript}
    except Exception:
        # Mantém temporários para diagnóstico, mas não polui o histórico.
        raise
