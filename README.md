# 🎧 AudioForge Local

**Estúdio pessoal em Python para baixar/converter mídia em WAV, MP3 e MP4, separar voz e instrumental e gerar transcrição.** O aplicativo abre em uma interface visual no navegador, mas o servidor e o processamento ficam **no seu próprio computador**.

**Versão atual:** `v0.2.1 — Smart Startup & Guided Tour` · **Plataforma principal:** Ubuntu 22.04+ · **Tecnologias:** Python, Gradio 6, FFmpeg, yt-dlp, Demucs e faster-whisper.

## ✨ Recursos

| Ferramenta | Resultado | Observação |
|---|---|---|
| Download/conversão WAV | `original.wav` | Áudio sem compressão; preserva o recurso da v0.1 |
| **Novo: download/conversão MP3** | `original.mp3` | Áudio padrão em 192 kbps |
| **Novo: download/conversão MP4** | `original.mp4` | **Vídeo original com áudio**; NÃO é vídeo de karaokê |
| Separar voz/instrumental | `voz.wav`, `voz.mp3`, `instrumental.wav`, `instrumental.mp3` | Modelos Demucs executados na CPU |
| Transcrição | `transcricao.txt`, `legendas.srt` | IA faster-whisper na CPU |
| Histórico | Lista de resultados e players para reabrir | Compatível com o histórico da versão anterior |
| Encerrar pela interface | Para o processo Python local | Confirmação em duas etapas; impede encerrar com tarefa ativa |
| **Novo: instância única** | Reabrir a interface pelo mesmo atalho | Evita dois servidores na mesma porta e verifica a instância ativa |
| **Novo: tutorial guiado** | 7 etapas navegáveis | Passos Anterior/Próximo/Pular; você pode reabrir depois |

Você pode marcar **mais de um formato na mesma tarefa**. Para baixar apenas MP3 ou MP4, **desmarque “Separar voz e instrumental”** se não precisar de karaokê. Escolha a entrada: **arquivo local** ou **link do YouTube para conteúdo autorizado**. O projeto não depende de GitHub Pages, Supabase, conta ou API paga.

## 🚀 Instalação (Ubuntu, primeira vez)

1. Extraia o pacote para um caminho permanente, por exemplo `~/Aplicativos/audioforge-local/`.
2. Na pasta extraída, clique com o botão direito → **Abrir no terminal**.
3. Execute:
   ```bash
   bash install.sh
   ```
4. A instalação cria o ambiente `.venv`, instala FFmpeg quando necessário, configura bibliotecas e cria o atalho no **menu de aplicativos do Ubuntu**.
5. Abra **AudioForge Local** pelo menu. A interface será aberta em `http://127.0.0.1:7860`.

Na primeira utilização do Demucs ou do Whisper, seus modelos podem ser baixados pela internet. Bibliotecas de IA e modelos podem exigir vários GB livres. No notebook sem GPU dedicada, use **`tiny` ou `base`** para transcrição; separar instrumentos pode levar vários minutos.

## 🔄 Atualizar da v0.2.0 para v0.2.1 (sem perder histórico)

1. **Encerre primeiro a versão v0.2.0:** no rodapé, clique **Encerrar AudioForge → Sim, encerrar aplicativo**. **Fechar só o Chrome não encerra**. Caso esteja no terminal, pode usar `Ctrl+C`.
2. Descompacte `audioforge-local-v0.2.1.zip`.
3. Abra a **pasta onde o AudioForge está instalado**: a que contém `app.py`, `start.sh` e `.venv/`.
4. Copie **o conteúdo INTERNO** da pasta extraída `audioforge-local-v0.2.1` para **dentro** da pasta já instalada, mesclando as subpastas e substituindo os arquivos com mesmo nome. Isso inclui os novos **`launcher.py` e `audioforge/single_instance.py` e `audioforge/tutorial.py`**.
5. **Não apague `.venv/`** e **não apague `~/Downloads/AudioForge-Local/`**. Não é preciso rodar `install.sh` novamente, pois não alteramos as bibliotecas.
6. Abra **AudioForge Local** pelo mesmo atalho do menu do Ubuntu. Confirme a indicação **v0.2.1** na parte superior.

Se você criou uma pasta de instalação *nova*, e não substituiu a antiga, execute `bash install.sh` na pasta nova para atualizar o atalho; nesse caso há nova instalação de dependências. Para saber para onde o atalho aponta: `grep '^Exec=' ~/.local/share/applications/audioforge-local.desktop`.

**Atenção:** se copiar os arquivos enquanto a v0.2.0 estiver aberta, ela não receberá o bloqueio de instância única retroativamente. Encerre a versão antiga e inicie a nova após copiar.

