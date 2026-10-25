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
# Pelo menu gráfico não há terminal para ver erros: salvamos as mensagens no log.
# Pelo terminal, a saída continua aparecendo normalmente.
if [ -t 1 ]; then
  exec .venv/bin/python launcher.py
else
  LOG_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/audioforge-local"
  mkdir -p "$LOG_DIR"
  exec .venv/bin/python launcher.py >> "$LOG_DIR/launcher.log" 2>&1
fi
