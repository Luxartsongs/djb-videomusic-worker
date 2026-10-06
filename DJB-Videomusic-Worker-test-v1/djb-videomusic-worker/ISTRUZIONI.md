# DJB Videomusic — prima prova Wan 2.2

Pacchetto di prova separato dal generatore musicale. Produce una scena MUTA da un’immagine e un prompt. Non è ancora il generatore completo del sito.

## 1. GitHub: primo passo

Crea un repository NUOVO chiamato `djb-videomusic-worker`, con ramo `main`.
Estrai questo ZIP e carica il CONTENUTO della cartella `djb-videomusic-worker` nella radice del repository. Non caricare solo lo ZIP o una cartella esterna aggiuntiva.
La struttura deve comprendere `Dockerfile`, `handler.py`, `patch_attention.py` e `.github/workflows/build.yml`. La cartella `.github` può risultare nascosta: deve essere inclusa.
Non sostituire alcun file del repository audio e non caricare immagini personali, chiavi o credenziali.

Apri Actions: deve apparire “Build DJB Videomusic Test Worker”. Esegui Run workflow se non è già partito. Attendi il risultato verde; in caso di errore conserva il messaggio del passaggio fallito.
L’immagine risultante è `ghcr.io/TUO-NOME-GITHUB/djb-videomusic-worker:test-v1` (tutto minuscolo). Dopo il build, nelle impostazioni del package GHCR rendilo pubblico per consentire a RunPod di scaricarlo senza credenziali del registro. Il package contiene codice e dipendenze, nessuna chiave.

## 2. RunPod: endpoint NUOVO

Usa un endpoint Serverless separato. L’endpoint musicale esistente resta quello attuale.
Seleziona la categoria GPU 96 GB PRO concordata; verifica che la GPU disponibile sia RTX PRO 6000 Blackwell e che la regione supporti il volume di rete.
Immagine: quella prodotta dal repository nuovo.
Max workers: 1. Active workers: 0. GPU per worker: 1.
Imposta execution timeout a 3600 secondi per la prima prova: il primo job deve anche scaricare i pesi.
Collega un Network Volume da 200 GB montato a `/runpod-volume`. Il worker rifiuta di scaricare i pesi senza questo montaggio persistente.
Con l’offload sulla CPU occorre anche RAM di sistema sufficiente: verificare l’allocazione della macchina, preferibilmente 128 GB. Se non disponibile, prima di lanciare la prova rivedere configurazione/offload.

Il volume ha un costo anche con zero worker attivi. Active workers 0 evita il worker sempre acceso, ma avvio, download iniziale, elaborazione e altri periodi fatturabili restano a pagamento. Controlla la tariffa in dollari mostrata da RunPod prima del test; non equivale automaticamente alla stessa cifra in euro.
Non inserire la chiave RunPod nell’HTML pubblico. Nessun collegamento al sito in questa fase.

## 3. Una sola scena di prova

Per preparare il JSON usa `Test-Wan-locale.html`: aprilo sul PC, scegli una foto JPG/PNG/WebP da massimo 4 MiB, poi scarica il JSON. La pagina lavora localmente e non invia nulla a RunPod.
Nel pannello test dell’endpoint usa il JSON ottenuto ed esegui UN job asincrono. Lascia completare il download iniziale senza inviare altre richieste.
Prima prova: 480p, 81 fotogrammi, 40 step, seed 42. Sono circa 5 secondi di video senza audio; il rapporto d’aspetto segue l’immagine e la dimensione effettiva viene riportata nel risultato.
Esporta o copia la risposta JSON COMPLETA in un file locale e aprila nello stesso HTML per scaricare l’MP4. In alternativa: `python download_test_result.py risposta.json`.
Una risposta di sola presa in carico, IN_QUEUE o IN_PROGRESS non contiene ancora il video: attendi COMPLETED. Se fallisce, conserva errore e log.
`worker_seconds` misura download e lavoro dentro l’handler: non è la durata totale fatturata.
Solo dopo il primo esito riuscito proveremo 720p e confronteremo volto, mani, movimento, tempo e consumo effettivo.

## 4. Cosa manca prima dell’uso pubblico

- Pianificazione delle scene dal testo e generazione delle immagini per scene senza riferimento.
- Continuità del personaggio tra scene, montaggio fino a 5 minuti e sincronizzazione con la musica selezionata.
- Archiviazione video sul server, ascolto/visione e download nel sito, scadenza ed eliminazione.
- Controllo account e saldo PRIMA di contattare RunPod, una generazione per utente, prenotazione dei crediti e addebito solo al successo.
- Misura dei costi reali per fissare i crediti video.

Il limite di un worker non sostituisce il controllo di una generazione per utente. Questo endpoint di prova deve restare accessibile esclusivamente tramite la chiave privata server/pannello.

## Verifiche e limiti

Sintassi Python, validazione degli input e costruzione dei comandi controllate localmente. Modifiche locali: import limitato a WanI2V e fallback di attenzione PyTorch SDPA quando FlashAttention non è installato. Il fallback va misurato sulla GPU: non sono garantiti gli stessi tempi delle implementazioni ottimizzate.
Non sono stati eseguiti qui build Docker completo, download dei pesi o inferenza CUDA. Nessun giudizio sulla qualità finale prima del test reale. Questa è una versione di prova, non un pacchetto di produzione già collaudato.

Codice Wan fissato al commit `1ea34ff48f87168174e12956e200b1d908b1c5ff`.
Pesi fissati alla revisione `206a9ee1b7bfaaf8f7e4d81335650533490646a3`.
Fonti originali e licenze: https://github.com/Wan-Video/Wan2.2 e https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B . Il checkout nel container conserva la licenza upstream; le modifiche DJB sono indicate nel file patch.
