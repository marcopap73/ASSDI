"""Gestione dei lavori di trascrizione in background.

Ogni file caricato diventa un "lavoro" (job) eseguito in un thread separato,
così il server resta reattivo e l'interfaccia web può mostrare l'avanzamento
in tempo reale interrogando lo stato del lavoro.
"""

from __future__ import annotations

import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field

from . import audio, core
from .core import InfoAudio
from .formats import ScrittoreTrascrizione, Segmento

# Quanti caratteri di anteprima del testo mostrare nell'interfaccia.
MAX_ANTEPRIMA = 4000


@dataclass
class Lavoro:
    """Stato di un singolo lavoro di trascrizione."""

    id: str
    nome_file: str
    percorso_audio: str
    cartella_uscita: str
    modello: str
    lingua: str | None

    stato: str = "in_coda"  # in_coda | in_corso | completato | errore
    progresso: float = 0.0  # 0.0 -> 1.0
    durata: float = 0.0  # secondi totali (0 se sconosciuta)
    secondi_elaborati: float = 0.0
    lingua_rilevata: str | None = None
    n_segmenti: int = 0
    anteprima: str = ""
    errore: str | None = None
    creato: float = field(default_factory=time.time)
    nome_base_uscita: str = "trascrizione"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome_file": self.nome_file,
            "stato": self.stato,
            "progresso": round(self.progresso, 4),
            "durata": self.durata,
            "durata_testo": audio.formato_durata(self.durata) if self.durata else None,
            "secondi_elaborati": round(self.secondi_elaborati, 1),
            "lingua_rilevata": self.lingua_rilevata,
            "n_segmenti": self.n_segmenti,
            "anteprima": self.anteprima,
            "errore": self.errore,
            "modello": self.modello,
        }


class GestoreLavori:
    """Crea ed esegue i lavori di trascrizione, mantenendone lo stato."""

    def __init__(self) -> None:
        self._lavori: dict[str, Lavoro] = {}
        self._lock = threading.Lock()

    def crea(
        self,
        *,
        nome_file: str,
        percorso_audio: str,
        cartella_uscita: str,
        modello: str,
        lingua: str | None,
        nome_base_uscita: str,
    ) -> Lavoro:
        lavoro = Lavoro(
            id=uuid.uuid4().hex,
            nome_file=nome_file,
            percorso_audio=percorso_audio,
            cartella_uscita=cartella_uscita,
            modello=modello,
            lingua=lingua,
            nome_base_uscita=nome_base_uscita,
        )
        with self._lock:
            self._lavori[lavoro.id] = lavoro

        thread = threading.Thread(target=self._esegui, args=(lavoro,), daemon=True)
        thread.start()
        return lavoro

    def ottieni(self, id_lavoro: str) -> Lavoro | None:
        with self._lock:
            return self._lavori.get(id_lavoro)

    # ------------------------------------------------------------------
    # Esecuzione in background
    # ------------------------------------------------------------------
    def _esegui(self, lavoro: Lavoro) -> None:
        lavoro.stato = "in_corso"
        try:
            # Durata totale: serve per la percentuale di avanzamento.
            try:
                lavoro.durata = audio.durata_secondi(lavoro.percorso_audio)
            except Exception:
                lavoro.durata = 0.0

            percorso_base = f"{lavoro.cartella_uscita}/{lavoro.nome_base_uscita}"

            def su_info(info: InfoAudio) -> None:
                lavoro.lingua_rilevata = info.lingua
                if not lavoro.durata and info.durata:
                    lavoro.durata = info.durata

            pezzi_anteprima: list[str] = []
            lunghezza_anteprima = 0

            with ScrittoreTrascrizione(percorso_base) as scrittore:
                for seg in core.trascrivi(
                    lavoro.percorso_audio,
                    modello=lavoro.modello,
                    lingua=lavoro.lingua,
                    su_info=su_info,
                ):
                    scrittore.aggiungi(seg)
                    lavoro.n_segmenti += 1
                    lavoro.secondi_elaborati = seg.fine
                    if lavoro.durata > 0:
                        lavoro.progresso = min(seg.fine / lavoro.durata, 0.999)

                    # Aggiorna l'anteprima (coda del testo) per l'interfaccia.
                    testo = seg.testo.strip()
                    if testo:
                        pezzi_anteprima.append(testo)
                        lunghezza_anteprima += len(testo) + 1
                        while lunghezza_anteprima > MAX_ANTEPRIMA and len(pezzi_anteprima) > 1:
                            rimosso = pezzi_anteprima.pop(0)
                            lunghezza_anteprima -= len(rimosso) + 1
                        lavoro.anteprima = " ".join(pezzi_anteprima)

            lavoro.progresso = 1.0
            lavoro.stato = "completato"
        except Exception as exc:  # noqa: BLE001 - vogliamo riportare ogni errore
            lavoro.stato = "errore"
            lavoro.errore = f"{type(exc).__name__}: {exc}"
            traceback.print_exc()
