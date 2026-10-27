"""AudioForge Local v0.4.0 — editor de vídeo karaokê PT/EN."""

from __future__ import annotations

import html
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import gradio as gr

from audioforge import __version__
from audioforge.tutorial import (STEPS, tutorial_card, tutorial_was_seen, finish_tutorial)
from audioforge.queue_manager import ProcessingQueue
from audioforge import karaoke
from audioforge.preferences import get_language, save_language
from audioforge.core import (
    AudioForgeError, DATA_DIR, history_choices, load_history_item, process,
)


PROJECT_DIR = Path(__file__).resolve().parent
CSS = (PROJECT_DIR / "assets" / "style.css").read_text(encoding="utf-8")
TOUR_JS = (PROJECT_DIR / "assets" / "tour.js").read_text(encoding="utf-8").replace("__DEFAULT_LANGUAGE__",get_language())
TASKS = ProcessingQueue()


ACTIVE_LOCK = threading.Lock()
ACTIVE_JOBS = 0
KARAOKE_ACTIVE = 0
SHUTTING_DOWN = False


def render_result(result: dict) -> tuple:
    return (
        "✅ **Concluído!** Reproduza ou baixe seus arquivos abaixo.",
        f"**Projeto:** {result['title']}\n\n**Pasta:** `{result['folder']}`",
        result.get("original_audio"), result.get("video"), result.get("instrumental"),
        result.get("vocals"), result.get("transcript", ""), result.get("files", []),
    )


def work(url: str, local_file: str | None, exports: list[str],
         do_separate: bool, do_transcribe: bool, model_name: str, language: str):
    """Generator + worker: status atualizado sem bloquear interface ou botão Sair."""
    global ACTIVE_JOBS
    with ACTIVE_LOCK:
        if SHUTTING_DOWN:
            yield ("⚠️ **O aplicativo está encerrando.**", "", "", None, None, None, None, "", None, gr.update())
            return
        ACTIVE_JOBS += 1

    events: queue.Queue = queue.Queue()
    recent: list[str] = []
    last_update = ["Preparando processamento..."]

    def status(message: str) -> None:
        events.put(("status", message))

    def worker() -> None:
        global ACTIVE_JOBS
        try:
            result = process(url, local_file, do_separate, do_transcribe, model_name, language, status, exports)
            events.put(("done", result))
        except Exception as exc:
            events.put(("error", str(exc)))
        finally:
            with ACTIVE_LOCK:
                ACTIVE_JOBS -= 1

    threading.Thread(target=worker, daemon=True).start()
    blank = ("", None, None, None, None, "", None)
    yield ("⏳ **Preparando...**", "", *blank, gr.update())
    while True:
        try:
            event_type, value = events.get(timeout=2)
        except queue.Empty:
            yield (f"⏳ **{last_update[0]}**", "\n".join(recent[-18:]), *blank, gr.update())
            continue
        if event_type == "status":
            recent.append(str(value))
            last_update[0] = str(value)
            yield (f"⏳ **{value}**", "\n".join(recent[-18:]), *blank, gr.update())
        elif event_type == "error":
            recent.append(f"ERRO: {value}")
            yield ("❌ **Não foi possível concluir.** Confira os detalhes no log.",
                   "\n".join(recent[-18:]), *blank, gr.update())
            return
        elif event_type == "done":
            result_values = render_result(value)
            yield (result_values[0], "\n".join(recent[-18:]), *result_values[1:],
                   gr.update(choices=history_choices()))
            return


def shutdown_app() -> str:
    """Confirmação de encerramento: sem matar um processamento ativo."""
    global SHUTTING_DOWN
    with ACTIVE_LOCK:
        active = TASKS.busy_count()
        if ACTIVE_JOBS or active or KARAOKE_ACTIVE:
            return f"⚠️ Existem {ACTIVE_JOBS + active + KARAOKE_ACTIVE} processamento(s) em execução ou na fila. Cancele ou aguarde terminar antes de encerrar."
        if SHUTTING_DOWN:
            return "⏻ O encerramento já foi solicitado. Pode fechar esta aba."
        SHUTTING_DOWN = True
    timer = threading.Timer(2.5, lambda: os.kill(os.getpid(), signal.SIGTERM))
    timer.daemon = True
    timer.start()
    return "⏻ **AudioForge está encerrando.** Seus arquivos foram preservados. Agora você pode fechar esta aba."


def open_folder() -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("linux"):
        command = ["xdg-open", str(DATA_DIR)]
    elif sys.platform == "darwin":
        command = ["open", str(DATA_DIR)]
    elif sys.platform == "win32":
        os.startfile(str(DATA_DIR))  # type: ignore[attr-defined]
        return f"📁 Pasta aberta: `{DATA_DIR}`"
    else:
        return f"Pasta de resultados: `{DATA_DIR}`"
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"📁 Pasta aberta: `{DATA_DIR}`"
    except OSError:
        return f"📁 Abra manualmente esta pasta: `{DATA_DIR}`"


def show_previous(item_id: str):
    try:
        return render_result(load_history_item(item_id))
    except AudioForgeError as exc:
        return f"⚠️ {exc}", "", None, None, None, None, "", None


def _tour_render(index: int):
    text, marker = tutorial_card(index)
    tab = STEPS[index][3]
    return (index, text, marker, gr.update(interactive=(index > 0)),
            gr.update(value="✓ Concluir tutorial" if index == len(STEPS)-1 else "Próximo →"),
            gr.update(visible=True), gr.update(selected=tab))


def tour_start():
    return _tour_render(0)


def tour_back(index: int):
    return _tour_render(max(0, int(index) - 1))


