#!/usr/bin/env bash
# Script di avvio rapido per Fast Mentoring (Linux / macOS).
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "==> Creo l'ambiente virtuale Python…"
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "==> Installo/aggiorno le dipendenze…"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

PORTA="${FASTMENTORING_PORTA:-8010}"
echo ""
echo "==> Fast Mentoring e' pronta! Apri il browser su: http://127.0.0.1:${PORTA}"
echo "    Account mentor demo: mentor@qualzaracademy.it / cambiami-subito"
echo "    (cambia la password appena entri, e' solo un valore di default)"
echo "    (Premi CTRL+C per fermare il server)"
echo ""
python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORTA}"
