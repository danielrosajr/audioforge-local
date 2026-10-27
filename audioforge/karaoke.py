"""Local, editable karaoke video projects (no cloud/API).

AI transcription suggests phrase timing; accurate forced alignment to user-provided
lyrics is NOT claimed. Progressive word highlighting is a visual approximation.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from . import core

PROJECTS_DIR = core.DATA_DIR / 'karaoke-projects'
MAX_LINES = 300
MAX_LYRICS_LENGTH = 25000

class KaraokeError(core.AudioForgeError):
    pass


def _is_safe_path(value: str | None) -> Path | None:
    return Path(value).expanduser().resolve() if value else None


def find_media(history_id: str | None, video_file: str | None = None,
               instrumental_file: str | None = None):
    """Explicit user upload takes priority over history media."""
    video, instrumental, vocals, caption = None, None, None, None
    if history_id:
        history = core.load_history_item(history_id)
        folder = Path(history['folder'])
        video = _is_safe_path(history.get('video'))
        instrumental = _is_safe_path(history.get('instrumental'))
        vocals = _is_safe_path(history.get('vocals'))
        candidate = folder / 'legendas.srt'
        if candidate.is_file():
            caption = candidate
    return (_is_safe_path(video_file) or video,
            _is_safe_path(instrumental_file) or instrumental,
            vocals, caption)


def duration_of(path: Path) -> float:
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                                 str(path)], capture_output=True, text=True, check=True, timeout=25)
        seconds = float(result.stdout.strip())
        if not 0 < seconds < 24 * 3600:
            raise ValueError('bad duration')
        return seconds
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise KaraokeError('Não foi possível ler a duração do vídeo (ffprobe).') from exc


def _timestamp(text: str) -> float:
    parts = text.strip().replace(',', '.').split(':')
    if len(parts) not in (2, 3):
        raise ValueError('bad timestamp')
    if len(parts) == 2:
        parts = ['0'] + parts
    hours, minutes, sec = int(parts[0]), int(parts[1]), float(parts[2])
    if not 0 <= minutes < 60 or not 0 <= sec < 60 or hours < 0:
        raise ValueError('bad timestamp')
    return hours * 3600 + minutes * 60 + sec


def parse_srt(value: str) -> list[list]:
    rows = []
    for block in re.split(r'\n\s*\n', (value or '').strip().replace('\r', '')):
        lines = block.splitlines()
        times_at = next((i for i, line in enumerate(lines) if '-->' in line), -1)
        if times_at < 0:
            continue
        match = re.fullmatch(r'\s*(\d\d:\d\d:\d\d[,.]\d{1,3})\s*-->\s*(\d\d:\d\d:\d\d[,.]\d{1,3})(?:\s+.*)?', lines[times_at])
        if not match:
            continue
        start, end = _timestamp(match.group(1)), _timestamp(match.group(2))
        text = ' '.join(re.sub(r'<[^>]+>', '', part) for part in lines[times_at+1:]).strip()
        if text and end > start:
            rows.append([round(start, 2), round(end, 2), text])
    return rows[:MAX_LINES]


def distribute_lines(lyrics: str, seconds: float) -> list[list]:
    if len(lyrics or '') > MAX_LYRICS_LENGTH:
        raise KaraokeError('Letra muito longa. Limite de 25.000 caracteres.')
    lines = [s.strip() for s in (lyrics or '').splitlines() if s.strip()]
    if not lines:
        raise KaraokeError('Cole a letra, uma frase por linha.')
    if len(lines) > MAX_LINES:
        raise KaraokeError('Limite de 300 frases por projeto.')
    if seconds <= 0:
        raise KaraokeError('Vídeo sem duração válida.')
    # Temporização inicial é estimativa matemática, e NÃO sincronização automática.
    step = seconds / len(lines)
    return [[round(i * step, 2), round(min(seconds, (i+1) * step), 2), text]
            for i, text in enumerate(lines)]


def validate_rows(rows) -> list[tuple[float, float, str]]:
    if not isinstance(rows, list):
        raise KaraokeError('Edite os tempos na tabela.')
    if not 0 < len(rows) <= MAX_LINES:
        raise KaraokeError('Adicione entre 1 e 300 frases.')
    result = []
    for index, row in enumerate(rows, start=1):
        try:
            if not isinstance(row, (list, tuple)) or len(row) < 3:
                raise ValueError('bad row')
            start, end, value = float(row[0]), float(row[1]), str(row[2]).strip()
            if not (0 <= start < end <= 24 * 3600) or not value or len(value) > 400:
                raise ValueError('bad content')
            result.append((start, end, value))
        except (TypeError, ValueError) as exc:
            raise KaraokeError(f'Frase {index}: início, fim ou texto inválido.') from exc
    result.sort(key=lambda row: row[0])
    # O editor aceita sobreposição ocasional para duetos, mas informa no README.
    return result


def _ass_time(seconds: float) -> str:
    cs = max(0, round(float(seconds) * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f'{h}:{m:02}:{s:02}.{cs:02}'


def _ass_escape(text: str) -> str:
    """Escape user-supplied ASS override syntax and newlines."""
    return text.replace('\\', '＼').replace('{', '｛').replace('}', '｝').replace('\n', r'\N')


def _ass_color(rgb: str) -> str:
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', rgb):
        raise KaraokeError('Cor inválida.')
    value = rgb[1:]
    return '&H00' + value[4:6] + value[2:4] + value[0:2] + '&'


def make_ass(rows, color: str = '#FFC857', position: str = 'bottom',
             fontsize: int = 44, progressive: bool = True) -> str:
    entries = validate_rows(rows)
    if position not in {'bottom', 'center', 'top'}:
        raise KaraokeError('Posição de legenda inválida.')
    size = int(fontsize)
    if not 20 <= size <= 80:
        raise KaraokeError('Tamanho da fonte deve estar entre 20 e 80.')
    alignment = {'bottom': 2, 'center': 5, 'top': 8}[position]
    color_ass = _ass_color(color)
    header = f'''[Script Info]
Title: AudioForge Karaoke
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Karaoke,DejaVu Sans,{size},{color_ass},&H00FFFFFF,&H00000000,&H7F000000,-1,0,0,0,100,100,0,0,1,3,1,{alignment},48,48,40,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
    events = []
    for start, end, value in entries:
        if progressive:
            words = re.findall(r'\S+\s*', value)
            total_cs = max(len(words), round((end-start)*100))
            weights = [max(1, len(w.strip())) for w in words]
            weighted = max(1, sum(weights))
            durations = [max(1, round(total_cs * weight/weighted)) for weight in weights]
            durations[-1] = max(1, durations[-1] + total_cs - sum(durations))
            result = ''.join(r'{\kf'+str(cs)+'}'+_ass_escape(w) for cs, w in zip(durations, words))
        else:
            result = _ass_escape(value)
        events.append(f'Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Karaoke,,0,0,0,,{result}')
    return header + '\n'.join(events) + '\n'


def timeline_html(rows, language='pt') -> str:
    try:
        validated = validate_rows(rows)
    except KaraokeError:
        return '<div class="af-timeline">Nenhuma frase / No lines yet</div>'
    max_time = max(end for _, end, _ in validated)
    pieces = []
    for i, (start,end,text) in enumerate(validated):
        left, width = 100 * start/max_time, max(0.4, 100 * (end-start)/max_time)
        pieces.append(f'<div class="af-time-seg" title="{html.escape(text, quote=True)} ({start:.2f}s–{end:.2f}s)" '
                      f'style="left:{left:.3f}%;width:{min(width,100-left):.3f}%">{html.escape(text)}</div>')
    title = 'Linha do tempo (estimativa)' if language != 'en' else 'Timeline (estimated)'
    return f'<div class="af-timeline"><b>{title}</b><div class="af-time-track">{"".join(pieces)}</div><small>0:00 — {_ass_time(max_time)}</small></div>'


def suggest_transcription(path: Path, language: str, model_name: str = 'base') -> list[list]:
    if language not in {'pt','en','auto'} or model_name not in {'tiny','base','small'}:
        raise KaraokeError('Idioma ou modelo não suportado.')
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise KaraokeError('Instale faster-whisper usando install.sh.') from exc
    whisper = WhisperModel(model_name, device='cpu', compute_type='int8', cpu_threads=min(4, __import__('os').cpu_count() or 2))
    segments, _info = whisper.transcribe(str(path), beam_size=3, language=None if language=='auto' else language,
                                        word_timestamps=True, vad_filter=False)
    rows = []
    for seg in segments:
        words = getattr(seg, 'words', None) or []
        if words:
            # Use limites reais dos vocábulos detectados para frase, não distribuir cegamente.
            start, end = float(words[0].start), float(words[-1].end)
        else:
            start, end = float(seg.start), float(seg.end)
        text = str(seg.text).strip()
        if text and end > start:
            rows.append([round(start,2),round(end,2),text])
        if len(rows)>=MAX_LINES:
            break
    if not rows:
        raise KaraokeError('A IA não encontrou palavras. Cole a letra e ajuste manualmente.')
    return rows


def _copy_if_temporary(path: Path, project_dir: Path, name: str) -> Path:
    path = path.resolve()
    if not path.is_file():
        raise KaraokeError('Um arquivo do projeto não existe mais. Selecione novamente.')
    # Files from a completed history job are already permanent. Files uploaded to
    # Gradio temp cache must be persisted to allow reopening the project later.
    try:
        path.relative_to(core.DATA_DIR.resolve())
        return path
    except ValueError:
        destination = project_dir / (name + path.suffix.lower())
        if destination.resolve() != path:
            shutil.copy2(path, destination)
        return destination


def save_project(history_id, video_file, instrumental_file, rows, language='pt',
                 color='#FFC857', position='bottom', font_size=44, progressive=True,
                 project_id: str | None=None) -> tuple[str, str]:
    lines = validate_rows(rows)
    video, instrumental, _, _ = find_media(history_id, video_file, instrumental_file)
    if not video or not instrumental:
        raise KaraokeError('Selecione um vídeo e uma faixa instrumental (arquivo ou histórico).')
    if video.suffix.lower() not in core.VIDEO_EXTENSIONS:
        raise KaraokeError('A fonte de vídeo precisa ser MP4, MOV, MKV, WEBM etc.')
    if not video.is_file() or not instrumental.is_file():
        raise KaraokeError('Vídeo ou instrumental não encontrado.')
    identifier = project_id if project_id and re.fullmatch('[0-9a-f]{12}', project_id) else uuid.uuid4().hex[:12]
    folder = PROJECTS_DIR / identifier
    folder.mkdir(parents=True, exist_ok=True)
    persistent_video = _copy_if_temporary(video, folder, 'video')
    persistent_audio = _copy_if_temporary(instrumental, folder, 'instrumental')
    project = {
        'version': 1, 'id': identifier, 'history_id': history_id,
        'video': str(persistent_video), 'instrumental': str(persistent_audio),
        'rows': [list(r) for r in lines], 'language': language if language in ('pt','en','auto') else 'auto',
        'color': color, 'position': position, 'font_size': int(font_size), 'progressive': bool(progressive),
    }
    tmp = folder / 'project.json.tmp'
    tmp.write_text(json.dumps(project,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(folder / 'project.json')
    return identifier, str(folder / 'project.json')


def project_choices() -> list[tuple[str,str]]:
    if not PROJECTS_DIR.exists():
        return []
    result = []
    for file in sorted(PROJECTS_DIR.glob('*/project.json'), key=lambda f: f.stat().st_mtime, reverse=True):
        if re.fullmatch('[0-9a-f]{12}',file.parent.name):
            result.append((f'{file.parent.name} • {len(file.parent.name)}',file.parent.name))
    return result[:200]


def load_project(identifier: str) -> dict:
    if not re.fullmatch('[0-9a-f]{12}', identifier or ''):
        raise KaraokeError('Selecione um projeto salvo.')
    folder = PROJECTS_DIR / identifier
    file = folder / 'project.json'
    try:
        data = json.loads(file.read_text(encoding='utf-8'))
        validate_rows(data['rows'])
        for field in ('video','instrumental'):
            path = Path(data[field]).resolve()
            if not path.is_file():
                raise KaraokeError('Arquivo original não encontrado: '+str(path))
        return data
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise KaraokeError('Não foi possível abrir o projeto salvo.') from exc


def export_video(identifier: str, rows, language='pt', color='#FFC857',
                 position='bottom', font_size=44, progressive=True, status=lambda _:None) -> tuple[str,str]:
    if not shutil.which('ffmpeg'):
        raise KaraokeError('FFmpeg não está instalado.')
    # Check the installed FFmpeg has libass. Failing early gives a useful message.
    filters = subprocess.run(['ffmpeg','-hide_banner','-filters'],capture_output=True,text=True,timeout=20)
    if not re.search(r'\sass\s',filters.stdout):
        raise KaraokeError('Este FFmpeg foi compilado sem suporte ao filtro ass/libass.')
    data = load_project(identifier)
    folder = PROJECTS_DIR / identifier
    validated = validate_rows(rows)
    ass = make_ass([list(x) for x in validated], color, position, font_size, progressive)
    (folder/'karaoke.ass').write_text(ass,encoding='utf-8-sig')
    data.update(rows=[list(r) for r in validated],color=color,position=position,
                font_size=int(font_size),progressive=bool(progressive),language=language)
    (folder/'project.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    video_file = Path(data['video']); audio_file = Path(data['instrumental'])
    output = folder/'karaoke.mp4'
    status('Renderizando MP4 com legendas e instrumental (CPU)...')
    core.run_command(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                      '-i',str(video_file),'-i',str(audio_file),
                      '-map','0:v:0','-map','1:a:0','-vf','ass=karaoke.ass',
                      '-c:v','libx264','-preset','veryfast','-crf','23',
                      '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',
                      '-shortest','-movflags','+faststart',str(output)],status,cwd=folder)
    if not output.is_file() or output.stat().st_size==0:
        raise KaraokeError('O FFmpeg não gerou um MP4 válido.')
    status('Vídeo de karaokê pronto!')
    return str(output), str(folder/'karaoke.ass')
