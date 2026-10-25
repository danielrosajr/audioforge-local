# Publicação da v0.2.0 no GitHub (pelo navegador)

O AudioForge é **local**. Não habilite GitHub Pages nem hospede seus áudios no repositório.

## Dados do repositório

| Campo | Valor |
|---|---|
| Nome do repositório | `audioforge-local` |
| Description | `Estúdio local em Python para baixar MP3/MP4/WAV, criar instrumental com IA e transcrever áudio e vídeo.` |
| Versão | `v0.2.0` |
| Tag | `v0.2.0` |
| Release title | `AudioForge Local v0.2.0 — Media Downloader` |
| Mensagem do commit | `feat: add MP3 and MP4 exports and safe shutdown (v0.2.0)` |
| Visibilidade | Pública ou privada, conforme sua preferência |

## Atualizar um repositório que já tem a v0.1.0

1. Abra seu repositório `audioforge-local` no navegador e entre na branch principal (`main`).
2. Descompacte o novo arquivo ZIP e copie o **conteúdo interno** da pasta `audioforge-local-v0.2.0` para o repositório pelo recurso **Add file → Upload files**.
3. Confirme substituir os arquivos já existentes. Caso o GitHub não permita sobrescrever pelo upload web na sua interface, edite os arquivos existentes com o ícone de lápis ou use a opção de upload via navegador que aceite sobrescrever arquivos com o mesmo caminho.
4. Os arquivos alterados incluem `app.py`, `audioforge/core.py`, `audioforge/__init__.py`, `assets/style.css`, `README.md`, `RELEASE_NOTES.md`, `GITHUB_PUBLISH.md`; os novos incluem `tests/test_exports.py` e `tests/test_app.py`.
5. Confira se `.gitignore`, `LICENSE`, `install.sh`, `start.sh` e `requirements.txt` continuam presentes.
6. Use a mensagem de commit:

   ```text
   feat: add MP3 and MP4 exports and safe shutdown (v0.2.0)
   ```

**Não envie:** `.venv/`, arquivos de áudio/vídeo pessoais, `historico.json`, pesos/modelos de IA ou pastas `__pycache__/`. O `.gitignore` já exclui a maioria desses arquivos.

## Criar a nova release

1. Abra **Releases → Draft a new release**.
2. Crie a tag `v0.2.0` a partir de `main`.
3. Coloque o título `AudioForge Local v0.2.0 — Media Downloader`.
4. Cole a descrição abaixo.
5. Se quiser disponibilizar a instalação completa como anexo, adicione `audioforge-local-v0.2.0.zip` como **Release asset** (opcional, não precisa commitar o ZIP no repositório).
6. Publique como release mais recente.

### Release description (pronta para copiar)

```md
## 🎧 AudioForge Local v0.2.0 — Media Downloader

Mais controle sobre downloads e conversão de áudio e vídeo, preservando o processamento local e o histórico anterior.

### ✨ O que mudou
- Download/conversão de áudio original em **MP3 (192 kbps)**.
- Download/conversão de **vídeo original em MP4**, com áudio.
- Exportação combinada **WAV + MP3 + MP4** em uma mesma tarefa.
- Players específicos para áudio e vídeo, além de instrumental e vocal.
- **Botão Encerrar AudioForge** com confirmação, impedindo desligar com um trabalho em execução.
- Histórico e resultados da versão v0.1.0 preservados.
- Otimização para não guardar WAV temporário quando não solicitado.
- Cobertura ampliada de testes e documentação de atualização.

### ⚠️ Notas
- MP4 é o vídeo original; karaokê em vídeo será uma funcionalidade futura.
- O app roda localmente e utiliza modelos de IA na CPU.
- URLs dependem da disponibilidade e permissão de acesso; nem todos os links do YouTube funcionam.
- A validação automatizada inclui fluxos simulados de download e conversões reais com FFmpeg; requer testes manuais com links no Ubuntu.

### 🔄 Como atualizar
Desligue a v0.1.0 e copie/mescle os arquivos da v0.2.0 na mesma pasta, **sem apagar `.venv`**. Continue abrindo pelo mesmo atalho.

### 🧭 Roadmap
- v0.2.1: correções após testes reais.
- v0.3.0: fila, cancelamento, ajustes de qualidade.
- v0.4.0: vídeo karaokê MP4 com instrumental e letras.
```

## Manutenção

Guarde a pasta do aplicativo no seu computador. Os arquivos de histórico em `~/Downloads/AudioForge-Local/` **não** são copiados para o GitHub. Faça backup separadamente, se necessário.
