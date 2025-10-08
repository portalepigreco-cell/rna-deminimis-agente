# 🚀 Guida Deployment su Render.com

## 📋 Preparazione Completata

✅ **File creati/aggiornati:**
- `requirements.txt` - Dipendenze Python aggiornate
- `render.yaml` - Configurazione deployment automatico
- `Procfile` - Comando avvio alternativo
- `web_finale.py` - App modificata per produzione

## 🔧 Passaggi per Deployment

### 1. Preparazione Repository Git

```bash
# Se non hai ancora git inizializzato
git init

# Aggiungi tutti i file
git add .

# Commit iniziale
git commit -m "🚀 Setup per deployment Render"

# Collega a GitHub/GitLab (sostituisci con il tuo repo)
git remote add origin https://github.com/TUO-USERNAME/rna-deminimis-agente.git
git branch -M main
git push -u origin main
```

### 2. Configurazione su Render.com

1. **Vai su [render.com](https://render.com)** e registrati/accedi
2. **Clicca "New +"** → **"Web Service"**
3. **Collega il repository:**
   - Seleziona GitHub/GitLab
   - Autorizza Render ad accedere ai tuoi repo
   - Scegli il repository `rna-deminimis-agente`

### 3. Configurazione Servizio

**Impostazioni principali:**
- **Name:** `rna-deminimis-app` (o nome a tua scelta)
- **Region:** `Frankfurt` (più vicino all'Italia)
- **Branch:** `main`
- **Root Directory:** lascia vuoto
- **Runtime:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn --bind 0.0.0.0:$PORT web_finale:app`

**Piano:**
- **Free Tier:** Gratuito ma con limitazioni (app si spegne dopo inattività)
- **Starter:** $7/mese per app sempre attiva

### 4. Variabili d'Ambiente (opzionali)

Nella sezione "Environment Variables" aggiungi:
- `FLASK_ENV` = `production`
- `FLASK_DEBUG` = `False`

### 5. Deploy

1. **Clicca "Create Web Service"**
2. **Render inizierà il build automaticamente**
3. **Attendi 2-5 minuti** per il completamento
4. **L'app sarà disponibile su:** `https://rna-deminimis-app.onrender.com`

## 🔄 Aggiornamenti Futuri

Per aggiornare l'app:

```bash
# Modifica i file necessari
git add .
git commit -m "📝 Aggiornamento funzionalità"
git push

# Render farà il deploy automaticamente!
```

## 🎯 Test dell'App

Una volta deployata, testa:
- **Homepage:** `https://tua-app.onrender.com/`
- **API Database:** `https://tua-app.onrender.com/database`
- **Calcolo De Minimis:** Inserisci una P.IVA di test

## ⚠️ Note Importanti

### Piano Gratuito:
- ✅ Perfetto per test e demo
- ⚠️ App si spegne dopo 15 min di inattività
- ⚠️ Primo avvio dopo inattività può richiedere 30-60 secondi

### Piano Starter ($7/mese):
- ✅ App sempre attiva
- ✅ Avvio istantaneo
- ✅ SSL automatico
- ✅ Dominio personalizzato

## 🐛 Risoluzione Problemi

### Build fallisce:
1. Controlla i log nella dashboard Render
2. Verifica che `requirements.txt` sia corretto
3. Assicurati che tutti i file siano committati

### App non si avvia:
1. Controlla che `web_finale.py` non abbia errori
2. Verifica le variabili d'ambiente
3. Controlla i log dell'applicazione

### Errori 500:
1. Attiva debug temporaneamente: `FLASK_DEBUG=True`
2. Controlla i log per errori specifici
3. Testa localmente prima del deploy

## 📞 Supporto

- **Render Docs:** [docs.render.com](https://docs.render.com)
- **Render Status:** [status.render.com](https://status.render.com)
- **Community:** [community.render.com](https://community.render.com)

---

**🎉 La tua app RNA De Minimis è pronta per il mondo!**
