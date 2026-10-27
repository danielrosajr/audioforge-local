# AudioForge Local

**A local-first Python media studio** / **Estúdio pessoal de mídia em Python**.

**Versão:** `v0.4.0 — Karaoke Video Studio & PT/EN`  
**Interface:** Português (Brasil) 🇧🇷 / English 🇺🇸  
**Execução:** Ubuntu/Linux, sem servidor público e sem APIs pagas de IA.

## Novidades da v0.4.0

- 🎤 **Karaoke Video Studio**: combina **vídeo MP4** e **faixa instrumental** em um novo MP4 com letras sobrepostas.
- 📝 **Editor de frases**: cole uma letra (uma frase por linha), importe SRT, ou peça sugestões de texto e tempos ao faster-whisper. **Revise as frases**: a IA pode errar letras cantadas.
- ⏱️ **Tabela editável**: início, fim e conteúdo de cada frase; linha do tempo visual para conferir o posicionamento antes da exportação.
- 🌈 **Efeitos**: cor de destaque, posição superior/central/inferior, tamanho da fonte e preenchimento progressivo das palavras por meio de legendas **ASS**. O preenchimento é **aproximado** dentro de cada frase, não um alinhamento fonético preciso palavra por palavra.
- 💾 **Projetos locais reutilizáveis**: salve, reabra e continue a edição posteriormente. Arquivos enviados pelo navegador são copiados para uma pasta persistente ao salvar o projeto.
- 🌎 **Interface PT-BR/EN**: seletor de idioma no topo, preferência salva em `~/.config/audioforge-local/preferences.json`. O tutorial spotlight também possui orientações em inglês e novas etapas do editor. Alguns logs legados do motor continuam em português.
- 🎼 **Música PT/EN**: idioma automático, português ou inglês para sugestões de transcrição via faster-whisper. A separação instrumental Demucs independe do idioma.

Permanecem as funções da v0.3: conversão/download de links autorizados e arquivos em **MP3/MP4/WAV**, fila FIFO, cancelamento de trabalhos, Demucs para separar voz/instrumental, faster-whisper para TXT/SRT, histórico e abertura em instância única. A renderização de karaokê espera a fila estar vazia para evitar disputar CPU com outro processamento.

## Requisitos

- Ubuntu/Linux e **Python 3.10+**.
- `ffmpeg` e `ffprobe` instalados; o FFmpeg deve ter filtro `ass` (libass). Teste com `ffmpeg -filters | grep ' ass '`.
- Internet no primeiro uso para instalar dependências/baixar modelos; uso de arquivo local e inferência de IA não exigem servidor remoto depois que os modelos estiverem disponíveis.
- A edição e exportação usam CPU; vídeos longos podem ser lentos em notebooks sem GPU e precisam de espaço em disco.

## Instalação nova

1. Extraia o arquivo ZIP numa pasta **permanente** (por exemplo `~/Aplicativos/audioforge-local`).
2. Abra um terminal nessa pasta e execute **uma vez**:

   ```bash
   bash install.sh
   ```

3. Depois procure **AudioForge Local** no menu de aplicativos do Ubuntu e clique. O Gradio abrirá no Chrome ou navegador padrão em `http://127.0.0.1:7860`.

## Atualizar v0.3.0 → v0.4.0

1. Na v0.3.0, clique em **Encerrar AudioForge** e confirme. **Fechar apenas a aba do Chrome não encerra o servidor.**
2. Extraia o novo ZIP. Copie o **conteúdo** de `audioforge-local-v0.4.0/` para a pasta **já instalada**, sobrescrevendo `app.py`, subpastas `audioforge/`, `assets/`, testes e documentação.
3. **Não apague `.venv` e nem `~/Downloads/AudioForge-Local/`**. A pasta de resultados contém seu histórico e as mídias. Como não entraram dependências obrigatórias novas, normalmente não precisa reinstalar; se faltar algum pacote, execute `bash install.sh` na pasta instalada.
4. Abra o atalho existente pelo menu Ubuntu e confira a versão `v0.4.0`.

Para localizar a pasta usada pelo atalho:

```bash
grep '^Path=' ~/.local/share/applications/audioforge-local.desktop
```

Se extrair o ZIP em uma **pasta diferente** sem copiar para a instalação existente, o atalho continuará abrindo a versão antiga.

## Fluxo recomendado para criar um vídeo de karaokê

