"""Autenticazione: password hashing e sessioni lato server."""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import Request

from .database import connessione

DURATA_SESSIONE = timedelta(days=14)


def genera_password_hash(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    derivato = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return derivato.hex(), salt


def verifica_password(password: str, password_hash: str, salt: str) -> bool:
    derivato, _ = genera_password_hash(password, salt)
    return secrets.compare_digest(derivato, password_hash)


def crea_sessione(utente_id: int) -> str:
    token = secrets.token_urlsafe(32)
    scadenza = (datetime.now(timezone.utc) + DURATA_SESSIONE).isoformat()
    with connessione() as conn:
        conn.execute(
            "INSERT INTO sessioni (token, utente_id, scadenza) VALUES (?, ?, ?)",
            (token, utente_id, scadenza),
        )
    return token


def distruggi_sessione(token: str) -> None:
    with connessione() as conn:
        conn.execute("DELETE FROM sessioni WHERE token = ?", (token,))


def utente_da_richiesta(request: Request) -> sqlite3.Row | None:
    token = request.cookies.get("sessione")
    if not token:
        return None
    with connessione() as conn:
        riga = conn.execute(
            """
            SELECT utenti.* FROM sessioni
            JOIN utenti ON utenti.id = sessioni.utente_id
            WHERE sessioni.token = ? AND sessioni.scadenza > datetime('now')
            """,
            (token,),
        ).fetchone()
    return riga
