# RNA De Minimis Calculator - Istruzioni per l'uso

## 📋 Cosa fa questo workflow

Questo workflow n8n automatizza il calcolo del **totale de minimis** di un'azienda sul sito [RNA - Registro Nazionale Aiuti](https://www.rna.gov.it/trasparenza/aiuti).

**Processo automatizzato:**
1. ✅ Accede al sito RNA e accetta i cookie
2. 📝 Inserisce la Partita IVA nel campo "C.F. Beneficiario"  
3. 🔍 Seleziona "De Minimis" come tipo procedimento
4. 🧮 Estrae tutti i valori dalla colonna "Elemento Aiuto"
5. ➕ Calcola la somma totale degli aiuti de minimis
6. 📧 Invia un report via email con i risultati

## 🚀 Come installare e configurare

### 1. Importare il workflow in n8n

1. **Apri n8n** (versione cloud o locale)
2. **Clicca su "+"** per creare un nuovo workflow
3. **Clicca sui tre puntini** in alto a destra → **Import from file**
4. **Seleziona il file** `rna-deminimis-workflow.json`
5. **Clicca "Import"**

### 2. Configurare l'email (Gmail)

⚠️ **IMPORTANTE**: Configura l'invio email prima di eseguire il workflow

**Passaggi per configurare Gmail:**

1. **Clicca sul nodo "Send Email Report"** (l'ultimo nodo)
2. **Clicca "Create New Credential"** accanto a "Gmail OAuth2 API"
3. **Segui la procedura OAuth2:**
   - Clicca "Connect my account"
   - Accedi con il tuo account Gmail
   - Autorizza n8n ad accedere alla tua email
4. **Inserisci l'email destinatario** nel campo "To Email"

### 3. Modificare la Partita IVA da cercare

**Per cambiare la P.IVA da monitorare:**

1. **Clicca sul nodo "Submit Search Form"** (il 4° nodo)
2. **Trova il parametro "cf_beneficiario"**
3. **Sostituisci "03254550738"** con la nuova Partita IVA
4. **Salva il workflow** (Ctrl+S)

## ▶️ Come eseguire il workflow

### Esecuzione manuale (per test)

1. **Clicca "Execute Workflow"** in alto a destra
2. **Attendi l'esecuzione** (circa 10-30 secondi)
3. **Controlla la tua email** per il report dei risultati

### Esecuzione automatica programmata

Il workflow è configurato per eseguirsi **ogni lunedì alle 9:00**.

**Per modificare la programmazione:**
1. **Clicca sul nodo "Schedule Trigger"** (il primo)
2. **Modifica "Cron Expression"**:
   - `0 9 * * 1` = ogni lunedì alle 9:00
   - `0 9 * * *` = ogni giorno alle 9:00
   - `0 */2 * * *` = ogni 2 ore

## 📊 Cosa contiene il report email

Il report include:

- **Partita IVA** cercata
- **Totale De Minimis** in euro (formattato)
- **Numero di aiuti** trovati
- **Data della ricerca**
- **Dettaglio di ogni aiuto** trovato
- **Informazioni di debug** per troubleshooting

## 🔧 Troubleshooting

### ❌ Problema: "Nessun risultato trovato"

**Possibili cause:**
- La P.IVA non ha aiuti de minimis registrati
- La P.IVA è scritta in modo errato
- Il sito RNA è temporaneamente non disponibile

**Soluzioni:**
1. Verifica la P.IVA manualmente sul sito RNA
2. Controlla se il sito è raggiungibile
3. Prova ad eseguire nuovamente dopo qualche minuto

### ❌ Problema: "Errore di connessione"

**Possibili cause:**
- Problemi di rete
- Il sito RNA ha cambiato struttura
- Blocco anti-bot

**Soluzioni:**
1. Verifica la connessione internet
2. Prova ad eseguire manualmente dal browser
3. Aumenta il delay tra le richieste (aggiungi nodo "Wait")

### ❌ Problema: "Token CSRF non trovato"

**Possibili cause:**
- Il sito ha modificato la struttura del form
- Blocco di sicurezza

**Soluzioni:**
1. Aggiorna l'User-Agent nei nodi HTTP Request
2. Aggiungi delay tra le richieste
3. Controlla se servono nuovi header

### ❌ Problema: "Email non inviata"

**Possibili cause:**
- Credenziali Gmail non configurate
- Account Gmail non autorizzato
- Limite email raggiunto

**Soluzioni:**
1. Riconfigura le credenziali OAuth2
2. Verifica i permessi dell'account
3. Usa un altro servizio email (SMTP)

## 🔄 Varianti del workflow

### 📅 Programmazione diversa

**Ogni 30 minuti:**
```
*/30 * * * *
```

**Ogni 2 ore:**
```
0 */2 * * *
```

**Solo giorni lavorativi alle 9:00:**
```
0 9 * * 1-5
```

### 📝 Aggiungere più Partite IVA

Per monitorare più aziende:

1. **Duplica il workflow** per ogni P.IVA
2. **Oppure** modifica il nodo "Submit Search Form" per gestire un array di P.IVA
3. **Usa un nodo "Set"** per iterare su più valori

### 📊 Salvare su Google Sheets

Per salvare i risultati su un foglio Google:

1. **Aggiungi un nodo "Google Sheets"** dopo "Extract and Sum Amounts"
2. **Configura OAuth2** per Google Sheets
3. **Mappa i campi**: P.IVA, Totale, Data, ecc.

### 📱 Notifiche Slack/Telegram

Per ricevere notifiche immediate:

1. **Sostituisci** il nodo "Send Email Report" 
2. **Aggiungi nodo "Slack"** o "Telegram"
3. **Configura** le credenziali del servizio scelto

## ⚙️ Parametri avanzati

### Modifica timeout richieste

Se il sito è lento, aumenta il timeout:

1. **Clicca sui nodi HTTP Request**
2. **Options → Request → Timeout**
3. **Imposta 30000** (30 secondi)

### Aggiungere retry automatico

Per gestire errori temporanei:

1. **Clicca sui nodi HTTP Request**
2. **Options → Request → Retry on Fail**
3. **Imposta 3 tentativi** con delay di 5 secondi

## 📞 Supporto

Se hai problemi:

1. **Controlla i log** di esecuzione in n8n
2. **Verifica** che il sito RNA sia accessibile
3. **Testa** manualmente ogni nodo del workflow

---

📅 **Creato:** Dicembre 2024  
🔧 **Testato con:** n8n v1.0+, P.IVA 03254550738  
📧 **Supporto:** marco@pigreco.it
