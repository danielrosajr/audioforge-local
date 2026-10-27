# AudioForge Local v0.4.0 — Karaoke Video Studio & PT/EN

**Tag:** `v0.4.0`  
**Release title:** `AudioForge Local v0.4.0 — Karaoke Video Studio & PT/EN`  
**Commit:** `feat: add karaoke video editor, MP4 export and PT-EN localization (v0.4.0)`

## ✨ What's new / Novidades

- **Karaoke Video Studio:** creates a new karaoke MP4 using an existing video plus a separate instrumental track. / Combina vídeo e instrumental para gerar um novo MP4 com letras.
- **Editable subtitles:** paste one lyric phrase per line, import SRT, edit start/end times and text, and review a visual timeline. / Letras e tempos editáveis por frase.
- **AI-assisted timing:** faster-whisper can propose recognized sung words and phrase times in Portuguese or English, or auto-detect language. Not forced alignment; manual correction is recommended. / Sugestões via IA com revisão manual.
- **ASS karaoke effects:** color, placement, font size, progressive word highlight using an estimated proportional distribution. / Efeito de preenchimento progressivo aproximado.
- **Projects:** save and reopen projects with locally preserved upload files, export video and `.ass` subtitles. / Projetos locais reutilizáveis.
- **Two interface languages:** Portuguese (Brazil) and English selection, preference persisted; guided spotlight tour updated for the editor and both languages. / Interface PT-BR/EN e tutorial atualizado.
- **Existing features preserved:** queue, cancellation, MP3/MP4/WAV, vocals/instrumental separation, TXT/SRT transcription, history, single-instance startup, safe shutdown.

## 🖥️ Install / Atualização

1. Shut down v0.3.0 from the application, not by closing Chrome alone. / Encerre a v0.3.0 no botão do próprio app.
2. Replace application **code files** in the current installation folder with the contents of the v0.4.0 ZIP (`app.py`, `audioforge/`, `assets/`, scripts and documentation).
3. **Preserve `.venv` and `~/Downloads/AudioForge-Local/`**. Dependencies are unchanged; no full reinstall normally required.
4. Open the existing Ubuntu launcher; version should display `v0.4.0`.

## ✅ Validation / Validação

- **36 automated tests passed**, including existing regression tests and a real FFmpeg export with synthetic video and audio, with video+audio streams verified using ffprobe.
- Gradio 6 interface builds successfully and answered an HTTP request with `200 OK`.
- JavaScript tour syntax checked with Node.
- **Not verified:** visual operation of the full tour/editor in the actual Ubuntu Chrome (local Chromium automation blocked by administrator policy); real YouTube downloads; quality of Whisper/Demucs on actual sung music (models were not run in these release tests).

## ⚠️ Known limitations / Limitações

- Karaoke word highlighting is a **visual approximation** distributed within each phrase, not guaranteed word-accurate synchronization.
- AI recognition of singing can be wrong and supplied lyrics are **not automatically force-aligned** to the recording. Review manually.
- The timeline is a visual guide, not yet a draggable video editor. To preview subtitles over the video, export it and watch the resulting MP4.
- Karaoke export requires both video and instrumental and performs CPU-intensive H.264 encoding; it cannot be individually cancelled in this version. Shutdown is blocked during active export.
- Some legacy processing log messages still appear in Portuguese even when English UI is selected.
- Online links depend on platform availability and permissions. Process only media you are authorized to use.

## 🔭 Roadmap

- `v0.4.1` — more responsive subtitle preview, localization refinements.
- `v0.5.0` — possible draggable timeline, forced alignment and media library.