1. Na aba **Estúdio / Studio**, escolha vídeo local ou link autorizado. Selecione **MP4** e marque **Separar voz e instrumental**. Adicione à fila.
2. Aguarde a conclusão; clique em **Ver resultado** ou vá ao **Histórico**.
3. Abra **Karaoke Video** e escolha esse resultado em **Usar mídia do histórico**. Alternativamente, selecione arquivos independentes de vídeo e instrumental pelos botões de upload.
4. Em **Letra**, cole uma frase por linha ou importe um `.srt`. Se houver SRT no processamento do Histórico e o campo Letra estiver vazio, o editor pode carregá-lo automaticamente.
5. Clique **Distribuir tempos** para gerar uma estimativa inicial **uniforme** conforme a duração; **isso NÃO sincroniza de verdade**. Ou use **Sugerir letra/tempos com Whisper** para estimar frases a partir do vocal separado (quando existir), senão a partir do vídeo original. Escolha o idioma da música (`Auto`, `Português`, `English`) e o modelo (`tiny`, `base`, `small`). Os resultados da IA substituem o texto da tabela; confira diferenças para a letra original.
6. Edite a **tabela de início/fim e letras**. Clique em **Atualizar linha do tempo** para conferir a distribuição visual. Frases sobrepostas podem aparecer simultaneamente; revise conflitos.
7. Escolha cor, posição da legenda, tamanho da fonte e destaque progressivo aproximado. Clique em **Salvar projeto** e depois em **Exportar MP4 de karaokê**.
8. O editor gera `karaoke.mp4` e `karaoke.ass`. Assista no player e faça ajustes quando necessário. Você pode reabrir o projeto pelo seletor **Reabrir projeto salvo** e exportar de novo.

### Onde ficam os arquivos

- Resultados do estúdio e histórico: `~/Downloads/AudioForge-Local/`.
- Projetos de karaokê: `~/Downloads/AudioForge-Local/karaoke-projects/<id>/`.
- Cada projeto tem `project.json` e, após a exportação, `karaoke.ass` e `karaoke.mp4`.
- Se um vídeo/instrumental foi carregado por upload, ao salvar o projeto ele é copiado para a pasta do projeto para continuar disponível depois. Isso pode usar espaço significativo. Se vier do histórico, o arquivo já é persistente e não é duplicado.
- Preferência de idioma: `~/.config/audioforge-local/preferences.json`. O tutorial registra a exibição no armazenamento do navegador.

### Exemplo de letra (sem timestamps)

```text
Primeira frase da música
Segunda frase da música
Third verse in English
```

**Importante:** texto de entrada no editor não é tradução automática. Música bilíngue também pode ser editada manualmente; Whisper com auto-detecção em faixas misturadas pode precisar de revisão adicional.

## Privacidade, permissões e limites

- A interface escuta apenas `127.0.0.1`; os modelos de IA rodam no computador sem API paga. Links online e download de modelos exigem internet.
- Use somente material cujo download e edição sejam autorizados. Links do YouTube dependem das permissões e restrições da plataforma e podem falhar.
- A **exportação é real**, mas o editor de v0.4.0 **não arrasta palavras individualmente** nem faz sincronização perfeita da letra fornecida. A sincronização é ajustada **por frase** em uma tabela; o preenchimento por palavra distribui o tempo proporcionalmente ao comprimento da palavra (efeito visual ASS).
- A **prévia com letra sobre vídeo** aparece após renderizar o MP4. A linha do tempo oferece uma prévia estrutural antes de renderizar, não uma sobreposição em tempo real.
- O editor v0.4.0 renderiza um MP4 por vez, sem suporte a cancelar a renderização individualmente. O botão de desligar é bloqueado enquanto a exportação estiver em curso. Aguarde o fim antes de encerrar.
- Para vídeos longos, a codificação H.264 com FFmpeg pode levar bastante tempo na CPU.
- Projetos ficam locais; não compartilhe a pasta de resultados nem envie vídeos, músicas, logs ou arquivos privados para o GitHub.

## Encerrar e reabrir

Clique **Encerrar AudioForge** → confirmação. Para abrir de novo, use **AudioForge Local** no menu Ubuntu. Se já existir uma instância, o atalho deverá reabrir a interface existente, evitando conflito de porta.

## Testes

```bash
.venv/bin/python -m unittest discover -s tests -v
```

O projeto inclui testes de exportação FFmpeg de verdade com vídeo sintético sem material protegido, além de testes de compatibilidade da fila, histórico, idioma e ASS. Não requer downloads reais nem a execução de modelos de IA pesados para os testes padrão.

## English quick start

1. Install with `bash install.sh` (once), then launch **AudioForge Local** from your Ubuntu application menu.
2. Switch **UI Language → English** at the top.
3. In **Studio**, process a video with **MP4** + **Separate vocals and instrumental**.
4. In **Karaoke Video**, choose that History item, import or type lyrics, select **Song Language → English** (or Auto), and generate estimated phrase timing.
5. Review each row in the timing table, **Save project**, then **Export karaoke MP4**. The result is a new video with the original video's visuals, instrumental audio and karaoke subtitles.
6. **Shut down AudioForge** when finished. Closing the browser tab alone will not stop the local Python service.

**Caution:** Singing recognition can be inaccurate. Word highlighting is approximate; manually adjust phrase timing for best results. Only use authorized media.

## Roadmap

- ✅ **v0.3.0** — Processing Queue & Spotlight Tour.
- ✅ **v0.4.0** — Karaoke Video Studio, editable phrase timing, projects, MP4 export and PT/EN.
- ⏭️ **v0.4.1** — Polish: richer live preview and more consistent translations in legacy logs.
- 💡 **v0.5.0** — Optional forced-alignment/word-level sync, draggable timeline and batch library (future study; not yet implemented).

## Tecnologias / Technologies

Python · Gradio 6 · yt-dlp · FFmpeg/libass · Demucs · faster-whisper

## Licença / License

MIT — see [`LICENSE`](LICENSE).
