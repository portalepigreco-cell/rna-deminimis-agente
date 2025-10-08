#!/usr/bin/env python3
"""
Interfaccia Web De Minimis Aggregato
Sistema integrato con ricerca associate Cribis X

Funzionalità:
- Input singola P.IVA/CF
- Ricerca automatica società associate
- Calcolo De Minimis aggregato del gruppo
- Visualizzazione risultati dettagliati per azienda
- Export Markdown per ChatGPT
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
from deminimis_aggregato import DeMinimisAggregato

# Inizializza Flask
app = Flask(__name__)
CORS(app)

# Configurazione
DATABASE_FILE = 'database_piva_aggregato.json'
aggregato_calculator = DeMinimisAggregato()

def carica_database():
    """Carica il database delle P.IVA già elaborate"""
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}

def salva_database(database):
    """Salva il database delle P.IVA"""
    try:
        with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(database, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Errore salvataggio database: {e}")

@app.route('/')
def index():
    """Pagina principale"""
    return render_template('inserisci_aggregato.html')

@app.route('/count')
def count():
    """Restituisce il numero di P.IVA nel database"""
    database = carica_database()
    return jsonify({"count": len(database)})

@app.route('/aggiungi', methods=['POST'])
def aggiungi_piva():
    """
    Processa una P.IVA e calcola De Minimis aggregato
    
    Body JSON:
    {
        "partite_iva": ["02918700168"]
    }
    
    Returns:
        JSON con risultati aggregati
    """
    try:
        data = request.get_json()
        partite_iva = data.get('partite_iva', [])
        
        if not partite_iva:
            return jsonify({"errore": "Nessuna P.IVA fornita"}), 400
        
        # Per ora processiamo solo la prima P.IVA (il sistema è progettato per elaborare una alla volta)
        piva = partite_iva[0].strip()
        
        if not piva:
            return jsonify({"errore": "P.IVA vuota"}), 400
        
        print(f"📝 Richiesta calcolo aggregato per: {piva}")
        
        # Carica database
        database = carica_database()
        
        # Rimuovi la P.IVA se esiste (ricalcola sempre)
        if piva in database:
            del database[piva]
            print(f"🔄 Ricalcolo P.IVA esistente: {piva}")
        
        # Calcola De Minimis aggregato
        print(f"🚀 Avvio calcolo aggregato...")
        risultato_aggregato = aggregato_calculator.calcola_deminimis_gruppo(piva)
        
        # Salva nel database
        database[piva] = risultato_aggregato
        salva_database(database)
        
        print(f"✅ Calcolo completato per {piva}")
        
        # Restituisci risultato
        return jsonify({
            "piva": piva,
            "risultato": risultato_aggregato
        })
        
    except Exception as e:
        print(f"❌ Errore processo P.IVA: {str(e)}")
        return jsonify({"errore": f"Errore interno: {str(e)}"}), 500

@app.route('/risultato/<piva>')
def get_risultato(piva):
    """Recupera risultato salvato per una P.IVA"""
    try:
        database = carica_database()
        
        if piva not in database:
            return jsonify({"errore": "P.IVA non trovata nel database"}), 404
        
        return jsonify({
            "piva": piva,
            "risultato": database[piva]
        })
        
    except Exception as e:
        print(f"❌ Errore recupero risultato: {str(e)}")
        return jsonify({"errore": f"Errore interno: {str(e)}"}), 500

@app.route('/lista')
def lista_piva():
    """Restituisce la lista di tutte le P.IVA elaborate"""
    try:
        database = carica_database()
        
        lista = []
        for piva, risultato in database.items():
            try:
                # Estrai informazioni principali
                totale_gruppo = risultato.get("totale_gruppo", {})
                lista.append({
                    "piva": piva,
                    "timestamp": risultato.get("timestamp", ""),
                    "metodo": risultato.get("metodo", "singolo"),
                    "numero_aziende": totale_gruppo.get("numero_aziende", 0),
                    "totale_deminimis": totale_gruppo.get("totale_deminimis", 0.0),
                    "stato": totale_gruppo.get("stato", "verde")
                })
            except Exception:
                # Risultato malformato, salta
                continue
        
        # Ordina per timestamp (più recenti prima)
        lista.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return jsonify({"lista": lista})
        
    except Exception as e:
        print(f"❌ Errore lista P.IVA: {str(e)}")
        return jsonify({"errore": f"Errore interno: {str(e)}"}), 500

@app.route('/cancella/<piva>', methods=['DELETE'])
def cancella_piva(piva):
    """Cancella una P.IVA dal database"""
    try:
        database = carica_database()
        
        if piva not in database:
            return jsonify({"errore": "P.IVA non trovata"}), 404
        
        del database[piva]
        salva_database(database)
        
        return jsonify({"messaggio": f"P.IVA {piva} cancellata"})
        
    except Exception as e:
        print(f"❌ Errore cancellazione: {str(e)}")
        return jsonify({"errore": f"Errore interno: {str(e)}"}), 500

@app.route('/calcola_singolo', methods=['POST'])
def calcola_singolo():
    """
    Endpoint per calcolo De Minimis singolo (senza ricerca associate)
    Più veloce per controlli rapidi di singole aziende
    """
    try:
        data = request.get_json()
        partite_iva = data.get('partite_iva', [])
        
        if not partite_iva:
            return jsonify({"errore": "Nessuna P.IVA fornita"}), 400
        
        piva = partite_iva[0].strip()
        
        if not piva:
            return jsonify({"errore": "P.IVA vuota"}), 400
        
        print(f"📝 Richiesta calcolo singolo per: {piva}")
        
        # Calcola De Minimis singolo (fallback diretto)
        print(f"🏠 Calcolo singolo diretto...")
        risultato_singolo = aggregato_calculator.calcola_deminimis_singolo(piva)
        
        print(f"✅ Calcolo singolo completato per {piva}")
        
        return jsonify({
            "piva": piva,
            "risultato": risultato_singolo,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Errore calcolo singolo: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({"errore": f"Errore interno: {str(e)}"}), 500

if __name__ == '__main__':
    print("🧮 De Minimis Aggregato - Sistema Integrato")
    print("📍 Vai su: http://localhost:8080")
    print("🏢 /aggiungi (POST) - Calcolo aggregato con Cribis X")
    print("🏠 /calcola_singolo (POST) - Calcolo singolo veloce")
    print("🛑 Premi Ctrl+C per fermare")
    
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=True
    )
