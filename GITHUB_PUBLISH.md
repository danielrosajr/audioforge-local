# Publicar AudioForge Local v0.2.1 no GitHub pelo navegador

## Dados desta release

| Campo | Valor |
|---|---|
| Repositório | `audioforge-local` |
| Branch | `main` |
| Versão/tag | `v0.2.1` |
| Release title | `AudioForge Local v0.2.1 — Smart Startup & Guided Tour` |
| Commit title | `feat: add single-instance startup and guided onboarding (v0.2.1)` |
| Description do repositório | `Estúdio local em Python para baixar MP3/MP4/WAV, criar karaokê instrumental e transcrever vídeos com IA.` |
| GitHub Pages | Não necessário |

**Descrição estendida do commit (opcional):**

```text
Prevent duplicate Python servers when launching AudioForge again.
Reuse the running local interface and detect port conflicts safely.
Add a guided, seven-step onboarding tutorial with local persistence.
Keep all downloads, transcription, karaoke, and history features intact.
```

## Atualizar usando só o site do GitHub

1. Abra o repositório `audioforge-local` na branch `main` pelo navegador.
2. Extraia o ZIP da v0.2.1 e envie **o conteúdo interno** da pasta para o repositório (não envie o ZIP como código-fonte).
3. Atualize `app.py`, `start.sh`, `audioforge/__init__.py`, `assets/style.css`, `README.md`, `RELEASE_NOTES.md` e `GITHUB_PUBLISH.md`.
4. Adicione os **novos arquivos** `launcher.py`, `audioforge/single_instance.py`, `audioforge/tutorial.py` e `tests/test_startup_tutorial.py`.
5. Não apague `tests/test_app.py`, `tests/test_core.py` ou `tests/test_exports.py`: seguem válidos e presentes no ZIP.
6. Clique em **Commit changes** com o título acima. Se o GitHub não aceitar a substituição de um arquivo existente pelo upload, abra esse arquivo e atualize pelo editor web (ícone do lápis). Para vários arquivos, é possível usar o editor web do repositório, quando disponível.
7. Vá a **Releases → Draft a new release**, crie a tag `v0.2.1` sobre `main` e use o título acima.
8. Cole a descrição abaixo e publique. Se quiser, anexe `audioforge-local-v0.2.1.zip` à release como asset, sem enviá-lo ao código-fonte.

**Nunca envie:** `.venv/`, `~/Downloads/AudioForge-Local/`, histórico real, modelos baixados, imagens pessoais nem preferências em `~/.config/audioforge-local/`.

## Release description (copiar e colar)

```md
# AudioForge Local v0.2.1 — Smart Startup & Guided Tour

Esta versão torna o estúdio local mais fácil de abrir, reabrir e aprender a usar.

### ✨ What's New
- **Single-instance startup:** ao clicar no atalho novamente, AudioForge abre a interface já ativa sem iniciar outro servidor Python.
- **Safer startup:** detecta processos desconhecidos ocupando a porta, em vez de confundi-los com o aplicativo.
- **Guided onboarding:** tutorial interativo com 7 etapas, Anterior/Próximo/Pular e indicação dos controles.
- **First-run memory:** lembra quando o tutorial já foi concluído; permite reabri-lo quando quiser.
- **Startup diagnostics:** arquivo de log para aberturas pelo menu gráfico.

### ✅ Preserved
- MP3, MP4, WAV, vocal/instrumental separation, offline speech transcription and local history.
- Safe shutdown button and Ubuntu launcher.

### 🔄 Upgrade from v0.2.0
Close the old app using its **Encerrar AudioForge** button. Replace/merge the source files in the installed folder, preserving `.venv/`. Start again from the Ubuntu menu. The first launch shows the guided tutorial.

### 🧪 Testing
23 automated tests passed, including real FFmpeg conversion and two-process single-instance verification. Browser-based walkthrough interactions still require validation on the user's Ubuntu setup.

### 🗺️ Next
v0.3.0 — Processing Queue: queue, cancellation, quality preferences and reprocessing.
```
