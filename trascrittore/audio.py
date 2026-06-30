"""Utilità per leggere i metadati dei file audio.

Per la decodifica usiamo PyAV (la libreria `av`), che viene installata
automaticamente come dipendenza di faster-whisper e include al suo interno
le librerie di FFmpeg. In questo modo l'app gestisce praticamente qualsiasi
formato (mp3, m4a, wav, flac, ogg, opus, mp4, ...) senza dover installare
FFmpeg a parte sul sistema.
"""

from __future__ import annotations

import os


def durata_secondi(percorso: str) -> float:
    """Restituisce la durata del file audio/video in secondi.

    Prova prima a leggere la durata dal contenitore (veloce). Se non è
    disponibile, scorre i pacchetti del primo stream audio per stimarla.
    Restituisce 0.0 se la durata non è determinabile (in tal caso il
    progresso percentuale non sarà calcolabile, ma la trascrizione funziona
    comunque).
    """
    try:
        import av
    except ImportError as exc:  # pragma: no cover - dipendenza garantita
        raise RuntimeError(
            "La libreria 'av' (PyAV) non è installata. Esegui: "
            "pip install -r requirements.txt"
        ) from exc

    if not os.path.exists(percorso):
        raise FileNotFoundError(percorso)

    try:
        with av.open(percorso) as contenitore:
            # 1) Durata del contenitore (in microsecondi -> secondi)
            if contenitore.duration is not None and contenitore.duration > 0:
                return float(contenitore.duration) / 1_000_000.0

            # 2) Durata del primo stream audio
            stream_audio = next(
                (s for s in contenitore.streams if s.type == "audio"), None
            )
            if stream_audio is not None and stream_audio.duration is not None:
                base = stream_audio.time_base
                if base is not None:
                    return float(stream_audio.duration * base)

            # 3) Fallback: scorri i pacchetti e prendi il timestamp finale
            if stream_audio is not None:
                ultimo = 0.0
                base = stream_audio.time_base
                for pacchetto in contenitore.demux(stream_audio):
                    if pacchetto.pts is not None and base is not None:
                        ultimo = max(ultimo, float(pacchetto.pts * base))
                return ultimo
    except av.AVError:
        return 0.0

    return 0.0


def formato_durata(secondi: float) -> str:
    """Converte una durata in secondi in una stringa leggibile (es. 2h 13m 05s)."""
    secondi = int(round(secondi))
    ore, resto = divmod(secondi, 3600)
    minuti, sec = divmod(resto, 60)
    if ore:
        return f"{ore}h {minuti:02d}m {sec:02d}s"
    if minuti:
        return f"{minuti}m {sec:02d}s"
    return f"{sec}s"
