#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo '===================================================='
echo ' AudioForge Local — instalação Ubuntu/Linux (CPU)'
echo '===================================================='
if ! command -v python3 >/dev/null; then
  echo 'Python 3 não encontrado. Instale Python 3.10+.'
  exit 1
fi
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit('Requer Python 3.10 ou superior.')
print('Python:', sys.version.split()[0])
PY

if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
  echo 'FFmpeg/ffprobe não encontrado(s). Tentando instalar via apt...'
  if command -v apt-get >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y ffmpeg
  else
    echo 'Instale FFmpeg e ffprobe pelo gerenciador de pacotes e tente de novo.'
    exit 1
  fi
fi

if ! python3 -m venv .venv 2>/dev/null; then
  echo 'venv ausente; tentando instalar python3-venv...'
  if command -v apt-get >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y python3-venv
    python3 -m venv .venv
  else
    echo 'Instale o pacote python3-venv e tente novamente.'
    exit 1
  fi
fi

PYTHON=.venv/bin/python
"$PYTHON" -m pip install --upgrade pip setuptools wheel

echo
echo 'Instalando PyTorch CPU-only (download inicial pode ser grande)...'
"$PYTHON" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

echo
echo 'Instalando interface e modelos de IA...'
"$PYTHON" -m pip install -r requirements.txt

chmod +x start.sh install.sh
mkdir -p "$HOME/.local/share/applications"
ROOT="$PWD"
cat > "$HOME/.local/share/applications/audioforge-local.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AudioForge Local
Comment=Estúdio pessoal de áudio, karaokê e transcrição
Exec="$ROOT/start.sh"
Path=$ROOT
Icon=audio-x-generic
Terminal=false
Categories=AudioVideo;Audio;Utility;
StartupNotify=true
EOF
chmod +x "$HOME/.local/share/applications/audioforge-local.desktop"
echo
echo '✅ Instalação concluída!'
echo 'Inicie pelo menu de aplicativos (AudioForge Local) ou pelo arquivo start.sh.'
echo 'Modelos de separação e transcrição serão baixados apenas no primeiro uso.'
