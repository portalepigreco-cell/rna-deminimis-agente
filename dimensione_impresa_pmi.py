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
        self.browser_attivo = False
        
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
            
            # Inizializza browser solo se non è già attivo (RIUTILIZZO SESSIONE)
            if not self.browser_attivo:
                print("🆕 Inizializzo browser e login (prima richiesta)")
                self.cribis = CribisNuovaRicerca(headless=self.headless)
                self.cribis.__enter__()  # Inizializza browser
                self.cribis.login()
                self.browser_attivo = True
            else:
                print("♻️  Browser già attivo, riutilizzo sessione esistente (nessun nuovo login)")
            
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
            
            # 🧪 MODALITÀ TEST: disabilitata per processare tutte le società
            import os
            TEST_MODE = False  # Disabilitata: processiamo sempre TUTTE le società
            MAX_SOCIETA_TEST = 3
            
            if TEST_MODE:
                print(f"⚠️  MODALITÀ TEST (locale): limito a {MAX_SOCIETA_TEST} società (+ principale)\n")
            else:
                print(f"🚀 MODALITÀ PRODUZIONE: processo TUTTE le società del gruppo\n")
            
            # Dati impresa principale
            dati_principale = self._scarica_dati_finanziari(
                gruppo['principale']['cf'],
                gruppo['principale']['ragione_sociale']
            )
            risultato["impresa_principale"].update(dati_principale)
            
            societa_processate = 0
            
            # Dati società collegate
            for i, soc in enumerate(risultato["societa_collegate"], 1):
                if TEST_MODE and societa_processate >= MAX_SOCIETA_TEST:
                    print(f"\n⏭️  Skip restanti collegate (modalità test)")
                    break
                
                print(f"\n📊 [{i}/{len(risultato['societa_collegate'])}] Collegata: {soc['nome']}")
                dati = self._scarica_dati_finanziari(soc['cf'], soc['nome'])
                soc.update(dati)
                societa_processate += 1
            
            # Dati società partner
            for i, soc in enumerate(risultato["societa_partner"], 1):
                if TEST_MODE and societa_processate >= MAX_SOCIETA_TEST:
                    print(f"\n⏭️  Skip restanti partner (modalità test)")
                    break
                
                print(f"\n📊 [{i}/{len(risultato['societa_partner'])}] Partner: {soc['nome']}")
                dati = self._scarica_dati_finanziari(soc['cf'], soc['nome'])
                soc.update(dati)
                societa_processate += 1
            
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
            # NON chiudere il browser (riutilizzo sessione tra richieste)
            # Il browser verrà chiuso solo chiamando esplicitamente close()
            pass
    
    def close(self):
        """
        Chiude il browser e termina la sessione.
        Da chiamare quando l'applicazione si chiude.
        """
        if self.cribis and self.browser_attivo:
            print("🔒 Chiudo browser...")
            self.cribis.__exit__(None, None, None)
            self.browser_attivo = False
            print("✅ Browser chiuso")
    
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
            
            # La chiave corretta è "associate_italiane_controllate"
            for soc in risultato_cribis.get("associate_italiane_controllate", []):
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
        
        IMPORTANTE: Se non trova il bottone "Richiedi" o non entra nella Company Card,
        solleva Exception per BLOCCARE il processo (non continuare con dati vuoti).
        
        Args:
            codice_fiscale (str): CF dell'azienda
            ragione_sociale (str): Nome azienda
            
        Returns:
            dict: Dati finanziari estratti
            
        Raises:
            Exception: Se non trova il bottone Richiedi o non entra nella Company Card
        """
        # CRITICO: Non catturare eccezioni da scarica_company_card_completa
        # Se solleva Exception (bottone non trovato, pagina errata), PROPAGA per bloccare
        
        # Usa il metodo di Cribis per aprire Company Card ed estrarre dati dalla pagina
        # Se questo fallisce (Exception), viene propagata e blocca il processo
        dati = self.cribis.scarica_company_card_completa(codice_fiscale)

        # Prova a scaricare anche il PDF dalla pagina corrente (link "Scarica")
        # Questa parte può fallire senza bloccare (il PDF è opzionale)
        try:
            pdf_res = self.cribis.scarica_pdf_company_card_corrente(codice_fiscale)
            if pdf_res.get("success"):
                dati["pdf_filename"] = pdf_res.get("filename")
            else:
                # Mantieni l'informazione del perché non disponibile
                dati["pdf_note"] = pdf_res.get("reason")
        except Exception as e:
            dati["pdf_note"] = f"Errore download PDF: {e}"
            # Non bloccare per errori PDF, è opzionale
        
        # Se c'è un errore nei dati (es. dati finanziari non trovati nella pagina),
        # restituisci comunque dati strutturati (non è critico)
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
        Classifica l'impresa secondo soglie UE (Raccomandazione 2003/361/CE).
        
        Regole UE "2 su 3":
        - Per ogni categoria, ALMENO 2 su 3 criteri devono essere rispettati
        - I 3 criteri sono: personale, fatturato, bilancio
        
        Categorie:
        - Micro: <10 dipendenti E (fatturato≤2M E bilancio≤2M)
        - Piccola: <50 dipendenti E (fatturato≤10M E bilancio≤10M)
        - Media: <250 dipendenti E (fatturato≤50M E bilancio≤43M)
        - Grande: se 2+ criteri superano le soglie della media
        
        Args:
            personale (float): ULA aggregate
            fatturato (float): Fatturato aggregato
            attivo (float): Attivo/Bilancio aggregato
            
        Returns:
            dict: Classificazione con dettagli soglie
        """
        dimensione = "Grande Impresa"
        
        # Helper: conta quanti criteri rispettano la soglia (ritorna True se almeno 2 su 3)
        def rispetta_soglia_2su3(pers_soglia, fatt_soglia, att_soglia):
            criteri_rispettati = 0
            
            if personale < pers_soglia:
                criteri_rispettati += 1
            if fatturato <= fatt_soglia:
                criteri_rispettati += 1
            if attivo <= att_soglia:
                criteri_rispettati += 1
            
            return criteri_rispettati >= 2
        
        # Check Micro (almeno 2 su 3 criteri rispettati)
        if rispetta_soglia_2su3(
            SOGLIE_UE["micro"]["personale"],
            SOGLIE_UE["micro"]["fatturato"],
            SOGLIE_UE["micro"]["attivo"]
        ):
            dimensione = SOGLIE_UE["micro"]["descrizione"]
        
        # Check Piccola
        elif rispetta_soglia_2su3(
            SOGLIE_UE["piccola"]["personale"],
            SOGLIE_UE["piccola"]["fatturato"],
            SOGLIE_UE["piccola"]["attivo"]
        ):
            dimensione = SOGLIE_UE["piccola"]["descrizione"]
        
        # Check Media
        elif rispetta_soglia_2su3(
            SOGLIE_UE["media"]["personale"],
            SOGLIE_UE["media"]["fatturato"],
            SOGLIE_UE["media"]["attivo"]
        ):
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
        """Genera nota esplicativa della classificazione con regola 2 su 3"""
        
        # Conta quanti criteri rispettano ciascuna soglia
        def conta_criteri_rispettati(categoria):
            soglia = SOGLIE_UE[categoria]
            criteri = 0
            if personale < soglia["personale"]:
                criteri += 1
            if fatturato <= soglia["fatturato"]:
                criteri += 1
            if attivo <= soglia["attivo"]:
                criteri += 1
            return criteri
        
        if "Micro" in dimensione:
            n = conta_criteri_rispettati("micro")
            return f"Microimpresa (regola 2/3): {n}/3 criteri rispettati (ULA:{personale:.1f}, Fatt:€{fatturato:,.0f}, Bil:€{attivo:,.0f})"
        elif "Piccola" in dimensione:
            n = conta_criteri_rispettati("piccola")
            return f"Piccola Impresa (regola 2/3): {n}/3 criteri rispettati (ULA:{personale:.1f}, Fatt:€{fatturato:,.0f}, Bil:€{attivo:,.0f})"
        elif "Media" in dimensione:
            n = conta_criteri_rispettati("media")
            return f"Media Impresa (regola 2/3): {n}/3 criteri rispettati (ULA:{personale:.1f}, Fatt:€{fatturato:,.0f}, Bil:€{attivo:,.0f})"
        else:
            return f"Grande Impresa: supera le soglie PMI in 2+ criteri (ULA:{personale:.1f}, Fatt:€{fatturato:,.0f}, Bil:€{attivo:,.0f})"
    
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
# FUNZIONI TEST
# ============================================================================

