# Dockerfile per RNA De Minimis Agent con Playwright
# Usa immagine ufficiale Microsoft Playwright con Python
# Questa immagine include già Chromium e tutte le dipendenze di sistema

FROM mcr.microsoft.com/playwright/python:v1.56.0-jammy

# Imposta directory di lavoro
WORKDIR /app

# Copia file requirements
COPY requirements.txt .

# Installa dipendenze Python
# --no-cache-dir riduce dimensione immagine
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia tutto il codice dell'applicazione
COPY . .

# Crea directory per eventuali file temporanei
RUN mkdir -p /app/temp

# Espone porta (Render usa variabile d'ambiente $PORT)
EXPOSE 10000

# Variabili d'ambiente di default (override da Render)
ENV FLASK_ENV=production
ENV FLASK_DEBUG=False
ENV PYTHONUNBUFFERED=1

# Comando di avvio
# Usa gunicorn con 1 worker per compatibilità Playwright
# Timeout 300s per operazioni lunghe (scraping RNA)
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --worker-class sync --timeout 600 --access-logfile - --error-logfile - wsgi:application


