#!/usr/bin/env python3
"""
De Minimis Aggregato - Sistema Integrato
Combina ricerca associate Cribis X + calcolo De Minimis

Funzionalità:
- Ricerca società associate tramite Cribis X
- Calcolo De Minimis per ogni azienda del gruppo
- Aggregazione dei risultati
- Output JSON strutturato per interfaccia web
"""

import json
import time
from datetime import datetime
from cribis_playwright_base import cerca_associate_playwright
from rna_deminimis_playwright import RNACalculator


class DeMinimisAggregato:
    """Calcolatore De Minimis aggregato per gruppi societari"""
    
    def __init__(self):
        """Inizializza i componenti necessari"""
        self.cribis = None
        self.rna_calculator = None
        self.soglia_deminimis = 300000.0  # €300.000 soglia EU
        
    def _inizializza_componenti(self):
        """Inizializza i componenti solo quando necessario"""
        if not self.rna_calculator:
            self.rna_calculator = RNACalculator()
            print("✅ RNACalculator inizializzato")
    
    def calcola_deminimis_gruppo(self, codice_fiscale_principale):
        """
        Calcola il De Minimis aggregato per un gruppo societario
        
        Args:
            codice_fiscale_principale (str): P.IVA/CF dell'azienda principale
            
        Returns:
            dict: Risultati aggregati del gruppo
        """
        print(f"🚀 CALCOLO DE MINIMIS AGGREGATO per: {codice_fiscale_principale}")
        
        risultato_finale = {
            "timestamp": datetime.now().isoformat(),
            "p_iva_principale": codice_fiscale_principale,
            "metodo": "aggregato",  # "singolo" o "aggregato"
            "associate_trovate": [],
            "risultati_per_azienda": [],
            "totale_gruppo": {
                "totale_deminimis": 0.0,
                "numero_aziende": 0,
                "numero_aiuti_totali": 0,
                "percentuale_utilizzata": 0.0,
                "margine_rimanente": 0.0,
                "stato": "verde"  # verde/giallo/rosso
            },
            "errore_cribis": None,
            "warning": []
        }
        
        try:
            # STEP 1: Ricerca associate su Cribis X con Playwright
            print("\n" + "="*50)
            print("📍 STEP 1: Ricerca società associate (Playwright)")
            print("="*50)
            
            # Usa Playwright invece di Selenium per maggiore affidabilità
            ricerca_cribis = cerca_associate_playwright(codice_fiscale_principale, headless=True)
            
            if ricerca_cribis.get("errore"):
                print(f"⚠️  Errore Cribis X: {ricerca_cribis['errore']}")
                risultato_finale["errore_cribis"] = ricerca_cribis["errore"]
                risultato_finale["warning"].append("Ricerca associate fallita - calcolo solo azienda principale")
                
                # Fallback: calcola solo l'azienda principale
                return self._calcola_solo_principale(codice_fiscale_principale, risultato_finale)
            
            # Associate trovate
            associate = ricerca_cribis.get("associate_italiane_controllate", [])
            risultato_finale["associate_trovate"] = associate
            
            if not associate:
                print("ℹ️  Nessuna associata >50% trovata - calcolo singolo")
                risultato_finale["metodo"] = "singolo"
                return self._calcola_solo_principale(codice_fiscale_principale, risultato_finale)
            
            print(f"✅ Trovate {len(associate)} società associate")
            for ass in associate:
                print(f"  • {ass['ragione_sociale']} - {ass['cf']} ({ass['percentuale']})")
            
            # STEP 2: Calcolo De Minimis per tutte le aziende
            print("\n" + "="*50)
            print("📍 STEP 2: Calcolo De Minimis aggregato")
            print("="*50)
            
            self._inizializza_componenti()
            
            # Lista di tutti i CF da calcolare (principale + associate)
            tutti_cf = [codice_fiscale_principale]
            tutti_cf.extend([ass["cf"] for ass in associate])
            
            risultati_aziende = []
            totale_aggregato = 0.0
            numero_aiuti_totali = 0
            
            # Calcola per ogni azienda
            for i, cf in enumerate(tutti_cf):
                print(f"\n📊 Calcolo {i+1}/{len(tutti_cf)}: {cf}")
                
                try:
                    # Trova ragione sociale
                    if cf == codice_fiscale_principale:
                        ragione_sociale = "AZIENDA PRINCIPALE"
                        percentuale = "100%"
                    else:
                        # Trova l'associata corrispondente
                        ass_trovata = next((a for a in associate if a["cf"] == cf), None)
                        if ass_trovata:
                            ragione_sociale = ass_trovata["ragione_sociale"]
                            percentuale = ass_trovata["percentuale"]
                        else:
                            ragione_sociale = f"CF {cf}"
                            percentuale = "N/A"
                    
                    # Calcola De Minimis per questa azienda
                    calcolo = self.rna_calculator.calcola_deminimis(cf)

                    # Normalizza elenco aiuti: compatibile con singolo
                    dettagli_aiuti = calcolo.get("dettagli_aiuti") or calcolo.get("aiuti_trovati") or []

                    # Struttura risultato azienda
                    risultato_azienda = {
                        "codice_fiscale": cf,
                        "ragione_sociale": ragione_sociale,
                        "percentuale_controllo": percentuale,
                        "tipo": "principale" if cf == codice_fiscale_principale else "associata",
                        "deminimis_ricevuto": calcolo.get("totale_de_minimis", 0.0),
                        "numero_aiuti": len(dettagli_aiuti),
                        "dettagli_aiuti": dettagli_aiuti,
                        "data_ricerca": calcolo.get("data_ricerca", ""),
                        "errore": calcolo.get("errore", None)
                    }
                    
                    risultati_aziende.append(risultato_azienda)
                    
                    # Aggrega i totali
                    if not calcolo.get("errore"):
                        totale_aggregato += calcolo.get("totale_de_minimis", 0.0)
                        numero_aiuti_totali += len(dettagli_aiuti)
                        print(f"  ✅ {ragione_sociale}: €{calcolo.get('totale_de_minimis', 0):,.2f}")
                    else:
                        print(f"  ❌ {ragione_sociale}: {calcolo.get('errore')}")
                        risultato_finale["warning"].append(f"Errore calcolo {cf}: {calcolo.get('errore')}")
                
                except Exception as e:
                    print(f"  ❌ Errore calcolo {cf}: {str(e)}")
                    risultato_finale["warning"].append(f"Errore calcolo {cf}: {str(e)}")
                    
                    # Aggiungi risultato con errore
                    risultato_azienda = {
                        "codice_fiscale": cf,
                        "ragione_sociale": ragione_sociale if 'ragione_sociale' in locals() else f"CF {cf}",
                        "percentuale_controllo": percentuale if 'percentuale' in locals() else "N/A",
                        "tipo": "principale" if cf == codice_fiscale_principale else "associata",
                        "deminimis_ricevuto": 0.0,
                        "numero_aiuti": 0,
                        "dettagli_aiuti": [],
                        "data_ricerca": "",
                        "errore": str(e)
                    }
                    risultati_aziende.append(risultato_azienda)
            
            # STEP 3: Aggregazione finale
            print("\n" + "="*50)
            print("📍 STEP 3: Aggregazione risultati")
            print("="*50)
            
            risultato_finale["risultati_per_azienda"] = risultati_aziende
            
            # Calcola percentuale utilizzata e margine
            numero_aziende = len(risultati_aziende)
            percentuale_utilizzata = (totale_aggregato / self.soglia_deminimis) * 100
            margine_rimanente = max(0, self.soglia_deminimis - totale_aggregato)
            
            # Determina stato (verde/giallo/rosso)
            if percentuale_utilizzata >= 90:
                stato = "rosso"
            elif percentuale_utilizzata >= 70:
                stato = "giallo"
            else:
                stato = "verde"
            
            # Popola totale gruppo
            risultato_finale["totale_gruppo"] = {
                "totale_deminimis": totale_aggregato,
                "numero_aziende": numero_aziende,
                "numero_aiuti_totali": numero_aiuti_totali,
                "percentuale_utilizzata": percentuale_utilizzata,
                "margine_rimanente": margine_rimanente,
                "stato": stato
            }
            
            print(f"✅ TOTALE GRUPPO: €{totale_aggregato:,.2f}")
            print(f"   Aziende: {numero_aziende}")
            print(f"   Aiuti totali: {numero_aiuti_totali}")
            print(f"   Utilizzato: {percentuale_utilizzata:.1f}%")
            print(f"   Margine: €{margine_rimanente:,.2f}")
            print(f"   Stato: {stato.upper()}")
            
            return risultato_finale
            
        except Exception as e:
            print(f"❌ Errore generale calcolo aggregato: {str(e)}")
            risultato_finale["errore_cribis"] = f"Errore generale: {str(e)}"
            return self._calcola_solo_principale(codice_fiscale_principale, risultato_finale)
        
        finally:
            # Cleanup non necessario con Playwright (gestito automaticamente)
            print("🔒 Cleanup completato")
    
    def _calcola_solo_principale(self, codice_fiscale, risultato_base):
        """
        Fallback: calcola solo l'azienda principale
        
        Args:
            codice_fiscale (str): CF dell'azienda principale
            risultato_base (dict): Struttura risultato da completare
            
        Returns:
            dict: Risultato per singola azienda
        """
        print(f"📍 FALLBACK: Calcolo singola azienda {codice_fiscale}")
        
        try:
            self._inizializza_componenti()
            
            # Calcola De Minimis per singola azienda
            calcolo = self.rna_calculator.calcola_deminimis(codice_fiscale)
            
            # Struttura risultato
            risultato_azienda = {
                "codice_fiscale": codice_fiscale,
                "ragione_sociale": "AZIENDA SINGOLA",
                "percentuale_controllo": "100%",
                "tipo": "principale",
                "deminimis_ricevuto": calcolo.get("totale_de_minimis", 0.0),
                "numero_aiuti": len(calcolo.get("dettagli_aiuti", [])),
                "dettagli_aiuti": calcolo.get("dettagli_aiuti", []),
                "data_ricerca": calcolo.get("data_ricerca", ""),
                "errore": calcolo.get("errore", None)
            }
            
            risultato_base["risultati_per_azienda"] = [risultato_azienda]
            risultato_base["metodo"] = "singolo"
            
            # Totali
            totale = calcolo.get("totale_de_minimis", 0.0)
            percentuale_utilizzata = (totale / self.soglia_deminimis) * 100
            margine_rimanente = max(0, self.soglia_deminimis - totale)
            
            # Stato
            if percentuale_utilizzata >= 90:
                stato = "rosso"
            elif percentuale_utilizzata >= 70:
                stato = "giallo"
            else:
                stato = "verde"
            
            risultato_base["totale_gruppo"] = {
                "totale_deminimis": totale,
                "numero_aziende": 1,
                "numero_aiuti_totali": len(calcolo.get("dettagli_aiuti", [])),
                "percentuale_utilizzata": percentuale_utilizzata,
                "margine_rimanente": margine_rimanente,
                "stato": stato
            }
            
            print(f"✅ Calcolo singolo completato: €{totale:,.2f}")
            return risultato_base
            
        except Exception as e:
            print(f"❌ Errore calcolo singolo: {str(e)}")
            
            # Risultato di errore
            risultato_base["totale_gruppo"] = {
                "totale_deminimis": 0.0,
                "numero_aziende": 0,
                "numero_aiuti_totali": 0,
                "percentuale_utilizzata": 0.0,
                "margine_rimanente": self.soglia_deminimis,
                "stato": "verde"
            }
            risultato_base["errore_cribis"] = f"Errore calcolo: {str(e)}"
            
            return risultato_base
    
    def calcola_deminimis_singolo(self, codice_fiscale):
        """
        Calcola De Minimis per singola azienda (senza ricerca associate)
        Metodo veloce per controlli rapidi
        
        Args:
            codice_fiscale (str): P.IVA o CF da analizzare
            
        Returns:
            dict: Risultato calcolo singolo
        """
        try:
            print(f"🏠 Calcolo De Minimis singolo per: {codice_fiscale}")
            # Assicura inizializzazione RNACalculator
            self._inizializza_componenti()

            # Calcola direttamente con RNA
            calcolo = self.rna_calculator.calcola_deminimis(codice_fiscale)
            
            # Formato risultato compatibile
            if calcolo.get("errore"):
                return {
                    "p_iva_principale": codice_fiscale,
                    "metodo": "singolo",
                    "errore": calcolo["errore"],
                    "totale_deminimis": 0.0,
                    "numero_aiuti_totali": 0,
                    "percentuale_utilizzata": 0.0,
                    "margine_rimanente": self.soglia_deminimis,
                    "stato": "verde",
                    "dettagli_aiuti": [],
                    "data_ricerca": calcolo.get("data_ricerca", ""),
                    "risultati_per_azienda": []
                }
            
            # Estrai dati
            totale = calcolo.get("totale_de_minimis", 0.0)
            percentuale_utilizzata = (totale / self.soglia_deminimis) * 100
            margine_rimanente = max(0, self.soglia_deminimis - totale)
            
            # Determina stato
            if percentuale_utilizzata >= 90:
                stato = "rosso"
            elif percentuale_utilizzata >= 70:
                stato = "giallo"
            else:
                stato = "verde"
            
            return {
                "p_iva_principale": codice_fiscale,
                "metodo": "singolo",
                "errore": None,
                "totale_deminimis": totale,
                "numero_aiuti_totali": len(calcolo.get("aiuti_trovati", [])),
                "percentuale_utilizzata": percentuale_utilizzata,
                "margine_rimanente": margine_rimanente,
                "stato": stato,
                "dettagli_aiuti": calcolo.get("aiuti_trovati", []),
                "data_ricerca": calcolo.get("data_ricerca", ""),
                "risultati_per_azienda": [{
                    "codice_fiscale": codice_fiscale,
                    "ragione_sociale": "AZIENDA SINGOLA",
                    "percentuale_controllo": "100%",
                    "tipo": "principale",
                    "deminimis_ricevuto": totale,
                    "numero_aiuti": len(calcolo.get("aiuti_trovati", [])),
                    "dettagli_aiuti": calcolo.get("aiuti_trovati", []),
                    "data_ricerca": calcolo.get("data_ricerca", ""),
                    "errore": None
                }]
            }
            
        except Exception as e:
            print(f"❌ Errore calcolo singolo: {str(e)}")
            return {
                "p_iva_principale": codice_fiscale,
                "metodo": "singolo",
                "errore": f"Errore calcolo: {str(e)}",
                "totale_deminimis": 0.0,
                "numero_aiuti_totali": 0,
                "percentuale_utilizzata": 0.0,
                "margine_rimanente": self.soglia_deminimis,
                "stato": "verde",
                "dettagli_aiuti": [],
                "data_ricerca": "",
                "risultati_per_azienda": []
            }


# Test della classe
if __name__ == "__main__":
    aggregato = DeMinimisAggregato()
    
    # Test con P.IVA di esempio
    test_cf = "02918700168"
    print(f"🧪 TEST CALCOLO AGGREGATO: {test_cf}")
    
    risultato = aggregato.calcola_deminimis_gruppo(test_cf)
    
    print("\n" + "="*60)
    print("📋 RISULTATO FINALE JSON:")
    print("="*60)
    print(json.dumps(risultato, indent=2, ensure_ascii=False))
