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
import os
import csv
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
                print("♻️  Browser già attivo, verifico sessione...")
                # Verifica che la sessione sia ancora valida
                if not self.cribis._check_and_handle_session_expired():
                    print("⚠️  Sessione scaduta durante riutilizzo, errore ripristino")
                    # Se fallisce, prova a rifare login completo
                    try:
                        print("🔄 Tento re-login completo...")
                        if not self.cribis.login():
                            raise Exception("Re-login fallito durante riutilizzo sessione")
                        print("✅ Re-login completato")
                    except Exception as e:
                        raise Exception(f"Impossibile ripristinare sessione: {e}")
                else:
                    print("✅ Sessione valida, procedo")
            
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
                gruppo['principale']['ragione_sociale'],
                gruppo['principale'].get('piva')  # P.IVA se disponibile
            )
            risultato["impresa_principale"].update(dati_principale)
            
            societa_processate = 0
            
            # Dati società collegate
            for i, soc in enumerate(risultato["societa_collegate"], 1):
                if TEST_MODE and societa_processate >= MAX_SOCIETA_TEST:
                    print(f"\n⏭️  Skip restanti collegate (modalità test)")
                    break
                
                print(f"\n📊 [{i}/{len(risultato['societa_collegate'])}] Collegata: {soc['nome']}")
                # Passa P.IVA se disponibile (migliora ricerca su Cribis)
                dati = self._scarica_dati_finanziari(soc['cf'], soc['nome'], soc.get('piva'))
                soc.update(dati)
                societa_processate += 1
            
            # Dati società partner
            for i, soc in enumerate(risultato["societa_partner"], 1):
                if TEST_MODE and societa_processate >= MAX_SOCIETA_TEST:
                    print(f"\n⏭️  Skip restanti partner (modalità test)")
                    break
                
                print(f"\n📊 [{i}/{len(risultato['societa_partner'])}] Partner: {soc['nome']}")
                # Passa P.IVA se disponibile (migliora ricerca su Cribis)
                dati = self._scarica_dati_finanziari(soc['cf'], soc['nome'], soc.get('piva'))
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
            
            # Costruisci ed esporta tabella grp (per Excel)
            grp_rows = self._costruisci_tabella_grp(
                risultato["impresa_principale"],
                risultato["societa_collegate"],
                risultato["societa_partner"]
            )
            risultato["grp_rows"] = grp_rows
            risultato["grp_markdown"] = self._grp_to_markdown(grp_rows)
            
            # STEP 4: Classifica impresa
            print(f"\n4️⃣ CLASSIFICAZIONE IMPRESA")
            print("-" * 70)
            classificazione = self._classifica_impresa(
                aggregati["personale_totale"],
                aggregati["fatturato_totale"],
                aggregati["attivo_totale"]
            )
            risultato["classificazione"] = classificazione
            
            # Raccogli società senza dati (SOLO tra le collegate >50%)
            # Le società partner (≤50%) non vengono incluse perché sono escluse per normativa, non per mancanza dati
            risultato["societa_senza_dati"] = []
            for soc in risultato["societa_collegate"]:  # Solo collegate, non partner
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

    def _costruisci_tabella_grp(self, principale: Dict, collegate: List[Dict], partner: List[Dict]) -> List[Dict]:
        """Crea la tabella grp: tipo, quota (decimale), ULA, fatturato, attivo.
        - Principale e Collegate: quota=1.0
        - Partner: quota = percentuale/100
        - N/D convertiti a 0 (modalità Excel)
        """
        # Modalità Excel: N/D=0
        excel_mode = os.environ.get("PMI_EXCEL_MODE_ND_ZERO", "1").lower() in {"1", "true", "yes", "on"}
        def val(v):
            return 0 if (excel_mode and v is None) else (v or 0 if excel_mode else v)

        rows: List[Dict] = []
        # Principale
        rows.append({
            "tipo": "Principale",
            "quota": 1.0,
            "ULA": val(principale.get("personale")),
            "fatturato": val(principale.get("fatturato")),
            "attivo": val(principale.get("attivo"))
        })
        # Collegate (100%)
        for s in collegate:
            rows.append({
                "tipo": "Collegata",
                "quota": 1.0,
                "ULA": val(s.get("personale")),
                "fatturato": val(s.get("fatturato")),
                "attivo": val(s.get("attivo"))
            })
        # Partner (pro-quota)
        for s in partner:
            quota = (s.get("percentuale", 0) or 0) / 100.0
            rows.append({
                "tipo": "Partner",
                "quota": quota,
                "ULA": val(s.get("personale")),
                "fatturato": val(s.get("fatturato")),
                "attivo": val(s.get("attivo"))
            })
        return rows

    def _salva_grp_csv(self, rows: List[Dict], partita_iva: str) -> str:
        """Salva la tabella grp in CSV e restituisce il path."""
        downloads_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"grp_{partita_iva}_{ts}.csv"
        filepath = os.path.join(downloads_dir, filename)
        fieldnames = ["tipo", "quota", "ULA", "fatturato", "attivo"]
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        print(f"   💾 Tabella grp esportata: {filepath}")
        return filepath

    def _grp_to_markdown(self, rows: List[Dict]) -> str:
        """Rende la tabella grp in formato Markdown (allineata per Excel/Docs)."""
        headers = ["tipo", "quota", "ULA", "fatturato", "attivo"]
        md_lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        def fmt_number(v):
            if v is None:
                return "0"
            try:
                # Evita notazione scientifica e usa punto come decimale (compatibile copia/incolla)
                if isinstance(v, float) and v.is_integer():
                    return str(int(v))
                return ("%g" % v)
            except Exception:
                return str(v)
        for r in rows:
            md_lines.append(
                "| "
                + " | ".join([
                    str(r.get("tipo", "")),
                    fmt_number(r.get("quota")),
                    fmt_number(r.get("ULA")),
                    fmt_number(r.get("fatturato")),
                    fmt_number(r.get("attivo")),
                ])
                + " |"
            )
        return "\n".join(md_lines)
    
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
            # IMPORTANTE: Rimuovi duplicati (l'azienda principale può apparire nelle associate)
            collegate = []
            partner = []
            cf_principale = principale["cf"]
            cf_gia_visti = {cf_principale}  # Evita duplicati dell'azienda principale
            
            # La chiave corretta è "associate_italiane_controllate"
            for soc in risultato_cribis.get("associate_italiane_controllate", []):
                cf_soc = soc.get("cf")
                
                # SKIP se è l'azienda principale (duplicato)
                if cf_soc == cf_principale:
                    print(f"   ⚠️  Skip duplicato: {soc.get('ragione_sociale', 'N/A')} (CF {cf_soc} - già presente come principale)")
                    continue
                
                # SKIP se già presente (evita duplicati multipli)
                if cf_soc in cf_gia_visti:
                    print(f"   ⚠️  Skip duplicato: {soc.get('ragione_sociale', 'N/A')} (CF {cf_soc} - già presente)")
                    continue
                
                cf_gia_visti.add(cf_soc)
                
                # Usa la nuova categorizzazione da cribis_nuova_ricerca
                categoria = soc.get("categoria", "collegata")
                percentuale_num = soc.get("percentuale_numerica", 100.0)
                
                dati_societa = {
                    "cf": cf_soc,
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
    
    def _scarica_dati_finanziari(self, codice_fiscale: str, ragione_sociale: str, partita_iva: str = None) -> Dict:
        """
        Scarica Company Card Completa ed estrae dati finanziari.
        
        IMPORTANTE: Se non trova il bottone "Richiedi" o non entra nella Company Card,
        solleva Exception per BLOCCARE il processo (non continuare con dati vuoti).
        
        Args:
            codice_fiscale (str): CF dell'azienda
            ragione_sociale (str): Nome azienda
            partita_iva (str, optional): P.IVA dell'azienda (preferita per ricerca Cribis)
            
        Returns:
            dict: Dati finanziari estratti
            
        Raises:
            Exception: Se non trova il bottone Richiedi o non entra nella Company Card
        """
        # CRITICO: Non catturare eccezioni da scarica_company_card_completa
        # Se solleva Exception (bottone non trovato, pagina errata), PROPAGA per bloccare
        
        # Usa il metodo di Cribis per aprire Company Card ed estrarre dati dalla pagina
        # Passa P.IVA se disponibile per migliorare la ricerca (Cribis preferisce P.IVA)
        # Se questo fallisce (Exception), viene propagata e blocca il processo
        dati = self.cribis.scarica_company_card_completa(codice_fiscale, partita_iva)

        # PDF: disattivato di default per non bloccare il flusso "Dimensione".
        # Abilitabile impostando CRIBIS_PDF_AUTO=1 (o true) nell'ambiente.
        import os
        auto_pdf = os.environ.get("CRIBIS_PDF_AUTO", "0").lower() in {"1", "true", "yes", "on"}
        if auto_pdf:
            try:
                pdf_res = self.cribis.scarica_pdf_company_card_corrente(codice_fiscale)
                if pdf_res.get("success"):
                    dati["pdf_filename"] = pdf_res.get("filename")
                else:
                    dati["pdf_note"] = pdf_res.get("reason")
            except Exception as e:
                dati["pdf_note"] = f"Errore download PDF: {e}"
        else:
            dati["pdf_note"] = "pdf_auto_disabilitato"
        
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
        # Modalità Excel-like: N/D trattato come 0 (abilitata di default)
        import os
        excel_mode = os.environ.get("PMI_EXCEL_MODE_ND_ZERO", "1").lower() in {"1", "true", "yes", "on"}
        
        # Valori core (manteniamo None se non disponibile, non convertiamo a 0)
        pers_core = principale.get("personale")
        fatt_core = principale.get("fatturato")
        att_core = principale.get("attivo")
        
        # Contributo collegate (100%)
        # Sommiamo solo valori non-None, altrimenti None
        pers_collegate_values = [s.get("personale") for s in collegate if s.get("personale") is not None]
        pers_collegate = sum(pers_collegate_values) if pers_collegate_values else None
        
        fatt_collegate_values = [s.get("fatturato") for s in collegate if s.get("fatturato") is not None]
        fatt_collegate = sum(fatt_collegate_values) if fatt_collegate_values else None
        
        att_collegate_values = [s.get("attivo") for s in collegate if s.get("attivo") is not None]
        att_collegate = sum(att_collegate_values) if att_collegate_values else None
        
        # Contributo partner (pro-quota)
        pers_partner_values = [
            s.get("personale") * (s.get("percentuale", 0) / 100.0)
            for s in partner
            if s.get("personale") is not None
        ]
        pers_partner = sum(pers_partner_values) if pers_partner_values else None
        
        fatt_partner_values = [
            s.get("fatturato") * (s.get("percentuale", 0) / 100.0)
            for s in partner
            if s.get("fatturato") is not None
        ]
        fatt_partner = sum(fatt_partner_values) if fatt_partner_values else None
        
        att_partner_values = [
            s.get("attivo") * (s.get("percentuale", 0) / 100.0)
            for s in partner
            if s.get("attivo") is not None
        ]
        att_partner = sum(att_partner_values) if att_partner_values else None
        
        # Totali
        if excel_mode:
            # Stile Excel: N/D=0 sempre. Il risultato è sempre un numero (0 se tutto N/D)
            personale_totale = (pers_core or 0) + (pers_collegate or 0) + (pers_partner or 0)
            fatturato_totale = (fatt_core or 0) + (fatt_collegate or 0) + (fatt_partner or 0)
            attivo_totale = (att_core or 0) + (att_collegate or 0) + (att_partner or 0)
        else:
            # Stile "dati conservativi": se tutti i componenti sono None, totale None
            personale_totale = None
            if pers_core is not None or pers_collegate is not None or pers_partner is not None:
                personale_totale = (pers_core or 0) + (pers_collegate or 0) + (pers_partner or 0)
            
            fatturato_totale = None
            if fatt_core is not None or fatt_collegate is not None or fatt_partner is not None:
                fatturato_totale = (fatt_core or 0) + (fatt_collegate or 0) + (fatt_partner or 0)
            
            attivo_totale = None
            if att_core is not None or att_collegate is not None or att_partner is not None:
                attivo_totale = (att_core or 0) + (att_collegate or 0) + (att_partner or 0)
        
        # Log con gestione None
        pers_str = f"{personale_totale:.1f}" if personale_totale is not None else "N/D"
        fatt_str = f"€{fatturato_totale:,.2f}" if fatturato_totale is not None else "N/D"
        att_str = f"€{attivo_totale:,.2f}" if attivo_totale is not None else "N/D"
        
        print(f"   ✅ Personale aggregato: {pers_str} ULA")
        print(f"   ✅ Fatturato aggregato: {fatt_str}")
        print(f"   ✅ Attivo aggregato: {att_str}")
        
        return {
            "personale_totale": round(personale_totale, 1) if personale_totale is not None else None,
            "fatturato_totale": round(fatturato_totale, 2) if fatturato_totale is not None else None,
            "attivo_totale": round(attivo_totale, 2) if attivo_totale is not None else None,
            "dettaglio_calcolo": {
                "core": {
                    "personale": pers_core,
                    "fatturato": fatt_core,
                    "attivo": att_core
                },
                "collegate_contributo": {
                    "personale": round(pers_collegate, 1) if pers_collegate is not None else None,
                    "fatturato": round(fatt_collegate, 2) if fatt_collegate is not None else None,
                    "attivo": round(att_collegate, 2) if att_collegate is not None else None
                },
                "partner_contributo": {
                    "personale": round(pers_partner, 1) if pers_partner is not None else None,
                    "fatturato": round(fatt_partner, 2) if fatt_partner is not None else None,
                    "attivo": round(att_partner, 2) if att_partner is not None else None
                }
            }
        }
    
    def _classifica_impresa(self, personale, fatturato, attivo) -> Dict:
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
            personale (float|None): ULA aggregate (None se non disponibile)
            fatturato (float|None): Fatturato aggregato (None se non disponibile)
            attivo (float|None): Attivo/Bilancio aggregato (None se non disponibile)
            
        Returns:
            dict: Classificazione con dettagli soglie
        """
        dimensione = "Grande Impresa"
        # Modalità Excel-like: N/D=0 anche per la classificazione (confronti su 3 criteri)
        import os
        excel_mode = os.environ.get("PMI_EXCEL_MODE_ND_ZERO", "1").lower() in {"1", "true", "yes", "on"}
        if excel_mode:
            personale_x = personale or 0
            fatturato_x = fatturato or 0
            attivo_x = attivo or 0
        else:
            personale_x = personale
            fatturato_x = fatturato
            attivo_x = attivo
        
        # Helper: conta quanti criteri rispettano la soglia (ritorna True se almeno 2 su 3)
        # Se un valore è None, non può rispettare la soglia (non disponibile)
        def rispetta_soglia_2su3(pers_soglia, fatt_soglia, att_soglia):
            criteri_rispettati = 0
            criteri_disponibili = 0
            
            if personale_x is not None:
                criteri_disponibili += 1
                if personale_x < pers_soglia:
                    criteri_rispettati += 1
            
            if fatturato_x is not None:
                criteri_disponibili += 1
                if fatturato_x <= fatt_soglia:
                    criteri_rispettati += 1
            
            if attivo_x is not None:
                criteri_disponibili += 1
                if attivo_x <= att_soglia:
                    criteri_rispettati += 1
            
            # In modalità Excel consideriamo sempre 3 criteri disponibili (perché N/D=0)
            if not excel_mode:
                if criteri_disponibili < 2:
                    return False
            
            # Almeno 2 su 3 criteri devono essere rispettati (tra quelli disponibili)
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
                "valore": personale_x,
                "soglia_micro": SOGLIE_UE["micro"]["personale"],
                "soglia_piccola": SOGLIE_UE["piccola"]["personale"],
                "soglia_media": SOGLIE_UE["media"]["personale"]
            },
            "fatturato": {
                "valore": fatturato_x,
                "soglia_micro": SOGLIE_UE["micro"]["fatturato"],
                "soglia_piccola": SOGLIE_UE["piccola"]["fatturato"],
                "soglia_media": SOGLIE_UE["media"]["fatturato"]
            },
            "attivo": {
                "valore": attivo_x,
                "soglia_micro": SOGLIE_UE["micro"]["attivo"],
                "soglia_piccola": SOGLIE_UE["piccola"]["attivo"],
                "soglia_media": SOGLIE_UE["media"]["attivo"]
            }
        }
        
        print(f"   🏆 Classificazione: {dimensione}")
        
        return {
            "dimensione": dimensione,
            "soglie_rispettate": soglie_rispettate,
            "note": self._genera_nota_classificazione(dimensione, personale_x, fatturato_x, attivo_x)
        }
    
    def _genera_nota_classificazione(self, dimensione: str, personale, fatturato, attivo) -> str:
        """Genera nota esplicativa della classificazione con regola 2 su 3"""
        
        # Conta quanti criteri rispettano ciascuna soglia
        # Gestisce None (valore non disponibile)
        def conta_criteri_rispettati(categoria):
            soglia = SOGLIE_UE[categoria]
            criteri = 0
            if personale is not None and personale < soglia["personale"]:
                criteri += 1
            if fatturato is not None and fatturato <= soglia["fatturato"]:
                criteri += 1
            if attivo is not None and attivo <= soglia["attivo"]:
                criteri += 1
            return criteri
        
        # Formattazione valori con gestione None
        pers_str = f"{personale:.1f}" if personale is not None else "N/D"
        fatt_str = f"€{fatturato:,.0f}" if fatturato is not None else "N/D"
        att_str = f"€{attivo:,.0f}" if attivo is not None else "N/D"
        
        if "Micro" in dimensione:
            n = conta_criteri_rispettati("micro")
            return f"Microimpresa (regola 2/3): {n}/3 criteri rispettati (ULA:{pers_str}, Fatt:{fatt_str}, Bil:{att_str})"
        elif "Piccola" in dimensione:
            n = conta_criteri_rispettati("piccola")
            return f"Piccola Impresa (regola 2/3): {n}/3 criteri rispettati (ULA:{pers_str}, Fatt:{fatt_str}, Bil:{att_str})"
        elif "Media" in dimensione:
            n = conta_criteri_rispettati("media")
            return f"Media Impresa (regola 2/3): {n}/3 criteri rispettati (ULA:{pers_str}, Fatt:{fatt_str}, Bil:{att_str})"
        else:
            return f"Grande Impresa: supera le soglie PMI in 2+ criteri (ULA:{pers_str}, Fatt:{fatt_str}, Bil:{att_str})"
    
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
            pers_str = f"{agg['personale_totale']:.1f}" if agg['personale_totale'] is not None else "N/D"
            fatt_str = f"€{agg['fatturato_totale']:,.2f}" if agg['fatturato_totale'] is not None else "N/D"
            att_str = f"€{agg['attivo_totale']:,.2f}" if agg['attivo_totale'] is not None else "N/D"
            print(f"\n📊 AGGREGATI UE:")
            print(f"   • Personale: {pers_str} ULA")
            print(f"   • Fatturato: {fatt_str}")
            print(f"   • Attivo: {att_str}")
        
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

