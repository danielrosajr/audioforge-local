"""Persist a lightweight, locally stored first-run walkthrough state."""
from __future__ import annotations
import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "audioforge-local"
SETTINGS_FILE = CONFIG_DIR / "preferences.json"

STEPS = (
    ("source", "Escolha o arquivo ou cole um link", "Na aba **Estúdio**, cole o link de uma mídia autorizada **ou** selecione um áudio/vídeo salvo no computador. Você não precisa preencher os dois campos.", "studio"),
    ("formats", "Escolha MP3, MP4 ou WAV", "Marque o formato desejado: **MP3** para ouvir áudio, **MP4** para manter o vídeo ou **WAV** para áudio sem compressão. Pode combinar formatos. MP4 exige origem em vídeo.", "studio"),
    ("ai", "Ative apenas as IAs necessárias", "**Separar voz e instrumental** cria uma base para karaokê; **Transcrever** gera texto e legendas SRT. Para baixar somente MP3/MP4, desmarque as duas opções. Em computadores modestos, Whisper *tiny* é mais rápido.", "studio"),
    ("process", "Inicie o processamento", "Clique em **Processar / Baixar**. O andamento aparece no painel à direita. A primeira execução de uma IA pode baixar o modelo pela internet; depois ele é reutilizado localmente.", "studio"),
    ("results", "Ouça e encontre os resultados", "Os players mostram áudio, vídeo, instrumental e voz conforme o que foi selecionado. Você também pode baixar os arquivos gerados ou abrir a pasta de resultados em **Downloads/AudioForge-Local**.", "studio"),
    ("history", "Reabra trabalhos sem refazer o download", "Na aba **Histórico**, clique em **Atualizar lista**, selecione um processamento e escolha **Carregar resultado**. O histórico anterior é preservado.", "history"),
    ("shutdown", "Encerre corretamente e volte quando quiser", "**Fechar a aba do Chrome não encerra o servidor.** Ao terminar, use **Encerrar AudioForge** e confirme. Depois, inicie pelo menu do Ubuntu. Clicar no atalho enquanto o app já está aberto apenas reabre a interface.", "studio"),
)


def tutorial_was_seen() -> bool:
    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return saved.get("tutorial_seen") is True
    except (OSError, ValueError, AttributeError):
        return False


def finish_tutorial() -> None:
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    data = {}
    try:
        loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data = loaded
    except (OSError, ValueError):
        pass
    data["tutorial_seen"] = True
    tmp = SETTINGS_FILE.with_name(f"preferences.{os.getpid()}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(tmp, SETTINGS_FILE)
    finally:
        tmp.unlink(missing_ok=True)


def tutorial_card(index: int) -> tuple[str, str]:
    marker, heading, detail, _tab = STEPS[index]
    content = f"**PASSO {index + 1} DE {len(STEPS)}** · {heading}\n\n{detail}"
    # Marker is fixed, never derived from a user-provided value.
    return content, f'<span id="af-tour-marker-{marker}" hidden></span>'