def test_classificazione_regola_2su3():
    """
    Test della logica di classificazione "2 su 3" con dati fittizi.
    Verifica che la regola UE sia implementata correttamente.
    """
    print("\n" + "="*70)
    print("🧪 TEST LOGICA CLASSIFICAZIONE '2 SU 3'")
    print("="*70 + "\n")
    
    calc = CalcolatoreDimensionePMI(headless=True)
    
    # Test case 1: MICROIMPRESA (tutti e 3 i criteri rispettati)
    print("Test 1: Microimpresa (3/3 criteri)")
    print("-" * 70)
    result1 = calc._classifica_impresa(
        personale=5.0,      # < 10 ✅
        fatturato=1_500_000,  # ≤ 2M ✅
        attivo=1_800_000      # ≤ 2M ✅
    )
    print(f"   Risultato: {result1['dimensione']}")
    print(f"   Nota: {result1['note']}\n")
    assert "Micro" in result1['dimensione'], "Dovrebbe essere Microimpresa!"
    
    # Test case 2: MICROIMPRESA (2/3 criteri: personale e fatturato OK, attivo NO)
    print("Test 2: Microimpresa (2/3 criteri - attivo sforato)")
    print("-" * 70)
    result2 = calc._classifica_impresa(
        personale=8.0,      # < 10 ✅
        fatturato=1_900_000,  # ≤ 2M ✅
        attivo=3_000_000      # > 2M ❌ ma OK perché 2/3
    )
    print(f"   Risultato: {result2['dimensione']}")
    print(f"   Nota: {result2['note']}\n")
    assert "Micro" in result2['dimensione'], "Dovrebbe essere ancora Microimpresa (2/3)!"
    
    # Test case 3: PICCOLA IMPRESA (solo 1 criterio micro rispettato, ma 2/3 piccola)
    print("Test 3: Piccola Impresa (esce da Micro, entra in Piccola)")
    print("-" * 70)
    result3 = calc._classifica_impresa(
        personale=25.0,     # > 10 ❌ micro, < 50 ✅ piccola
        fatturato=8_000_000,  # > 2M ❌ micro, ≤ 10M ✅ piccola
        attivo=9_500_000      # > 2M ❌ micro, ≤ 10M ✅ piccola
    )
    print(f"   Risultato: {result3['dimensione']}")
    print(f"   Nota: {result3['note']}\n")
    assert "Piccola" in result3['dimensione'], "Dovrebbe essere Piccola Impresa!"
    
    # Test case 4: MEDIA IMPRESA
    print("Test 4: Media Impresa")
    print("-" * 70)
    result4 = calc._classifica_impresa(
        personale=180.0,      # < 250 ✅
        fatturato=45_000_000,   # ≤ 50M ✅
        attivo=40_000_000       # ≤ 43M ✅
    )
    print(f"   Risultato: {result4['dimensione']}")
    print(f"   Nota: {result4['note']}\n")
    assert "Media" in result4['dimensione'], "Dovrebbe essere Media Impresa!"
    
    # Test case 5: GRANDE IMPRESA (supera 2/3 criteri media)
    print("Test 5: Grande Impresa (supera soglie PMI)")
    print("-" * 70)
    result5 = calc._classifica_impresa(
        personale=300.0,        # > 250 ❌
        fatturato=60_000_000,     # > 50M ❌
        attivo=40_000_000         # ≤ 43M ✅ (ma non basta)
    )
    print(f"   Risultato: {result5['dimensione']}")
    print(f"   Nota: {result5['note']}\n")
    assert "Grande" in result5['dimensione'], "Dovrebbe essere Grande Impresa!"
    
    # Test case 6: EDGE CASE - Esattamente 2/3 criteri al limite
    print("Test 6: Edge case - Piccola con 2 valori esatti al limite")
    print("-" * 70)
    result6 = calc._classifica_impresa(
        personale=49.9,         # < 50 ✅
        fatturato=10_000_000,     # = 10M ✅ (≤)
        attivo=15_000_000         # > 10M ❌
    )
    print(f"   Risultato: {result6['dimensione']}")
    print(f"   Nota: {result6['note']}\n")
    assert "Piccola" in result6['dimensione'], "Dovrebbe essere Piccola (2/3 al limite)!"
    
    print("="*70)
    print("✅ TUTTI I TEST SUPERATI! Logica '2 su 3' implementata correttamente.")
    print("="*70 + "\n")


