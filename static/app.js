"use strict";

// Riferimenti agli elementi della pagina
const inputFile = document.getElementById("input-file");
const zonaDrop = document.getElementById("zona-drop");
const btnSfoglia = document.getElementById("btn-sfoglia");
const nomeFileScelto = document.getElementById("nome-file-scelto");
const selectModello = document.getElementById("select-modello");
const selectLingua = document.getElementById("select-lingua");
const btnAvvia = document.getElementById("btn-avvia");

const pannelloUpload = document.getElementById("pannello-upload");
const pannelloLavoro = document.getElementById("pannello-lavoro");
const titoloLavoro = document.getElementById("titolo-lavoro");
const badgeStato = document.getElementById("badge-stato");
const riempimento = document.getElementById("riempimento-progresso");
const testoProgresso = document.getElementById("testo-progresso");
const metaLingua = document.getElementById("meta-lingua");
const metaSegmenti = document.getElementById("meta-segmenti");
const metaTempo = document.getElementById("meta-tempo");
const anteprima = document.getElementById("anteprima");

const zonaDownload = document.getElementById("zona-download");
const dlTxt = document.getElementById("dl-txt");
const dlSrt = document.getElementById("dl-srt");
const dlVtt = document.getElementById("dl-vtt");
const zonaErrore = document.getElementById("zona-errore");
const testoErrore = document.getElementById("testo-errore");
const btnNuovo = document.getElementById("btn-nuovo");

let fileScelto = null;
let timerPolling = null;

// Etichette descrittive per i modelli
const ETICHETTE_MODELLO = {
  "tiny": "tiny — molto veloce, meno preciso",
  "base": "base — veloce",
  "small": "small — buon compromesso",
  "medium": "medium — consigliato (fedele)",
  "large-v3": "large-v3 — massima fedeltà (lento)",
};

// Carica l'elenco dei modelli dal server
async function caricaModelli() {
  try {
    const r = await fetch("/api/modelli");
    const dati = await r.json();
    selectModello.innerHTML = "";
    for (const m of dati.modelli) {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = ETICHETTE_MODELLO[m] || m;
      if (m === dati.predefinito) opt.selected = true;
      selectModello.appendChild(opt);
    }
  } catch (e) {
    console.error("Impossibile caricare i modelli", e);
  }
}

function formattaTempo(secondi) {
  secondi = Math.round(secondi || 0);
  const h = Math.floor(secondi / 3600);
  const m = Math.floor((secondi % 3600) / 60);
  const s = secondi % 60;
  if (h) return `${h}h ${String(m).padStart(2, "0")}m ${String(s).padStart(2, "0")}s`;
  if (m) return `${m}m ${String(s).padStart(2, "0")}s`;
  return `${s}s`;
}

function scegliFile(file) {
  if (!file) return;
  fileScelto = file;
  nomeFileScelto.textContent = file.name;
  btnAvvia.disabled = false;
}

// --- Eventi di selezione/drag & drop ---
btnSfoglia.addEventListener("click", (e) => { e.stopPropagation(); inputFile.click(); });
zonaDrop.addEventListener("click", () => inputFile.click());
inputFile.addEventListener("change", () => scegliFile(inputFile.files[0]));

["dragenter", "dragover"].forEach((ev) =>
  zonaDrop.addEventListener(ev, (e) => {
    e.preventDefault();
    zonaDrop.classList.add("attiva");
  })
);
["dragleave", "drop"].forEach((ev) =>
  zonaDrop.addEventListener(ev, (e) => {
    e.preventDefault();
    zonaDrop.classList.remove("attiva");
  })
);
zonaDrop.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length) scegliFile(e.dataTransfer.files[0]);
});

