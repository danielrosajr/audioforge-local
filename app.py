"""AudioForge Local v0.2.1 — instância única e tutorial guiado."""

from __future__ import annotations

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
from audioforge.core import (
    AudioForgeError, DATA_DIR, history_choices, load_history_item, process,
)


PROJECT_DIR = Path(__file__).resolve().parent
CSS = (PROJECT_DIR / "assets" / "style.css").read_text(encoding="utf-8")


ACTIVE_LOCK = threading.Lock()
ACTIVE_JOBS = 0
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
        if ACTIVE_JOBS:
            return f"⚠️ Existem {ACTIVE_JOBS} processamento(s) em execução. Aguarde concluir antes de encerrar."
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


# JS roda apenas no navegador local. Ele procura o destaque da etapa,
# rola suavemente até o controle e nunca lê URLs nem conteúdo de arquivos.
TOUR_JS = r"""() => {
  const app = document.querySelector('gradio-app');
  const root = (app && app.shadowRoot) || document;
  let last = '';
  let pending = false;
  function refresh() {
    pending = false;
    const panel = root.querySelector('#af-tour-panel');
    if (!panel || panel.offsetParent === null) { last = ''; return; }
    const marker = root.querySelector('[id^="af-tour-marker-"]');
    const key = marker?.id?.replace('af-tour-marker-', '') || '';
    if (!key || key === last) return;
    const target = root.querySelector('#af-guide-' + key);
    if (!target) return;
    last = key;
    setTimeout(() => target.scrollIntoView({behavior:'smooth', block:'center'}), 180);
  }
  const observer = new MutationObserver(() => {
    if (!pending) { pending = true; requestAnimationFrame(refresh); }
  });
  observer.observe(root, {subtree:true, childList:true, attributes:false});
  setTimeout(refresh, 350);
}"""