def test_aggregazione_con_dati_fittizi():
    """
    Test completo con dati fittizi di un gruppo societario.
    """
    print("\n" + "="*70)
    print("🧪 TEST AGGREGAZIONE GRUPPO SOCIETARIO (DATI FITTIZI)")
    print("="*70 + "\n")
    
    calc = CalcolatoreDimensionePMI(headless=True)
    
    # Impresa principale
    principale = {
        "personale": 15,
        "fatturato": 3_000_000,
        "attivo": 2_500_000
    }
    
    # Società collegate (>50%, contano al 100%)
    collegate = [
        {
            "nome": "COLLEGATA 1 SRL",
            "cf": "12345678901",
            "personale": 8,
            "fatturato": 1_500_000,
            "attivo": 1_200_000,
            "percentuale": 100.0
        },
        {
            "nome": "COLLEGATA 2 SRL",
            "cf": "23456789012",
            "personale": 12,
            "fatturato": 2_000_000,
            "attivo": 1_800_000,
            "percentuale": 75.0  # Anche se 75%, conta come 100%
        }
    ]
    
    # Società partner (25-50%, contano pro-quota)
    partner = [
        {
            "nome": "PARTNER 1 SPA",
            "cf": "34567890123",
            "personale": 20,
            "fatturato": 4_000_000,
            "attivo": 3_500_000,
            "percentuale": 30.0  # Conta al 30%
        }
    ]
    
    print("📊 DATI INPUT:")
    print(f"   Principale: {principale['personale']} ULA, €{principale['fatturato']:,}, €{principale['attivo']:,}")
    print(f"   Collegate ({len(collegate)}): totali da aggregare al 100%")
    for c in collegate:
        print(f"      • {c['nome']}: {c['personale']} ULA, €{c['fatturato']:,}")
    print(f"   Partner ({len(partner)}): totali da aggregare pro-quota")
    for p in partner:
        print(f"      • {p['nome']} ({p['percentuale']}%): {p['personale']} ULA, €{p['fatturato']:,}")
    
    # Calcola aggregati
    print("\n📊 CALCOLO AGGREGATI:")
    aggregati = calc._calcola_aggregati_ue(principale, collegate, partner)
    
    print("\n📊 RISULTATO AGGREGAZIONE:")
    print(f"   Personale totale: {aggregati['personale_totale']} ULA")
    print(f"   Fatturato totale: €{aggregati['fatturato_totale']:,.2f}")
    print(f"   Attivo totale: €{aggregati['attivo_totale']:,.2f}")
    
    # Classifica
    print("\n🏆 CLASSIFICAZIONE:")
    classificazione = calc._classifica_impresa(
        aggregati['personale_totale'],
        aggregati['fatturato_totale'],
        aggregati['attivo_totale']
    )
    print(f"   {classificazione['dimensione']}")
    print(f"   {classificazione['note']}")
    
    # Verifica manuale
    print("\n✅ VERIFICA MANUALE:")
    pers_atteso = 15 + 8 + 12 + (20 * 0.30)  # 15 + 8 + 12 + 6 = 41
    fatt_atteso = 3_000_000 + 1_500_000 + 2_000_000 + (4_000_000 * 0.30)  # 7.7M
    print(f"   Personale atteso: {pers_atteso} → Calcolato: {aggregati['personale_totale']}")
    print(f"   Fatturato atteso: €{fatt_atteso:,.0f} → Calcolato: €{aggregati['fatturato_totale']:,.2f}")
    
    assert aggregati['personale_totale'] == pers_atteso, "Personale aggregato errato!"
    assert abs(aggregati['fatturato_totale'] - fatt_atteso) < 1, "Fatturato aggregato errato!"
    
    print("\n" + "="*70)
    print("✅ TEST AGGREGAZIONE SUPERATO!")
    print("="*70 + "\n")


