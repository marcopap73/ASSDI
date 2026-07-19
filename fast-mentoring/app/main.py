"""Fast Mentoring — Qualzar Academy Italia.

Web app per l'invio di domande a pagamento (a ticket) su tre aree di
intervento e per la gestione delle risposte da parte del mentor.

Avvio: uvicorn app.main:app --host 127.0.0.1 --port 8010
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import (
    crea_sessione,
    distruggi_sessione,
    genera_password_hash,
    utente_da_richiesta,
    verifica_password,
)
from .database import connessione
from .models import AREE, inizializza_db
from .payments import provider_attivo

DIR_APP = os.path.dirname(os.path.abspath(__file__))
DIR_PROGETTO = os.path.dirname(DIR_APP)


@asynccontextmanager
async def lifespan(app: FastAPI):
    inizializza_db()
    yield


app = FastAPI(title="Fast Mentoring — Qualzar Academy Italia", lifespan=lifespan)
templates = Jinja2Templates(directory=os.path.join(DIR_PROGETTO, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(DIR_PROGETTO, "static")), name="static")


def _contesto_base(request: Request, utente=None) -> dict:
    return {"utente": utente, "aree": AREE}


def _render(request: Request, nome_template: str, contesto: dict, status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(request, nome_template, contesto, status_code=status_code)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    utente = utente_da_richiesta(request)
    if utente is None:
        return RedirectResponse("/accedi", status_code=303)
    if utente["ruolo"] == "mentor":
        return RedirectResponse("/mentor", status_code=303)
    return RedirectResponse("/dashboard", status_code=303)


# --- Autenticazione ----------------------------------------------------


@app.get("/registrati", response_class=HTMLResponse)
def form_registrazione(request: Request):
    return _render(request, "registrati.html", _contesto_base(request))


@app.post("/registrati")
def registrati(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    ente: str = Form(""),
    password: str = Form(...),
):
    email = email.strip().lower()
    if len(password) < 8:
        return _render(
            request,
            "registrati.html",
            {**_contesto_base(request), "errore": "La password deve avere almeno 8 caratteri."},
            status_code=400,
        )
    with connessione() as conn:
        esiste = conn.execute("SELECT id FROM utenti WHERE email = ?", (email,)).fetchone()
        if esiste:
            return _render(
                request,
                "registrati.html",
                {**_contesto_base(request), "errore": "Esiste gia' un account con questa email."},
                status_code=400,
            )
        password_hash, salt = genera_password_hash(password)
        cur = conn.execute(
            "INSERT INTO utenti (nome, email, ente, password_hash, salt) VALUES (?, ?, ?, ?, ?)",
            (nome.strip(), email, ente.strip(), password_hash, salt),
        )
        utente_id = cur.lastrowid
    token = crea_sessione(utente_id)
    risposta = RedirectResponse("/dashboard", status_code=303)
    risposta.set_cookie("sessione", token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 14)
    return risposta


@app.get("/accedi", response_class=HTMLResponse)
def form_accesso(request: Request):
    return _render(request, "login.html", _contesto_base(request))


@app.post("/accedi")
def accedi(request: Request, email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    with connessione() as conn:
        riga = conn.execute("SELECT * FROM utenti WHERE email = ?", (email,)).fetchone()
    if riga is None or not verifica_password(password, riga["password_hash"], riga["salt"]):
        return _render(
            request,
            "login.html",
            {**_contesto_base(request), "errore": "Email o password non corrette."},
            status_code=400,
        )
    token = crea_sessione(riga["id"])
    destinazione = "/mentor" if riga["ruolo"] == "mentor" else "/dashboard"
    risposta = RedirectResponse(destinazione, status_code=303)
    risposta.set_cookie("sessione", token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 14)
    return risposta


@app.post("/esci")
def esci(request: Request):
    token = request.cookies.get("sessione")
    if token:
        distruggi_sessione(token)
    risposta = RedirectResponse("/accedi", status_code=303)
    risposta.delete_cookie("sessione")
    return risposta


# --- Area utente (assistente sociale) -----------------------------------


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_utente(request: Request):
    utente = utente_da_richiesta(request)
    if utente is None:
        return RedirectResponse("/accedi", status_code=303)
    with connessione() as conn:
        domande = conn.execute(
            """
            SELECT domande.*, risposte.testo AS risposta_testo, risposte.risposta_il
            FROM domande
            LEFT JOIN risposte ON risposte.domanda_id = domande.id
            WHERE domande.utente_id = ?
            ORDER BY domande.creata_il DESC
            """,
            (utente["id"],),
        ).fetchall()
    return _render(
        request, "dashboard_utente.html", {**_contesto_base(request, utente), "domande": domande}
    )


@app.get("/nuova-domanda", response_class=HTMLResponse)
def form_nuova_domanda(request: Request):
    utente = utente_da_richiesta(request)
    if utente is None:
        return RedirectResponse("/accedi", status_code=303)
    if utente["ruolo"] == "mentor":
        return RedirectResponse("/mentor", status_code=303)
    return _render(request, "nuova_domanda.html", _contesto_base(request, utente))


@app.post("/nuova-domanda")
def crea_domanda(request: Request, area: str = Form(...), testo: str = Form(...)):
    utente = utente_da_richiesta(request)
    if utente is None:
        return RedirectResponse("/accedi", status_code=303)
    if area not in AREE:
        return _render(
            request,
            "nuova_domanda.html",
            {**_contesto_base(request, utente), "errore": "Area non valida."},
            status_code=400,
        )
    testo = testo.strip()
    if not testo:
        return _render(
            request,
            "nuova_domanda.html",
            {**_contesto_base(request, utente), "errore": "Scrivi il testo della domanda."},
            status_code=400,
        )
    if utente["ticket_disponibili"] < 1:
        return _render(
            request,
            "nuova_domanda.html",
            {
                **_contesto_base(request, utente),
                "errore": "Non hai ticket disponibili. Acquistane uno per inviare la domanda.",
            },
            status_code=400,
        )
    with connessione() as conn:
        conn.execute(
            "INSERT INTO domande (utente_id, area, testo) VALUES (?, ?, ?)",
            (utente["id"], area, testo),
        )
        conn.execute(
            "UPDATE utenti SET ticket_disponibili = ticket_disponibili - 1 WHERE id = ?",
            (utente["id"],),
        )
    return RedirectResponse("/dashboard", status_code=303)


# --- Ticket ---------------------------------------------------------------


@app.get("/ticket", response_class=HTMLResponse)
def pagina_ticket(request: Request):
    utente = utente_da_richiesta(request)
    if utente is None:
        return RedirectResponse("/accedi", status_code=303)
    with connessione() as conn:
        pacchetti = conn.execute(
            "SELECT * FROM pacchetti_ticket WHERE attivo = 1 ORDER BY numero_ticket"
        ).fetchall()
    return _render(
        request, "acquista_ticket.html", {**_contesto_base(request, utente), "pacchetti": pacchetti}
    )


@app.post("/ticket/{pacchetto_id}/acquista")
def acquista_ticket(request: Request, pacchetto_id: int):
    utente = utente_da_richiesta(request)
    if utente is None:
        return RedirectResponse("/accedi", status_code=303)
    with connessione() as conn:
        pacchetto = conn.execute(
            "SELECT * FROM pacchetti_ticket WHERE id = ? AND attivo = 1", (pacchetto_id,)
        ).fetchone()
        if pacchetto is None:
            return RedirectResponse("/ticket", status_code=303)
        risultato = provider_attivo.avvia_pagamento(
            pacchetto_id=pacchetto_id,
            importo_centesimi=pacchetto["prezzo_centesimi"],
            utente_id=utente["id"],
        )
        stato = "completato" if risultato.riuscito else "fallito"
        conn.execute(
            "INSERT INTO pagamenti (utente_id, pacchetto_id, importo_centesimi, stato, provider) "
            "VALUES (?, ?, ?, ?, ?)",
            (utente["id"], pacchetto_id, pacchetto["prezzo_centesimi"], stato, provider_attivo.nome),
        )
        if risultato.riuscito:
            conn.execute(
                "UPDATE utenti SET ticket_disponibili = ticket_disponibili + ? WHERE id = ?",
                (pacchetto["numero_ticket"], utente["id"]),
            )
    return RedirectResponse("/dashboard", status_code=303)


# --- Area mentor ------------------------------------------------------


def _richiedi_mentor(request: Request):
    utente = utente_da_richiesta(request)
    if utente is None or utente["ruolo"] != "mentor":
        return None
    return utente


@app.get("/mentor", response_class=HTMLResponse)
def dashboard_mentor(request: Request):
    mentor = _richiedi_mentor(request)
    if mentor is None:
        return RedirectResponse("/accedi", status_code=303)
    with connessione() as conn:
        in_coda = conn.execute(
            """
            SELECT domande.*, utenti.nome AS nome_utente, utenti.ente AS ente_utente
            FROM domande
            JOIN utenti ON utenti.id = domande.utente_id
            WHERE domande.stato = 'in_coda'
            ORDER BY domande.creata_il ASC
            """
        ).fetchall()
        risposte_recenti = conn.execute(
            """
            SELECT domande.id, domande.area, utenti.nome AS nome_utente, risposte.risposta_il
            FROM risposte
            JOIN domande ON domande.id = risposte.domanda_id
            JOIN utenti ON utenti.id = domande.utente_id
            ORDER BY risposte.risposta_il DESC
            LIMIT 10
            """
        ).fetchall()
    return _render(
        request,
        "dashboard_mentor.html",
        {**_contesto_base(request, mentor), "in_coda": in_coda, "risposte_recenti": risposte_recenti},
    )


@app.get("/mentor/domanda/{domanda_id}", response_class=HTMLResponse)
def form_rispondi(request: Request, domanda_id: int):
    mentor = _richiedi_mentor(request)
    if mentor is None:
        return RedirectResponse("/accedi", status_code=303)
    with connessione() as conn:
        domanda = conn.execute(
            """
            SELECT domande.*, utenti.nome AS nome_utente, utenti.ente AS ente_utente
            FROM domande JOIN utenti ON utenti.id = domande.utente_id
            WHERE domande.id = ?
            """,
            (domanda_id,),
        ).fetchone()
    if domanda is None:
        return RedirectResponse("/mentor", status_code=303)
    return _render(
        request, "rispondi.html", {**_contesto_base(request, mentor), "domanda": domanda}
    )


@app.post("/mentor/domanda/{domanda_id}/rispondi")
def rispondi(request: Request, domanda_id: int, testo: str = Form(...)):
    mentor = _richiedi_mentor(request)
    if mentor is None:
        return RedirectResponse("/accedi", status_code=303)
    testo = testo.strip()
    with connessione() as conn:
        domanda = conn.execute("SELECT id FROM domande WHERE id = ?", (domanda_id,)).fetchone()
        if domanda is None or not testo:
            return RedirectResponse("/mentor", status_code=303)
        conn.execute(
            "INSERT INTO risposte (domanda_id, testo) VALUES (?, ?)",
            (domanda_id, testo),
        )
        conn.execute("UPDATE domande SET stato = 'risposta' WHERE id = ?", (domanda_id,))
    return RedirectResponse("/mentor", status_code=303)