### Como iniciar no dia a dia

- Procure **AudioForge Local** no menu de aplicativos do Ubuntu, ou clique no mesmo atalho novamente.
- **Se já estiver aberto, o atalho apenas abre outra aba com a mesma interface** (não inicia outro Python nem baixa modelos novamente).
- Se tiver fechado somente a aba, clique no atalho para reabrir.
- Para realmente desligar: **Encerrar AudioForge** no rodapé, ou `Ctrl+C` no terminal que o executa.
- Se a porta `7860` estiver ocupada por um programa **não reconhecido**, o AudioForge não tentará assumir esse programa: exibirá aviso e deixará instruções no log.

### 🧭 Tutorial guiado

Na **primeira execução da v0.2.1** o tutorial aparece automaticamente, com sete etapas:

1. Selecionar vídeo/áudio ou colar link.
2. Escolher WAV, MP3 ou MP4.
3. Ativar (ou desativar) karaokê e transcrição.
4. Iniciar o processamento.
5. Ouvir, copiar texto e baixar arquivos.
6. Reabrir trabalhos no histórico.
7. Encerrar com segurança.

Use **Próximo →**, **← Anterior** ou **Pular tutorial**. As áreas correspondentes ganham destaque na interface e a aba **Histórico** é selecionada quando você chega à sua etapa. Ao terminar/pular, a preferência fica salva **somente no computador**, em `~/.config/audioforge-local/preferences.json`. O botão **Abrir tutorial guiado**, logo abaixo do cabeçalho, permite refazer a visita quantas vezes quiser.

## 🧭 Guia rápido

1. Cole um link autorizado do YouTube **ou** selecione um arquivo local.
2. Em **Baixar / exportar**, marque `WAV`, `MP3`, `MP4` ou uma combinação.
3. Marque **Separar voz e instrumental** e/ou **Transcrever**, se quiser aplicar IA.
4. Clique em **Processar / Baixar** e acompanhe o status. O resultado aparece com player e arquivos para download.
5. Clique em **Abrir pasta de resultados**, se quiser usar os arquivos fora da interface.
6. Na aba **Histórico**, carregue um resultado anterior sem processar de novo.

**Exemplos:**

- **Baixar música em MP3:** marcar **MP3**; desmarcar **WAV**, **MP4**, **Separar** e **Transcrever**.
- **Baixar vídeo em MP4:** marcar **MP4**; desmarcar os demais.
- **Gerar instrumental:** marcar **Separar**; usar WAV opcionalmente. O programa entrega voz + instrumental em WAV/MP3.
- **Baixar vídeo e também MP3:** marcar **MP4 + MP3**. Se houver um vídeo no link, baixa uma vez e extrai o áudio.
- **Transcrever e baixar MP3:** marcar **MP3** e **Transcrever**.

**MP4 exige um vídeo**: não funciona com um arquivo que contenha somente áudio. Alguns links não oferecem opções MP4 adequadas, ou podem estar bloqueados por restrições do YouTube; o programa mostra um erro explicativo. Em vídeos locais com codecs incompatíveis, o FFmpeg pode recodificar para H.264/AAC; isso pode ser lento na CPU.

## ⏻ Como encerrar corretamente

**Fechar o Chrome não encerra o AudioForge.** O navegador só exibe a interface; o processo Python continua executando. Na v0.2.1, clicar no atalho novamente reconhece o processo já aberto e reabre a interface.

- **Abrindo pelo menu do Ubuntu:** role até o rodapé da página → **Encerrar AudioForge** → **Sim, encerrar aplicativo**. O processo é encerrado após mostrar a confirmação, e você pode fechar a aba.
- **Abrindo por terminal:** pressione `Ctrl+C` no terminal, ou use o mesmo botão de encerramento.
- **Enquanto processa um arquivo:** o botão impede o encerramento para não perder o trabalho. Espere a tarefa terminar, depois encerre.

Os resultados e o histórico já salvos **não são apagados** pelo encerramento.

## 📂 Onde ficam os arquivos?

Por padrão: **`~/Downloads/AudioForge-Local/`**. Essa pasta é **a mesma da v0.1.0**, sem migração.

```text
~/Downloads/AudioForge-Local/
├── historico.json
├── 123456789abc/
│   ├── original.mp4        # se MP4 foi escolhido
│   ├── original.mp3        # se MP3 foi escolhido
│   ├── original.wav        # se WAV foi escolhido
│   ├── instrumental.wav    # se separação foi escolhida
│   ├── instrumental.mp3
│   ├── voz.wav
│   ├── voz.mp3
│   ├── transcricao.txt     # se transcrição foi escolhida
│   └── legendas.srt
└── ...
```

