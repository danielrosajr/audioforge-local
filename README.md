# 🎧 AudioForge Local

**Um estúdio pessoal de áudio e vídeo, 100% local no Ubuntu/Linux.** Extraia WAV, separe voz de instrumental para karaokê e transforme áudio em texto usando modelos de IA que rodam no seu computador.

> **Versão:** `v0.1.0 — First Cut` · **Tecnologias:** Python 3.10+, Gradio 6, yt-dlp, FFmpeg, Demucs, faster-whisper.

## ✨ O que faz

| Recurso | Entrada | Saída |
|---|---|---|
| Extrair áudio | Arquivo local ou link compatível | `original.wav` |
| Separar voz e instrumental | Áudio/vídeo | `instrumental.wav`, `instrumental.mp3`, `voz.wav`, `voz.mp3` |
| Transcrever | Áudio/vídeo | `transcricao.txt`, `legendas.srt` |
| Rever projetos | Histórico persistente | Players, texto copiável, links para arquivos |

- Interface clicável no navegador; **não é um site público**.
- CPU por padrão (não exige placa NVIDIA).
- **Sem API paga, sem Supabase, sem criação de conta.** A primeira utilização das IAs requer download dos modelos.
- As operações de IA rodam localmente; acesso à internet é usado para baixar links autorizados e pesos de modelo.

## 🚀 Instalação — Ubuntu 22.04+ (uma vez só)

1. Baixe o ZIP do projeto e extraia para uma pasta permanente, por exemplo `~/Aplicativos/audioforge-local/`.
2. Abra essa pasta no gerenciador de arquivos. Clique com o botão direito e escolha **Abrir no terminal**. **Na primeira instalação apenas**, execute:

   ```bash
   bash install.sh
   ```

3. Aguarde a instalação do FFmpeg (se necessário), ambiente Python e bibliotecas. O script configura um atalho **AudioForge Local** no menu de aplicativos.
4. Depois disso, abra **AudioForge Local** pelo menu de aplicativos, sem terminal. Como alternativa, execute `start.sh` pelo gerenciador de arquivos (a opção “Executar como programa” pode depender do gerenciador).
5. Seu navegador abrirá `http://127.0.0.1:7860` automaticamente.

> A instalação inicial baixa bibliotecas grandes como PyTorch CPU. Precisa de internet e alguns GB livres no disco. O primeiro uso de Demucs ou Whisper também baixa um modelo. Deixe a pasta do projeto no mesmo lugar depois de instalar: o atalho utiliza esse caminho.

### Atualização

Para atualizar no futuro: substitua os arquivos do projeto pelos da nova versão, **sem apagar a pasta `.venv`**. Quando mudarem dependências, execute `bash install.sh` novamente. O histórico está fora do repositório, em `~/Downloads/AudioForge-Local`.

### Linux: se quiser iniciar manualmente

```bash
bash start.sh
```

Para interromper o servidor iniciado pelo terminal, pressione `Ctrl+C`. Fechar apenas a aba do navegador não encerra o servidor.

## 🎛️ Como usar

1. Na aba **Estúdio**, cole uma URL permitida do YouTube **ou** envie um arquivo de áudio/vídeo.
2. Marque **Separar voz e instrumental** e/ou **Transcrever áudio**. Se deixar as duas desmarcadas, gera apenas WAV.
3. (Opcional) Em **Opções de transcrição**, escolha idioma e modelo (`tiny`, `base` ou `small`). `base` é a opção padrão.
4. Clique em **Processar arquivo**. Acompanhe o status e abra o log quando necessário.
5. Reproduza o instrumental e os vocais, copie a transcrição ou baixe os arquivos.
6. Use a aba **Histórico** para abrir os resultados antigos.

### Onde ficam os arquivos?