def tour_next(index: int):
    index = int(index)
    if index >= len(STEPS) - 1:
        finish_tutorial()
        text, _marker = tutorial_card(0)
        return (0, text, "", gr.update(interactive=False),
                gr.update(value="Próximo →"), gr.update(visible=False),
                gr.update(selected="studio"))
    return _tour_render(index + 1)


def tour_skip():
    finish_tutorial()
    return gr.update(visible=False), ""





def queue_display(selected=None):
    rows = TASKS.snapshot()
    active = sum(r['state'] in {'aguardando','processando','cancelando'} for r in rows)
    done = sum(r['state'] == 'concluído' for r in rows)
    if not rows:
        table = '<div class="af-queue-table" style="padding:16px">Nenhum trabalho nesta sessão. Adicione o primeiro à fila.</div>'
    else:
        body = []
        for r in rows:
            name = html.escape(r['title'][:55])
            msg = html.escape(r['message'][:105])
            pct = f"{r['progress']}%" if r['progress'] is not None else '—'
            display_state = ({'aguardando':'pending','processando':'running','cancelando':'cancelling','concluído':'completed','cancelado':'cancelled','erro':'error'}.get(r['state'],r['state']) if get_language()=='en' else r['state'])
            body.append(f'<tr><td><strong>{name}</strong><br><small>{r["id"]}</small></td>'
                        f'<td><span class="af-job-pill" data-state="{r["state"]}">{r["state"]}</span></td>'
                        f'<td>{pct}</td><td>{msg}</td></tr>')
        headers = '<th>Media</th><th>Status</th><th>Download</th><th>Current step</th>' if get_language()=='en' else '<th>Material</th><th>Estado</th><th>Download</th><th>Etapa atual</th>'
        table = '<div class="af-queue-table"><table><thead><tr>' + headers + '</tr></thead><tbody>' + ''.join(body) + '</tbody></table></div>'
    choices = [(f"{r['id']} • {r['state']} • {r['title'][:40]}",r['id']) for r in rows]
    info = (f'**{active}** running or waiting · **{done}** completed · **{len(rows)}** jobs this session' if get_language()=='en' else f'**{active}** em andamento ou aguardando · **{done}** concluídos · **{len(rows)}** registros nesta sessão')
    valid_ids = {r['id'] for r in rows}
    return table, gr.update(choices=choices, value=selected if selected in valid_ids else None), info


def enqueue_work(url, local_file, exports, separate, transcribe, model, language, bitrate, height):
    try:
        id_ = TASKS.enqueue(url, local_file, exports, separate, transcribe,
                            model, language, int(bitrate), height)
        return f'✅ Trabalho **{id_}** adicionado. Ele começará automaticamente na sua vez.', *queue_display()
    except Exception as exc:
        return f'⚠️ {exc}', *queue_display()


def cancel_work(id_):
    try: message = TASKS.cancel_job(id_)
    except AudioForgeError as exc: message = f'⚠️ {exc}'
    return message, *queue_display()


def clear_queue():
    total = TASKS.clear_finished()
    return f'🧹 {total} item(ns) finalizados removidos da lista. Seus arquivos permanecem no histórico.', *queue_display()


def load_queue_result(id_):
    try: return render_result(TASKS.get_result(id_))
    except AudioForgeError as exc:
        return f'⚠️ {exc}', '', None, None, None, None, '', None


def queue_log(id_):
    return TASKS.log_for(id_) if id_ else ''

def queue_tick(selected):
    return (*queue_display(selected), queue_log(selected))




# -------- Karaoke Video Studio --------

def _kerror(exc, lang):
    return f"⚠️ {str(exc)}" if lang != 'en' else f"⚠️ {str(exc)}"


def karaoke_import(history_id, source_video, source_inst, lyrics, subtitles, lang):
    try:
        video, _, _, caption = karaoke.find_media(history_id, source_video, source_inst)
        if subtitles:
            rows = karaoke.parse_srt(Path(subtitles).read_text(encoding='utf-8-sig'))
            if not rows: raise karaoke.KaraokeError('SRT sem frases válidas.')
        elif caption and not (lyrics or '').strip():
            rows = karaoke.parse_srt(caption.read_text(encoding='utf-8-sig'))
        else:
            if not video: raise karaoke.KaraokeError('Selecione um vídeo para calcular a duração.')
            rows = karaoke.distribute_lines(lyrics, karaoke.duration_of(video))
        message = '✅ Tempos carregados. Revise cada frase.' if lang == 'pt' else '✅ Timing loaded. Review every phrase.'
        return rows, karaoke.timeline_html(rows,lang),message
    except Exception as exc:
        return gr.update(), gr.update(), _kerror(exc,lang)


def karaoke_ai(history_id, source_video, source_inst, lang, model, ui_lang):
    try:
        video, _, vocal, _ = karaoke.find_media(history_id,source_video,source_inst)
        origin = vocal or video
        if not origin: raise karaoke.KaraokeError('Selecione vídeo ou processamento com vocal.')
        rows = karaoke.suggest_transcription(origin,lang,model)
        message = ('✅ Tempos sugeridos pela IA. Corrija palavras e tempos antes de exportar.'
                   if ui_lang=='pt' else '✅ AI suggested timing. Review words and timing before exporting.')
        return rows, karaoke.timeline_html(rows,ui_lang),message
    except Exception as exc:
        return gr.update(),gr.update(),_kerror(exc,ui_lang)


def karaoke_preview(rows,ui_lang):
    return karaoke.timeline_html(rows,ui_lang)


