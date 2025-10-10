#!/bin/bash
# Script di build robusto per Render con fallback automatico
# Autore: Pigreco Team
# Data: Ottobre 2025

set -e  # Exit on error

echo "🚀 Avvio build RNA De Minimis App per Render..."

# 1. Upgrade pip
echo "📦 Upgrade pip..."
pip install --upgrade pip

# 2. Installa requirements
echo "📦 Installazione requirements..."
pip install -r requirements.txt

# 3. Installa browser Playwright con fallback automatico
echo "🌐 Installazione browser Playwright..."
echo "ℹ️ Uso path di default Playwright (più stabile su Render)"

# Tentativo 1: Senza --with-deps (consigliato per Render Free/Starter)
if playwright install chromium 2>&1 | tee /tmp/playwright-install.log; then
    echo "✅ Browser installato con successo"
    echo "ℹ️ Gli argomenti --no-sandbox nel codice compensano le dipendenze di sistema"
else
    echo "❌ ERRORE: Impossibile installare browser Playwright"
    echo "📋 Log installazione:"
    cat /tmp/playwright-install.log || true
    exit 1
fi

# 4. Verifica installazione
echo "🔍 Verifica installazione browser..."
PLAYWRIGHT_DEFAULT_PATH="$HOME/.cache/ms-playwright"

if [ -d "$PLAYWRIGHT_DEFAULT_PATH" ]; then
    echo "✅ Directory browser trovata: $PLAYWRIGHT_DEFAULT_PATH"
    ls -lah "$PLAYWRIGHT_DEFAULT_PATH" || true
elif [ -d "/opt/render/.cache/ms-playwright" ]; then
    echo "✅ Directory browser trovata: /opt/render/.cache/ms-playwright"
    ls -lah "/opt/render/.cache/ms-playwright" || true
else
    echo "🔍 Ricerca browser in tutti i path..."
    find /opt/render -name "*chromium*" -type d 2>/dev/null | head -10 || true
    find $HOME -name "*chromium*" -type d 2>/dev/null | head -10 || true
fi

echo "🎉 Build completato con successo!"