Um `original.wav` temporário utilizado apenas pela IA é removido após o processamento quando você não solicita WAV, para economizar espaço. Downloads incompletos podem deixar pastas intermediárias para diagnóstico, mas não aparecem no histórico.

## 🧰 Solução de problemas

| Sintoma | O que fazer |
|---|---|
| Erro ao baixar YouTube | Verifique URL e autorização de uso; plataformas alteram formatos e restrições. Para atualizar a biblioteca: `.venv/bin/python -m pip install -U yt-dlp` |
| MP4 não disponível | O link pode não fornecer fluxo MP4 adequado. Teste outro vídeo autorizado ou arquivo local. |
| Erro de FFmpeg | Execute `bash install.sh` ou `sudo apt install ffmpeg` |
| Erro de módulo Python | Na pasta instalada, execute `bash install.sh` |
| Processamento lento | Vídeos grandes e conversões H.264 consomem CPU. Para transcrição, escolha `tiny`. |
| Página fecha mas aplicativo ainda ativo | Volte a `http://127.0.0.1:7860` e use **Encerrar AudioForge**; ou `Ctrl+C` no terminal. |
| Porta 7860 ocupada | Se for uma **versão antiga**, encerre-a antes de iniciar v0.2.1. Se for outro programa, use `AUDIOFORGE_PORT=7861 bash start.sh` (ainda haverá apenas uma instância AudioForge por usuário). |
| Clique no atalho e nada apareceu | Consulte `~/.cache/audioforge-local/launcher.log` (inicialização pelo menu gráfico). Em terminal, `bash start.sh` mostra mensagens diretamente. |
| Interface já estava aberta | Isso é esperado. O novo atalho reabre `http://127.0.0.1:7860` sem criar outro servidor. |
| Tutorial não aparece | Clique em **Abrir tutorial guiado**. A conclusão anterior é lembrada em `~/.config/audioforge-local/preferences.json`. |

## 🔐 Limites e privacidade

- A interface usa **`127.0.0.1`**; não é publicada na internet. O processo atual mantém apenas um identificador e uma porta de controle **também em `127.0.0.1`**, para a reabertura segura.
- Arquivos locais e transcrições não são enviados a serviços de IA. Ao usar links, o `yt-dlp` acessa o serviço de origem; modelos de IA podem ser baixados da internet na primeira utilização.
- O aplicativo não remove DRM nem promete funcionar para vídeos bloqueados, privados ou protegidos. **Use somente conteúdo próprio/licenciado ou com download e processamento autorizados**. Consulte os [Termos do YouTube](https://www.youtube.com/t/terms).
- **MP4 desta versão é o vídeo original**, não a música instrumental sincronizada em vídeo; isso permanece para uma versão futura.

## 🗂️ Estrutura do projeto

```text
app.py                 # Interface, tutoriais e botão de encerramento
launcher.py            # Inicialização leve com proteção de instância única
assets/style.css       # Design
audioforge/core.py    # Download, FFmpeg, Demucs, Whisper e histórico
audioforge/single_instance.py # Bloqueio, status e reabertura segura
audioforge/tutorial.py        # Etapas e preferências locais do tutorial
audioforge/__init__.py
install.sh             # Instalação Ubuntu, ambiente virtual e atalho
start.sh               # Inicialização pelo menu ou terminal
requirements.txt       # Dependências
README.md              # Este manual
RELEASE_NOTES.md       # Notas e roadmap
GITHUB_PUBLISH.md      # Atualização do repositório pelo navegador
tests/                 # Testes unitários, simulações e teste leve com FFmpeg
```

## 🧪 Testes

Com a instalação já feita, rode (opcional):

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Os testes automatizados não acessam YouTube nem baixam modelos de IA. Nesta versão, há **23 testes automatizados**, incluindo inicialização concorrente em dois processos, identificação de porta ocupada, salvamento do tutorial, conversão real com FFmpeg e teste leve da interface. **A sequência visual dos botões do tutorial ainda deve ser conferida no Chrome do seu Ubuntu**, junto com uma mídia autorizada.

## 🗺️ Roadmap

- **v0.2.1 (atual):** instância única, reabrir pelo atalho e tutorial guiado.
- **v0.3.0:** fila, cancelamento seguro, preferências de qualidade e reprocessamento sem baixar novamente.
- **v0.4.0:** criar **vídeo karaokê MP4** com instrumental e opção de exibir legendas/letra sincronizada.
- **v0.5.0:** processamento em lote e organização de coleções.

## 📜 Licença

Código sob licença MIT (`LICENSE`). As dependências, modelos, mídias e seus direitos mantêm as licenças e termos próprios.
