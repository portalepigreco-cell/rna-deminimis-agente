#!/usr/bin/env python3
"""
🤖 RNA De Minimis Calculator - Versione Finale
============================================

Calcola automaticamente il totale de minimis per qualsiasi P.IVA 
direttamente dal sito RNA.gov.it

Uso: python rna_deminimis.py [PARTITA_IVA]

Esempi:
  python rna_deminimis.py 03254550738
  python rna_deminimis.py 04108170962

Autore: Pigreco Team
Data: Settembre 2025
"""

import sys
import time
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.firefox import GeckoDriverManager

class RNACalculator:
    """Calcolatore automatico de minimis RNA"""
    
    def __init__(self, headless=True):
        self.driver = None
        self.headless = headless
        self.url = "https://www.rna.gov.it/trasparenza/aiuti"
        
    def setup_browser(self):
        """Configura Firefox"""
        print("🔧 Avviando browser...")
        
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        
        service = Service(GeckoDriverManager().install())
        self.driver = webdriver.Firefox(service=service, options=options)
        self.driver.set_window_size(1920, 1080)
        self.driver.implicitly_wait(10)
        
        return True
    
    def accetta_cookie(self):
        """Gestisce il banner cookie"""
        try:
            cookie_selectors = [
                "//button[contains(text(), 'Accett')]",
                "//button[contains(text(), 'accett')]", 
                "//a[contains(text(), 'Accett')]",
                "//button[contains(text(), 'OK')]"
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    cookie_btn.click()
                    time.sleep(1)
                    return True
                except TimeoutException:
                    continue
            return True
        except:
            return True
    
    def calcola_deminimis(self, partita_iva):
        """
        Calcola il totale de minimis per una P.IVA
        
        Args:
            partita_iva (str): Partita IVA da cercare
            
        Returns:
            dict: Risultato con totale e dettagli
        """
        try:
            print(f"🔍 Ricerca de minimis per P.IVA: {partita_iva}")
            
            # Validazione P.IVA
            if not re.match(r'^\d{11}$', partita_iva):
                return {"errore": "P.IVA deve essere di 11 cifre"}
            
            # Setup browser
            if not self.setup_browser():
                return {"errore": "Impossibile avviare browser"}
            
            # Step 1: Carica pagina (con cookie)
            print("📄 Accesso al sito RNA...")
            self.driver.get(self.url)
            time.sleep(3)
            
            # Step 2: Gestisci cookie
            self.accetta_cookie()
            
            # Step 3: Ricarica per form
            print("🔄 Caricamento form di ricerca...")
            self.driver.get(self.url)
            time.sleep(3)
            
            # Step 4: Compila form
            print("📝 Compilazione automatica...")
            
            # Trova campo CF
            cf_field = self.driver.find_element(By.NAME, "cfBen")
            cf_field.clear()
            cf_field.send_keys(partita_iva)
            
            # Seleziona De Minimis
            tipo_select = Select(self.driver.find_element(By.NAME, "tipp"))
            tipo_select.select_by_visible_text("De Minimis")
            
            # Imposta date (ultimi 6 anni per sicurezza)
            oggi = datetime.now()
            sei_anni_fa = oggi - timedelta(days=6*365)
            
            # Prova diversi formati e nomi di campo
            try:
                # Formato italiano gg/mm/aaaa
                data_da = self.driver.find_element(By.NAME, "annoc")
                data_da.clear()
                data_da.send_keys(sei_anni_fa.strftime('%d/%m/%Y'))
                
                data_a = self.driver.find_element(By.NAME, "annoc2") 
                data_a.clear()
                data_a.send_keys(oggi.strftime('%d/%m/%Y'))
                print(f"📅 Date impostate: {sei_anni_fa.strftime('%d/%m/%Y')} - {oggi.strftime('%d/%m/%Y')}")
            except:
                # Fallback: prova formato ISO
                try:
                    data_da = self.driver.find_element(By.NAME, "annoc")
                    data_da.clear()
                    data_da.send_keys(sei_anni_fa.strftime('%Y-%m-%d'))
                    
                    data_a = self.driver.find_element(By.NAME, "annoc2")
                    data_a.clear() 
                    data_a.send_keys(oggi.strftime('%Y-%m-%d'))
                    print(f"📅 Date impostate (ISO): {sei_anni_fa.strftime('%Y-%m-%d')} - {oggi.strftime('%Y-%m-%d')}")
                except:
                    print("⚠️ Impossibile impostare date, procedo senza filtro temporale")
            
            # Step 5: Invia ricerca
            print("🚀 Invio ricerca...")
            submit_btn = self.driver.find_element(By.XPATH, "//input[@type='submit'] | //button[@type='submit']")
            submit_btn.click()
            time.sleep(5)
            
            # Step 6: Screenshot per debug
            screenshot_path = f"debug_risultati_{partita_iva}.png"
            self.driver.save_screenshot(screenshot_path)
            print(f"📸 Screenshot salvato: {screenshot_path}")
            
            # Step 7: Analizza risultati con paginazione
            return self.analizza_risultati_completi(partita_iva)
            
        except NoSuchElementException as e:
            return {
                "errore": f"Elemento non trovato: {e}",
                "partita_iva": partita_iva,
                "data_ricerca": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "totale_de_minimis": 0,
                "numero_aiuti": 0,
                "percentuale_utilizzata": 0,
                "margine_rimanente": 300000
            }
        except Exception as e:
            return {
                "errore": f"Errore generico: {e}",
                "partita_iva": partita_iva,
                "data_ricerca": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "totale_de_minimis": 0,
                "numero_aiuti": 0,
                "percentuale_utilizzata": 0,
                "margine_rimanente": 300000
            }
        finally:
            if self.driver:
                self.driver.quit()
    
    def analizza_risultati_completi(self, partita_iva):
        """Analizza tutti i risultati attraverso tutte le pagine per gli ultimi 3 anni"""
        try:
            tre_anni_fa = datetime.now() - timedelta(days=3*365)
            tutti_aiuti = []
            pagina_corrente = 1
            max_pagine = 10  # Limite ottimizzato
            
            print(f"🔍 Inizio analisi multipagina per {partita_iva}")
            print(f"📅 Periodo: dal {tre_anni_fa.strftime('%d/%m/%Y')} ad oggi")
            
            while pagina_corrente <= max_pagine:
                # Analizza la pagina corrente
                aiuti_pagina, continua = self.analizza_pagina_corrente(tre_anni_fa)
                tutti_aiuti.extend(aiuti_pagina)
                
                # Se non ci sono più dati recenti, fermati
                if not continua:
                    break
                
                # Se questa pagina è vuota, fermati
                if len(aiuti_pagina) == 0 and pagina_corrente >= 2:
                    break
                
                # Prova ad andare alla pagina successiva
                if not self.vai_pagina_successiva():
                    break
                    
                pagina_corrente += 1
            
            # Calcola totali
            totale = sum(aiuto['importo'] for aiuto in tutti_aiuti)
            
            print(f"✅ Completato: {len(tutti_aiuti)} aiuti = €{totale:,.2f}")
            
            # Costruisci risultato finale
            soglia_deminimis = 300000.0
            soglia_superata = totale > soglia_deminimis
            margine_rimanente = max(0, soglia_deminimis - totale)
            
            return {
                "partita_iva": partita_iva,
                "totale_de_minimis": round(totale, 2),
                "numero_aiuti": len(tutti_aiuti),
                "aiuti_trovati": tutti_aiuti,
                "soglia_superata": soglia_superata,
                "margine_rimanente": round(margine_rimanente, 2),
                "soglia_limite": soglia_deminimis,
                "percentuale_utilizzata": round((totale / soglia_deminimis) * 100, 1),
                "data_ricerca": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "pagine_analizzate": pagina_corrente
            }
            
        except Exception as e:
            print(f"❌ Errore nell'analisi multipagina: {e}")
            return {
                "errore": f"Errore nell'analisi: {e}",
                "partita_iva": partita_iva,
                "totale_de_minimis": 0,
                "numero_aiuti": 0,
                "aiuti_trovati": [],
                "soglia_superata": False,
                "margine_rimanente": 300000.0,
                "messaggio": "Errore durante l'analisi delle pagine"
            }

    def analizza_pagina_corrente(self, tre_anni_fa):
        """Analizza la pagina corrente e restituisce aiuti validi + flag se continuare"""
        aiuti_trovati = []
        continua = True
        date_vecchie_consecutive = 0
        
        try:
            # Cerca la tabella dei risultati
            tabella = self.driver.find_element(By.TAG_NAME, "table")
            righe = tabella.find_elements(By.TAG_NAME, "tr")
            
            if len(righe) < 2:
                print("   ⚠️ Tabella vuota o solo header")
                return aiuti_trovati, False
            
            # Analizza header per identificare le colonne
            header = righe[0]
            colonne_header = header.find_elements(By.TAG_NAME, "th")
            
            data_col = -1
            importo_col = -1
            
            for i, col in enumerate(colonne_header):
                testo_col = col.text.strip().lower()
                if "data" in testo_col and "concessione" in testo_col:
                    data_col = i
                elif "elemento" in testo_col and "aiuto" in testo_col:
                    importo_col = i
            
            # Se non trova le colonne, usa posizioni fisse dallo screenshot
            if data_col == -1:
                data_col = 6  # "Data Concessione" dovrebbe essere la 7a colonna (indice 6)
            
            if importo_col == -1:
                importo_col = -1  # Ultima colonna
            
            # Analizza le righe dati
            for i, riga in enumerate(righe[1:], 1):  # Salta header
                try:
                    celle = riga.find_elements(By.TAG_NAME, "td")
                    if len(celle) < 7:  # Verifica minimo colonne
                        continue
                    
                    # Estrai data concessione
                    if data_col < len(celle):
                        data_testo = celle[data_col].text.strip()
                    else:
                        continue
                    
                    if not data_testo:
                        continue
                    
                    # Converti data
                    try:
                        data_concessione = datetime.strptime(data_testo, "%d/%m/%Y")
                    except ValueError:
                        continue
                    
                    # Se la data è troppo vecchia, salta ma continua
                    if data_concessione < tre_anni_fa:
                        date_vecchie_consecutive += 1
                        
                        # Se tutta la pagina è troppo vecchia, ferma la ricerca
                        if date_vecchie_consecutive >= 3:  # Limite ancora più aggressivo
                            continua = False
                            break
                        continue
                    else:
                        # Reset counter se trova data recente
                        date_vecchie_consecutive = 0
                    
                    # Estrai importo "Elemento Aiuto"
                    if importo_col == -1:
                        importo_testo = celle[-1].text.strip()  # Ultima colonna
                    elif importo_col < len(celle):
                        importo_testo = celle[importo_col].text.strip()
                    else:
                        continue
                    
                    if not importo_testo:
                        continue
                    
                    # Pulisci e converti importo (formato italiano: €1.234,56)
                    importo_pulito = importo_testo.replace('€', '').replace(' ', '').strip()
                    
                    # Gestisci formato italiano: 1.234,56 → 1234.56
                    if ',' in importo_pulito:
                        parti = importo_pulito.split(',')
                        if len(parti) == 2:
                            parte_intera = parti[0].replace('.', '')  # Rimuovi separatori migliaia
                            parte_decimale = parti[1]
                            importo_pulito = f"{parte_intera}.{parte_decimale}"
                    
                    try:
                        importo = float(importo_pulito)
                        if importo <= 0:
                            continue
                    except ValueError:
                        continue
                    
                    # Aggiungi aiuto valido con dettagli estesi
                    titolo_misura = celle[2].text.strip() if len(celle) > 2 else "N/A"
                    aiuti_trovati.append({
                        'data_concessione': data_testo,
                        'importo': importo,
                        'titolo_misura': titolo_misura,
                        'data': data_testo  # Mantieni per compatibilità
                    })
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"   ⚠️ Errore lettura tabella: {e}")
        
        return aiuti_trovati, continua

    def vai_pagina_successiva(self):
        """Prova ad andare alla pagina successiva, restituisce True se ci riesce"""
        try:
            # Attendi che la paginazione si carichi
            time.sleep(1)
            
            # Metodo 0: DATATABLES specifico - cerca i controlli paginazione DataTables
            dt_next = self.driver.find_elements(By.XPATH, "//a[contains(@class, 'paginate_button') and contains(@class, 'next')]")
            if dt_next and dt_next[0].is_enabled() and dt_next[0].is_displayed():
                dt_next[0].click()
                time.sleep(2)
                return True
            
            # Cerca anche numeri di pagina DataTables
            dt_numbers = self.driver.find_elements(By.XPATH, "//a[contains(@class, 'paginate_button') and not(contains(@class, 'previous')) and not(contains(@class, 'next'))]")
            for btn in dt_numbers:
                if btn.is_enabled() and btn.is_displayed() and btn.text.strip().isdigit():
                    numero = int(btn.text.strip())
                    if numero > 1:  # Clicca la prima pagina successiva trovata
                        btn.click()
                        time.sleep(2)
                        return True
            
            # Metodo 1: Cerca freccia destra per paginazione
            frecce_destra = self.driver.find_elements(By.XPATH, "//a[contains(text(), '›') or contains(text(), '»') or contains(text(), 'Next')]")
            for freccia in frecce_destra:
                if freccia.is_enabled() and freccia.is_displayed():
                    freccia.click()
                    time.sleep(2)
                    return True
            
            # Metodo 2: Cerca numeri specifici
            for numero_pagina in [2, 3, 4, 5]:
                link_numero = self.driver.find_elements(By.XPATH, f"//a[text()='{numero_pagina}']")
                if link_numero and link_numero[0].is_enabled() and link_numero[0].is_displayed():
                    link_numero[0].click()
                    time.sleep(2)
                    return True
            
            return False
            
        except Exception as e:
            print(f"   ⚠️ Errore navigazione pagina: {e}")
            return False

    def analizza_risultati(self, partita_iva):
        """Estrae e calcola il totale degli aiuti"""
        try:
            print("📊 Analisi risultati...")
            
            page_html = self.driver.page_source
            
            # Controlla se ci sono risultati
            no_results = [
                "nessun risultato", "non sono stati trovati", 
                "valorizzare almeno un parametro"
            ]
            
            if any(indicator in page_html.lower() for indicator in no_results):
                return {
                    "partita_iva": partita_iva,
                    "totale_de_minimis": 0.0,
                    "numero_aiuti": 0,
                    "aiuti_trovati": [],
                    "soglia_superata": False,
                    "margine_rimanente": 300000.0,
                    "messaggio": "Nessun aiuto de minimis trovato"
                }
            
            # Estrai importi
            aiuti_trovati = []
            totale = 0.0
            
            # Cerca tabelle
            tabelle = self.driver.find_elements(By.TAG_NAME, "table")
            
            for tabella in tabelle:
                try:
                    headers = tabella.find_elements(By.TAG_NAME, "th")
                    header_texts = [h.text.lower().strip() for h in headers]
                    
                    # Trova colonna importo
                    colonna_importo = -1
                    for i, header in enumerate(header_texts):
                        if 'elemento' in header and 'aiuto' in header:
                            colonna_importo = i
                            break
                    
                    if colonna_importo == -1:
                        continue
                    
                    # Analizza righe
                    righe = tabella.find_elements(By.TAG_NAME, "tr")[1:]
                    
                    for riga in righe:
                        celle = riga.find_elements(By.TAG_NAME, "td")
                        
                        if len(celle) <= colonna_importo:
                            continue
                        
                        importo_text = celle[colonna_importo].text.strip()
                        
                        # Estrai importo
                        for pattern in [r'€\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)', 
                                      r'([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)\s*€',
                                      r'([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)']:
                            match = re.search(pattern, importo_text)
                            if match:
                                importo_str = match.group(1)
                                importo_num = float(importo_str.replace('.', '').replace(',', '.'))
                                
                                if importo_num > 0:
                                    aiuti_trovati.append({
                                        "importo": importo_num,
                                        "importo_formattato": f"€{importo_num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                                    })
                                    totale += importo_num
                                break
                
                except Exception:
                    continue
            
            # Se non trova tabelle, cerca pattern nella pagina
            if not aiuti_trovati:
                importi_pagina = re.findall(r'€\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)', page_html)
                
                for importo_str in importi_pagina:
                    try:
                        importo_num = float(importo_str.replace('.', '').replace(',', '.'))
                        if importo_num >= 100:
                            aiuti_trovati.append({
                                "importo": importo_num,
                                "importo_formattato": f"€{importo_num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                            })
                            totale += importo_num
                    except ValueError:
                        continue
            
            # Analisi soglia de minimis
            soglia_deminimis = 300000.0
            soglia_superata = totale > soglia_deminimis
            margine_rimanente = max(0, soglia_deminimis - totale)
            
            return {
                "partita_iva": partita_iva,
                "totale_de_minimis": round(totale, 2),
                "numero_aiuti": len(aiuti_trovati),
                "aiuti_trovati": aiuti_trovati,
                "soglia_superata": soglia_superata,
                "margine_rimanente": round(margine_rimanente, 2),
                "soglia_limite": soglia_deminimis,
                "percentuale_utilizzata": round((totale / soglia_deminimis) * 100, 1),
                "data_ricerca": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "anni_considerati": "2022-2025 (ultimi 3 anni)",
                "messaggio": f"Trovati {len(aiuti_trovati)} aiuti de minimis"
            }
            
        except Exception as e:
            return {"errore": f"Errore analisi risultati: {e}"}

def stampa_risultati(risultato):
    """Stampa i risultati in formato elegante"""
    
    print("\n" + "="*70)
    print("📋 RISULTATO CALCOLO DE MINIMIS")
    print("="*70)
    
    if "errore" in risultato:
        print(f"❌ ERRORE: {risultato['errore']}")
        return
    
    # Informazioni base
    print(f"🏢 Partita IVA: {risultato['partita_iva']}")
    print(f"📅 Data ricerca: {risultato['data_ricerca']}")
    print(f"📊 Periodo analizzato: {risultato['anni_considerati']}")
    
    # Totale de minimis
    totale_formattato = f"€{risultato['totale_de_minimis']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    print(f"\n💰 TOTALE DE MINIMIS: {totale_formattato}")
    print(f"📊 Numero aiuti trovati: {risultato['numero_aiuti']}")
    
    # Analisi soglia
    print(f"\n📈 ANALISI SOGLIA:")
    print(f"   Soglia massima: €200.000,00")
    print(f"   Utilizzo attuale: {risultato['percentuale_utilizzata']}%")
    
    margine_formattato = f"€{risultato['margine_rimanente']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    if risultato['soglia_superata']:
        eccesso = risultato['totale_de_minimis'] - risultato['soglia_limite']
        eccesso_formattato = f"€{eccesso:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        print(f"   🚨 SOGLIA SUPERATA di {eccesso_formattato}")
        print(f"   ⚠️  ATTENZIONE: Non è possibile ricevere ulteriori aiuti de minimis!")
    else:
        print(f"   ✅ Margine disponibile: {margine_formattato}")
        if risultato['percentuale_utilizzata'] > 80:
            print(f"   ⚠️  ATTENZIONE: Prossimi al limite!")
        elif risultato['percentuale_utilizzata'] > 50:
            print(f"   💡 Utilizzo moderato")
        else:
            print(f"   ✅ Utilizzo basso, molto margine disponibile")
    
    # Dettaglio aiuti
    if risultato['aiuti_trovati']:
        print(f"\n📝 DETTAGLIO AIUTI:")
        for i, aiuto in enumerate(risultato['aiuti_trovati'], 1):
            print(f"   {i}. {aiuto['importo_formattato']}")
    
    print("\n" + "="*70)
    print("✅ Calcolo completato con successo!")

def main():
    """Funzione principale"""
    
    print("🤖 RNA De Minimis Calculator - Pigreco Team")
    print("="*50)
    
    # Leggi P.IVA
    if len(sys.argv) > 1:
        partita_iva = sys.argv[1].strip()
    else:
        partita_iva = input("🔢 Inserisci Partita IVA (11 cifre): ").strip()
    
    if not partita_iva:
        print("❌ Partita IVA non fornita!")
        return
    
    # Opzione modalità visiva
    modalita_visiva = False
    if len(sys.argv) > 2 and sys.argv[2].lower() in ['--visual', '-v', '--debug']:
        modalita_visiva = True
        print("👁️  Modalità visiva attivata")
    
    # Calcola de minimis
    calcolatore = RNACalculator(headless=not modalita_visiva)
    risultato = calcolatore.calcola_deminimis(partita_iva)
    
    # Stampa risultati
    stampa_risultati(risultato)

if __name__ == "__main__":
    main()
