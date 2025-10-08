#!/usr/bin/env python3
"""
🌐 RNA De Minimis Web - Versione Semplice
=======================================

Interfaccia web semplice per visualizzare risultati de minimis
(senza automazione - per inserimento manuale)

Uso: python web_simple.py
Poi vai su: http://localhost:8080

Autore: Pigreco Team
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('simple.html')

@app.route('/calcola', methods=['POST'])
def calcola_manuale():
    """Calcola totali da dati inseriti manualmente"""
    try:
        data = request.get_json()
        entries = data.get('entries', [])
        
        risultati = []
        for entry in entries:
            piva = entry.get('piva', '').strip()
            importo = float(entry.get('importo', 0))
            
            # Validazione P.IVA
            if not re.match(r'^\d{11}$', piva):
                risultati.append({
                    "partita_iva": piva,
                    "errore": "P.IVA deve essere di 11 cifre",
                    "stato": "errore"
                })
                continue
            
            # Analisi soglia
            soglia = 200000.0
            percentuale = (importo / soglia) * 100
            margine = max(0, soglia - importo)
            
            if importo == 0:
                stato = "nessun_aiuto"
            elif importo > soglia:
                stato = "superata"
            elif percentuale > 80:
                stato = "attenzione"
            else:
                stato = "ok"
            
            risultati.append({
                "partita_iva": piva,
                "totale_de_minimis": importo,
                "percentuale_utilizzata": round(percentuale, 1),
                "margine_rimanente": margine,
                "stato": stato
            })
        
        return jsonify({"risultati": risultati})
        
    except Exception as e:
        return jsonify({"errore": f"Errore: {e}"}), 500

if __name__ == '__main__':
    PORT = 8080
    print("🌐 RNA De Minimis Web - Versione Semplice")
    print(f"📍 Vai su: http://localhost:{PORT}")
    print("🛑 Premi Ctrl+C per fermare")
    
    app.run(debug=True, host='0.0.0.0', port=PORT)
