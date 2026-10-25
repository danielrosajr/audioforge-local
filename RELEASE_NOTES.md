# AudioForge Local — Releases e roadmap

## v0.2.0 — Media Downloader (2026-10-25)

**Release title:** `AudioForge Local v0.2.0 — Media Downloader`  
**Tag:** `v0.2.0`  
**Commit:** `feat: add MP3 and MP4 exports and safe shutdown (v0.2.0)`

### ✨ Novidades

- **MP3 original:** download direto do áudio e conversão pelo FFmpeg em 192 kbps.
- **MP4 original:** download de vídeo com áudio via yt-dlp, com preferência por formatos compatíveis com MP4; também converte vídeos locais.
- **WAV preservado:** mantém o conversor original do script Python e os recursos da v0.1.0.
- **Formatos combináveis:** WAV, MP3 e MP4 no mesmo processamento; sem downloads duplicados quando MP4 + áudio são escolhidos.
- **Players separados:** áudio original, vídeo MP4, instrumental e vocal.
- **Histórico compatível:** pode reabrir os arquivos da v0.1.0 e os novos vídeos/MP3s.
- **Encerramento pela interface:** botão com confirmação dupla e bloqueio enquanto existe processamento ativo.
- **Melhoria de armazenamento:** remove o WAV temporário da IA caso WAV não seja pedido; não apaga resultados anteriores.
- **19 testes automatizados:** cobertura dos formatos, histórico, interface, proteção de encerramento e conversões FFmpeg pequenas.

### ⚠️ Observações

- **MP4 exportado é o vídeo original, NÃO vídeo de karaokê.** O karaokê continua entregando instrumental/voz em áudio.
- Links do YouTube só funcionam quando acessíveis e cujo download seja permitido; a plataforma pode bloquear links ou não oferecer streams MP4 adequadas.
- Converter alguns vídeos locais para H.264/AAC pode demorar na CPU.
- O fechamento da aba do navegador não encerra o servidor; use **Encerrar AudioForge**.
- Testes de download real por link e processamento de modelos pesados não foram executados no ambiente de desenvolvimento; validar com arquivos e links autorizados no Ubuntu do usuário.

### 🚀 Atualização

Desligue a versão anterior, sobrescreva/mescle os arquivos na mesma pasta de instalação **sem apagar `.venv`** e execute pelo mesmo atalho. Bibliotecas exigidas não mudaram. Histórico mantido em `~/Downloads/AudioForge-Local`.

### 🧭 Próximos passos

- `v0.2.1`: correções de compatibilidade com base nos testes reais.
- `v0.3.0`: filas, cancelamento e seleção de qualidade.
- `v0.4.0`: geração de **vídeo karaokê MP4** com instrumental e letras.
- `v0.5.0`: processamento em lote.

---

## v0.1.0 — First Cut (2026-10-24)

- Primeira interface local em Gradio (`127.0.0.1:7860`).
- Importação de arquivo local e link compatível via `yt-dlp`.
- Extração de WAV com FFmpeg, usando abordagem do script original.
- Separação de instrumental e vocal com Demucs (WAV + MP3).
- Transcrição com faster-whisper, TXT e SRT.
- Histórico local persistente, players e botão para abrir pasta de resultados.
- Instalação para Ubuntu/Linux, atalho de menu e testes básicos.