def karaoke_save(history_id, source_video, source_inst, rows, song_language,
                 color, position, fontsize, progressive, project_id, ui_lang):
    try:
        if project_id and not history_id and not source_video and not source_inst:
            stored = karaoke.load_project(project_id)
            source_video, source_inst = stored['video'], stored['instrumental']
        identifier,path = karaoke.save_project(history_id,source_video,source_inst,rows,
                song_language,color,position,fontsize,progressive,project_id)
        msg = ('✅ Projeto salvo localmente. Você pode continuar depois.' if ui_lang=='pt'
               else '✅ Project saved locally. You can continue editing later.')
        return identifier, msg+f'  `{path}`',gr.update(choices=karaoke.project_choices(),value=identifier)
    except Exception as exc:
        return project_id,_kerror(exc,ui_lang),gr.update()


def karaoke_load(identifier,ui_lang):
    try:
        data=karaoke.load_project(identifier)
        msg = '✅ Projeto carregado.' if ui_lang=='pt' else '✅ Project loaded.'
        return (data['id'],None,None,None,data['rows'],karaoke.timeline_html(data['rows'],ui_lang),
                data['language'],data['color'],data['position'],data['font_size'],
                data['progressive'],msg,str(data['video']),str(data['instrumental']))
    except Exception as exc:
        return (None,)*11+(_kerror(exc,ui_lang),None,None)


def karaoke_render(identifier,rows,song_language,color,position,font_size,progressive,ui_lang):
    global KARAOKE_ACTIVE
    with ACTIVE_LOCK:
        if SHUTTING_DOWN or TASKS.busy_count() or KARAOKE_ACTIVE:
            message = ('⚠️ Aguarde a fila terminar antes de renderizar o vídeo.' if ui_lang=='pt'
                       else '⚠️ Finish queued jobs before rendering a video.')
            return gr.update(),gr.update(),message
        KARAOKE_ACTIVE += 1
    try:
        if not identifier:
            raise karaoke.KaraokeError('Salve o projeto antes de exportar.')
        mp4,ass=karaoke.export_video(identifier,rows,song_language,color,position,font_size,progressive)
        msg = '✅ MP4 de karaokê pronto!' if ui_lang=='pt' else '✅ Karaoke MP4 ready!'
        return mp4,[mp4,ass],msg
    except Exception as exc:
        return gr.update(),gr.update(),_kerror(exc,ui_lang)
    finally:
        with ACTIVE_LOCK:
            KARAOKE_ACTIVE -= 1


def karaoke_history_preview(history_id):
    if not history_id:
        return gr.update(), gr.update()
    try:
        video,audio,_,_ = karaoke.find_media(history_id,None,None)
        return str(video) if video else None, str(audio) if audio else None
    except Exception:
        return None,None

