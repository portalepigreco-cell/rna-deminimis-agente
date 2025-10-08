#!/usr/bin/env python3
"""
🌐 RNA De Minimis Web Interface
============================

Interfaccia web dark mode per calcolare il de minimis di una o più P.IVA

Uso: python web_interface.py
Poi vai su: http://localhost:5000

Autore: Pigreco Team
Data: Settembre 2025
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import threading
import re
from datetime import datetime
from rna_deminimis import RNACalculator

app = Flask(__name__)
CORS(app)  # Abilita CORS per evitare errori 403

@app.route('/')
def home():
    """Pagina principale"""
    return render_template('index.html')

@app.route('/calcola', methods=['POST'])
def calcola_deminimis():
    """API per calcolare de minimis"""
    try:
        data = request.get_json()
        partite_iva = data.get('partite_iva', [])
        
        if not partite_iva:
            return jsonify({"errore": "Nessuna P.IVA fornita"})
        
        risultati = []
        
        for piva in partite_iva:
            piva = piva.strip()
            
            # Validazione
            if not re.match(r'^\d{11}$', piva):
                risultati.append({
                    "partita_iva": piva,
                    "errore": "P.IVA deve essere di 11 cifre",
                    "totale_de_minimis": 0,
                    "stato": "errore"
                })
                continue
            
            # Calcola de minimis
            calcolatore = RNACalculator(headless=True)
            risultato = calcolatore.calcola_deminimis(piva)
            
            if "errore" in risultato:
                risultati.append({
                    "partita_iva": piva,
                    "errore": risultato["errore"],
                    "totale_de_minimis": 0,
                    "numero_aiuti": 0,
                    "percentuale_utilizzata": 0,
                    "margine_rimanente": 200000,
                    "stato": "errore",
                    "data_ricerca": risultato.get("data_ricerca", "N/A")
                })
            else:
                # Determina stato
                if risultato["totale_de_minimis"] == 0:
                    stato = "nessun_aiuto"
                elif risultato["soglia_superata"]:
                    stato = "superata"
                elif risultato["percentuale_utilizzata"] > 80:
                    stato = "attenzione"
                else:
                    stato = "ok"
                
                risultati.append({
                    "partita_iva": piva,
                    "totale_de_minimis": risultato["totale_de_minimis"],
                    "numero_aiuti": risultato["numero_aiuti"],
                    "percentuale_utilizzata": risultato["percentuale_utilizzata"],
                    "margine_rimanente": risultato["margine_rimanente"],
                    "stato": stato,
                    "data_ricerca": risultato["data_ricerca"]
                })
        
        return jsonify({"risultati": risultati})
        
    except Exception as e:
        import traceback
        print(f"Errore completo: {traceback.format_exc()}")
        return jsonify({"errore": f"Errore server: {str(e)}"}), 500

if __name__ == '__main__':
    PORT = 8080  # Usa porta 8080 invece di 5000
    print("🌐 Avviando RNA De Minimis Web Interface...")
    print(f"📍 Vai su: http://localhost:{PORT}")
    print("🛑 Premi Ctrl+C per fermare")
    
    app.run(debug=True, host='0.0.0.0', port=PORT)