def build_interface() -> gr.Blocks:
    with gr.Blocks(title=f"AudioForge Local • v{__version__}") as demo:
        gr.HTML(f"""
        <section class="af-hero">
          <div class="af-topline"><span class="af-dot"></span> LOCAL • PRIVADO • SEM API PAGA <span class="af-version">v{__version__}</span></div>
          <h1>Audio<span>Forge</span> <em>Local</em></h1>
          <p>Baixe vídeo ou áudio em MP4, MP3 ou WAV, crie instrumentais e transforme fala em texto.</p>
          <div class="af-tags"><span>▶ MP4</span><span>♫ MP3 / WAV</span><span>🎤 Karaokê</span><span>✦ Transcrição com IA</span></div>
        </section>
        """)
        tutorial_open = not tutorial_was_seen()
        open_tour = gr.Button("❔ Abrir tutorial guiado", variant="secondary", size="sm", elem_id="af-tour-launch")
        tour_index = gr.State(0)
        initial_text, initial_marker = tutorial_card(0)
        with gr.Group(visible=tutorial_open, elem_id="af-tour-panel", elem_classes=["af-tour-panel"]) as tour_panel:
            gr.Markdown("### 🧭 Conheça seu estúdio — tutorial interativo")
            tour_body = gr.Markdown(initial_text, elem_classes=["af-tour-description"])
            tour_marker = gr.HTML(initial_marker if tutorial_open else "", show_label=False, container=False)
            with gr.Row():
                tour_prev_btn = gr.Button("← Anterior", interactive=False)
                tour_next_btn = gr.Button("Próximo →", variant="primary")
                tour_skip_btn = gr.Button("Pular tutorial", variant="secondary")
            gr.Markdown("*Os controles indicados ficam destacados na tela. Você pode reabrir este tutorial a qualquer momento.*", elem_classes=["af-muted"])
        with gr.Tabs(selected="studio") as tabs:
            with gr.Tab("✨ Estúdio", id="studio"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, min_width=310):
                        with gr.Group(elem_id="af-guide-source", elem_classes=["af-tour-area"]):
                            gr.Markdown("### 01 / Escolha o material")
                            url = gr.Textbox(label="Link do YouTube", placeholder="https://www.youtube.com/watch?v=...", lines=1,
                                         info="Use somente mídias cujo download e processamento sejam autorizados.")
                            gr.Markdown("<p class='af-or'>— OU —</p>")
                            file_input = gr.File(label="Enviar áudio ou vídeo do computador", type="filepath",
                                                 file_types=["audio", "video"], file_count="single")
                        with gr.Group(elem_id="af-guide-formats", elem_classes=["af-tour-area"]):
                            gr.Markdown("### 02 / Escolha os formatos")
                            exports = gr.CheckboxGroup(
                            label="Baixar / exportar",
                            choices=[("🔊 WAV (áudio sem compressão)", "wav"),
                                     ("🎧 MP3 (áudio leve)", "mp3"),
                                     ("🎬 MP4 (vídeo com áudio)", "mp4")],
                            value=["wav"],
                                info="Você pode marcar mais de um. MP4 requer um vídeo na origem.",
                            )
                        with gr.Group(elem_id="af-guide-ai", elem_classes=["af-tour-area"]):
                            gr.Markdown("### 03 / Ferramentas de IA (opcionais)")
                            do_separate = gr.Checkbox(label="🎤 Separar voz e instrumental (WAV + MP3)", value=True)
                            do_transcribe = gr.Checkbox(label="📝 Transcrever áudio (TXT + SRT)", value=False)
                            gr.Markdown("<p class='af-muted'>Só quer baixar MP3 ou MP4? Desmarque o karaokê. Sem seleção de formatos, as IAs ainda podem gerar seus resultados.</p>")
                            with gr.Accordion("⚙️ Opções de transcrição", open=False):
                                model_name = gr.Dropdown(choices=[("Rápido — tiny", "tiny"), ("Equilibrado — base", "base"),
                                                               ("Mais preciso — small (mais lento)", "small")],
                                                     value="base", label="Modelo Whisper")
                                language = gr.Dropdown(choices=[("Detectar automaticamente", "auto"), ("Português", "pt"),
                                                                 ("Inglês", "en"), ("Espanhol", "es")],
                                                       value="auto", label="Idioma")
                        with gr.Group(elem_id="af-guide-process", elem_classes=["af-tour-area"]):
                            submit = gr.Button("✦ Processar / Baixar", variant="primary", size="lg", elem_classes=["af-action"])
                        open_btn = gr.Button("📁 Abrir pasta de resultados", variant="secondary")
                        folder_hint = gr.Markdown()
                    with gr.Column(scale=6, min_width=330):
                        with gr.Group(elem_id="af-guide-results", elem_classes=["af-tour-area"]):
                            gr.Markdown("### 04 / Resultado")
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
            with gr.Tab("🕘 Histórico", id="history"):
                with gr.Group(elem_id="af-guide-history", elem_classes=["af-tour-area"]):
                    gr.Markdown("### Processamentos anteriores\nO histórico das versões antigas continua disponível em `~/Downloads/AudioForge-Local/`.")
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
            with gr.Tab("ℹ️ Sobre", id="about"):
                gr.Markdown(f"""### AudioForge Local v{__version__}

                **Novidades v0.2.1:** inicialização em instância única, reabertura pelo atalho e tutorial passo a passo. Mantém MP3/MP4/WAV, karaokê, transcrição e encerramento seguro.

                **Privacidade:** interface apenas em `127.0.0.1` (localhost). Operações de IA rodam no seu computador. Links utilizam internet para acesso à fonte e os modelos podem ser baixados no primeiro uso.

                **Limitações:** MP4 não é ainda um vídeo de karaokê; é o vídeo original. Arquivos locais em formatos de vídeo não compatíveis podem precisar de recodificação (lenta na CPU). YouTube pode bloquear determinados links ou não fornecer MP4.

                **Importante:** use apenas conteúdo cujo download e processamento sejam autorizados. Fechar a aba do Chrome não encerra o Python: utilize **Encerrar AudioForge** abaixo.

                **Instalação e upgrade:** consulte o README na pasta do projeto.
                """)
        submit.click(fn=work,
                     inputs=[url, file_input, exports, do_separate, do_transcribe, model_name, language],
                     outputs=outputs + [previous], concurrency_limit=1)
        with gr.Group(elem_id="af-guide-shutdown", elem_classes=["af-shutdown-area", "af-tour-area"]):
            with gr.Row():
                gr.Markdown("**Controle do aplicativo**\nFechar a aba não desliga o servidor local.")
                shut_btn = gr.Button("⏻ Encerrar AudioForge", variant="secondary")
            with gr.Column(visible=False) as confirm_area:
                gr.Markdown("Tem certeza? O AudioForge será encerrado, mas seus arquivos e histórico continuarão salvos.")
                with gr.Row():
                    cancel_shutdown = gr.Button("Voltar", variant="secondary")
                    confirm_shutdown = gr.Button("Sim, encerrar aplicativo", variant="stop")
            shutdown_status = gr.Markdown()
            shut_btn.click(fn=lambda: gr.update(visible=True), outputs=confirm_area, queue=False)
            cancel_shutdown.click(fn=lambda: gr.update(visible=False), outputs=confirm_area, queue=False)
            confirm_shutdown.click(fn=shutdown_app, outputs=shutdown_status, queue=False)
        tour_out = [tour_index, tour_body, tour_marker, tour_prev_btn, tour_next_btn, tour_panel, tabs]
        open_tour.click(fn=tour_start, outputs=tour_out, queue=False)
        tour_prev_btn.click(fn=tour_back, inputs=tour_index, outputs=tour_out, queue=False)
        tour_next_btn.click(fn=tour_next, inputs=tour_index, outputs=tour_out, queue=False)
        tour_skip_btn.click(fn=tour_skip, outputs=[tour_panel, tour_marker], queue=False)
        gr.HTML('<footer class="af-footer">AUDIOFORGE LOCAL • FEITO PARA USO PESSOAL • SEM TELEMETRIA PRÓPRIA</footer>')
    return demo


def main(ready_callback=None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    demo = build_interface()
    demo.queue(max_size=5, default_concurrency_limit=1)
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
