# 🎙️ ASSDI — Trascrizione audio fedele in italiano

App **locale e privata** per trascrivere file audio (anche di **molte ore**) in
testo fedele a ciò che viene detto. Tutto avviene **sul tuo computer**: nessun
file viene caricato su server esterni e non ci sono costi a consumo.

Il motore di trascrizione è [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
un'implementazione veloce del modello **Whisper** di OpenAI, ottima per la
lingua italiana.

## ✨ Caratteristiche

- **Interfaccia web** semplice: trascini il file nel browser e parte.
- **File lunghi** (molte ore) gestiti in *streaming*: i segmenti vengono salvati
  su disco man mano, quindi anche un'interruzione non fa perdere il lavoro fatto.
- **Barra di avanzamento** reale (basata sulla durata) e **anteprima dal vivo**
  del testo trascritto.
- **Italiano** preimpostato, con possibilità di rilevamento automatico della lingua.
- **Scelta della qualità**: dal modello `tiny` (veloce) a `large-v3` (massima fedeltà).
- Output in **`.txt`** (testo), **`.srt`** e **`.vtt`** (sottotitoli con tempi).
- Formati supportati: mp3, m4a, wav, flac, ogg, opus, mp4, mkv e altri.

## 🚀 Avvio rapido

### Linux / macOS

```bash
./avvia.sh
```

Poi apri il browser su **http://127.0.0.1:8000**.

### Windows / avvio manuale

```bash
# 1) Ambiente virtuale (consigliato)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 2) Dipendenze
pip install -r requirements.txt

# 3) Avvio
python server.py
```

Apri il browser su **http://127.0.0.1:8000**.

> **Nota sul primo avvio:** la prima volta che usi un modello, questo viene
> scaricato automaticamente da Internet (una sola volta) e salvato nella cache
> locale. I modelli più grandi sono più fedeli ma più pesanti da scaricare e
> più lenti da eseguire.

## 🧠 Quale modello scegliere?

| Modello    | Velocità      | Fedeltà    | Quando usarlo |
|------------|---------------|------------|---------------|
| `tiny`     | molto veloce  | bassa      | prove rapide |
| `base`     | veloce        | discreta   | bozze |
| `small`    | media         | buona      | buon compromesso |
| `medium`   | più lenta     | molto buona| **consigliato** (predefinito) |
| `large-v3` | lenta         | massima    | quando conta la massima precisione |

Su computer **senza scheda video (GPU)** i modelli grandi possono essere lenti su
registrazioni molto lunghe: in tal caso `medium` o `small` offrono il miglior
equilibrio. Con una **GPU NVIDIA** l'app la rileva e la usa automaticamente
(molto più veloce).

## ⚙️ Configurazione (variabili d'ambiente)

| Variabile             | Significato | Predefinito |
|-----------------------|-------------|-------------|
| `ASSDI_PORTA`         | Porta del server web | `8000` |
| `ASSDI_CARTELLA_DATI` | Cartella per upload e trascrizioni | cartella temporanea di sistema |

## 📁 Struttura del progetto

```
ASSDI/
├── server.py              # Server web (FastAPI): upload, stato, download
├── trascrittore/
│   ├── core.py            # Motore di trascrizione (faster-whisper)
│   ├── audio.py           # Lettura durata audio (PyAV)
│   ├── formats.py         # Scrittura incrementale .txt/.srt/.vtt
│   └── jobs.py            # Gestione dei lavori in background + progresso
├── static/                # Interfaccia web (HTML/CSS/JS)
├── requirements.txt
├── avvia.sh               # Avvio rapido (Linux/macOS)
└── README.md
```

## ❓ Risoluzione problemi

- **"Il modello ci mette tanto a partire"** → è il download iniziale del modello,
  succede solo la prima volta. Le volte successive parte subito.
- **Trascrizione lenta** → usa un modello più piccolo (`small`/`medium`) oppure
  un computer con GPU NVIDIA.
- **Lingua sbagliata** → la lingua è impostata su *Italiano*; per altri audio
  scegli *Rilevamento automatico* nel menu a tendina.

## 🔒 Privacy

Tutta l'elaborazione è locale. I file audio e le trascrizioni restano sul tuo
computer (nella cartella dati configurata) e non vengono inviati a nessun
servizio esterno.