def test_dimensione_pmi_live():
    """Test standalone con P.IVA reale (richiede Cribis)"""
    piva_test = "04143180984"  # Pozzi Milano SPA
    
    print("\n" + "="*70)
    print("🧪 TEST LIVE CON P.IVA REALE")
    print(f"P.IVA: {piva_test}")
    print("⚠️  Richiede login Cribis e download Company Card")
    print("="*70 + "\n")
    
    calc = CalcolatoreDimensionePMI(headless=False)
    risultato = calc.calcola_dimensione(piva_test)
    
    if risultato["risultato"] == "success":
        print("\n✅ TEST COMPLETATO CON SUCCESSO!")
    else:
        print(f"\n❌ TEST FALLITO: {risultato.get('errore', 'Errore sconosciuto')}")
    
    return risultato


if __name__ == "__main__":
    # Menu test
    print("\n🧪 SUITE TEST DIMENSIONE PMI")
    print("="*70)
    print("1. Test logica classificazione '2 su 3' (veloce, senza Cribis)")
    print("2. Test aggregazione gruppo societario (veloce, senza Cribis)")
    print("3. Test LIVE con P.IVA reale (lento, richiede Cribis)")
    print("="*70)
    
    scelta = input("\nScegli test (1/2/3 o 'all'): ").strip()
    
    if scelta == "1" or scelta == "all":
        test_classificazione_regola_2su3()
    
    if scelta == "2" or scelta == "all":
        test_aggregazione_con_dati_fittizi()
    
    if scelta == "3" or scelta == "all":
        test_dimensione_pmi_live()
    
    if scelta not in ["1", "2", "3", "all"]:
        print("❌ Scelta non valida. Eseguo test veloce (opzione 1)...")
        test_classificazione_regola_2su3()

