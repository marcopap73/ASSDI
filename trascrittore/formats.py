"""Scrittura incrementale dei file di trascrizione.

Per gestire registrazioni di molte ore, i segmenti vengono scritti su disco
mano a mano che arrivano dal motore di trascrizione, invece di tenere tutto
in memoria e salvare solo alla fine. In questo modo, anche se il processo si
interrompe, la parte già trascritta resta salvata.

Vengono prodotti tre file:
  - .txt : testo semplice, una riga per segmento (la trascrizione "fedele")
  - .srt : sottotitoli con tempi (per video player, editing, ecc.)
  - .vtt : sottotitoli WebVTT (per il web)
"""

from __future__ import annotations

import io
from dataclasses import dataclass


@dataclass
class Segmento:
    """Un blocco di parlato con tempo di inizio e fine (in secondi)."""

    indice: int
    inizio: float
    fine: float
    testo: str


def _tempo_srt(secondi: float) -> str:
    """Formatta i secondi come timestamp SRT: HH:MM:SS,mmm."""
    if secondi < 0:
        secondi = 0.0
    millis_totali = int(round(secondi * 1000))
    ore, resto = divmod(millis_totali, 3_600_000)
    minuti, resto = divmod(resto, 60_000)
    sec, millis = divmod(resto, 1000)
    return f"{ore:02d}:{minuti:02d}:{sec:02d},{millis:03d}"


def _tempo_vtt(secondi: float) -> str:
    """Formatta i secondi come timestamp WebVTT: HH:MM:SS.mmm."""
    return _tempo_srt(secondi).replace(",", ".")


class ScrittoreTrascrizione:
    """Gestisce la scrittura incrementale dei file .txt, .srt e .vtt.

    Uso::

        with ScrittoreTrascrizione("uscita/registrazione") as scrittore:
            for seg in segmenti:
                scrittore.aggiungi(seg)
    """

    def __init__(self, percorso_base: str):
        self.percorso_base = percorso_base
        self.txt_path = f"{percorso_base}.txt"
        self.srt_path = f"{percorso_base}.srt"
        self.vtt_path = f"{percorso_base}.vtt"
        self._txt: io.TextIOWrapper | None = None
        self._srt: io.TextIOWrapper | None = None
        self._vtt: io.TextIOWrapper | None = None

    def __enter__(self) -> "ScrittoreTrascrizione":
        self._txt = open(self.txt_path, "w", encoding="utf-8")
        self._srt = open(self.srt_path, "w", encoding="utf-8")
        self._vtt = open(self.vtt_path, "w", encoding="utf-8")
        self._vtt.write("WEBVTT\n\n")
        return self

    def aggiungi(self, seg: Segmento) -> None:
        """Aggiunge un segmento a tutti e tre i file e forza la scrittura su disco."""
        testo = seg.testo.strip()
        if not testo:
            return

        # .txt: testo continuo, una riga per segmento
        self._txt.write(testo + "\n")

        # .srt
        self._srt.write(f"{seg.indice}\n")
        self._srt.write(f"{_tempo_srt(seg.inizio)} --> {_tempo_srt(seg.fine)}\n")
        self._srt.write(testo + "\n\n")

        # .vtt
        self._vtt.write(f"{_tempo_vtt(seg.inizio)} --> {_tempo_vtt(seg.fine)}\n")
        self._vtt.write(testo + "\n\n")

        # Flush: la parte trascritta è subito al sicuro su disco.
        for f in (self._txt, self._srt, self._vtt):
            f.flush()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        for f in (self._txt, self._srt, self._vtt):
            if f is not None:
                f.close()
