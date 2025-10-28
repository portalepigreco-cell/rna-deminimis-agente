#!/usr/bin/env python3
"""
📊 Calcolatore Dimensione d'Impresa PMI
==========================================

Calcola la dimensione d'impresa (Micro/Piccola/Media/Grande) secondo la 
Raccomandazione UE 2003/361/CE a partire da una P.IVA, aggregando dati di 
imprese collegate (>50%) e partner (25-50%).

Autore: Sistema RNA De Minimis
Data: 28 Ottobre 2025
"""

from datetime import datetime
import re
import time
from typing import Dict, List, Optional
from cribis_nuova_ricerca import CribisNuovaRicerca


# ============================================================================
# SOGLIE UE PER CLASSIFICAZIONE PMI (Raccomandazione 2003/361/CE)
# ============================================================================

SOGLIE_UE = {
    "micro": {
        "personale": 10,
        "fatturato": 2_000_000,
        "attivo": 2_000_000,
        "descrizione": "Microimpresa"
    },
    "piccola": {
        "personale": 50,
        "fatturato": 10_000_000,
        "attivo": 10_000_000,
        "descrizione": "Piccola Impresa"
    },
    "media": {
        "personale": 250,
        "fatturato": 50_000_000,
        "attivo": 43_000_000,
        "descrizione": "Media Impresa"
    }
}