def build_interface() -> gr.Blocks:
    with gr.Blocks(title=f"AudioForge Local • v{__version__}") as demo:
        ui_lang = gr.Dropdown(choices=[("🇧🇷 Português", "pt"), ("🇺🇸 English", "en")],
                              value=get_language(),label="🌐 Idioma da interface / UI Language",
                              elem_id="af-ui-language",interactive=True)
        hero = gr.HTML(f"""
        <section class="af-hero">
          <div class="af-topline"><span class="af-dot"></span> LOCAL • PRIVADO • SEM API PAGA <span class="af-version">v{__version__}</span></div>
          <h1>Audio<span>Forge</span> <em>Local</em></h1>
          <p>Baixe vídeo ou áudio em MP4, MP3 ou WAV, crie instrumentais e transforme fala em texto.</p>
          <div class="af-tags"><span>▶ MP4</span><span>♫ MP3 / WAV</span><span>🎤 Karaokê</span><span>✦ Transcrição com IA</span></div>
        </section>
        """)
        tour_btn = gr.Button("❔ Abrir tutorial interativo", variant="secondary", size="sm", elem_id="af-tour-launch")
        with gr.Tabs(selected="studio") as tabs:
            with gr.Tab("✨ Estúdio", id="studio") as studio_tab:
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, min_width=310):
                        with gr.Group(elem_id="af-guide-source", elem_classes=["af-tour-area"]):
                            source_heading = gr.Markdown("### 01 / Escolha o material")
                            url = gr.Textbox(label="Link do YouTube", placeholder="https://www.youtube.com/watch?v=...", lines=1,
                                         info="Use somente mídias cujo download e processamento sejam autorizados.")
                            gr.Markdown("<p class='af-or'>— OU —</p>")
                            file_input = gr.File(label="Enviar áudio ou vídeo do computador", type="filepath",
                                                 file_types=["audio", "video"], file_count="single")
                        with gr.Group(elem_id="af-guide-formats", elem_classes=["af-tour-area"]):
                            format_heading = gr.Markdown("### 02 / Escolha os formatos")
                            exports = gr.CheckboxGroup(
                            label="Baixar / exportar",
                            choices=[("🔊 WAV (áudio sem compressão)", "wav"),
                                     ("🎧 MP3 (áudio leve)", "mp3"),
                                     ("🎬 MP4 (vídeo com áudio)", "mp4")],
                            value=["wav"],
                                info="Você pode marcar mais de um. MP4 requer um vídeo na origem.",
                            )
                        with gr.Group(elem_id="af-guide-quality", elem_classes=["af-tour-area"]):
                            quality_heading = gr.Markdown("### 03 / Qualidade da mídia")
                            with gr.Row():
                                bitrate = gr.Dropdown(label="MP3 (kbps)", choices=[("128 — menor", 128), ("192 — equilibrado", 192), ("320 — maior", 320)], value=192)
                                height = gr.Dropdown(label="MP4 (resolução máxima)", choices=[("Original", "original"), ("Até 720p", "720"), ("Até 1080p", "1080")], value="original")
                        with gr.Group(elem_id="af-guide-ai", elem_classes=["af-tour-area"]):
                            ai_heading = gr.Markdown("### 04 / Ferramentas de IA (opcionais)")
                            do_separate = gr.Checkbox(label="🎤 Separar voz e instrumental (WAV + MP3)", value=True)
                            do_transcribe = gr.Checkbox(label="📝 Transcrever áudio (TXT + SRT)", value=False)
                            ai_hint = gr.Markdown("<p class='af-muted'>Só quer baixar MP3 ou MP4? Desmarque o karaokê. Sem seleção de formatos, as IAs ainda podem gerar seus resultados.</p>")
                            with gr.Accordion("⚙️ Opções de transcrição", open=False):
                                model_name = gr.Dropdown(choices=[("Rápido — tiny", "tiny"), ("Equilibrado — base", "base"),
                                                               ("Mais preciso — small (mais lento)", "small")],
                                                     value="base", label="Modelo Whisper")
                                language = gr.Dropdown(choices=[("Detectar automaticamente", "auto"), ("Português", "pt"),
                                                                 ("Inglês", "en"), ("Espanhol", "es")],
                                                       value="auto", label="Idioma")
                        with gr.Group(elem_id="af-guide-enqueue", elem_classes=["af-tour-area"]):
                            submit = gr.Button("＋ Adicionar à fila", variant="primary", size="lg", elem_classes=["af-action"])
                            enqueue_message = gr.Markdown("**Dica:** você pode incluir vários trabalhos enquanto o primeiro é processado.")
                        open_btn = gr.Button("📁 Abrir pasta de resultados", variant="secondary")
                        folder_hint = gr.Markdown()
                    with gr.Column(scale=6, min_width=330):
                        with gr.Group(elem_id="af-guide-queue", elem_classes=["af-tour-area"]):
                            queue_heading = gr.Markdown("### 05 / Fila de processamento\nOs itens iniciam automaticamente, um por vez, para não sobrecarregar seu computador.")
                            queue_table = gr.HTML('<div class="af-queue-table" style="padding:16px">A fila está vazia.</div>', container=False)
                            queue_summary = gr.Markdown('Nenhuma tarefa adicionada.')
                            selected_job = gr.Dropdown(label="Selecionar trabalho", choices=[], interactive=True)
                            with gr.Row():
                                cancel_btn = gr.Button("✕ Cancelar selecionado", variant="stop")
                                view_btn = gr.Button("↗ Ver resultado", variant="primary")
                                clean_btn = gr.Button("🧹 Limpar finalizados", variant="secondary")
                            queue_feedback = gr.Markdown()
                            queue_details = gr.Textbox(label="Log do trabalho selecionado", lines=4, interactive=False, buttons=["copy"])
                        with gr.Group(elem_id="af-guide-results", elem_classes=["af-tour-area"]):
                            result_heading = gr.Markdown("### 06 / Resultado selecionado")
                            status = gr.Markdown("**Pronto para começar.** Escolha o material e os formatos.", elem_classes=["af-status"])
                        project_info = gr.Markdown("Tudo é salvo no seu computador.")
                        with gr.Row():
                            original_audio = gr.Audio(label="🎧 Áudio original", type="filepath", interactive=False)
                            video_preview = gr.Video(label="🎬 Vídeo MP4", interactive=False)
                        with gr.Row():
                            inst = gr.Audio(label="🎹 Instrumental", type="filepath", interactive=False)
                            vocals = gr.Audio(label="🎙️ Somente voz", type="filepath", interactive=False)
                        transcript = gr.Textbox(label="📝 Texto transcrito", lines=7, buttons=["copy"],
                                                placeholder="A transcrição aparecerá aqui...", interactive=False)
                        files = gr.File(label="⬇️ Arquivos prontos para download", file_count="multiple", interactive=False)
                        with gr.Accordion("🛠️ Acompanhamento / log", open=False):
                            log = gr.Textbox(label="Etapas do processamento", lines=7, interactive=False, buttons=["copy"])
                outputs = [status, log, project_info, original_audio, video_preview, inst, vocals, transcript, files]
                open_btn.click(fn=open_folder, outputs=folder_hint)
            with gr.Tab("🎤 Karaoke Video", id="karaoke") as karaoke_tab:
                with gr.Group(elem_id="af-guide-karaoke", elem_classes=["af-tour-area"]):
                    karaoke_intro = gr.Markdown("### Karaoke Video Studio\nUse um processamento do **Histórico** que contenha MP4 + instrumental, ou envie os dois arquivos. Ajuste cada frase antes de exportar.")
                    with gr.Row():
                        saved_project = gr.Dropdown(label="Reabrir projeto salvo", choices=karaoke.project_choices(),interactive=True)
                        reload_projects = gr.Button("↻ Atualizar projetos")
                        open_project_btn = gr.Button("↗ Reabrir projeto")
                    karaoke_id = gr.State(None)
                    with gr.Row():
                        history_source = gr.Dropdown(label="Usar mídia do histórico",choices=history_choices(),interactive=True)
                        reload_history = gr.Button("↻ Atualizar histórico")
                    with gr.Row():
                        karaoke_video_upload = gr.File(label="Ou enviar vídeo",file_types=["video"],type="filepath")
                        karaoke_instrumental_upload = gr.File(label="Ou enviar instrumental",file_types=["audio"],type="filepath")
                    with gr.Row():
                        video_source_preview = gr.Video(label="Vídeo selecionado",interactive=False)
                        audio_source_preview = gr.Audio(label="Instrumental selecionado",type="filepath",interactive=False)
                    with gr.Group(elem_id="af-guide-lyrics",elem_classes=["af-tour-area"]):
                        lyric_input = gr.Textbox(label="Letra: uma frase por linha",lines=7,
                            placeholder="Escreva ou cole as letras. Uma linha = uma frase de karaokê.")
                        karaoke_srt_file = gr.File(label="Ou importar legenda SRT",file_types=[".srt"],type="filepath")
                        with gr.Row():
                            lines_btn = gr.Button("◷ Distribuir tempos (estimativa)",variant="secondary")
                            ai_btn = gr.Button("✦ Sugerir letra/tempos com Whisper (CPU)",variant="secondary")
                        karaoke_warning = gr.Markdown("A distribuição é uma **estimativa**, não alinhamento da letra. O Whisper transcreve vocais e pode errar palavras cantadas.")
                    with gr.Row():
                        song_language = gr.Dropdown(label="Idioma da música",choices=[("Automático","auto"),("Português","pt"),("English","en")],value="auto")
                        karaoke_model = gr.Dropdown(label="Modelo de reconhecimento",choices=["tiny","base","small"],value="base")
                    with gr.Group(elem_id="af-guide-timing",elem_classes=["af-tour-area"]):
                        karaoke_grid = gr.Dataframe(headers=["Início (s)","Fim (s)","Letra"],
                             datatype=["number","number","str"],type="array",value=[],
                             interactive=True,column_count=3,row_limits=(0,300),max_height=360,
                             label="Edite cada frase e seus tempos")
                        preview_timeline = gr.Button("◷ Atualizar linha do tempo")
                        timeline = gr.HTML('<div class="af-timeline">Adicione as frases para visualizar a linha do tempo.</div>')
                    with gr.Group(elem_id="af-guide-export",elem_classes=["af-tour-area"]):
                        with gr.Row():
                            color = gr.Dropdown(label="Cor do destaque",choices=[("Dourado","#FFC857"),("Verde","#5AF99A"),("Ciano","#64D8FF"),("Rosa","#FF86BE")],value="#FFC857")
                            placement = gr.Dropdown(label="Posição das legendas",choices=[("Inferior","bottom"),("Centro","center"),("Superior","top")],value="bottom")
                            font_size = gr.Slider(label="Tamanho da fonte",minimum=20,maximum=80,step=2,value=44)
                        progressive = gr.Checkbox(label="Destacar progressivamente as palavras (tempo aproximado)",value=True)
                        with gr.Row():
                            save_project_btn = gr.Button("💾 Salvar projeto",variant="secondary")
                            export_karaoke_btn = gr.Button("🎬 Exportar MP4 de karaokê",variant="primary")
                        karaoke_message = gr.Markdown("Salve o projeto antes de exportar. O vídeo é renderizado localmente pelo FFmpeg.")
                        output_karaoke_video = gr.Video(label="Karaokê pronto",interactive=False)
                        karaoke_files = gr.File(label="Baixar vídeo e legenda ASS",file_count="multiple",interactive=False)
                history_source.change(fn=karaoke_history_preview,inputs=history_source,
                                      outputs=[video_source_preview,audio_source_preview],queue=False)
                karaoke_video_upload.change(fn=lambda path: path,inputs=karaoke_video_upload,
                                            outputs=video_source_preview,queue=False)
                karaoke_instrumental_upload.change(fn=lambda path: path,inputs=karaoke_instrumental_upload,
                                                   outputs=audio_source_preview,queue=False)
                karaoke_grid.change(fn=karaoke_preview,inputs=[karaoke_grid,ui_lang],outputs=timeline,queue=False)
                reload_history.click(fn=lambda: gr.update(choices=history_choices()),outputs=history_source,queue=False)
                reload_projects.click(fn=lambda: gr.update(choices=karaoke.project_choices()),outputs=saved_project,queue=False)
                lines_btn.click(fn=karaoke_import,
                    inputs=[history_source,karaoke_video_upload,karaoke_instrumental_upload,lyric_input,karaoke_srt_file,ui_lang],
                    outputs=[karaoke_grid,timeline,karaoke_warning])
                ai_btn.click(fn=karaoke_ai,inputs=[history_source,karaoke_video_upload,karaoke_instrumental_upload,song_language,karaoke_model,ui_lang],
                    outputs=[karaoke_grid,timeline,karaoke_warning])
                preview_timeline.click(fn=karaoke_preview,inputs=[karaoke_grid,ui_lang],outputs=timeline,queue=False)
                save_project_btn.click(fn=karaoke_save,
                    inputs=[history_source,karaoke_video_upload,karaoke_instrumental_upload,karaoke_grid,
                            song_language,color,placement,font_size,progressive,karaoke_id,ui_lang],
                    outputs=[karaoke_id,karaoke_message,saved_project])
                open_project_btn.click(fn=karaoke_load,inputs=[saved_project,ui_lang],
                    outputs=[karaoke_id,history_source,karaoke_video_upload,karaoke_instrumental_upload,
                             karaoke_grid,timeline,song_language,color,placement,font_size,
                             progressive,karaoke_message,video_source_preview,audio_source_preview],queue=False)
                export_karaoke_btn.click(fn=karaoke_render,inputs=[karaoke_id,karaoke_grid,song_language,color,placement,font_size,progressive,ui_lang],
                    outputs=[output_karaoke_video,karaoke_files,karaoke_message],concurrency_limit=1)
            with gr.Tab("🕘 Histórico", id="history") as history_tab:
                with gr.Group(elem_id="af-guide-history", elem_classes=["af-tour-area"]):
                    history_heading = gr.Markdown("### Processamentos anteriores\nO histórico das versões antigas continua disponível em `~/Downloads/AudioForge-Local/`.")
                    previous = gr.Dropdown(label="Selecionar processamento", choices=history_choices(), value=None,
                                       interactive=True, allow_custom_value=False)
                with gr.Row():
                    refresh = gr.Button("↻ Atualizar lista")
                    load = gr.Button("↗ Carregar resultado", variant="primary")
                hist_status = gr.Markdown()
                hist_info = gr.Markdown()
                with gr.Row():
                    hist_audio = gr.Audio(label="Áudio original", type="filepath", interactive=False)
                    hist_video = gr.Video(label="Vídeo MP4", interactive=False)
                with gr.Row():
                    hist_inst = gr.Audio(label="Instrumental", type="filepath", interactive=False)
                    hist_vocal = gr.Audio(label="Voz", type="filepath", interactive=False)
                hist_txt = gr.Textbox(label="Transcrição", interactive=False, buttons=["copy"], lines=5)
                hist_files = gr.File(label="Arquivos disponíveis", interactive=False, file_count="multiple")
                refresh.click(fn=lambda: gr.update(choices=history_choices()), outputs=previous)
                load.click(fn=show_previous, inputs=previous,
                           outputs=[hist_status, hist_info, hist_audio, hist_video, hist_inst, hist_vocal, hist_txt, hist_files])
            with gr.Tab("ℹ️ Sobre", id="about") as about_tab:
                about_content = gr.Markdown(f"""### AudioForge Local v{__version__}

                **Novidades v0.4.0:** Karaoke Video Studio com legendas ASS sincronizáveis por frase, destaque progressivo aproximado, exportação MP4, projetos salvos e interface PT/EN. Mantém fila, MP3/MP4/WAV, transcrição e encerramento seguro.

                **Privacidade:** interface apenas em `127.0.0.1` (localhost). Operações de IA rodam no seu computador. Links utilizam internet para acesso à fonte e os modelos podem ser baixados no primeiro uso.

                **Limitações:** sincronização sugerida por Whisper pode errar palavras cantadas; o destaque progressivo por palavra é aproximado até que você refine as frases. A renderização de vídeo consome CPU; YouTube pode restringir links.

                **Importante:** use apenas conteúdo cujo download e processamento sejam autorizados. Fechar a aba do Chrome não encerra o Python: utilize **Encerrar AudioForge** abaixo.

                **Instalação e upgrade:** consulte o README na pasta do projeto.
                """)
        submit.click(fn=enqueue_work,
                     inputs=[url, file_input, exports, do_separate, do_transcribe, model_name, language, bitrate, height],
                     outputs=[enqueue_message, queue_table, selected_job, queue_summary], queue=False)
        cancel_btn.click(fn=cancel_work, inputs=selected_job,
                         outputs=[queue_feedback, queue_table, selected_job, queue_summary], queue=False)
        clean_btn.click(fn=clear_queue,
                        outputs=[queue_feedback, queue_table, selected_job, queue_summary], queue=False)
        view_btn.click(fn=load_queue_result, inputs=selected_job, outputs=outputs, queue=False)
        selected_job.change(fn=queue_log, inputs=selected_job, outputs=queue_details, queue=False)
        queue_timer = gr.Timer(1.5)
        queue_timer.tick(fn=queue_tick, inputs=selected_job,
                         outputs=[queue_table, selected_job, queue_summary, queue_details], queue=False)
        with gr.Group(elem_id="af-guide-shutdown", elem_classes=["af-shutdown-area", "af-tour-area"]):
            with gr.Row():
                shutdown_heading = gr.Markdown("**Controle do aplicativo**\nFechar a aba não desliga o servidor local.")
                shut_btn = gr.Button("⏻ Encerrar AudioForge", variant="secondary")
            with gr.Column(visible=False) as confirm_area:
                shutdown_confirm = gr.Markdown("Tem certeza? O AudioForge será encerrado, mas seus arquivos e histórico continuarão salvos.")
                with gr.Row():
                    cancel_shutdown = gr.Button("Voltar", variant="secondary")
                    confirm_shutdown = gr.Button("Sim, encerrar aplicativo", variant="stop")
            shutdown_status = gr.Markdown()
            shut_btn.click(fn=lambda: gr.update(visible=True), outputs=confirm_area, queue=False)
            cancel_shutdown.click(fn=lambda: gr.update(visible=False), outputs=confirm_area, queue=False)
            confirm_shutdown.click(fn=shutdown_app, outputs=shutdown_status, queue=False)
        language_targets = [tour_btn,studio_tab,karaoke_tab,history_tab,about_tab,url,file_input,exports,bitrate,height,
            do_separate,do_transcribe,model_name,language,submit,open_btn,selected_job,cancel_btn,view_btn,clean_btn,
            queue_details,original_audio,video_preview,inst,vocals,transcript,files,
            saved_project,reload_projects,open_project_btn,history_source,reload_history,
            karaoke_video_upload,karaoke_instrumental_upload,video_source_preview,audio_source_preview,
            lyric_input,karaoke_srt_file,lines_btn,ai_btn,song_language,karaoke_model,karaoke_grid,
            preview_timeline,color,placement,font_size,progressive,save_project_btn,export_karaoke_btn,
            output_karaoke_video,karaoke_files,previous,refresh,load,hist_audio,hist_video,hist_inst,
            hist_vocal,hist_txt,hist_files,shut_btn,cancel_shutdown,confirm_shutdown,karaoke_intro,karaoke_warning,hero,source_heading,format_heading,quality_heading,ai_heading,ai_hint,queue_heading,result_heading,history_heading,shutdown_heading,shutdown_confirm,about_content]
        ui_lang.change(fn=translate_controls,inputs=ui_lang,outputs=language_targets,queue=False)
        demo.load(fn=translate_controls,inputs=ui_lang,outputs=language_targets,queue=False)
        gr.HTML('<footer class="af-footer">AUDIOFORGE LOCAL • FEITO PARA USO PESSOAL • SEM TELEMETRIA PRÓPRIA</footer>')
    return demo



