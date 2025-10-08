#!/usr/bin/env python3
"""
🤖 Agente RNA De Minimis - Pigreco Team
=====================================

Agente che va direttamente sul sito RNA.gov.it e calcola automaticamente
il totale de minimis per una partita IVA.

Uso: python agente_rna_web.py [PARTITA_IVA]
Esempio: python agente_rna_web.py 03254550738

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

class RNAWebAgent:
    """Agente per ricerca automatica de minimis su RNA.gov.it con Firefox"""
    
    def __init__(self):
        self.driver = None
        self.base_url = "https://www.rna.gov.it/trasparenza/aiuti"
        
    def setup_driver(self):
        """Configura Firefox WebDriver"""
        print("🔧 Configurando Firefox WebDriver...")
        
        # Opzioni Firefox
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        options.set_preference("general.useragent.override", 
                             "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0")
        
        # Per debugging, rimuovi headless
        # options.add_argument("--headless")
        
        try:
            # Usa webdriver-manager per scaricare geckodriver automaticamente
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=options)
            
            # Imposta timeout e dimensioni finestra
            self.driver.implicitly_wait(10)
            self.driver.set_window_size(1920, 1080)
            
            print("✅ Firefox WebDriver configurato con successo")
            return True
            
        except Exception as e:
            print(f"❌ Errore configurazione WebDriver: {e}")
            return False
    
    def accetta_cookie(self):
        """Accetta i cookie se richiesto"""
        try:
            print("🍪 Gestendo cookie...")
            
            # Cerca bottoni comuni per accettare cookie
            cookie_selectors = [
                "//button[contains(text(), 'Accett')]",
                "//button[contains(text(), 'accett')]",
                "//a[contains(text(), 'Accett')]",
                "//button[@id='cookie-accept']",
                "//button[contains(@class, 'cookie')]",
                "//button[contains(@class, 'accept')]"
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    cookie_btn.click()
                    print("✅ Cookie accettati")
                    time.sleep(2)
                    return True
                except TimeoutException:
                    continue
            
            print("ℹ️ Nessun banner cookie trovato")
            return True
            
        except Exception as e:
            print(f"⚠️ Errore gestione cookie: {e}")
            return True  # Continua comunque
    
    def cerca_de_minimis(self, partita_iva):
        """
        Cerca aiuti de minimis per una partita IVA
        
        Args:
            partita_iva (str): Partita IVA da cercare
            
        Returns:
            dict: Risultato della ricerca
        """
        try:
            print(f"🔍 Ricerca de minimis per P.IVA: {partita_iva}")
            
            # Step 1: Apri pagina di ricerca
            print("📄 Caricando pagina RNA...")
            self.driver.get(self.base_url)
            time.sleep(3)
            
            # Step 2: Gestisci cookie
            self.accetta_cookie()
            
            # Step 3: Compila form di ricerca
            print("📝 Compilando form di ricerca...")
            
            # Cerca campo CF/P.IVA (prova diversi selettori)
            cf_selectors = [
                "input[name*='cf']",
                "input[name*='beneficiario']", 
                "input[name*='codice']",
                "input[placeholder*='CF']",
                "input[placeholder*='Codice']",
                "input[placeholder*='Beneficiario']",
                "#cf_beneficiario",
                "#codice_fiscale"
            ]
            
            cf_field = None
            for selector in cf_selectors:
                try:
                    cf_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"✅ Campo CF trovato: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not cf_field:
                # Prova con XPATH
                xpath_selectors = [
                    "//input[contains(@name, 'cf')]",
                    "//input[contains(@placeholder, 'CF')]",
                    "//input[contains(@placeholder, 'Beneficiario')]"
                ]
                
                for selector in xpath_selectors:
                    try:
                        cf_field = self.driver.find_element(By.XPATH, selector)
                        print(f"✅ Campo CF trovato (XPATH): {selector}")
                        break
                    except NoSuchElementException:
                        continue
            
            if cf_field:
                cf_field.clear()
                cf_field.send_keys(partita_iva)
                print(f"✅ P.IVA inserita: {partita_iva}")
            else:
                print("❌ Campo CF non trovato!")
                return {"errore": "Campo CF non trovato"}
            
            # Cerca campo Tipo Procedimento
            print("🔍 Cercando campo Tipo Procedimento...")
            
            tipo_selectors = [
                "select[name*='tipo']",
                "select[name*='procedimento']",
                "#tipo_procedimento",
                "select[name*='Tipo']"
            ]
            
            tipo_field = None
            for selector in tipo_selectors:
                try:
                    tipo_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"✅ Campo Tipo trovato: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if tipo_field:
                select = Select(tipo_field)
                # Cerca opzione De Minimis
                for option in select.options:
                    if 'minimis' in option.text.lower():
                        select.select_by_visible_text(option.text)
                        print(f"✅ Selezionato: {option.text}")
                        break
                else:
                    # Se non trova "De Minimis", prova altri valori
                    try:
                        select.select_by_value("de_minimis")
                        print("✅ Selezionato de_minimis (by value)")
                    except:
                        print("⚠️ Opzione De Minimis non trovata, continuo...")
            
            # Step 4: Invia ricerca
            print("🚀 Inviando ricerca...")
            
            # Cerca bottone submit
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']", 
                "//button[contains(text(), 'Cerc')]",
                "//input[contains(@value, 'Cerc')]",
                ".btn-primary",
                "#submit"
            ]
            
            submit_clicked = False
            for selector in submit_selectors:
                try:
                    if selector.startswith("//"):
                        submit_btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        submit_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    submit_btn.click()
                    print(f"✅ Form inviato: {selector}")
                    submit_clicked = True
                    break
                except:
                    continue
            
            if not submit_clicked:
                # Prova con ENTER sul campo CF
                try:
                    from selenium.webdriver.common.keys import Keys
                    cf_field.send_keys(Keys.RETURN)
                    print("✅ Form inviato con ENTER")
                except:
                    print("❌ Non riesco a inviare il form")
                    return {"errore": "Non riesco a inviare il form"}
            
            # Step 5: Attendi risultati
            print("⏳ Attendendo risultati...")
            time.sleep(5)
            
            # Step 6: Analizza risultati
            return self.analizza_risultati_pagina(partita_iva)
            
        except Exception as e:
            print(f"❌ Errore durante la ricerca: {e}")
            return {"errore": f"Errore ricerca: {e}"}
    
    def analizza_risultati_pagina(self, partita_iva):
        """
        Analizza la pagina dei risultati per estrarre gli importi de minimis
        
        Args:
            partita_iva (str): P.IVA cercata
            
        Returns:
            dict: Risultati con totale de minimis
        """
        print("📊 Analizzando risultati...")
        
        try:
            # Salva screenshot per debug
            self.driver.save_screenshot("debug_risultati.png")
            print("📸 Screenshot salvato: debug_risultati.png")
            
            # Ottieni HTML della pagina
            page_html = self.driver.page_source
            
            # Salva HTML per debug
            with open("debug_risultati.html", "w", encoding="utf-8") as f:
                f.write(page_html)
            print("💾 HTML salvato: debug_risultati.html")
            
            # Controlla se ci sono risultati
            no_results_indicators = [
                "nessun risultato", "non sono stati trovati", "no results",
                "valorizzare almeno un parametro", "inserire almeno"
            ]
            
            page_text = page_html.lower()
            for indicator in no_results_indicators:
                if indicator in page_text:
                    print(f"ℹ️ Nessun risultato: {indicator}")
                    return {
                        "partita_iva": partita_iva,
                        "totale_de_minimis": 0.0,
                        "numero_aiuti": 0,
                        "aiuti_trovati": [],
                        "messaggio": "Nessun aiuto de minimis trovato"
                    }
            
            # Cerca tabelle con risultati
            print("🔍 Cercando tabelle dei risultati...")
            
            tabelle = self.driver.find_elements(By.TAG_NAME, "table")
            print(f"📋 Trovate {len(tabelle)} tabelle")
            
            aiuti_trovati = []
            totale = 0.0
            
            # Filtra ultimi 3 anni
            anno_corrente = datetime.now().year
            anni_validi = [anno_corrente - i for i in range(3)]  # 2025, 2024, 2023
            print(f"📅 Anni considerati: {anni_validi}")
            
            for idx, tabella in enumerate(tabelle):
                print(f"📊 Analizzando tabella {idx + 1}...")
                
                try:
                    # Cerca header
                    headers = tabella.find_elements(By.TAG_NAME, "th")
                    header_texts = [h.text.lower().strip() for h in headers]
                    
                    print(f"📝 Headers: {header_texts}")
                    
                    # Trova indici colonne importanti
                    colonna_importo = -1
                    colonna_data = -1
                    
                    for i, header in enumerate(header_texts):
                        if 'elemento' in header and 'aiuto' in header:
                            colonna_importo = i
                            print(f"✅ Colonna Elemento Aiuto: {i}")
                        elif 'data' in header and 'concession' in header:
                            colonna_data = i
                            print(f"✅ Colonna Data: {i}")
                    
                    if colonna_importo == -1:
                        print(f"⚠️ Tabella {idx + 1}: colonna importo non trovata")
                        continue
                    
                    # Analizza righe
                    righe = tabella.find_elements(By.TAG_NAME, "tr")[1:]  # Salta header
                    print(f"📊 Righe da analizzare: {len(righe)}")
                    
                    for riga_idx, riga in enumerate(righe):
                        celle = riga.find_elements(By.TAG_NAME, "td")
                        
                        if len(celle) <= colonna_importo:
                            continue
                        
                        # Verifica data (se disponibile)
                        anno_valido = True
                        data_str = "N/A"
                        
                        if colonna_data >= 0 and len(celle) > colonna_data:
                            data_str = celle[colonna_data].text.strip()
                            anno_valido = any(str(anno) in data_str for anno in anni_validi)
                            
                            if not anno_valido:
                                print(f"🔍 Riga {riga_idx + 1}: anno non valido ({data_str})")
                                continue
                        
                        # Estrai importo
                        importo_text = celle[colonna_importo].text.strip()
                        
                        # Pattern per importi italiani
                        importo_patterns = [
                            r'€\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',  # €1.234,56
                            r'([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)\s*€',  # 1.234,56 €
                            r'([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',      # 1.234,56
                        ]
                        
                        for pattern in importo_patterns:
                            match = re.search(pattern, importo_text)
                            if match:
                                importo_str = match.group(1)
                                # Converte formato italiano in float
                                importo_numero = float(importo_str.replace('.', '').replace(',', '.'))
                                
                                if importo_numero > 0:
                                    aiuti_trovati.append({
                                        "importo_originale": importo_text,
                                        "importo": importo_numero,
                                        "data_concessione": data_str,
                                        "tabella": idx + 1,
                                        "riga": riga_idx + 1
                                    })
                                    totale += importo_numero
                                    print(f"💰 Aiuto trovato: €{importo_numero:,.2f} del {data_str}")
                                break
                
                except Exception as e:
                    print(f"⚠️ Errore analisi tabella {idx + 1}: {e}")
                    continue
            
            # Se non trova tabelle, cerca pattern nella pagina
            if not aiuti_trovati:
                print("🔍 Cercando pattern nella pagina...")
                
                # Basandomi sui tuoi screenshot: €4.347,30 e €5.158,65
                importi_pattern = re.findall(r'€\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)', page_html)
                
                for importo_str in importi_pattern:
                    try:
                        importo_numero = float(importo_str.replace('.', '').replace(',', '.'))
                        if importo_numero >= 100:  # Filtra importi piccoli
                            aiuti_trovati.append({
                                "importo_originale": f"€{importo_str}",
                                "importo": importo_numero,
                                "data_concessione": "Pattern generico",
                                "tabella": "N/A",
                                "riga": "N/A"
                            })
                            totale += importo_numero
                            print(f"💰 Pattern trovato: €{importo_numero:,.2f}")
                    except ValueError:
                        continue
            
            # Risultato finale
            risultato = {
                "partita_iva": partita_iva,
                "totale_de_minimis": round(totale, 2),
                "numero_aiuti": len(aiuti_trovati),
                "aiuti_trovati": aiuti_trovati,
                "anni_considerati": anni_validi,
                "data_ricerca": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "messaggio": f"Trovati {len(aiuti_trovati)} aiuti per un totale di €{totale:,.2f}"
            }
            
            print(f"🎯 RISULTATO: €{totale:,.2f} ({len(aiuti_trovati)} aiuti)")
            return risultato
            
        except Exception as e:
            print(f"❌ Errore analisi risultati: {e}")
            return {"errore": f"Errore analisi: {e}"}
    
    def cleanup(self):
        """Chiude il browser"""
        if self.driver:
            self.driver.quit()
            print("🔧 Browser chiuso")

def main():
    """Funzione principale"""
    
    print("🤖 Agente RNA De Minimis - Pigreco Team")
    print("=" * 50)
    
    # Leggi P.IVA da argomenti
    if len(sys.argv) > 1:
        partita_iva = sys.argv[1].strip()
    else:
        partita_iva = input("🔢 Inserisci Partita IVA: ").strip()
    
    if not partita_iva:
        print("❌ Partita IVA non fornita!")
        return
    
    # Validazione P.IVA
    if not re.match(r'^\d{11}$', partita_iva):
        print("❌ Partita IVA deve essere di 11 cifre!")
        return
    
    # Crea agente
    agente = RNAWebAgent()
    
    try:
        # Setup browser
        if not agente.setup_driver():
            print("❌ Impossibile configurare il browser")
            return
        
        # Esegui ricerca
        risultato = agente.cerca_de_minimis(partita_iva)
        
        # Mostra risultati
        print("\n" + "=" * 60)
        print("📋 RISULTATO RICERCA DE MINIMIS")
        print("=" * 60)
        
        if "errore" in risultato:
            print(f"❌ {risultato['errore']}")
        else:
            print(f"🏢 Partita IVA: {risultato['partita_iva']}")
            print(f"💰 Totale De Minimis: €{risultato['totale_de_minimis']:,.2f}")
            print(f"📊 Numero aiuti: {risultato['numero_aiuti']}")
            print(f"📅 Data ricerca: {risultato['data_ricerca']}")
            
            if risultato.get('anni_considerati'):
                print(f"📅 Anni considerati: {risultato['anni_considerati']}")
            
            if risultato['aiuti_trovati']:
                print(f"\n📝 Dettaglio aiuti:")
                for i, aiuto in enumerate(risultato['aiuti_trovati'], 1):
                    print(f"  {i}. €{aiuto['importo']:,.2f} ({aiuto['importo_originale']}) - {aiuto['data_concessione']}")
        
        print("\n✅ Ricerca completata!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Ricerca interrotta dall'utente")
    except Exception as e:
        print(f"\n❌ Errore generale: {e}")
    finally:
        agente.cleanup()

if __name__ == "__main__":
    main()