class CalcolatoreDimensionePMI:
    """
    Calcolatore automatico della dimensione d'impresa secondo normativa UE.
    
    Processo:
    1. Estrae gruppo societario (collegate >50% e partner 25-50%)
    2. Scarica Company Card Completa per ogni società
    3. Estrae dati finanziari (ULA, Fatturato, Attivo)
    4. Calcola aggregati secondo formula UE
    5. Classifica l'impresa
    """
    
    def __init__(self, headless: bool = True):
        """
        Inizializza il calcolatore.
        
        Args:
            headless (bool): Se True, browser in background
        """
        self.headless = headless
        self.cribis = None
        
    def calcola_dimensione(self, partita_iva: str) -> Dict:
        """
        Calcola la dimensione d'impresa per una P.IVA.
        
        Args:
            partita_iva (str): Partita IVA dell'impresa principale
            
        Returns:
            dict: Risultato completo con classificazione e dettagli
        """
        risultato = {
            "risultato": "in_corso",
            "partita_iva_richiesta": partita_iva,
            "data_calcolo": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "errore": None,
            "tempo_inizio": time.time()
        }
        
        try:
            print(f"\n{'='*70}")
            print(f"📊 CALCOLO DIMENSIONE PMI - P.IVA: {partita_iva}")
            print(f"{'='*70}\n")
            
            # Inizializza connessione Cribis
            self.cribis = CribisNuovaRicerca(headless=self.headless)
            self.cribis._inizializza_browser()
            self.cribis.login()
            
            # STEP 1: Estrai gruppo societario completo (collegate + partner)
            print("\n1️⃣ ESTRAZIONE GRUPPO SOCIETARIO")
            print("-" * 70)
            gruppo = self._estrai_gruppo_completo(partita_iva)
            
            if gruppo["errore"]:
                risultato["errore"] = gruppo["errore"]
                risultato["risultato"] = "errore"
                return risultato
            
            risultato["impresa_principale"] = gruppo["principale"]
            risultato["societa_collegate"] = gruppo["collegate"]
            risultato["societa_partner"] = gruppo["partner"]
            
            print(f"\n✅ Gruppo estratto:")
            print(f"   • Impresa principale: {gruppo['principale']['ragione_sociale']}")
            print(f"   • Società collegate (>50%): {len(gruppo['collegate'])}")
            print(f"   • Società partner (25-50%): {len(gruppo['partner'])}")
            
            # STEP 2: Scarica dati finanziari per tutte le società
            print(f"\n2️⃣ DOWNLOAD DATI FINANZIARI")
            print("-" * 70)
            
            # Dati impresa principale
            dati_principale = self._scarica_dati_finanziari(
                gruppo['principale']['cf'],
                gruppo['principale']['ragione_sociale']
            )
            risultato["impresa_principale"].update(dati_principale)
            
            # Dati società collegate
            for i, soc in enumerate(risultato["societa_collegate"], 1):
                print(f"\n📊 [{i}/{len(risultato['societa_collegate'])}] Collegata: {soc['nome']}")
                dati = self._scarica_dati_finanziari(soc['cf'], soc['nome'])
                soc.update(dati)
            
            # Dati società partner
            for i, soc in enumerate(risultato["societa_partner"], 1):
                print(f"\n📊 [{i}/{len(risultato['societa_partner'])}] Partner: {soc['nome']}")
                dati = self._scarica_dati_finanziari(soc['cf'], soc['nome'])
                soc.update(dati)
            
            # STEP 3: Calcola aggregati UE
            print(f"\n3️⃣ CALCOLO AGGREGATI UE")
            print("-" * 70)
            aggregati = self._calcola_aggregati_ue(
                risultato["impresa_principale"],
                risultato["societa_collegate"],
                risultato["societa_partner"]
            )
            risultato["aggregati_ue"] = aggregati
            
            # STEP 4: Classifica impresa
            print(f"\n4️⃣ CLASSIFICAZIONE IMPRESA")
            print("-" * 70)
            classificazione = self._classifica_impresa(
                aggregati["personale_totale"],
                aggregati["fatturato_totale"],
                aggregati["attivo_totale"]
            )
            risultato["classificazione"] = classificazione
            
            # Raccogli società senza dati
            risultato["societa_senza_dati"] = []
            for soc in (risultato["societa_collegate"] + risultato["societa_partner"]):
                if soc.get("stato_dati") == "assenti":
                    risultato["societa_senza_dati"].append({
                        "cf": soc["cf"],
                        "nome": soc["nome"]
                    })
            
            risultato["risultato"] = "success"
            risultato["tempo_elaborazione_secondi"] = int(time.time() - risultato["tempo_inizio"])
            
            # Stampa riepilogo finale
            self._stampa_riepilogo(risultato)
            
            return risultato
            
        except Exception as e:
            print(f"\n❌ ERRORE FATALE: {str(e)}")
            import traceback
            traceback.print_exc()
            
            risultato["errore"] = str(e)
            risultato["risultato"] = "errore"
            risultato["tempo_elaborazione_secondi"] = int(time.time() - risultato.get("tempo_inizio", time.time()))
            
            return risultato
            
        finally:
            if self.cribis:
                self.cribis.close()
    
    def _estrai_gruppo_completo(self, partita_iva: str) -> Dict:
        """
        Estrae gruppo societario completo con collegate (>50%) e partner (25-50%).
        
        Args:
            partita_iva (str): P.IVA impresa principale
            
        Returns:
            dict: {
                "principale": {...},
                "collegate": [...],
                "partner": [...],
                "errore": str | None
            }
        """
        try:
            risultato_cribis = self.cribis.cerca_associate(partita_iva)
            
            if risultato_cribis.get("errore"):
                return {
                    "principale": None,
                    "collegate": [],
                    "partner": [],
                    "errore": risultato_cribis["errore"]
                }
            
            # Impresa principale
            principale = {
                "cf": partita_iva,
                "ragione_sociale": "Impresa Principale",  # Verrà aggiornato da Company Card
                "tipo_relazione": "core",
                "percentuale": 100.0
            }
            
            # Separa collegate (>50%) e partner (25-50%)
            collegate = []
            partner = []
            
            for soc in risultato_cribis.get("associate", []):
                # Usa la nuova categorizzazione da cribis_nuova_ricerca
                categoria = soc.get("categoria", "collegata")
                percentuale_num = soc.get("percentuale_numerica", 100.0)
                
                dati_societa = {
                    "cf": soc["cf"],
                    "nome": soc["ragione_sociale"],
                    "percentuale": percentuale_num,
                    "tipo_relazione": categoria
                }
                
                if categoria == "collegata":
                    collegate.append(dati_societa)
                else:  # partner
                    partner.append(dati_societa)
            
            return {
                "principale": principale,
                "collegate": collegate,
                "partner": partner,
                "errore": None
            }
            
        except Exception as e:
            return {
                "principale": None,
                "collegate": [],
                "partner": [],
                "errore": f"Errore estrazione gruppo: {str(e)}"
            }
    
    def _scarica_dati_finanziari(self, codice_fiscale: str, ragione_sociale: str) -> Dict:
        """
        Scarica Company Card Completa ed estrae dati finanziari.
        
        Args:
            codice_fiscale (str): CF dell'azienda
            ragione_sociale (str): Nome azienda
            
        Returns:
            dict: Dati finanziari estratti
        """
        try:
            # Usa il metodo di Cribis per scaricare Company Card
            dati = self.cribis.scarica_company_card_completa(codice_fiscale)
            
            # Se c'è un errore, restituisci comunque dati strutturati
            if "errore" in dati:
                print(f"   ⚠️  Errore: {dati['errore']}")
                return {
                    "personale": None,
                    "fatturato": None,
                    "attivo": None,
                    "anno_riferimento": "N/D",
                    "stato_dati": "errore",
                    "note": f"Errore: {dati['errore']}"
                }
            
            # Restituisci dati estratti
            return dati
            
        except Exception as e:
            print(f"   ❌ Errore download: {str(e)}")
            return {
                "personale": None,
                "fatturato": None,
                "attivo": None,
                "anno_riferimento": "N/D",
                "stato_dati": "errore",
                "note": f"Errore: {str(e)}"
            }
    
    def _calcola_aggregati_ue(self, principale: Dict, collegate: List[Dict], 
                              partner: List[Dict]) -> Dict:
        """
        Calcola aggregati secondo Raccomandazione UE 2003/361/CE.
        
        Formula:
        - personale_totale = core + SUM(collegata × 100%) + SUM(partner × quota%)
        - fatturato_totale = [stessa formula]
        - attivo_totale = [stessa formula]
        
        Returns:
            dict: Aggregati calcolati
        """
        print("   📊 Calcolo aggregati con formula UE...")
        
        # Valori core
        pers_core = principale.get("personale") or 0
        fatt_core = principale.get("fatturato") or 0
        att_core = principale.get("attivo") or 0
        
        # Contributo collegate (100%)
        pers_collegate = sum(s.get("personale", 0) or 0 for s in collegate)
        fatt_collegate = sum(s.get("fatturato", 0) or 0 for s in collegate)
        att_collegate = sum(s.get("attivo", 0) or 0 for s in collegate)
        
        # Contributo partner (pro-quota)
        pers_partner = sum(
            (s.get("personale", 0) or 0) * (s.get("percentuale", 0) / 100.0)
            for s in partner
        )
        fatt_partner = sum(
            (s.get("fatturato", 0) or 0) * (s.get("percentuale", 0) / 100.0)
            for s in partner
        )
        att_partner = sum(
            (s.get("attivo", 0) or 0) * (s.get("percentuale", 0) / 100.0)
            for s in partner
        )
        
        # Totali
        personale_totale = pers_core + pers_collegate + pers_partner
        fatturato_totale = fatt_core + fatt_collegate + fatt_partner
        attivo_totale = att_core + att_collegate + att_partner
        
        print(f"   ✅ Personale aggregato: {personale_totale:.1f} ULA")
        print(f"   ✅ Fatturato aggregato: €{fatturato_totale:,.2f}")
        print(f"   ✅ Attivo aggregato: €{attivo_totale:,.2f}")
        
        return {
            "personale_totale": round(personale_totale, 1),
            "fatturato_totale": round(fatturato_totale, 2),
            "attivo_totale": round(attivo_totale, 2),
            "dettaglio_calcolo": {
                "core": {
                    "personale": pers_core,
                    "fatturato": fatt_core,
                    "attivo": att_core
                },
                "collegate_contributo": {
                    "personale": round(pers_collegate, 1),
                    "fatturato": round(fatt_collegate, 2),
                    "attivo": round(att_collegate, 2)
                },
                "partner_contributo": {
                    "personale": round(pers_partner, 1),
                    "fatturato": round(fatt_partner, 2),
                    "attivo": round(att_partner, 2)
                }
            }
        }
    
    def _classifica_impresa(self, personale: float, fatturato: float, 
                           attivo: float) -> Dict:
        """
        Classifica l'impresa secondo soglie UE.
        
        Regole:
        - Micro: personale<10 AND (fatturato≤2M OR attivo≤2M)
        - Piccola: personale<50 AND (fatturato≤10M OR attivo≤10M)
        - Media: personale<250 AND (fatturato≤50M OR attivo≤43M)
        - Grande: altrimenti
        
        Args:
            personale (float): ULA aggregate
            fatturato (float): Fatturato aggregato
            attivo (float): Attivo aggregato
            
        Returns:
            dict: Classificazione con dettagli soglie
        """
        dimensione = "Grande Impresa"
        
        # Check Micro
        if personale < SOGLIE_UE["micro"]["personale"]:
            if (fatturato <= SOGLIE_UE["micro"]["fatturato"] or 
                attivo <= SOGLIE_UE["micro"]["attivo"]):
                dimensione = SOGLIE_UE["micro"]["descrizione"]
        
        # Check Piccola
        elif personale < SOGLIE_UE["piccola"]["personale"]:
            if (fatturato <= SOGLIE_UE["piccola"]["fatturato"] or 
                attivo <= SOGLIE_UE["piccola"]["attivo"]):
                dimensione = SOGLIE_UE["piccola"]["descrizione"]
        
        # Check Media
        elif personale < SOGLIE_UE["media"]["personale"]:
            if (fatturato <= SOGLIE_UE["media"]["fatturato"] or 
                attivo <= SOGLIE_UE["media"]["attivo"]):
                dimensione = SOGLIE_UE["media"]["descrizione"]
        
        # Dettaglio soglie rispettate
        soglie_rispettate = {
            "personale": {
                "valore": personale,
                "soglia_micro": SOGLIE_UE["micro"]["personale"],
                "soglia_piccola": SOGLIE_UE["piccola"]["personale"],
                "soglia_media": SOGLIE_UE["media"]["personale"]
            },
            "fatturato": {
                "valore": fatturato,
                "soglia_micro": SOGLIE_UE["micro"]["fatturato"],
                "soglia_piccola": SOGLIE_UE["piccola"]["fatturato"],
                "soglia_media": SOGLIE_UE["media"]["fatturato"]
            },
            "attivo": {
                "valore": attivo,
                "soglia_micro": SOGLIE_UE["micro"]["attivo"],
                "soglia_piccola": SOGLIE_UE["piccola"]["attivo"],
                "soglia_media": SOGLIE_UE["media"]["attivo"]
            }
        }
        
        print(f"   🏆 Classificazione: {dimensione}")
        
        return {
            "dimensione": dimensione,
            "soglie_rispettate": soglie_rispettate,
            "note": self._genera_nota_classificazione(dimensione, personale, fatturato, attivo)
        }
    
    def _genera_nota_classificazione(self, dimensione: str, personale: float,
                                     fatturato: float, attivo: float) -> str:
        """Genera nota esplicativa della classificazione"""
        if "Micro" in dimensione:
            return f"Classificata come Microimpresa: personale<10 ({personale:.1f}) e valori finanziari ridotti"
        elif "Piccola" in dimensione:
            return f"Classificata come Piccola Impresa: personale<50 ({personale:.1f})"
        elif "Media" in dimensione:
            return f"Classificata come Media Impresa: personale<250 ({personale:.1f})"
        else:
            return f"Classificata come Grande Impresa: supera le soglie PMI"
    
    def _stampa_riepilogo(self, risultato: Dict):
        """Stampa riepilogo finale"""
        print(f"\n{'='*70}")
        print(f"📊 RIEPILOGO DIMENSIONE PMI")
        print(f"{'='*70}")
        
        if risultato.get("classificazione"):
            cls = risultato["classificazione"]
            print(f"\n🏆 CLASSIFICAZIONE: {cls['dimensione']}")
            print(f"   {cls['note']}")
            
        if risultato.get("aggregati_ue"):
            agg = risultato["aggregati_ue"]
            print(f"\n📊 AGGREGATI UE:")
            print(f"   • Personale: {agg['personale_totale']:.1f} ULA")
            print(f"   • Fatturato: €{agg['fatturato_totale']:,.2f}")
            print(f"   • Attivo: €{agg['attivo_totale']:,.2f}")
        
        if risultato.get("societa_senza_dati"):
            print(f"\n⚠️  Società senza dati finanziari: {len(risultato['societa_senza_dati'])}")
        
        print(f"\n⏱️  Tempo elaborazione: {risultato['tempo_elaborazione_secondi']}s")
        print(f"{'='*70}\n")


# ============================================================================
# FUNZIONE TEST STANDALONE
# ============================================================================

def test_dimensione_pmi():
    """Test standalone del calcolatore"""
    piva_test = "04143180984"  # Pozzi Milano SPA
    
    print("🧪 TEST CALCOLATORE DIMENSIONE PMI")
    print(f"P.IVA test: {piva_test}\n")
    
    calc = CalcolatoreDimensionePMI(headless=False)
    risultato = calc.calcola_dimensione(piva_test)
    
    if risultato["risultato"] == "success":
        print("\n✅ TEST COMPLETATO CON SUCCESSO!")
    else:
        print(f"\n❌ TEST FALLITO: {risultato.get('errore', 'Errore sconosciuto')}")
    
    return risultato


if __name__ == "__main__":
    # Esegui test se lanciato direttamente
    risultato = test_dimensione_pmi()

