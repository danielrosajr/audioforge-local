#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Instalação não encontrada. Execute ./install.sh uma única vez.'
  if command -v zenity >/dev/null; then
    zenity --error --text='AudioForge não foi instalado. Execute install.sh primeiro.' || true
  fi
  exit 1
fi
export PYTHONUNBUFFERED=1
exec .venv/bin/python app.py
