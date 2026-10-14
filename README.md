# 🚆 I-Sopraelevazioni 2.0

Applicazione Streamlit per confronto **assistito e verificabile** delle sopraelevazioni ferroviarie.

## Pubblicazione su GitHub + Streamlit Community Cloud

1. Crea repository GitHub `I-Sopraelevazioni-2.0` (preferibilmente **privato**, poiché i documenti possono essere riservati).
2. Carica **tutti i file di questa cartella**, compresa `.streamlit/config.toml`, preservando le sottocartelle.
3. Su https://share.streamlit.io/ collega il repository, imposta `app.py` come entry point e distribuisci l'app.
4. In alternativa, in locale: `pip install -r requirements.txt` e `streamlit run app.py`; installa anche Tesseract con lingua italiana (`ita`).

**Nota**: GitHub Pages da solo non esegue Python/Streamlit. È necessario un host Streamlit o un server Python.

## Utilizzo

1. Carica il tabellino PDF scansionato, XLSX o CSV. Il PDF viene sottoposto a OCR preliminare.
2. Correggi la tabella e compila **progressiva_m** (metri), **h_mm** (mm), **rotaia_alzata** (`sx`/`dx`); marca `verificato` dopo confronto con l'originale. Scarica il tabellino Excel.
3. Carica uno o più grafici PDF/JPG/PNG. Seleziona la pagina e calibra due punti di progressiva e due punti di valore verticale usando l'immagine. **I campi precompilati sono segnaposto**.
4. La traccia estratta automaticamente è una **proposta** e resta `verificato=False`. Conferma soltanto i punti affidabili oppure inserisci valori misurati manualmente.
5. Configura le soglie, esegui il confronto e scarica l'Excel con fogli Tabellino, Dettaglio, Report aggregato.

## Regole e limiti

- Verde: |rilievo − progetto| <= 10 mm.
- Giallo: scostamento > 10 mm.
- Arancione: sopraelevazione non prevista (|progetto| <= tolleranza), valore rilevato > tolleranza e <= soglia arancione.
- Rosso: |rilievo| > soglia rossa (default 160 mm); prevale sugli altri.
- Progetto positivo per rotaia `sx`, negativo per `dx` (progressiva crescente).
- Progetto interpolato solo tra due punti verificati con stessa rotaia alzata e distanza <= max(100 m, 20 × passo campionamento). **Attenzione**: la semplice interpolazione lineare può non descrivere raccordi non lineari; in questi casi caricare punti di progetto sufficientemente ravvicinati e verificati.
- Le misure non verificate, non leggibili, con più tracce o senza progetto valido sono **NON LEGGIBILE**; mai verdi.
- L'aggregazione raggruppa solo punti consecutivi con stesso codice e senza intervalli oltre 1,51 × passo.
- Se le soglie arancione e rossa coincidono a 160 mm, i valori fino a 160 possono essere arancioni solo se non previsti da progetto; sopra 160 sono rossi.
- L'estrazione di tracce da immagini può fallire su linee tratteggiate, griglie, sovrapposizioni, curve e scansioni. Non è uno strumento di misura certificato. **Non utilizzare i risultati per decisioni di sicurezza senza verifica tecnica.**
- Il PDF campione grafico riporta progressive decrescenti da sinistra a destra e la scritta `(1.00 : 6.00)`; la scala grafica non è deducibile dalla sola scritta e deve essere calibrata.
- La scansione del tabellino campione non permette estrazione automatica affidabile di tutte le colonne: la compilazione/verifica di h e rotaia alzata è intenzionalmente obbligatoria.

## Privacy

I file caricati vengono processati dalla sessione dell'host Streamlit; non sono inviati a servizi OCR esterni dal codice. Valutare l'hosting secondo le regole aziendali e la classificazione dei documenti. Non caricare documentazione RFI riservata su un servizio pubblico senza autorizzazione.

## Test

`python -m unittest discover -s tests -v`
