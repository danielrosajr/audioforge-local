# Release notes

## v0.1.0 — First Cut (2026-10-24)

### Funcionalidades
- Interface local visual feita em Gradio, com execução no navegador (`127.0.0.1:7860`).
- Importação por arquivo de áudio/vídeo ou link compatível do YouTube, reaproveitando a abordagem `yt_dlp.YoutubeDL` do script original.
- Extração/conversão automática para `original.wav` usando FFmpeg.
- Separação de voz e instrumental com Demucs (`htdemucs`, CPU), exportando WAV e MP3.
- Transcrição por faster-whisper (tiny, base, small; detecção automática/idiomas), exportando TXT e SRT.
- Players para ouvir instrumental e vocais, botões de download e transcrição copiável.
- Histórico persistente local, com possibilidade de reabrir resultados anteriores.
- Pasta de resultados em `~/Downloads/AudioForge-Local/`, com botão para abri-la.
- Scripts de instalação e inicialização no Ubuntu; atalho no menu de aplicativos.
- Processamento em fila, mensagens de acompanhamento e tratamento de falhas comuns.

### Limitações conhecidas
- Executa somente em CPU; em notebooks modestos, Demucs e Whisper podem demorar.
- A primeira execução das IAs baixa pesos de modelo, exigindo internet e espaço no disco.
- yt-dlp não garante compatibilidade com qualquer vídeo; vídeos bloqueados e protegidos podem falhar.
- Não gera vídeo MP4 de karaokê nem letra sincronizada sobre vídeo nesta versão.
- Isolamento vocal pode deixar artefatos; transcrição de músicas pode ser imprecisa.
- Testes automatizados cobrem funções básicas, mas os modelos completos precisam ser validados na máquina de destino.

### Próximas versões (propostas)
- v0.2.0 — Fila de tarefas, botão de cancelar, detecção de arquivos já processados e opções de qualidade.
- v0.3.0 — Geração de vídeo MP4 com instrumental e sincronização de letras revisáveis.
- v0.4.0 — Exportação por lote, pastas favoritas e personalização de modelos.
