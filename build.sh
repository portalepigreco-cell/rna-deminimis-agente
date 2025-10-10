#!/bin/bash
# Script di build robusto per Render con fallback automatico
# Autore: Pigreco Team
# Data: Ottobre 2025

set -e  # Exit on error

echo "🚀 Avvio build RNA De Minimis App per Render..."

# 1. Imposta variabile d'ambiente Playwright PRIMA di tutto
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.cache/ms-playwright
echo "✅ PLAYWRIGHT_BROWSERS_PATH impostato: $PLAYWRIGHT_BROWSERS_PATH"

# 2. Upgrade pip
echo "📦 Upgrade pip..."
pip install --upgrade pip

# 3. Installa requirements
echo "📦 Installazione requirements..."
pip install -r requirements.txt

# 4. Installa browser Playwright con fallback automatico
echo "🌐 Installazione browser Playwright..."

# Tentativo 1: Con --with-deps (richiede permessi di sistema)
if playwright install --with-deps chromium 2>&1 | tee /tmp/playwright-install.log; then
    echo "✅ Browser installato con successo (con dipendenze di sistema)"
else
    echo "⚠️ Installazione con --with-deps fallita, provo senza..."
    
    # Tentativo 2: Senza --with-deps (fallback)
    if playwright install chromium; then
        echo "✅ Browser installato con successo (modalità fallback)"
        echo "ℹ️ Nota: Alcune funzionalità potrebbero essere limitate senza dipendenze di sistema"
    else
        echo "❌ ERRORE: Impossibile installare browser Playwright"
        echo "📋 Log installazione:"
        cat /tmp/playwright-install.log || true
        exit 1
    fi
fi

# 5. Verifica installazione
echo "🔍 Verifica installazione browser..."
if [ -d "$PLAYWRIGHT_BROWSERS_PATH" ]; then
    echo "✅ Directory browser trovata: $PLAYWRIGHT_BROWSERS_PATH"
    ls -lah "$PLAYWRIGHT_BROWSERS_PATH" || true
else
    echo "⚠️ Directory browser non trovata nel path configurato"
    echo "🔍 Ricerca browser in path alternativi..."
    find /opt/render -name "*chromium*" -type d 2>/dev/null | head -5 || true
fi

echo "🎉 Build completato con successo!"

