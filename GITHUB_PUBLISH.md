# Publicar AudioForge Local v0.4.0 no GitHub (pelo navegador)

## Repository

**Nome:** `audioforge-local`  
**Description:** `Local Python media studio: MP3/MP4/WAV, vocal separation, transcription and bilingual karaoke video editor (PT/EN).`  
**Topics:** `python`, `gradio`, `karaoke`, `ffmpeg`, `faster-whisper`, `demucs`, `audio-processing`, `video-editor`, `local-first`, `pt-br`  
**Visibility:** `Public` ou `Private`, a seu critério.  
**License:** `MIT` (já incluída).  
**GitHub Pages:** não necessário.

## Commit

**Título:**

```text
feat: add karaoke video editor, MP4 export and PT-EN localization (v0.4.0)
```

**Descrição opcional:**

```text
- Add karaoke MP4 rendering with instrumental audio and ASS subtitles
- Add editable phrase timing, SRT import and AI timing suggestions for PT/EN songs
- Add local project save/open and configurable karaoke effects
- Add English UI option and bilingual spotlight walkthrough
- Preserve processing queue, download formats, transcription, history and smart startup
- Add FFmpeg smoke tests and update README/release documentation
```

## Release

**Tag:** `v0.4.0`  
**Title:** `AudioForge Local v0.4.0 — Karaoke Video Studio & PT/EN`  
**Release description:** copie o conteúdo de `RELEASE_NOTES.md`.

## Pelo navegador

1. No repositório `audioforge-local`, atualize os arquivos de código usando **Add file → Upload files** para arquivos novos, e edição/substituição dos existentes quando necessário. Garanta que a estrutura de `audioforge/`, `assets/` e `tests/` permaneça idêntica à do ZIP.
2. Faça commit com a mensagem acima na `main`.
3. Em **Releases → Draft a new release**, crie a tag `v0.4.0` sobre `main`, cole o título e as notas da release.
4. Anexe o ZIP como asset de release se quiser facilitar o backup/download de futuras instalações.

**Não suba** `.venv/`, `__pycache__/`, dados do navegador, pastas de resultados, `historico.json`, vídeos/músicas de terceiros, arquivos temporários nem modelos de IA baixados. O `.gitignore` cobre a maioria desses casos, mas uploads pelo navegador devem ser conferidos manualmente.

## Atualização no Ubuntu

O repositório é um backup do código, não um instalador automático. Para atualizar o aplicativo que já está funcionando no seu notebook, encerre a versão anterior, substitua os arquivos de código e mantenha `.venv` e `~/Downloads/AudioForge-Local/`. Consulte `README.md`.
