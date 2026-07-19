"""Connessione al database SQLite dell'app di fast mentoring."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager

CARTELLA_DATI = os.environ.get(
    "FASTMENTORING_CARTELLA_DATI",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dati"),
)
os.makedirs(CARTELLA_DATI, exist_ok=True)
PERCORSO_DB = os.path.join(CARTELLA_DATI, "fast_mentoring.db")


def get_connessione() -> sqlite3.Connection:
    conn = sqlite3.connect(PERCORSO_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connessione():
    conn = get_connessione()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