def translate_controls(code: str):
    save_language(code)
    en = code == 'en'
    a = lambda pt,eng: eng if en else pt
    updates = [
        gr.update(value=a("❔ Abrir tutorial interativo","❔ Open guided tour")),
        gr.update(label=a('✨ Estúdio','✨ Studio')),
        gr.update(label=a('🎤 Karaoke Video','🎤 Karaoke Video')),
        gr.update(label=a('🕘 Histórico','🕘 History')),
        gr.update(label=a('ℹ️ Sobre','ℹ️ About')),
        gr.update(label=a('Link do YouTube','YouTube link')),
        gr.update(label=a('Enviar áudio ou vídeo do computador','Upload audio or video file')),
        gr.update(label=a('Baixar / exportar','Download / export')),
        gr.update(label=a('MP3 (kbps)','MP3 (kbps)'),choices=[(a('128 — menor','128 — small'),128),(a('192 — equilibrado','192 — balanced'),192),(a('320 — maior','320 — best'),320)]),
        gr.update(label=a('MP4 (resolução máxima)','MP4 (maximum resolution)'),choices=[('Original','original'),(a('Até 720p','Up to 720p'),'720'),(a('Até 1080p','Up to 1080p'),'1080')]),
        gr.update(label=a('🎤 Separar voz e instrumental (WAV + MP3)','🎤 Separate vocals and instrumental (WAV + MP3)')),
        gr.update(label=a('📝 Transcrever áudio (TXT + SRT)','📝 Transcribe audio (TXT + SRT)')),
        gr.update(label=a('Modelo Whisper','Whisper model')),
        gr.update(label=a('Idioma','Language'),choices=[(a('Detectar automaticamente','Auto detect'),'auto'),(a('Português','Portuguese'),'pt'),(a('Inglês','English'),'en'),(a('Espanhol','Spanish'),'es')]),
        gr.update(value=a('＋ Adicionar à fila','＋ Add to queue')),
        gr.update(value=a('📁 Abrir pasta de resultados','📁 Open output folder')),
        gr.update(label=a('Selecionar trabalho','Select job')),
        gr.update(value=a('✕ Cancelar selecionado','✕ Cancel selected')),
        gr.update(value=a('↗ Ver resultado','↗ View result')),
        gr.update(value=a('🧹 Limpar finalizados','🧹 Clear completed')),
        gr.update(label=a('Log do trabalho selecionado','Selected job log')),
        gr.update(label=a('🎧 Áudio original','🎧 Original audio')),
        gr.update(label=a('🎬 Vídeo MP4','🎬 MP4 video')),
        gr.update(label=a('🎹 Instrumental','🎹 Instrumental')),
        gr.update(label=a('🎙️ Somente voz','🎙️ Vocals only')),
        gr.update(label=a('📝 Texto transcrito','📝 Transcript')),
        gr.update(label=a('⬇️ Arquivos prontos para download','⬇️ Download files')),
        gr.update(label=a('Reabrir projeto salvo','Open saved project')),
        gr.update(value=a('↻ Atualizar projetos','↻ Refresh projects')),
        gr.update(value=a('↗ Reabrir projeto','↗ Open project')),
        gr.update(label=a('Usar mídia do histórico','Use history media')),
        gr.update(value=a('↻ Atualizar histórico','↻ Refresh history')),
        gr.update(label=a('Ou enviar vídeo','Or upload video')),
        gr.update(label=a('Ou enviar instrumental','Or upload instrumental')),
        gr.update(label=a('Vídeo selecionado','Selected video')),
        gr.update(label=a('Instrumental selecionado','Selected instrumental')),
        gr.update(label=a('Letra: uma frase por linha','Lyrics: one phrase per line')),
        gr.update(label=a('Ou importar legenda SRT','Or import SRT subtitles')),
        gr.update(value=a('◷ Distribuir tempos (estimativa)','◷ Estimate phrase timing')),
        gr.update(value=a('✦ Sugerir letra/tempos com Whisper (CPU)','✦ Suggest words/timing with Whisper (CPU)')),
        gr.update(label=a('Idioma da música','Song language'),choices=[(a('Automático','Auto detect'),'auto'),(a('Português','Portuguese'),'pt'),('English','en')]),
        gr.update(label=a('Modelo de reconhecimento','Recognition model')),
        gr.update(label=a('Edite cada frase e seus tempos','Edit phrases and timing'),headers=['Start (s)','End (s)','Lyrics'] if en else ['Início (s)','Fim (s)','Letra']),
        gr.update(value=a('◷ Atualizar linha do tempo','◷ Refresh timeline')),
        gr.update(label=a('Cor do destaque','Highlight color'),choices=[(a('Dourado','Gold'),'#FFC857'),(a('Verde','Green'),'#5AF99A'),(a('Ciano','Cyan'),'#64D8FF'),(a('Rosa','Pink'),'#FF86BE')]),
        gr.update(label=a('Posição das legendas','Subtitle position'),choices=[(a('Inferior','Bottom'),'bottom'),(a('Centro','Middle'),'center'),(a('Superior','Top'),'top')]),
        gr.update(label=a('Tamanho da fonte','Font size')),
        gr.update(label=a('Destacar progressivamente as palavras (tempo aproximado)','Progressively highlight words (approximate timing)')),
        gr.update(value=a('💾 Salvar projeto','💾 Save project')),
        gr.update(value=a('🎬 Exportar MP4 de karaokê','🎬 Export karaoke MP4')),
        gr.update(label=a('Karaokê pronto','Rendered karaoke')),
        gr.update(label=a('Baixar vídeo e legenda ASS','Download video and ASS subtitles')),
        gr.update(label=a('Selecionar processamento','Select processing')),
        gr.update(value=a('↻ Atualizar lista','↻ Refresh list')),
        gr.update(value=a('↗ Carregar resultado','↗ Load result')),
        gr.update(label=a('Áudio original','Original audio')),
        gr.update(label=a('Vídeo MP4','MP4 video')),
        gr.update(label=a('Instrumental','Instrumental')),
        gr.update(label=a('Voz','Vocals')),
        gr.update(label=a('Transcrição','Transcript')),
        gr.update(label=a('Arquivos disponíveis','Available files')),
        gr.update(value=a('⏻ Encerrar AudioForge','⏻ Shut down AudioForge')),
        gr.update(value=a('Voltar','Go back')),
        gr.update(value=a('Sim, encerrar aplicativo','Yes, shut down')),
        gr.update(value=a('### Karaoke Video Studio\nUse um processamento do **Histórico** que contenha MP4 + instrumental, ou envie os dois arquivos. Ajuste cada frase antes de exportar.',
                          '### Karaoke Video Studio\nChoose a **History** entry with MP4 + instrumental or upload both files. Review phrase timing before export.')),
        gr.update(value=a('A distribuição é uma **estimativa**, não alinhamento da letra. O Whisper transcreve vocais e pode errar palavras cantadas.',
                          'Evenly distributed timing is an **estimate**, not alignment. Whisper may mishear singing.')),

        gr.update(value=('<section class="af-hero"><div class="af-topline"><span class="af-dot"></span> '+a('LOCAL • PRIVADO • SEM API PAGA','LOCAL • PRIVATE • NO PAID API')+f' <span class="af-version">v{__version__}</span></div><h1>Audio<span>Forge</span> <em>Local</em></h1><p>'+a('Baixe vídeo ou áudio em MP4, MP3 ou WAV, crie instrumentais e transforme fala em texto.','Convert MP3/MP4/WAV, isolate instrumentals and transcribe audio, all locally.')+'</p><div class="af-tags"><span>▶ MP4</span><span>♫ MP3 / WAV</span><span>🎤 Karaoke</span><span>✦ AI</span></div></section>')),
        gr.update(value=a('### 01 / Escolha o material','### 01 / Choose your source')),
        gr.update(value=a('### 02 / Escolha os formatos','### 02 / Choose formats')),
        gr.update(value=a('### 03 / Qualidade da mídia','### 03 / Media quality')),
        gr.update(value=a('### 04 / Ferramentas de IA (opcionais)','### 04 / AI tools (optional)')),
        gr.update(value=a("<p class='af-muted'>Só quer baixar MP3 ou MP4? Desmarque o karaokê. Sem seleção de formatos, as IAs ainda podem gerar seus resultados.</p>","<p class='af-muted'>Need only MP3/MP4? Uncheck the AI operations. AI results do not require selecting an export format.</p>")),
        gr.update(value=a('### 05 / Fila de processamento\nOs itens iniciam automaticamente, um por vez, para não sobrecarregar seu computador.','### 05 / Processing queue\nJobs run automatically one at a time.')),
        gr.update(value=a('### 06 / Resultado selecionado','### 06 / Selected result')),
        gr.update(value=a('### Processamentos anteriores\nO histórico das versões antigas continua disponível em `~/Downloads/AudioForge-Local/`.','### Previous jobs\nOlder jobs remain in `~/Downloads/AudioForge-Local/`.')),
        gr.update(value=a('**Controle do aplicativo**\nFechar a aba não desliga o servidor local.','**Application control**\nClosing the browser tab does not stop the server.')),
        gr.update(value=a('Tem certeza? O AudioForge será encerrado, mas seus arquivos e histórico continuarão salvos.','Are you sure? AudioForge will stop, but your media and history remain saved.')),
        gr.update(value=a('### AudioForge Local v0.4.0\nEditor de vídeos de karaokê, fila, processamento local. Letras cantadas podem ser reconhecidas incorretamente; revise a sincronização antes de exportar.','### AudioForge Local v0.4.0\nKaraoke video editor, queue and local processing. Singing recognition can be inaccurate; review timing before exporting.'))
    ]
    return tuple(updates)


def main(ready_callback=None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    demo = build_interface()
    demo.queue(max_size=12, default_concurrency_limit=1)
    demo.launch(
        server_name="127.0.0.1", server_port=int(os.environ.get("AUDIOFORGE_PORT", "7860")),
        inbrowser=True, share=False, show_error=True, allowed_paths=[str(DATA_DIR)],
        prevent_thread_lock=True, js=TOUR_JS,
        theme=gr.themes.Soft(primary_hue="violet", secondary_hue="cyan"), css=CSS,
    )
    if ready_callback is not None:
        ready_callback()


if __name__ == "__main__":
    from audioforge.single_instance import run_single_instance
    raise SystemExit(run_single_instance(main))
