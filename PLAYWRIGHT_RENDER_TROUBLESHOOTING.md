# 🔧 Playwright su Render - Troubleshooting

## ✅ Configurazione Attuale (CONSIGLIATA)

La configurazione in `render.yaml` include:

1. **Variabile d'ambiente PLAYWRIGHT_BROWSERS_PATH**: `/opt/render/project/src/.cache/ms-playwright`
2. **Build command**: Export della variabile + `playwright install --with-deps chromium`
3. **Argomenti browser**: `--no-sandbox`, `--disable-setuid-sandbox`, etc.

## 🔴 Se l'errore persiste: "Executable doesn't exist"

### Soluzione A: Rimuovere --with-deps

Se il build fallisce con errori di permessi, modifica `render.yaml`:

```yaml
buildCommand: |
  export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.cache/ms-playwright
  pip install --upgrade pip
  pip install -r requirements.txt
  playwright install chromium
```

**Nota**: Rimuovi `--with-deps`. Gli argomenti browser nel codice Python (`--no-sandbox`, etc.) compensano la mancanza delle dipendenze di sistema complete.

### Soluzione B: Usare piano Render superiore

Il piano **Standard** ($25/mese) ha più permessi di sistema e supporta `--with-deps`.

### Soluzione C: Clear Build Cache

Su Render Dashboard:
1. Vai al tuo servizio
2. Settings → Build & Deploy
3. Clicca "Clear Build Cache"
4. Fai un nuovo deploy manuale

### Soluzione D: Usare Docker (AVANZATA)

Crea un `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Installa dipendenze di sistema per Playwright
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libgbm1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installa browser Playwright
RUN playwright install chromium

COPY . .

CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 300 wsgi:application
```

Poi modifica `render.yaml` per usare Docker invece di Python nativo.

## 🧪 Test Locale Prima del Deploy

Prima di deployare, testa localmente con variabili d'ambiente Render simulate:

```bash
export PLAYWRIGHT_BROWSERS_PATH=/tmp/.cache/ms-playwright
export FLASK_ENV=production
playwright install chromium
python web_finale.py
```

## 📊 Verificare i Log su Render

Dopo il deploy, controlla i log:

1. Vai su Render Dashboard
2. Seleziona il tuo servizio
3. Clicca "Logs"
4. Cerca messaggi come:
   - `🔍 DEBUG Playwright:` - Mostra il path usato
   - `✅ Browser Chromium lanciato con successo` - OK!
   - `❌ ERRORE lancio browser` - Problema!

## 🆘 Se Nulla Funziona

Opzioni:
1. **Usa un servizio alternativo**: Heroku, Railway, Fly.io
2. **Usa API esterne**: Servizi come Browserless.io o ScrapingBee
3. **Usa Selenium + Firefox** invece di Playwright (meno performante ma più compatibile)

## 📞 Risorse Utili

- [Playwright Docs - System Requirements](https://playwright.dev/docs/intro)
- [Render Community Forum](https://community.render.com)
- [Playwright Docker Images](https://playwright.dev/docs/docker)

