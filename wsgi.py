#!/usr/bin/env python3
"""
WSGI Entry Point per RNA De Minimis App
======================================

File WSGI necessario per il deploy su Render.com
Punta all'applicazione Flask principale in web_finale.py

Autore: Pigreco Team
Data: Ottobre 2025
"""

# Importa l'applicazione Flask principale
from web_finale import app

# WSGI application object per Gunicorn
application = app

# Per compatibilità con diversi server WSGI
if __name__ == "__main__":
    # Questo non dovrebbe mai essere eseguito in produzione
    # ma è utile per test locali
    app.run(debug=False, host='0.0.0.0', port=8080)
