# Configurazione Email Alert System
## Sistema di Notifiche Automatiche per Errori Scraping

### 📧 Panoramica

Il sistema invia automaticamente email a **portalepigreco@gmail.com** quando:

- ❌ Il sito **RNA.gov.it** cambia struttura e gli scraping falliscono
- ❌ Il sito **Cribis X** cambia interfaccia e il login/ricerca fallisce
- ❌ I selettori CSS/XPath non funzionano più
- ❌ Si verificano timeout o errori critici

### 🔧 Configurazione

#### Metodo 1: Variabile d'Ambiente (Raccomandato per Render)

Imposta la variabile d'ambiente sul server Render:

```bash
EMAIL_PASSWORD=6v&J81w5yN&v#9)U
```

**Su Render.com:**
1. Vai al tuo servizio
2. Environment → Add Environment Variable
3. Key: `EMAIL_PASSWORD`
4. Value: `6v&J81w5yN&v#9)U`
5. Salva e rideploy

#### Metodo 2: Hardcoded (Già configurato)

La password è già inserita nel file `email_alert.py` come fallback:

```python
self.password = os.environ.get('EMAIL_PASSWORD', '6v&J81w5yN&v#9)U')
```

### 📨 Tipi di Alert

#### 1. Alert RNA (rna_deminimis_playwright.py)

**Oggetto:** `⚠️ ALERT RNA - Errore Scraping per [P.IVA]`

**Quando viene inviato:**
- Selettori non trovati (input CF, bottoni, tabelle)
- Timeout caricamento pagina
- Errori parsing dati

**Contiene:**
- P.IVA ricercata
- Messaggio di errore dettagliato
- Screenshot debug (se disponibile)
- Dettagli tecnici (URL, browser, etc)

#### 2. Alert Cribis (cribis_nuova_ricerca.py)

**Oggetto:** `⚠️ ALERT CRIBIS - Errore Scraping per [P.IVA]`

**Quando viene inviato:**
- Login fallito
- Campo ricerca non trovato
- Risultati non caricati
- Bottone "Gruppo Societario" non trovato

**Contiene:**
- P.IVA ricercata
- Fase dove si è verificato l'errore
- Screenshot debug (se disponibile)
- URL Cribis X per verifica manuale

#### 3. Alert Risultati Sospetti

**Oggetto:** `⚠️ Risultati Sospetti RNA - [P.IVA]`

**Quando viene inviato:**
- 0 aiuti trovati per P.IVA che dovrebbe averne
- Importi anomali
- Dati inconsistenti

### 🧪 Test del Sistema

Testa il sistema di email con:

```bash
python email_alert.py
```

Questo invierà 3 email di test a portalepigreco@gmail.com:
1. Test alert errore RNA
2. Test alert errore Cribis
3. Test alert risultati sospetti

### 📂 File Modificati

#### Nuovi File:
- `email_alert.py` - Modulo gestione email

#### File Modificati:
- `rna_deminimis_playwright.py` - Aggiunto import e chiamate alert
- `cribis_nuova_ricerca.py` - Aggiunto import e chiamate alert

### 🔐 Sicurezza

**⚠️ IMPORTANTE:**
- La password email è sensibile
- Su sistemi di produzione usa sempre variabili d'ambiente
- Non commitare mai password in Git (già protetto da .gitignore)

### 🛠️ Risoluzione Problemi

#### Email non vengono inviate

1. **Verifica credenziali Gmail:**
   - Email: portalepigreco@gmail.com
   - Password: 6v&J81w5yN&v#9)U

2. **Controlla log server:**
   ```
   ✅ Email inviata con successo a portalepigreco@gmail.com
   ```
   oppure
   ```
   ❌ Errore invio email: [dettagli errore]
   ```

3. **Gmail App Password:**
   - La password fornita è una "App Password" di Gmail
   - Se non funziona, genera nuova App Password su Google Account

4. **Firewall/Rete:**
   - Assicurati che Render.com possa accedere a smtp.gmail.com:587
   - TLS deve essere supportato

#### Alert troppo frequenti

Se ricevi troppe email, puoi disabilitare temporaneamente:

**Opzione 1:** Commenta import in file Python:
```python
# try:
#     from email_alert import alert_rna_error
#     EMAIL_ALERTS_ENABLED = True
# except ImportError:
EMAIL_ALERTS_ENABLED = False
```

**Opzione 2:** Modifica logica condizionale in `email_alert.py`:
```python
# Invia solo per errori molto critici
if 'selector' in errore_str and 'timeout' in errore_str:
    # invia email
```

### 📊 Monitoraggio

Puoi monitorare l'efficacia del sistema controllando:

1. **Inbox portalepigreco@gmail.com** - Ricevi alert?
2. **Log server Render** - Vedi "📧 Invio alert email..."?
3. **Screenshot debug** - Salvati localmente quando si verifica errore

### 🚀 Funzionalità Future (Opzionali)

Possibili miglioramenti:

- [ ] Dashboard web per visualizzare storico errori
- [ ] Telegram bot per notifiche real-time
- [ ] Rate limiting (max 1 email/ora per evitare spam)
- [ ] Email riassuntive giornaliere invece di immediate
- [ ] Webhook Discord/Slack invece di email
- [ ] Auto-fix: tentativo di aggiornare selettori usando AI

### 📞 Contatti

Email alert: portalepigreco@gmail.com
Progetto: RNA De Minimis Agente
Server: Render.com

