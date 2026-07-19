#!/usr/bin/env bash
# Script di avvio rapido per ASSDI (Linux / macOS).
# Crea l'ambiente virtuale, installa le dipendenze e avvia il server web.
set -e

cd "$(dirname "$0")"

# 1) Ambiente virtuale
if [ ! -d ".venv" ]; then
  echo "==> Creo l'ambiente virtuale Python…"
  python3 -m venv .venv
fi
source .venv/bin/activate

# 2) Dipendenze
echo "==> Installo/aggiorno le dipendenze…"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 3) Avvio del server
PORTA="${ASSDI_PORTA:-8000}"
echo ""
echo "==> ASSDI è pronta! Apri il browser su: http://127.0.0.1:${PORTA}"
echo "    (Premi CTRL+C per fermare il server)"
echo ""
python server.py
