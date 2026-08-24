"""Motore di trascrizione locale basato su faster-whisper (Whisper).

Caratteristiche pensate per registrazioni di molte ore e per la massima
fedeltà al parlato in italiano:

  * Elaborazione in streaming: i segmenti vengono prodotti e salvati uno alla
    volta, senza caricare l'intera trascrizione in memoria.
  * Filtro VAD (Voice Activity Detection): salta i silenzi, riducendo errori e
    "allucinazioni" nelle pause lunghe tipiche delle registrazioni estese.
  * Parametri orientati alla fedeltà (beam search, soglie anti-ripetizione).
  * Scelta del modello: da 'tiny' (veloce, meno preciso) a 'large-v3'
    (massima fedeltà). Per l'italiano 'large-v3' o 'medium' danno i risultati
    migliori.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Iterator

from .formats import Segmento

# Modelli Whisper disponibili, dal più veloce al più fedele.
MODELLI_DISPONIBILI = ("tiny", "base", "small", "medium", "large-v3")
MODELLO_PREDEFINITO = "medium"
LINGUA_PREDEFINITA = "it"

# Cache dei modelli già caricati: caricare un modello è costoso, quindi lo
# riutilizziamo tra una trascrizione e l'altra.
_cache_modelli: dict[tuple, object] = {}
_lock_cache = threading.Lock()


@dataclass
class InfoAudio:
    """Informazioni rilevate sull'audio prima della trascrizione."""

    lingua: str
    probabilita_lingua: float
    durata: float


def _rileva_dispositivo() -> tuple[str, str]:
    """Sceglie GPU (CUDA) se disponibile, altrimenti CPU.

    Restituisce (dispositivo, compute_type) ottimali. Su GPU usiamo float16
    per velocità; su CPU usiamo int8 per non saturare la memoria su file lunghi.
    """
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def carica_modello(dimensione: str = MODELLO_PREDEFINITO):
    """Carica (e mette in cache) un modello faster-whisper.

    Al primo utilizzo il modello viene scaricato automaticamente da Hugging
    Face e salvato nella cache locale (~/.cache/huggingface). Le volte
    successive viene riusato senza riscaricarlo.
    """
    if dimensione not in MODELLI_DISPONIBILI:
        raise ValueError(
            f"Modello '{dimensione}' non valido. "
            f"Scegli tra: {', '.join(MODELLI_DISPONIBILI)}"
        )

    dispositivo, compute_type = _rileva_dispositivo()
    chiave = (dimensione, dispositivo, compute_type)

    with _lock_cache:
        if chiave not in _cache_modelli:
            from faster_whisper import WhisperModel

            _cache_modelli[chiave] = WhisperModel(
                dimensione,
                device=dispositivo,
                compute_type=compute_type,
            )
        return _cache_modelli[chiave]


def trascrivi(
    percorso_audio: str,
    *,
    modello: str = MODELLO_PREDEFINITO,
    lingua: str | None = LINGUA_PREDEFINITA,
    su_info: Callable[[InfoAudio], None] | None = None,
) -> Iterator[Segmento]:
    """Trascrive un file audio e produce i segmenti uno alla volta.

    Parametri
    ---------
    percorso_audio : percorso del file audio/video.
    modello        : dimensione del modello Whisper (vedi MODELLI_DISPONIBILI).
    lingua         : codice lingua ('it' per italiano). None = rilevamento
                     automatico.
    su_info        : callback opzionale richiamata una volta con le info
                     dell'audio (lingua rilevata, durata) appena disponibili.

    Restituisce un iteratore di :class:`Segmento`. La trascrizione vera e
    propria avviene man mano che si consuma l'iteratore (lazy/streaming).
    """
    whisper = carica_modello(modello)

    # Parametri scelti per la fedeltà al parlato:
    #  - beam_size=5: ricerca più accurata della trascrizione migliore.
    #  - vad_filter: salta i silenzi (fondamentale nelle registrazioni lunghe).
    #  - condition_on_previous_text: mantiene la coerenza del contesto.
    #  - soglie su compression_ratio/log_prob/no_speech: tagliano i segmenti
    #    poco affidabili e prevengono i loop di ripetizione.
    segmenti, info = whisper.transcribe(
        percorso_audio,
        language=lingua,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=True,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
        no_speech_threshold=0.6,
        temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    )

    if su_info is not None:
        su_info(
            InfoAudio(
                lingua=info.language,
                probabilita_lingua=float(info.language_probability),
                durata=float(info.duration),
            )
        )

    for i, seg in enumerate(segmenti, start=1):
        yield Segmento(
            indice=i,
            inizio=float(seg.start),
            fine=float(seg.end),
            testo=seg.text,
        )
