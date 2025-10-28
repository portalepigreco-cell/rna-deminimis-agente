#!/usr/bin/env python3
"""
🌐 RNA De Minimis Web - Versione Finale Funzionante
=================================================

Interfaccia web che funziona immediatamente con i dati precaricati
+ possibilità di inserimento manuale

Uso: python web_finale.py
Poi vai su: http://localhost:8080
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Istanza globale del calcolatore PMI (per riutilizzare la sessione browser)
calcolatore_pmi_globale = None

# Database precaricato con i risultati che abbiamo già testato
DATABASE_PIVA = {
    "03254550738": {"totale": 9505.95, "aiuti": 2, "note": "Testato - OK"},
    "04108170962": {"totale": 191018.50, "aiuti": 3, "note": "Testato - Attenzione"},
    "01392840417": {"totale": 68170.58, "aiuti": 8, "note": "Testato - OK"},
    "02279960419": {"totale": 162224.13, "aiuti": 6, "note": "Testato - Attenzione"}
}

@app.route('/')
def home():
    return render_template('finale.html')

@app.route('/calcola', methods=['POST'])
def calcola_deminimis():
    """Calcola de minimis (automatico se disponibile, altrimenti manuale)"""
    try:
        data = request.get_json()
        mode = data.get('mode', 'auto')  # 'auto' o 'manual'
        
        risultati = []
        
        if mode == 'auto':
            # Modalità automatica con calcolo reale RNA
            partite_iva = data.get('partite_iva', [])
            
            # Inizializza calcolatore RNA
            # Import lazy per evitare errori di dipendenze all'avvio su Render
            try:
                from rna_deminimis_playwright import RNACalculator
                calc = RNACalculator(headless=True)
            except Exception as e:
                print(f"⚠️ Errore inizializzazione RNA Calculator: {e}")
                return jsonify({"errore": f"❌ Servizio RNA temporaneamente non disponibile: {str(e)}"}), 503
            
            for piva in partite_iva:
                piva = piva.strip()
                
                if not re.match(r'^\d{11}$', piva):
                    risultati.append({
                        "partita_iva": piva,
                        "errore": "C.F. deve essere di 11 cifre",
                        "stato": "errore"
                    })
                    continue
                
                # Calcolo reale da RNA
                print(f"🔍 Calcolo de minimis per C.F.: {piva}")
                risultato_rna = calc.calcola_deminimis(piva)
                
                if risultato_rna.get("errore"):
                    risultati.append({
                        "partita_iva": piva,
                        "errore": risultato_rna["errore"],
                        "stato": "errore"
                    })
                    continue
                
                totale = risultato_rna["totale_de_minimis"]
                soglia = risultato_rna["soglia_limite"]
                percentuale = risultato_rna["percentuale_utilizzata"]
                
                # Determina stato
                if totale == 0:
                    stato = "nessun_aiuto"
                elif totale > soglia:
                    stato = "superata"
                elif percentuale > 80:
                    stato = "attenzione"
                else:
                    stato = "ok"
                
                risultati.append({
                    "partita_iva": piva,
                    "totale_de_minimis": totale,
                    "numero_aiuti": risultato_rna["numero_aiuti"],
                    "aiuti_trovati": risultato_rna.get("aiuti_trovati", []),
                    "percentuale_utilizzata": percentuale,
                    "margine_rimanente": risultato_rna["margine_rimanente"],
                    "stato": stato,
                    "data_ricerca": risultato_rna["data_ricerca"],
                    "fonte": "RNA.gov.it",
                    "pagine_analizzate": risultato_rna.get("pagine_analizzate", 1)
                })
        
        elif mode == 'aggregato':
            # Modalità aggregato: cerca nell'archivio Cribis + calcola de minimis gruppo
            # TEMPORANEAMENTE DISABILITATA SU RENDER (usa Selenium invece di Playwright)
            import os
            if os.environ.get('RENDER') or os.environ.get('FLASK_ENV') == 'production':
                return jsonify({
                    "errore": "⚠️ Non presente in archivio Pigreco di Cribis",
                    "dettaglio": "Utilizza la modalità 'Collegato (Nuova Ricerca)' per generare un report in tempo reale."
                }), 404
            
            partita_iva = data.get('partita_iva', '').strip()
            
            if not partita_iva:
                return jsonify({"errore": "Partita IVA mancante"}), 400
            
            print(f"🏢 Avvio calcolo aggregato per C.F.: {partita_iva}")
            
            # 1. Cerca associate nell'archivio Cribis (import lazy)
            try:
                from cribis_connector import CribisXConnector
                cribis = CribisXConnector(headless=True)
            except Exception as e:
                print(f"⚠️ Errore inizializzazione Cribis: {e}")
                return jsonify({"errore": "Servizio Cribis archivio non disponibile. Usa 'Nuova Ricerca' invece."}), 503
            risultato_cribis = cribis.cerca_associate(partita_iva)
            
            if risultato_cribis.get("errore"):
                return jsonify({
                    "errore": f"Errore ricerca Cribis: {risultato_cribis['errore']}",
                    "partita_iva": partita_iva
                }), 500
            
            # 2. Prepara lista società da calcolare (capogruppo + associate)
            societa_da_calcolare = [partita_iva]  # Capogruppo
            associate = risultato_cribis.get("associate_italiane_controllate", [])
            
            for azienda in associate:
                cf = azienda.get("codice_fiscale", "").strip()
                if cf and cf not in societa_da_calcolare:
                    societa_da_calcolare.append(cf)
            
            print(f"📋 Società da calcolare: {len(societa_da_calcolare)}")
            
            # 3. Calcola de minimis per ogni società (import lazy)
            try:
                from rna_deminimis_playwright import RNACalculator
                calc = RNACalculator(headless=True)
            except Exception as e:
                print(f"⚠️ Errore inizializzazione RNA Calculator: {e}")
                return jsonify({"errore": f"❌ Servizio RNA temporaneamente non disponibile: {str(e)}"}), 503
            risultati_dettaglio = []
            totale_gruppo = 0
            
            for cf in societa_da_calcolare:
                print(f"  🔍 Calcolo de minimis per C.F.: {cf}")
                risultato_rna = calc.calcola_deminimis(cf)
                
                if not risultato_rna.get("errore"):
                    totale = risultato_rna["totale_de_minimis"]
                    totale_gruppo += totale
                    
                    risultati_dettaglio.append({
                        "codice_fiscale": cf,
                        "totale_de_minimis": totale,
                        "numero_aiuti": risultato_rna["numero_aiuti"],
                        "aiuti_trovati": risultato_rna.get("aiuti_trovati", []),
                        "stato": "ok" if totale < 160000 else "attenzione"
                    })
                else:
                    print(f"  ⚠️ Errore per {cf}: {risultato_rna['errore']}")
                    risultati_dettaglio.append({
                        "codice_fiscale": cf,
                        "errore": risultato_rna["errore"]
                    })
            
            # 4. Calcola stato globale
            soglia = 200000.0
            percentuale_gruppo = (totale_gruppo / soglia) * 100
            margine_gruppo = max(0, soglia - totale_gruppo)
            
            if totale_gruppo == 0:
                stato_gruppo = "nessun_aiuto"
            elif totale_gruppo > soglia:
                stato_gruppo = "superata"
            elif percentuale_gruppo > 80:
                stato_gruppo = "attenzione"
            else:
                stato_gruppo = "ok"
            
            # 5. Prepara risposta aggregata
            risultati.append({
                "partita_iva": partita_iva,
                "totale_de_minimis": totale_gruppo,
                "percentuale_utilizzata": round(percentuale_gruppo, 1),
                "margine_rimanente": margine_gruppo,
                "stato": stato_gruppo,
                "data_ricerca": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "fonte": "RNA.gov.it + Cribis Archivio",
                "numero_societa": len(societa_da_calcolare),
                "dettaglio_societa": risultati_dettaglio
            })
        
        else:
            # Modalità manuale
            entries = data.get('entries', [])
            
            for entry in entries:
                piva = entry.get('piva', '').strip()
                importo = float(entry.get('importo', 0))
                
                if not re.match(r'^\d{11}$', piva):
                    risultati.append({
                        "partita_iva": piva,
                        "errore": "P.IVA deve essere di 11 cifre",
                        "stato": "errore"
                    })
                    continue
                
                # Calcola percentuali
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
                    "stato": stato,
                    "data_ricerca": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "fonte": "Inserimento manuale"
                })
        
        return jsonify({"risultati": risultati})
        
    except Exception as e:
        import traceback
        print(f"Errore: {traceback.format_exc()}")
        return jsonify({"errore": f"Errore server: {str(e)}"}), 500

@app.route('/database')
def mostra_database():
    """Mostra il database delle P.IVA precaricate"""
    return jsonify({"database": DATABASE_PIVA})

@app.route('/cribis_nuova_ricerca', methods=['POST'])
def cribis_nuova_ricerca():
    """Nuova Ricerca Cribis - genera report in tempo reale"""
    try:
        data = request.get_json()
        partita_iva = data.get('partita_iva', '').strip()
        
        # Validazione P.IVA
        if not re.match(r'^\d{11}$', partita_iva):
            return jsonify({
                "errore": "P.IVA deve essere di 11 cifre",
                "partita_iva": partita_iva
            }), 400
        
        # Chiama la funzione di ricerca (headless su produzione, visibile su sviluppo)
        print(f"🔍 Avvio Nuova Ricerca Cribis per P.IVA: {partita_iva}")
        # Import lazy per evitare errori di dipendenze all'avvio su Render
        try:
            import os
            from cribis_nuova_ricerca import cerca_associate_nuova_procedura
            # Headless su Render/produzione, visibile in locale
            is_production = ('RENDER' in os.environ) or (os.environ.get('FLASK_ENV') == 'production')
            risultato = cerca_associate_nuova_procedura(partita_iva, headless=is_production)
        except Exception as e:
            print(f"⚠️ Errore inizializzazione Cribis Nuova Ricerca: {e}")
            import traceback
            print(traceback.format_exc())
            return jsonify({"errore": f"❌ Servizio Cribis temporaneamente non disponibile: {str(e)}"}), 503
        
        # Formatta il risultato per il frontend
        if risultato.get("errore"):
            errore_msg = risultato["errore"]
            
            # Gestione errori specifici
            if "Click nome azienda fallito" in errore_msg or "Ricerca nel campo principale fallita" in errore_msg:
                # P.IVA non trovata in Cribis (potrebbe essere CF o non esistere)
                return jsonify({
                    "errore": "⚠️ Verifica Partita IVA: non presente in Cribis",
                    "dettaglio": "La P.IVA cercata non è stata trovata nel database Cribis. Potrebbe essere un Codice Fiscale o una P.IVA non registrata.",
                    "partita_iva": partita_iva
                }), 404
            else:
                # Altri errori
                return jsonify({
                    "errore": errore_msg,
                    "partita_iva": partita_iva
                }), 500
        
        # Gestione messaggio informativo (es: "La società non ha collegate")
        if risultato.get("messaggio"):
            return jsonify({
                "messaggio": risultato["messaggio"],
                "partita_iva": partita_iva,
                "associate_italiane_controllate": [],
                "riepilogo": {
                    "numero_associate": 0,
                    "totale_de_minimis": 0,
                    "numero_aiuti_totale": 0
                }
            }), 200
        
        associate = risultato.get("associate_italiane_controllate", [])
        
        # Calcola de minimis per capogruppo + tutte le associate
        print(f"📊 Calcolo de minimis aggregato per {len(associate) + 1} società...")
        
        # Prepara lista società da calcolare (capogruppo + associate)
        societa_da_calcolare = [partita_iva]  # Capogruppo
        for azienda in associate:
            cf = azienda.get("codice_fiscale", "").strip()
            if cf and cf not in societa_da_calcolare:
                societa_da_calcolare.append(cf)
        
        # Calcola de minimis per ogni società (import lazy)
        try:
            from rna_deminimis_playwright import RNACalculator
            calc = RNACalculator(headless=True)
        except Exception as e:
            print(f"⚠️ Errore inizializzazione RNA Calculator: {e}")
            return jsonify({"errore": f"❌ Servizio RNA temporaneamente non disponibile: {str(e)}"}), 503
        risultati_dettaglio = []
        totale_gruppo = 0
        numero_aiuti_totale = 0
        tutti_aiuti = []
        
        for cf in societa_da_calcolare:
            print(f"  🔍 Calcolo de minimis per C.F.: {cf}")
            risultato_rna = calc.calcola_deminimis(cf)
            
            if not risultato_rna.get("errore"):
                totale = risultato_rna["totale_de_minimis"]
                numero_aiuti = risultato_rna["numero_aiuti"]
                totale_gruppo += totale
                numero_aiuti_totale += numero_aiuti
                
                # Aggiungi aiuti con info società
                aiuti_societa = risultato_rna.get("aiuti_trovati", [])
                for aiuto in aiuti_societa:
                    aiuto["societa_cf"] = cf
                    tutti_aiuti.append(aiuto)
                
                risultati_dettaglio.append({
                    "codice_fiscale": cf,
                    "totale_de_minimis": totale,
                    "numero_aiuti": numero_aiuti,
                    "aiuti_trovati": aiuti_societa,
                    "stato": "ok" if totale < 160000 else "attenzione"
                })
            else:
                print(f"  ⚠️ Errore per {cf}: {risultato_rna['errore']}")
                risultati_dettaglio.append({
                    "codice_fiscale": cf,
                    "errore": risultato_rna["errore"]
                })
        
        # Calcola stato globale
        soglia = 200000.0
        percentuale_gruppo = (totale_gruppo / soglia) * 100
        margine_gruppo = max(0, soglia - totale_gruppo)
        
        if totale_gruppo == 0:
            stato_gruppo = "nessun_aiuto"
        elif totale_gruppo > soglia:
            stato_gruppo = "superata"
        elif percentuale_gruppo > 80:
            stato_gruppo = "attenzione"
        else:
            stato_gruppo = "ok"
        
        # Ordina aiuti per data (più recenti prima)
        tutti_aiuti.sort(key=lambda x: x.get("data_concessione", x.get("data", "")), reverse=True)
        
        return jsonify({
            "partita_iva": partita_iva,
            "associate_controllate": associate,
            "numero_associate": len(associate),
            "data_ricerca": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "successo": True,
            # Dati aggregati de minimis
            "totale_de_minimis": totale_gruppo,
            "numero_aiuti": numero_aiuti_totale,
            "percentuale_utilizzata": round(percentuale_gruppo, 1),
            "margine_rimanente": margine_gruppo,
            "stato": stato_gruppo,
            "fonte": "RNA.gov.it + Cribis Nuova Ricerca",
            "numero_societa": len(societa_da_calcolare),
            "dettaglio_societa": risultati_dettaglio,
            "tutti_aiuti": tutti_aiuti
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Errore Cribis: {traceback.format_exc()}")
        return jsonify({
            "errore": f"Errore durante la ricerca: {str(e)}",
            "partita_iva": partita_iva
        }), 500


@app.route('/calcola_dimensione_pmi', methods=['POST'])
def calcola_dimensione_pmi():
    """
    Calcola la dimensione d'impresa (PMI) secondo Raccomandazione UE 2003/361/CE
    
    Input JSON:
        {
            "partita_iva": "12345678901"
        }
    
    Output JSON:
        {
            "risultato": "success" | "errore",
            "partita_iva": "12345678901",
            "classificazione": {
                "dimensione": "Media Impresa",
                "note": "...",
                "soglie_rispettate": {...}
            },
            "aggregati_ue": {
                "personale_totale": 45.5,
                "fatturato_totale": 15000000,
                "attivo_totale": 12000000
            },
            "gruppo_societario": {
                "principale": {...},
                "collegate": [...],
                "partner": [...]
            },
            "societa_senza_dati": [...],
            "tempo_elaborazione_secondi": 120
        }
    """
    try:
        data = request.get_json()
        partita_iva = data.get('partita_iva', '').strip()
        
        # Validazione P.IVA
        if not re.match(r'^\d{11}$', partita_iva):
            return jsonify({
                "risultato": "errore",
                "errore": "P.IVA deve essere di 11 cifre",
                "partita_iva": partita_iva
            }), 400
        
        print(f"\n{'='*70}")
        print(f"📊 RICHIESTA CALCOLO DIMENSIONE PMI")
        print(f"P.IVA: {partita_iva}")
        print(f"{'='*70}\n")
        
        # Import lazy per evitare errori di dipendenze all'avvio
        try:
            import os
            from dimensione_impresa_pmi import CalcolatoreDimensionePMI
            
            # Headless su Render/produzione, visibile in locale per debug
            is_production = ('RENDER' in os.environ) or (os.environ.get('FLASK_ENV') == 'production')
            
            print(f"🔧 Modalità: {'PRODUZIONE (headless)' if is_production else 'SVILUPPO (browser visibile)'}")
            
            # Riutilizza istanza globale se esiste, altrimenti creane una nuova
            global calcolatore_pmi_globale
            if calcolatore_pmi_globale is None:
                print("🆕 Creo nuova istanza calcolatore (prima richiesta)")
                calcolatore_pmi_globale = CalcolatoreDimensionePMI(headless=is_production)
                # Inizializza browser e login una sola volta
                calcolatore_pmi_globale.cribis = None  # Sarà inizializzato al primo uso
            else:
                print("♻️  Riutilizzo istanza calcolatore esistente (sessione già attiva)")
            
            calc = calcolatore_pmi_globale
            
        except Exception as e:
            print(f"⚠️ Errore inizializzazione Calcolatore PMI: {e}")
            import traceback
            print(traceback.format_exc())
            return jsonify({
                "risultato": "errore",
                "errore": f"❌ Servizio Dimensione PMI temporaneamente non disponibile: {str(e)}"
            }), 503
        
        # Esegui calcolo
        try:
            risultato = calc.calcola_dimensione(partita_iva)
            
            # Verifica se c'è un errore
            if risultato.get("risultato") == "errore":
                print(f"❌ Errore calcolo: {risultato.get('errore', 'Errore sconosciuto')}")
                return jsonify({
                    "risultato": "errore",
                    "errore": risultato.get("errore", "Errore durante il calcolo"),
                    "partita_iva": partita_iva
                }), 500
            
            # Successo - formatta risposta per frontend
            print(f"✅ Calcolo completato con successo!")
            print(f"   Classificazione: {risultato['classificazione']['dimensione']}")
            print(f"   Tempo: {risultato['tempo_elaborazione_secondi']}s")
            
            # Prepara risposta JSON pulita
            risposta = {
                "risultato": "success",
                "partita_iva": partita_iva,
                "data_calcolo": risultato["data_calcolo"],
                
                # Impresa principale
                "impresa_principale": {
                    "cf": risultato["impresa_principale"]["cf"],
                    "ragione_sociale": risultato["impresa_principale"].get("ragione_sociale", "N/D"),
                    "personale": risultato["impresa_principale"].get("personale"),
                    "fatturato": risultato["impresa_principale"].get("fatturato"),
                    "attivo": risultato["impresa_principale"].get("attivo"),
                    "anno_riferimento": risultato["impresa_principale"].get("anno_riferimento", "N/D"),
                    "stato_dati": risultato["impresa_principale"].get("stato_dati", "assenti")
                },
                
                # Gruppo societario
                "gruppo_societario": {
                    "collegate": [
                        {
                            "cf": soc["cf"],
                            "nome": soc["nome"],
                            "percentuale": soc["percentuale"],
                            "personale": soc.get("personale"),
                            "fatturato": soc.get("fatturato"),
                            "attivo": soc.get("attivo"),
                            "stato_dati": soc.get("stato_dati", "assenti")
                        }
                        for soc in risultato.get("societa_collegate", [])
                    ],
                    "partner": [
                        {
                            "cf": soc["cf"],
                            "nome": soc["nome"],
                            "percentuale": soc["percentuale"],
                            "personale": soc.get("personale"),
                            "fatturato": soc.get("fatturato"),
                            "attivo": soc.get("attivo"),
                            "stato_dati": soc.get("stato_dati", "assenti")
                        }
                        for soc in risultato.get("societa_partner", [])
                    ],
                    "numero_collegate": len(risultato.get("societa_collegate", [])),
                    "numero_partner": len(risultato.get("societa_partner", [])),
                    "totale_societa": len(risultato.get("societa_collegate", [])) + len(risultato.get("societa_partner", []))
                },
                
                # Aggregati UE
                "aggregati_ue": risultato["aggregati_ue"],
                
                # Classificazione
                "classificazione": risultato["classificazione"],
                
                # Società senza dati
                "societa_senza_dati": risultato.get("societa_senza_dati", []),
                
                # Metadati
                "tempo_elaborazione_secondi": risultato["tempo_elaborazione_secondi"],
                "fonte": "Cribis X + Raccomandazione UE 2003/361/CE"
            }
            
            return jsonify(risposta), 200
            
        except Exception as e:
            print(f"❌ Errore durante il calcolo: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            return jsonify({
                "risultato": "errore",
                "errore": f"Errore durante il calcolo: {str(e)}",
                "partita_iva": partita_iva
            }), 500
    
    except Exception as e:
        import traceback
        print(f"❌ Errore generale endpoint PMI: {traceback.format_exc()}")
        return jsonify({
            "risultato": "errore",
            "errore": f"Errore del server: {str(e)}",
            "partita_iva": partita_iva if 'partita_iva' in locals() else "N/D"
        }), 500


if __name__ == '__main__':
    import os
    
    # Configurazione per produzione vs sviluppo
    PORT = int(os.environ.get('PORT', 8080))  # Render fornisce PORT via env var
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print("🌐 RNA De Minimis Web - Versione Finale")
    print(f"📍 Porta: {PORT}")
    print(f"🔧 Debug: {DEBUG}")
    print("🎯 Calcolo reale da RNA.gov.it + Cribis")
    print("📋 Output con copia Markdown")
    
    # Verifica ambiente Render
    if os.environ.get('RENDER'):
        print("🚀 Deploy su Render rilevato")
        print("⚠️  Su Free Plan: funzionalità Cribis/RNA potrebbero essere limitate")
        print("💡 Upgrade a Hobby ($19) per prestazioni complete")
    
    if not DEBUG:
        print("🚀 Modalità PRODUZIONE - App pronta per Render")
    else:
        print(f"🛠️  Modalità SVILUPPO - Vai su: http://localhost:{PORT}")
        print("🛑 Premi Ctrl+C per fermare")
    
    app.run(debug=DEBUG, host='0.0.0.0', port=PORT)
