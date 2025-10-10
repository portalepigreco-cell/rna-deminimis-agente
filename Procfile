# Procfile per Render deployment
# =============================
# 
# Definisce come avviare l'applicazione su Render
# Usa gunicorn per performance migliori in produzione
#
# Autore: Pigreco Team

web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --worker-class sync --timeout 120 wsgi:application