// --- Avvio della trascrizione ---
btnAvvia.addEventListener("click", async () => {
  if (!fileScelto) return;
  btnAvvia.disabled = true;
  btnAvvia.textContent = "Caricamento del file…";

  const fd = new FormData();
  fd.append("file", fileScelto);
  fd.append("modello", selectModello.value);
  fd.append("lingua", selectLingua.value);

  try {
    const r = await fetch("/api/trascrivi", { method: "POST", body: fd });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `Errore ${r.status}`);
    }
    const dati = await r.json();
    mostraPannelloLavoro();
    avviaPolling(dati.id);
  } catch (e) {
    alert("Errore nell'avvio: " + e.message);
    btnAvvia.disabled = false;
    btnAvvia.textContent = "Avvia trascrizione";
  }
});

function mostraPannelloLavoro() {
  pannelloUpload.classList.add("nascosto");
  pannelloLavoro.classList.remove("nascosto");
  zonaDownload.classList.add("nascosto");
  zonaErrore.classList.add("nascosto");
  btnNuovo.classList.add("nascosto");
  anteprima.textContent = "…";
}

function avviaPolling(id) {
  const aggiorna = async () => {
    try {
      const r = await fetch(`/api/lavori/${id}`);
      if (!r.ok) throw new Error("Stato non disponibile");
      const j = await r.json();
      applicaStato(id, j);
      if (j.stato === "completato" || j.stato === "errore") {
        clearInterval(timerPolling);
      }
    } catch (e) {
      console.error(e);
    }
  };
  aggiorna();
  timerPolling = setInterval(aggiorna, 2000);
}

function applicaStato(id, j) {
  const pct = Math.round((j.progresso || 0) * 100);
  riempimento.style.width = pct + "%";

  if (j.stato === "in_corso" || j.stato === "in_coda") {
    badgeStato.textContent = j.stato === "in_coda" ? "in coda" : "in corso";
    badgeStato.className = "badge";
    if (j.durata) {
      testoProgresso.textContent =
        `${pct}% — elaborati ${formattaTempo(j.secondi_elaborati)} su ${j.durata_testo}`;
    } else {
      testoProgresso.textContent =
        `In elaborazione… ${formattaTempo(j.secondi_elaborati)} trascritti`;
    }
  }

  metaLingua.textContent = j.lingua_rilevata ? `Lingua: ${j.lingua_rilevata}` : "";
  metaSegmenti.textContent = j.n_segmenti ? `Segmenti: ${j.n_segmenti}` : "";
  metaTempo.textContent = j.durata_testo ? `Durata: ${j.durata_testo}` : "";

  if (j.anteprima) {
    anteprima.textContent = j.anteprima;
    anteprima.scrollTop = anteprima.scrollHeight;
  }

  if (j.stato === "completato") {
    titoloLavoro.textContent = "Trascrizione completata";
    badgeStato.textContent = "completato";
    badgeStato.className = "badge ok";
    testoProgresso.textContent = `100% — ${j.durata_testo || ""} trascritti in ${j.n_segmenti} segmenti`;
    dlTxt.href = `/api/lavori/${id}/scarica?formato=txt`;
    dlSrt.href = `/api/lavori/${id}/scarica?formato=srt`;
    dlVtt.href = `/api/lavori/${id}/scarica?formato=vtt`;
    zonaDownload.classList.remove("nascosto");
    btnNuovo.classList.remove("nascosto");
  } else if (j.stato === "errore") {
    titoloLavoro.textContent = "Trascrizione interrotta";
    badgeStato.textContent = "errore";
    badgeStato.className = "badge errore";
    testoErrore.textContent = j.errore || "Errore sconosciuto";
    zonaErrore.classList.remove("nascosto");
    btnNuovo.classList.remove("nascosto");
  }
}

btnNuovo.addEventListener("click", () => {
  fileScelto = null;
  inputFile.value = "";
  nomeFileScelto.textContent = "";
  btnAvvia.disabled = true;
  btnAvvia.textContent = "Avvia trascrizione";
  pannelloLavoro.classList.add("nascosto");
  pannelloUpload.classList.remove("nascosto");
});

caricaModelli();