```text
~/Downloads/AudioForge-Local/
├── historico.json
├── <id-aleatorio>/
│   ├── original.wav
│   ├── instrumental.wav        # caso separação seja escolhida
│   ├── instrumental.mp3
│   ├── voz.wav
│   ├── voz.mp3
│   ├── transcricao.txt         # caso transcrição seja escolhida
│   └── legendas.srt
└── ...
```

Para mudar a pasta, defina a variável de ambiente `AUDIOFORGE_HOME` **antes** de abrir o aplicativo. Para mudar a porta padrão `7860`, use `AUDIOFORGE_PORT`.

## 🧠 Modelos, qualidade e limitações

- **Demucs (`htdemucs`)**: separa voz e acompanhamento em duas faixas. Nem toda voz é removida completamente; instrumentos podem perder qualidade. Opera em CPU e pode demorar muitos minutos dependendo do hardware e da duração.
- **faster-whisper**: transcrição por IA local. `tiny` é leve/rápido; `base` equilibra velocidade e precisão; `small` pode melhorar resultados, mas aumenta tempo/memória. Letras cantadas e música alta são particularmente difíceis.
- **yt-dlp**: nem toda URL funciona; mudanças no site, restrições e login podem bloquear operações. Esta versão **não** tenta contornar DRM nem disponibiliza armazenamento online.
- **Vídeo karaokê em MP4 e legendas sincronizadas na imagem** ainda **não** estão implementados. O modo karaokê atual gera **áudio instrumental**, não vídeo.

## ⚠️ Direitos autorais e plataformas

Utilize somente mídias próprias, licenciadas ou cuja extração/processamento esteja autorizada. O YouTube pode restringir download de conteúdo, inclusive para uso pessoal, salvo quando autorizado pelos próprios termos ou titulares. A disponibilidade técnica do recurso não é garantia de permissão de uso. Consulte [Termos do YouTube](https://www.youtube.com/t/terms).

## 🧰 Solução de problemas

**`FFmpeg não encontrado`** — execute `sudo apt install ffmpeg` e tente novamente.

**`No module named ...`** — verifique se `bash install.sh` concluiu sem erros. Inicie sempre por `start.sh`, que usa o Python da pasta `.venv`.

**Erro do yt-dlp** — teste um arquivo local para confirmar que as funções de IA funcionam. Depois, atualize a biblioteca com `.venv/bin/python -m pip install -U yt-dlp`. Alguns links podem não funcionar.

**Demucs/Whisper muito lentos** — isto é esperado em CPU, principalmente com vídeos longos. Para transcrição, selecione `tiny` e teste arquivos curtos primeiro.

**Porta em uso** — execute `AUDIOFORGE_PORT=7861 bash start.sh`.

**Não abre pelo atalho** — reinstale o atalho com `bash install.sh`, a partir da pasta permanente. O inicializador funciona sem terminal apenas depois da instalação.

## 📂 Estrutura do código

```text
app.py                 # Interface Gradio
assets/style.css       # Design da interface
audioforge/core.py     # yt-dlp, FFmpeg, Demucs, Whisper e histórico
audioforge/__init__.py # Versão
install.sh             # Instalador (CPU/Ubuntu) + atalho
start.sh               # Inicializador de um clique
requirements.txt       # Dependências do Python
RELEASE_NOTES.md       # Histórico de versões
tests/                 # Testes do motor
```

## 🗺️ Roadmap

- **v0.2.0:** fila detalhada, cancelamento real de tarefas, reprocessamento sem novo download.
- **v0.3.0:** exportação de vídeo MP4 para karaokê, letra revisável sincronizada.
- **v0.4.0:** processamento em lote, coleções e configuração de modelos.

## 🧪 Testes básicos

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Eles não fazem download dos modelos; testam os componentes locais e o fluxo básico com simulação de IA. Execute testes reais de música e transcrição na máquina de destino.

## 📜 Licença

Código disponibilizado sob licença MIT (consulte `LICENSE`). Modelos, fontes de mídia e bibliotecas mantêm suas próprias licenças e termos.
