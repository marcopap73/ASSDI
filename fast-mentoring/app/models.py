"""Schema del database e dati iniziali (aree, pacchetti ticket, account mentor)."""
from __future__ import annotations

import os

from .auth import genera_password_hash
from .database import connessione

AREE = {
    "socio-assistenziale": "Socio-assistenziale",
    "non-autosufficienza": "Non autosufficienza",
    "coordinamento-leadership": "Coordinamento e Leadership (SBF Leadership)",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS utenti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    ente TEXT,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    ruolo TEXT NOT NULL DEFAULT 'utente',
    ticket_disponibili INTEGER NOT NULL DEFAULT 0,
    creato_il TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessioni (
    token TEXT PRIMARY KEY,
    utente_id INTEGER NOT NULL REFERENCES utenti(id),
    creata_il TEXT NOT NULL DEFAULT (datetime('now')),
    scadenza TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pacchetti_ticket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    numero_ticket INTEGER NOT NULL,
    prezzo_centesimi INTEGER NOT NULL,
    attivo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pagamenti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    utente_id INTEGER NOT NULL REFERENCES utenti(id),
    pacchetto_id INTEGER NOT NULL REFERENCES pacchetti_ticket(id),
    importo_centesimi INTEGER NOT NULL,
    stato TEXT NOT NULL DEFAULT 'completato',
    provider TEXT NOT NULL DEFAULT 'demo',
    creato_il TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS domande (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    utente_id INTEGER NOT NULL REFERENCES utenti(id),
    area TEXT NOT NULL,
    testo TEXT NOT NULL,
    stato TEXT NOT NULL DEFAULT 'in_coda',
    creata_il TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS risposte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domanda_id INTEGER NOT NULL UNIQUE REFERENCES domande(id),
    testo TEXT NOT NULL,
    risposta_il TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def inizializza_db() -> None:
    with connessione() as conn:
        conn.executescript(SCHEMA)
        _semina_pacchetti(conn)
        _semina_mentor(conn)


def _semina_pacchetti(conn) -> None:
    esiste = conn.execute("SELECT COUNT(*) AS n FROM pacchetti_ticket").fetchone()["n"]
    if esiste:
        return
    pacchetti = [
        ("Ticket singolo", 1, 4900),
        ("Pacchetto 5 ticket", 5, 19900),
        ("Pacchetto 10 ticket", 10, 34900),
    ]
    conn.executemany(
        "INSERT INTO pacchetti_ticket (nome, numero_ticket, prezzo_centesimi) VALUES (?, ?, ?)",
        pacchetti,
    )


def _semina_mentor(conn) -> None:
    email_mentor = os.environ.get("FASTMENTORING_MENTOR_EMAIL", "mentor@qualzaracademy.it")
    password_mentor = os.environ.get("FASTMENTORING_MENTOR_PASSWORD", "cambiami-subito")
    esiste = conn.execute("SELECT id FROM utenti WHERE email = ?", (email_mentor,)).fetchone()
    if esiste:
        return
    password_hash, salt = genera_password_hash(password_mentor)
    conn.execute(
        "INSERT INTO utenti (nome, email, ente, password_hash, salt, ruolo) VALUES (?, ?, ?, ?, ?, 'mentor')",
        ("Mentor Qualzar Academy", email_mentor, "Qualzar Academy Italia", password_hash, salt),
    )
