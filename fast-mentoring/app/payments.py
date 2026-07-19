"""Interfaccia per i provider di pagamento.

Oggi esiste solo un provider demo che conferma il pagamento all'istante,
per poter costruire e testare tutto il flusso ticket prima di scegliere e
collegare un provider reale (es. Stripe). Per passare a un provider vero:
creare una classe con la stessa interfaccia (avviene_pagamento) e
assegnarla a `provider_attivo` qui sotto.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RisultatoPagamento:
    riuscito: bool
    riferimento: str


class ProviderPagamentoDemo:
    """Provider finto: conferma sempre il pagamento. Solo per sviluppo/demo."""

    nome = "demo"

    def avvia_pagamento(self, *, pacchetto_id: int, importo_centesimi: int, utente_id: int) -> RisultatoPagamento:
        return RisultatoPagamento(riuscito=True, riferimento=f"demo-{utente_id}-{pacchetto_id}")


provider_attivo = ProviderPagamentoDemo()
