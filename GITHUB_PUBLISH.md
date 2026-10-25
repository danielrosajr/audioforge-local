# Publicar no GitHub — AudioForge Local

Este projeto roda **localmente**. Não configure GitHub Pages, GitHub Actions nem variáveis secretas.

## Informações do repositório

- **Nome sugerido:** `audioforge-local`
- **Description:** `Estúdio local em Python para extrair áudio, separar voz/instrumental e transcrever vídeos com IA, sem APIs pagas.`
- **Visibility:** Public (se quiser mostrar e compartilhar o código) ou Private (se for só backup).
- **README:** já incluído no pacote; **não** marque a opção de criar outro README.
- **.gitignore:** já incluído; **não** gere outro durante a criação.
- **License:** MIT; arquivo `LICENSE` incluído.

## Primeiro upload pelo navegador

1. Crie um repositório vazio no GitHub com nome `audioforge-local`.
2. Descompacte `audioforge-local-v0.1.0.zip` no computador.
3. No repositório vazio, escolha **uploading an existing file** (ou **Add file → Upload files**).
4. Arraste os **arquivos e as pastas de dentro da pasta do projeto**, incluindo `audioforge/`, `assets/` e `tests/`. **Não** envie apenas o arquivo ZIP (o GitHub não extrai automaticamente).
5. Confira se `app.py`, `README.md`, `.gitignore`, `audioforge/core.py`, `assets/style.css` e os scripts aparecem nos caminhos corretos. No gerenciador de arquivos, pressione `Ctrl+H` se `.gitignore` estiver oculto.
6. Na mensagem do commit, use o texto abaixo e confirme **Commit changes**.

**Mensagem do primeiro commit:**

```text
feat: release AudioForge Local v0.1.0 with GUI, karaoke and transcription
```

## Criar a primeira Release

1. Abra **Releases → Create a new release**.
2. **Tag:** `v0.1.0` (crie-a a partir de `main`).
3. **Release title:** `AudioForge Local v0.1.0 — First Cut`.
4. Na descrição, cole o texto abaixo ou use o arquivo `RELEASE_NOTES.md`.
5. Marque como **Latest release** e publique.

### Release description sugerida

```md
## 🎧 AudioForge Local v0.1.0 — First Cut

Primeira versão do meu estúdio pessoal de áudio e vídeo, feito em Python e executado localmente no Ubuntu.

### ✨ Novidades
- Interface clicável e responsiva em Gradio, sem depender de GitHub Pages.
- Integração com yt-dlp para links compatíveis e upload de arquivos locais.
- Extração do áudio original em WAV com FFmpeg.
- Separação de voz e instrumental com Demucs (WAV e MP3).
- Transcrição com faster-whisper e exportação TXT/SRT.
- Reprodução na interface, downloads e histórico persistente.
- Instalador Ubuntu, inicializador e atalho no menu de aplicativos.

### ⚠️ Observações
- Modelos de IA são baixados no primeiro uso.
- O processamento roda em CPU e pode ser lento dependendo do arquivo.
- Links de plataformas podem falhar ou ter restrições; utilize apenas conteúdo autorizado.
- A exportação de vídeo karaokê MP4 fica para uma versão futura.

### 🧭 Próximos passos
- v0.2.0: fila/cancelamento e melhorias no processamento.
- v0.3.0: MP4 com instrumental e legendas/lyrics editáveis.
- v0.4.0: processamento em lote e preferências avançadas.
```

> Dica: crie os lançamentos futuros sempre com tags semânticas (`v0.1.1`, `v0.2.0` etc.) e mensagens como `fix: ...`, `feat: ...` e `docs: ...`.
