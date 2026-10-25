# AudioForge Local v0.2.1 — Smart Startup & Guided Tour

**Tag:** `v0.2.1`  
**Commit:** `feat: add single-instance startup and guided onboarding (v0.2.1)`  
**Release title:** `AudioForge Local v0.2.1 — Smart Startup & Guided Tour`

## ✨ Novidades

- **Instância única:** clicar duas vezes no atalho não cria dois servidores Python. Se houver um AudioForge v0.2.1 aberto, outro clique reutiliza a instância, abrindo a interface no navegador.
- **Proteção de porta:** quando a porta configurada estiver ocupada por um processo não reconhecido (inclusive versão anterior do app), não se conecta automaticamente a esse processo e mostra mensagem de diagnóstico.
- **Inicializador leve:** `launcher.py` verifica bloqueio/instância antes de carregar a interface Gradio; funciona tanto via `start.sh` quanto por `python app.py`.
- **Tutorial guiado em 7 etapas:** navegar com **Anterior / Próximo / Pular**, ver destaque da área atual e visitar a aba Histórico automaticamente.
- **Tutorial na primeira execução:** conclusão ou pulo lembrados no computador. É possível reabrir pelo botão **Abrir tutorial guiado**.
- **Log pelo menu:** mensagens de inicialização ficam em `~/.cache/audioforge-local/launcher.log` quando não há terminal visível.
- **Compatibilidade:** mesmas dependências e mesma pasta de downloads/histórico da v0.2.0.

## ✅ Continua disponível

- Downloads/conversões MP3 (192 kbps), MP4 e WAV.
- Instrumental e voz separados por Demucs (MP3 + WAV).
- Transcrição local com faster-whisper (TXT + SRT).
- Histórico local e players de mídia.
- Encerramento seguro com confirmação, bloqueado durante trabalhos ativos.

## 🔄 Atualizar da v0.2.0

1. Encerre a v0.2.0 **pelo botão Encerrar AudioForge** (fechar apenas o Chrome não encerra o Python).
2. Extraia o ZIP e copie o **conteúdo interno** do pacote para a pasta já instalada, substituindo/mesclando os arquivos e mantendo `.venv/`.
3. Confira que **`launcher.py`**, **`audioforge/single_instance.py`** e **`audioforge/tutorial.py`** foram copiados.
4. Abra pelo mesmo atalho do Ubuntu. A versão exibida será **v0.2.1** e o tutorial aparecerá na primeira abertura.
5. Não é necessário rodar `install.sh` novamente para uma atualização na mesma pasta.

**Dados preservados:** `~/Downloads/AudioForge-Local/` e todos os trabalhos anteriores. Preferência do tutorial: `~/.config/audioforge-local/preferences.json`.

## 🧪 Testes e limitações

- **23 testes automatizados passaram**, incluindo instância única entre dois processos, detecção de conflito, estado do tutorial, exportações e FFmpeg real.
- Servidor Gradio aberto por um primeiro processo e reutilizado por outro processo com sucesso; a finalização liberou os arquivos de controle.
- A navegação visual completa do tutorial não pôde ser validada dentro de um Chrome conectado a esta sessão; teste os botões no seu Ubuntu.
- A primeira abertura de Demucs/Whisper pode baixar modelos e levar mais tempo. Links do YouTube dependem das restrições da plataforma e de autorização de uso. A versão MP4 corresponde ao vídeo original, não ao karaokê.

## 🗺️ Roadmap

- **v0.3.0 — Processing Queue:** fila, cancelamento de tarefas, qualidade de exportação e reprocessamento sem novo download.
- **v0.4.0 — Karaoke Video:** exportar vídeo MP4 com áudio instrumental e opção de letra/legenda sincronizada.
- **v0.5.0 — Media Library:** lotes, filtros e coleções locais.
