#!/usr/bin/env python3
"""
🔧 Gestione P.IVA - Interfaccia Semplice
=====================================

Interfaccia per aggiungere nuove P.IVA al database

Uso: python gestione_piva.py
Poi vai su: http://localhost:8080

Autore: Pigreco Team
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import re
from datetime import datetime
import os

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
    return render_template('gestione.html')

@app.route('/lista', methods=['GET'])
def lista_piva():
    """Lista tutte le P.IVA nel database"""
    database = carica_database()
    
    # Trasforma in lista con calcoli
    piva_list = []
    for piva, dati in database.items():
        soglia = 200000.0
        percentuale = (dati["totale"] / soglia) * 100
        margine = max(0, soglia - dati["totale"])
        
        if dati["totale"] == 0:
            stato = "nessun_aiuto"
        elif dati["totale"] > soglia:
            stato = "superata"
        elif percentuale > 80:
            stato = "attenzione"
        else:
            stato = "ok"
        
        piva_list.append({
            "partita_iva": piva,
            "totale_de_minimis": dati["totale"],
            "numero_aiuti": dati.get("aiuti", 0),
            "percentuale_utilizzata": round(percentuale, 1),
            "margine_rimanente": margine,
            "stato": stato,
            "note": dati.get("note", ""),
            "data_aggiunta": dati.get("data_aggiunta", "N/A")
        })
    
    # Ordina per percentuale (più alta prima)
    piva_list.sort(key=lambda x: x["percentuale_utilizzata"], reverse=True)
    
    return jsonify({"piva_list": piva_list, "totale": len(piva_list)})

@app.route('/aggiungi', methods=['POST'])
def aggiungi_piva():
    """Aggiunge una nuova P.IVA al database"""
    try:
        data = request.get_json()
        piva = data.get('piva', '').strip()
        totale = float(data.get('totale', 0))
        aiuti = int(data.get('aiuti', 0))
        note = data.get('note', '').strip()
        
        # Validazione
        if not re.match(r'^\d{11}$', piva):
            return jsonify({"errore": "P.IVA deve essere di 11 cifre"}), 400
        
        if totale < 0:
            return jsonify({"errore": "Totale non può essere negativo"}), 400
        
        if aiuti < 0:
            return jsonify({"errore": "Numero aiuti non può essere negativo"}), 400
        
        # Carica database
        database = carica_database()
        
        # Controlla se esiste già
        if piva in database:
            return jsonify({"errore": f"P.IVA {piva} già presente nel database"}), 400
        
        # Aggiungi nuova P.IVA
        database[piva] = {
            "totale": totale,
            "aiuti": aiuti,
            "note": note or "Aggiunta manualmente",
            "data_aggiunta": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        
        # Salva
        salva_database(database)
        
        return jsonify({
            "successo": True,
            "messaggio": f"P.IVA {piva} aggiunta con successo",
            "totale_database": len(database)
        })
        
    except ValueError:
        return jsonify({"errore": "Valori numerici non validi"}), 400
    except Exception as e:
        return jsonify({"errore": f"Errore: {str(e)}"}), 500

@app.route('/modifica', methods=['POST'])
def modifica_piva():
    """Modifica una P.IVA esistente"""
    try:
        data = request.get_json()
        piva = data.get('piva', '').strip()
        totale = float(data.get('totale', 0))
        aiuti = int(data.get('aiuti', 0))
        note = data.get('note', '').strip()
        
        # Validazione
        if not re.match(r'^\d{11}$', piva):
            return jsonify({"errore": "P.IVA deve essere di 11 cifre"}), 400
        
        # Carica database
        database = carica_database()
        
        # Controlla se esiste
        if piva not in database:
            return jsonify({"errore": f"P.IVA {piva} non trovata nel database"}), 404
        
        # Aggiorna
        database[piva].update({
            "totale": totale,
            "aiuti": aiuti,
            "note": note or database[piva].get("note", ""),
            "data_modifica": datetime.now().strftime("%d/%m/%Y %H:%M")
        })
        
        # Salva
        salva_database(database)
        
        return jsonify({
            "successo": True,
            "messaggio": f"P.IVA {piva} modificata con successo"
        })
        
    except ValueError:
        return jsonify({"errore": "Valori numerici non validi"}), 400
    except Exception as e:
        return jsonify({"errore": f"Errore: {str(e)}"}), 500

@app.route('/elimina', methods=['POST'])
def elimina_piva():
    """Elimina una P.IVA dal database"""
    try:
        data = request.get_json()
        piva = data.get('piva', '').strip()
        
        # Carica database
        database = carica_database()
        
        # Controlla se esiste
        if piva not in database:
            return jsonify({"errore": f"P.IVA {piva} non trovata"}), 404
        
        # Elimina
        del database[piva]
        
        # Salva
        salva_database(database)
        
        return jsonify({
            "successo": True,
            "messaggio": f"P.IVA {piva} eliminata con successo",
            "totale_database": len(database)
        })
        
    except Exception as e:
        return jsonify({"errore": f"Errore: {str(e)}"}), 500

@app.route('/calcola/<piva>')
def calcola_singola(piva):
    """Calcola de minimis per una singola P.IVA"""
    database = carica_database()
    
    if piva not in database:
        return jsonify({"errore": "P.IVA non trovata"}), 404
    
    dati = database[piva]
    soglia = 200000.0
    percentuale = (dati["totale"] / soglia) * 100
    margine = max(0, soglia - dati["totale"])
    
    if dati["totale"] == 0:
        stato = "nessun_aiuto"
    elif dati["totale"] > soglia:
        stato = "superata"
    elif percentuale > 80:
        stato = "attenzione"
    else:
        stato = "ok"
    
    return jsonify({
        "partita_iva": piva,
        "totale_de_minimis": dati["totale"],
        "numero_aiuti": dati.get("aiuti", 0),
        "percentuale_utilizzata": round(percentuale, 1),
        "margine_rimanente": margine,
        "stato": stato,
        "note": dati.get("note", ""),
        "data_aggiunta": dati.get("data_aggiunta", "N/A")
    })

if __name__ == '__main__':
    PORT = 8080
    print("🔧 Gestione P.IVA - RNA De Minimis")
    print(f"📍 Vai su: http://localhost:{PORT}")
    print("➕ Aggiungi, modifica ed elimina P.IVA")
    print("🛑 Premi Ctrl+C per fermare")
    
    app.run(debug=True, host='0.0.0.0', port=PORT)
