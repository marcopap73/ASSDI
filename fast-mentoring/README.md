# 🧭 Fast Mentoring — Qualzar Academy Italia

MVP di una web app di mentoring a ticket per assistenti sociali. Gli utenti
acquistano ticket (singoli o a pacchetto), inviano domande su una delle tre
aree di intervento, e il mentor risponde da una dashboard dedicata.

## Aree di intervento

- Socio-assistenziale
- Non autosufficienza
- Coordinamento e Leadership (SBF Leadership)

## Avvio rapido

```bash
./avvia.sh
```

Poi apri il browser su **http://127.0.0.1:8010**.

Account mentor di default (da cambiare subito): `mentor@qualzaracademy.it` /
`cambiami-subito`. Puoi personalizzarlo con le variabili d'ambiente
`FASTMENTORING_MENTOR_EMAIL` e `FASTMENTORING_MENTOR_PASSWORD` **prima** del
primo avvio (vengono usate solo per creare l'account la prima volta).

### Avvio manuale

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

## Configurazione (variabili d'ambiente)

| Variabile                        | Significato                              | Predefinito |
|-----------------------------------|-------------------------------------------|-------------|
| `FASTMENTORING_PORTA`             | Porta del server web                      | `8010` |
| `FASTMENTORING_CARTELLA_DATI`     | Cartella per il database SQLite           | `./dati` |
| `FASTMENTORING_MENTOR_EMAIL`      | Email dell'account mentor creato al primo avvio | `mentor@qualzaracademy.it` |
| `FASTMENTORING_MENTOR_PASSWORD`   | Password dell'account mentor creato al primo avvio | `cambiami-subito` |

## Struttura del progetto

```
fast-mentoring/
├── app/
│   ├── main.py         # Rotte FastAPI (autenticazione, ticket, domande, dashboard mentor)
│   ├── models.py        # Schema del database e dati iniziali (aree, pacchetti, account mentor)
│   ├── auth.py           # Password hashing e sessioni
│   ├── payments.py       # Interfaccia pagamenti (oggi: provider demo)
│   └── database.py       # Connessione SQLite
├── templates/            # Pagine HTML (Jinja2)
├── static/style.css
├── requirements.txt
└── avvia.sh
```

## Stato del progetto (MVP)

Implementato:
- Registrazione/login utenti (email + password), sessioni server-side
- Acquisto ticket (singolo o pacchetto) con **provider di pagamento demo**
  (conferma sempre, nessun addebito reale)
- Invio domanda su una delle tre aree, che consuma 1 ticket
- Dashboard mentor con coda delle domande e form di risposta
- Storico domande/risposte per l'utente

Da fare per andare in produzione (roadmap):
- Collegare un provider di pagamento reale (Stripe consigliato): creare una
  classe in `app/payments.py` con la stessa interfaccia di
  `ProviderPagamentoDemo` e assegnarla a `provider_attivo`
- Notifiche email (nuova domanda in coda / risposta ricevuta)
- Allegati alle domande/risposte
- Pagina di informativa privacy/GDPR e avviso su dati sensibili degli assistiti
- Passaggio a Postgres se il volume cresce oltre SQLite
- Deploy (es. Railway/Render) con dominio dedicato
