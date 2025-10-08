#!/usr/bin/env python3
"""
📝 Inserisci P.IVA - Interfaccia Ultra Semplice
===============================================

Solo per aggiungere P.IVA al database

Uso: python inserisci_piva.py
Poi vai su: http://localhost:8080

Autore: Pigreco Team
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import re
from datetime import datetime
import os
from rna_deminimis import RNACalculator

app = Flask(__name__)
CORS(app)

DATABASE_FILE = "database_piva.json"

def carica_database():
    """Carica il database delle P.IVA"""
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as f:
            return json.load(f)
    else:
        # Database iniziale con le P.IVA già testate
        return {
            "03254550738": {"totale": 9505.95, "aiuti": 2, "note": "Testato - OK", "data_aggiunta": "16/09/2025"},
            "04108170962": {"totale": 191018.50, "aiuti": 3, "note": "Testato - Attenzione", "data_aggiunta": "16/09/2025"},
            "01392840417": {"totale": 68170.58, "aiuti": 8, "note": "Testato - OK", "data_aggiunta": "16/09/2025"},
            "02279960419": {"totale": 162224.13, "aiuti": 6, "note": "Testato - Attenzione", "data_aggiunta": "16/09/2025"}
        }

def salva_database(database):
    """Salva il database delle P.IVA"""
    with open(DATABASE_FILE, 'w') as f:
        json.dump(database, f, indent=2)

@app.route('/')
def home():
    return render_template('inserisci.html')

@app.route('/aggiungi', methods=['POST'])
def aggiungi_piva():
    """Aggiunge P.IVA al database con calcolo automatico de minimis"""
    try:
        data = request.get_json()
        partite_iva = data.get('partite_iva', [])
        
        database = carica_database()
        aggiunte = []
        errori = []
        risultati = []
        
        # Inizializza calcolatore RNA
        calcolatore = RNACalculator()
        
        for piva in partite_iva:
            piva = piva.strip()
            
            # Validazione
            if not re.match(r'^\d{11}$', piva):
                errori.append(f"{piva}: deve essere di 11 cifre")
                continue
            
            # Rimuovi P.IVA esistente per ricalcolarla
            if piva in database:
                print(f"🔄 Aggiornando P.IVA esistente: {piva}")
                del database[piva]
            
            # Calcola de minimis automaticamente
            print(f"🔍 Calcolando de minimis per {piva}...")
            dati_rna = calcolatore.calcola_deminimis(piva)
            
            # Aggiungi P.IVA con dati calcolati
            database[piva] = {
                "totale": dati_rna.get("totale_de_minimis", 0.0),
                "aiuti": dati_rna.get("numero_aiuti", 0),
                "note": f"Calcolato automaticamente - {dati_rna.get('data_ricerca', 'N/A')}",
                "data_aggiunta": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "percentuale": dati_rna.get("percentuale_utilizzata", 0.0),
                "margine": dati_rna.get("margine_rimanente", 300000.0)
            }
            
            aggiunte.append(piva)
            risultati.append({
                "piva": piva,
                "totale": dati_rna.get("totale_de_minimis", 0.0),
                "aiuti": dati_rna.get("numero_aiuti", 0),
                "percentuale": dati_rna.get("percentuale_utilizzata", 0.0),
                "margine": dati_rna.get("margine_rimanente", 300000.0),
                "dettagli_aiuti": dati_rna.get("aiuti_trovati", [])
            })
        
        # Salva se ci sono state aggiunte
        if aggiunte:
            salva_database(database)
        
        return jsonify({
            "successo": len(aggiunte) > 0,
            "aggiunte": len(aggiunte),
            "totale_database": len(database),
            "piva_aggiunte": aggiunte,
            "risultati": risultati,
            "errori": errori
        })
        
    except Exception as e:
        print(f"❌ Errore nel calcolo: {str(e)}")
        return jsonify({"errore": f"Errore: {str(e)}"}), 500

@app.route('/count', methods=['GET'])
def conta_piva():
    """Conta P.IVA nel database"""
    database = carica_database()
    return jsonify({"totale": len(database)})

if __name__ == '__main__':
    PORT = 8080
    print("📝 Inserisci P.IVA - Ultra Semplice")
    print(f"📍 Vai su: http://localhost:{PORT}")
    print("➕ Solo per aggiungere P.IVA")
    print("🛑 Premi Ctrl+C per fermare")
    
    app.run(debug=True, host='0.0.0.0', port=PORT)
