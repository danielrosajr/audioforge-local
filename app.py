"""AudioForge Local v0.1.0 — interface web que roda somente no computador."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import gradio as gr

from audioforge import __version__
from audioforge.core import (
    AudioForgeError, DATA_DIR, history_choices, load_history_item, process,
)


PROJECT_DIR = Path(__file__).resolve().parent
CSS = (PROJECT_DIR / "assets" / "style.css").read_text(encoding="utf-8")


def render_result(result: dict) -> tuple:
    return (
        "✅ **Concluído!** Reproduza ou baixe seus arquivos abaixo.",
        f"**Projeto:** {result['title']}\n\n**Pasta:** `{result['folder']}`",
        result["instrumental"], result["vocals"], result["transcript"], result["files"],
    )


def work(url: str, local_file: str | None, do_separate: bool, do_transcribe: bool,
         model_name: str, language: str):
    """Generator + worker: status permanece atualizado, sem travar a interface."""
    events: queue.Queue = queue.Queue()
    recent: list[str] = []
    last_update = ["Preparando processamento..."]

    def status(message: str) -> None:
        events.put(("status", message))

    def worker() -> None:
        try:
            answer = process(url, local_file, do_separate, do_transcribe, model_name, language, status)
            events.put(("done", answer))
        except Exception as exc:
            events.put(("error", str(exc)))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    yield ("⏳ **Preparando...**", "", "", None, None, "", None, gr.update())
    while True:
        try:
            event_type, value = events.get(timeout=2)
        except queue.Empty:
            yield (f"⏳ **{last_update[0]}**", "\n".join(recent[-18:]), "", None, None, "", None, gr.update())
            continue
        if event_type == "status":
            recent.append(str(value))
            last_update[0] = str(value)
            yield (f"⏳ **{value}**", "\n".join(recent[-18:]), "", None, None, "", None, gr.update())
        elif event_type == "error":
            recent.append(f"ERRO: {value}")
            yield ("❌ **Não foi possível concluir.** Confira os detalhes abaixo.",
                   "\n".join(recent[-18:]), "", None, None, "", None, gr.update())
            return
        elif event_type == "done":
            state, info, inst, vocal, txt, files = render_result(value)
            yield (state, "\n".join(recent[-18:]), info, inst, vocal, txt, files,
                   gr.update(choices=history_choices()))
            return


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
        result = load_history_item(item_id)
        return render_result(result)
    except AudioForgeError as exc:
        return f"⚠️ {exc}", "", None, None, "", None


def build_interface() -> gr.Blocks:
    with gr.Blocks(title=f"AudioForge Local • v{__version__}") as demo:
        gr.HTML(f"""
        <section class="af-hero">
          <div class="af-topline"><span class="af-dot"></span> LOCAL • PRIVADO • SEM API PAGA <span class="af-version">v{__version__}</span></div>
          <h1>Audio<span>Forge</span> <em>Local</em></h1>
          <p>Um estúdio pessoal para extrair áudio, separar vocais e transformar fala em texto.</p>
          <div class="af-tags"><span>♫ Karaokê</span><span>✦ Transcrição com IA</span><span>◉ WAV / MP3</span></div>
        </section>
        """)
        with gr.Tabs():
            with gr.Tab("✨ Estúdio"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, min_width=310):
                        gr.Markdown("### 01 / Escolha o material")
                        url = gr.Textbox(label="Link do YouTube", placeholder="https://www.youtube.com/watch?v=...", lines=1,
                                         info="Use somente material próprio ou que você tenha autorização para baixar.")
                        gr.Markdown("<p class='af-or'>— OU —</p>")
                        file_input = gr.File(label="Enviar áudio ou vídeo do computador", type="filepath",
                                             file_types=["audio", "video"], file_count="single")
                        gr.Markdown("### 02 / O que vamos fazer?")
                        do_separate = gr.Checkbox(label="🎤 Separar voz e instrumental (WAV + MP3)", value=True)
                        do_transcribe = gr.Checkbox(label="📝 Transcrever áudio (TXT + SRT)", value=False)
                        gr.Markdown("<p class='af-muted'>O áudio original em WAV é salvo sempre, mesmo sem usar IA.</p>")
                        with gr.Accordion("⚙️ Opções de transcrição", open=False):
                            model_name = gr.Dropdown(choices=[("Rápido — tiny", "tiny"), ("Equilibrado — base", "base"),
                                                               ("Mais preciso — small (mais lento)", "small")],
                                                     value="base", label="Modelo Whisper")
                            language = gr.Dropdown(choices=[("Detectar automaticamente", "auto"), ("Português", "pt"),
                                                             ("Inglês", "en"), ("Espanhol", "es")],
                                                   value="auto", label="Idioma")
                        submit = gr.Button("✦ Processar arquivo", variant="primary", size="lg", elem_classes=["af-action"])
                        open_btn = gr.Button("📁 Abrir pasta de resultados", variant="secondary")
                    with gr.Column(scale=6, min_width=330):
                        gr.Markdown("### 03 / Resultado")
                        status = gr.Markdown("**Pronto para começar.** Escolha um arquivo ou cole uma URL.", elem_classes=["af-status"])
                        project_info = gr.Markdown("Os resultados ficam no seu computador.")
                        with gr.Row():
                            inst = gr.Audio(label="🎹 Instrumental", type="filepath", interactive=False)
                            vocals = gr.Audio(label="🎙️ Somente voz", type="filepath", interactive=False)
                        transcript = gr.Textbox(label="📝 Texto transcrito", lines=7, buttons=["copy"],
                                                placeholder="A transcrição aparecerá aqui...", interactive=False)
                        files = gr.File(label="⬇️ Arquivos prontos para download", file_count="multiple", interactive=False)
                        with gr.Accordion("🛠️ Acompanhamento / log", open=False):
                            log = gr.Textbox(label="Etapas do processamento", lines=7, interactive=False, buttons=["copy"])
                        folder_hint = gr.Markdown(visible=True)
                outputs = [status, log, project_info, inst, vocals, transcript, files]
                open_btn.click(fn=open_folder, outputs=folder_hint)
            with gr.Tab("🕘 Histórico"):
                gr.Markdown("### Seus processamentos anteriores\nOs arquivos ficam em `~/Downloads/AudioForge-Local/` e não são enviados para nenhum servidor do aplicativo.")
                previous = gr.Dropdown(label="Selecionar processamento", choices=history_choices(), value=None,
                                       interactive=True, allow_custom_value=False)
                with gr.Row():
                    refresh = gr.Button("↻ Atualizar lista")
                    load = gr.Button("↗ Carregar resultado", variant="primary")
                hist_status = gr.Markdown()
                hist_info = gr.Markdown()
                with gr.Row():
                    hist_inst = gr.Audio(label="Instrumental", type="filepath", interactive=False)
                    hist_vocal = gr.Audio(label="Voz", type="filepath", interactive=False)
                hist_txt = gr.Textbox(label="Transcrição", interactive=False, buttons=["copy"], lines=5)
                hist_files = gr.File(label="Arquivos disponíveis", interactive=False, file_count="multiple")
                refresh.click(fn=lambda: gr.update(choices=history_choices()), outputs=previous)
                load.click(fn=show_previous, inputs=previous,
                           outputs=[hist_status, hist_info, hist_inst, hist_vocal, hist_txt, hist_files])
            with gr.Tab("ℹ️ Sobre"):
                gr.Markdown(f"""### AudioForge Local {__version__}

                **O que faz:** converte mídia em WAV, separa voz e instrumental com Demucs e faz transcrição com faster-whisper.

                **Privacidade:** o site abre apenas em `127.0.0.1` (seu computador). Os arquivos e o histórico ficam locais. Para links, o yt-dlp acessa a plataforma de origem. Os modelos de IA podem ser baixados da internet no primeiro uso.

                **Importante:** extrair conteúdo do YouTube pode contrariar os termos da plataforma e exigir autorização. Use somente conteúdo cujo download e processamento sejam permitidos. O yt-dlp pode parar de funcionar em certos links.

                **Desempenho:** o Demucs e o Whisper usam CPU por padrão, inclusive em computadores sem GPU dedicada. Em computadores modestos, a separação musical pode demorar.

                **Projeto:** Python + Gradio + FFmpeg + yt-dlp + Demucs + faster-whisper. Confira o README para atualizações e resolução de problemas.
                """)
        submit.click(fn=work, inputs=[url, file_input, do_separate, do_transcribe, model_name, language],
                     outputs=outputs + [previous], concurrency_limit=1)
        gr.HTML('<footer class="af-footer">AUDIOFORGE LOCAL • FEITO PARA USO PESSOAL • SEM TELEMETRIA PRÓPRIA</footer>')
    return demo


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    demo = build_interface()
    demo.queue(max_size=5, default_concurrency_limit=1)
    demo.launch(
        server_name="127.0.0.1", server_port=int(os.environ.get("AUDIOFORGE_PORT", "7860")),
        inbrowser=True, share=False, show_error=True, allowed_paths=[str(DATA_DIR)],
        theme=gr.themes.Soft(primary_hue="violet", secondary_hue="cyan"), css=CSS,
    )


if __name__ == "__main__":
    main()
