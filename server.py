"""Server web dell'app di trascrizione ASSDI.

Avvio:
    python -m uvicorn server:app --host 127.0.0.1 --port 8000
oppure semplicemente:
    python server.py

Poi apri il browser su http://127.0.0.1:8000
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from trascrittore import core
from trascrittore.jobs import GestoreLavori

# Cartella dove vengono salvati gli upload e le trascrizioni prodotte.
CARTELLA_DATI = os.environ.get(
    "ASSDI_CARTELLA_DATI", os.path.join(tempfile.gettempdir(), "assdi_dati")
)
os.makedirs(CARTELLA_DATI, exist_ok=True)

# Dimensione dei blocchi di lettura durante l'upload (file di molte ore possono
# pesare diversi GB: leggiamo a pezzi per non riempire la memoria).
BLOCCO_UPLOAD = 1024 * 1024  # 1 MB

DIR_BASE = os.path.dirname(os.path.abspath(__file__))
DIR_STATIC = os.path.join(DIR_BASE, "static")

app = FastAPI(title="ASSDI - Trascrizione audio in italiano")
gestore = GestoreLavori()


def _nome_sicuro(nome: str) -> str:
    """Rende un nome file sicuro per il filesystem."""
    nome = os.path.basename(nome or "audio")
    nome = re.sub(r"[^\w.\- ]+", "_", nome, flags=re.UNICODE).strip()
    return nome or "audio"


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    with open(os.path.join(DIR_STATIC, "index.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/api/modelli")
def lista_modelli() -> dict:
    """Elenco dei modelli disponibili e di quello predefinito."""
    return {
        "modelli": list(core.MODELLI_DISPONIBILI),
        "predefinito": core.MODELLO_PREDEFINITO,
        "lingua_predefinita": core.LINGUA_PREDEFINITA,
    }


@app.post("/api/trascrivi")
async def avvia_trascrizione(
    file: UploadFile = File(...),
    modello: str = Form(core.MODELLO_PREDEFINITO),
    lingua: str = Form(core.LINGUA_PREDEFINITA),
) -> JSONResponse:
    if modello not in core.MODELLI_DISPONIBILI:
        raise HTTPException(status_code=400, detail=f"Modello non valido: {modello}")

    nome_file = _nome_sicuro(file.filename)
    id_provvisorio = os.urandom(8).hex()
    cartella_lavoro = os.path.join(CARTELLA_DATI, id_provvisorio)
    os.makedirs(cartella_lavoro, exist_ok=True)
    percorso_audio = os.path.join(cartella_lavoro, nome_file)

    # Salvataggio dell'upload a blocchi (gestisce file molto grandi).
    try:
        with open(percorso_audio, "wb") as out:
            while True:
                blocco = await file.read(BLOCCO_UPLOAD)
                if not blocco:
                    break
                out.write(blocco)
    finally:
        await file.close()

    if os.path.getsize(percorso_audio) == 0:
        shutil.rmtree(cartella_lavoro, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Il file caricato è vuoto.")

    # 'auto' -> rilevamento automatico della lingua.
    lingua_norm = None if lingua.strip().lower() in ("", "auto") else lingua.strip()
    nome_base = os.path.splitext(nome_file)[0] or "trascrizione"

    lavoro = gestore.crea(
        nome_file=nome_file,
        percorso_audio=percorso_audio,
        cartella_uscita=cartella_lavoro,
        modello=modello,
        lingua=lingua_norm,
        nome_base_uscita=nome_base,
    )
    return JSONResponse({"id": lavoro.id})


@app.get("/api/lavori/{id_lavoro}")
def stato_lavoro(id_lavoro: str) -> dict:
    lavoro = gestore.ottieni(id_lavoro)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato.")
    return lavoro.to_dict()


@app.get("/api/lavori/{id_lavoro}/scarica")
def scarica(id_lavoro: str, formato: str = "txt") -> FileResponse:
    if formato not in ("txt", "srt", "vtt"):
        raise HTTPException(status_code=400, detail="Formato non valido.")
    lavoro = gestore.ottieni(id_lavoro)
    if lavoro is None:
        raise HTTPException(status_code=404, detail="Lavoro non trovato.")

    percorso = os.path.join(
        lavoro.cartella_uscita, f"{lavoro.nome_base_uscita}.{formato}"
    )
    if not os.path.exists(percorso):
        raise HTTPException(status_code=404, detail="File non ancora disponibile.")

    return FileResponse(
        percorso,
        media_type="text/plain; charset=utf-8",
        filename=f"{lavoro.nome_base_uscita}.{formato}",
    )


# File statici (CSS/JS) serviti sotto /static
app.mount("/static", StaticFiles(directory=DIR_STATIC), name="static")


if __name__ == "__main__":
    import uvicorn

    porta = int(os.environ.get("ASSDI_PORTA", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=porta)
