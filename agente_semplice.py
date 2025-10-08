#!/usr/bin/env python3
"""
🤖 Agente RNA Semplice - Pigreco Team
===================================

Versione semplificata che mostra esattamente cosa fa step by step
e salva screenshots per ogni passaggio.

Uso: python agente_semplice.py 03254550738
"""

import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.firefox import GeckoDriverManager

def setup_firefox():
    """Configura Firefox"""
    print("🔧 Configurando Firefox...")
    
    options = Options()
    # NON usare headless per debug
    # options.add_argument("--headless")
    
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    driver.set_window_size(1920, 1080)
    
    print("✅ Firefox configurato")
    return driver

def debug_pagina(driver, nome_step):
    """Salva screenshot e HTML per debug"""
    screenshot_file = f"debug_{nome_step}.png"
    html_file = f"debug_{nome_step}.html"
    
    driver.save_screenshot(screenshot_file)
    
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    
    print(f"💾 Debug salvato: {screenshot_file} e {html_file}")

def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python agente_semplice.py [PARTITA_IVA]")
        return
    
    partita_iva = sys.argv[1]
    print(f"🎯 Cercando P.IVA: {partita_iva}")
    
    driver = setup_firefox()
    
    try:
        # Step 1: Vai al sito (prima volta - apparirà il cookie banner)
        print("📄 Caricando sito RNA (prima volta)...")
        driver.get("https://www.rna.gov.it/trasparenza/aiuti")
        time.sleep(5)
        
        debug_pagina(driver, "01_caricamento_iniziale")
        
        # Step 2: Gestisci cookie
        print("🍪 Cercando e chiudendo cookie banner...")
        
        cookie_closed = False
        cookie_selectors = [
            "//button[contains(text(), 'Accett')]",
            "//button[contains(text(), 'accett')]", 
            "//a[contains(text(), 'Accett')]",
            "//button[contains(text(), 'OK')]",
            "//button[contains(text(), 'Chiudi')]",
            "//button[@class*='cookie']",
            "//button[@class*='accept']",
            "//span[contains(text(), 'Accett')]/parent::button",
            "//*[contains(text(), 'cookie')]/ancestor::*[contains(@class, 'button') or contains(@class, 'btn')]"
        ]
        
        for selector in cookie_selectors:
            try:
                cookie_element = driver.find_element(By.XPATH, selector)
                if cookie_element.is_displayed():
                    cookie_element.click()
                    print(f"✅ Cookie chiusi con: {selector}")
                    cookie_closed = True
                    time.sleep(2)
                    break
            except:
                continue
        
        if not cookie_closed:
            print("⚠️ Cookie banner non trovato, provo comunque...")
        
        debug_pagina(driver, "02_dopo_cookie")
        
        # Step 3: RICARICA la pagina (FONDAMENTALE!)
        print("🔄 RICARICANDO la pagina per far apparire il form...")
        driver.get("https://www.rna.gov.it/trasparenza/aiuti")
        time.sleep(5)
        
        debug_pagina(driver, "03_dopo_reload")
        
        # Step 4: Ora cerca il form corretto
        print("🔍 Cercando form nella pagina DOPO il reload...")
        
        # Prova a trovare TUTTI gli input nella pagina
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"📝 Trovati {len(all_inputs)} input nella pagina:")
        
        for i, inp in enumerate(all_inputs[:10]):  # Mostra primi 10
            name = inp.get_attribute("name") or "N/A"
            input_type = inp.get_attribute("type") or "N/A"
            placeholder = inp.get_attribute("placeholder") or "N/A"
            print(f"  {i+1}. name='{name}', type='{input_type}', placeholder='{placeholder}'")
        
        # Cerca anche select
        all_selects = driver.find_elements(By.TAG_NAME, "select")
        print(f"📝 Trovati {len(all_selects)} select nella pagina:")
        
        for i, sel in enumerate(all_selects[:5]):
            name = sel.get_attribute("name") or "N/A"
            print(f"  {i+1}. name='{name}'")
        
        debug_pagina(driver, "02_analisi_form")
        
        # Step 5: Analisi automatica (senza pausa)
        print("\n🔍 Procedendo con analisi automatica...")
        time.sleep(2)
        
        # Step 4: Prova a compilare form con euristica
        print("📝 Tentativo di compilazione automatica...")
        
        # Cerca campo che potrebbe essere CF/P.IVA
        possible_cf_fields = []
        for inp in all_inputs:
            name = (inp.get_attribute("name") or "").lower()
            placeholder = (inp.get_attribute("placeholder") or "").lower()
            
            if any(term in name for term in ['cf', 'codice', 'fiscale', 'beneficiario']) or \
               any(term in placeholder for term in ['cf', 'codice', 'fiscale', 'beneficiario']):
                possible_cf_fields.append(inp)
                print(f"✅ Campo CF candidato: name='{inp.get_attribute('name')}', placeholder='{inp.get_attribute('placeholder')}'")
        
        if possible_cf_fields:
            # Usa il primo campo trovato
            cf_field = possible_cf_fields[0]
            cf_field.clear()
            cf_field.send_keys(partita_iva)
            print(f"✅ P.IVA inserita nel campo: {cf_field.get_attribute('name')}")
            
            # Cerca e seleziona "De Minimis" nel tipo procedimento
            print("🔍 Cercando campo Tipo Procedimento...")
            tipo_selects = [sel for sel in all_selects if 'tipp' in (sel.get_attribute('name') or '')]
            
            if tipo_selects:
                from selenium.webdriver.support.ui import Select
                select_element = Select(tipo_selects[0])
                
                print(f"📝 Opzioni disponibili in Tipo Procedimento:")
                for i, option in enumerate(select_element.options):
                    print(f"  {i}. '{option.text}' (value: '{option.get_attribute('value')}')")
                
                # Cerca opzione De Minimis
                de_minimis_found = False
                for option in select_element.options:
                    if 'minimis' in option.text.lower() or 'de minimis' in option.text.lower():
                        select_element.select_by_visible_text(option.text)
                        print(f"✅ Selezionato Tipo Procedimento: {option.text}")
                        de_minimis_found = True
                        break
                
                if not de_minimis_found:
                    print("⚠️ Opzione 'De Minimis' non trovata automaticamente")
                    # Prova valori comuni
                    common_values = ['de_minimis', 'deminimis', 'De Minimis', 'DE_MINIMIS']
                    for value in common_values:
                        try:
                            select_element.select_by_value(value)
                            print(f"✅ Selezionato per valore: {value}")
                            de_minimis_found = True
                            break
                        except:
                            continue
                    
                    if not de_minimis_found:
                        print("❌ Non riesco a selezionare De Minimis automaticamente")
            else:
                print("⚠️ Campo Tipo Procedimento non trovato")
            
            # Imposta filtro date (ultimi 3 anni)
            print("📅 Impostando filtro date (ultimi 3 anni)...")
            from datetime import datetime, timedelta
            
            oggi = datetime.now()
            tre_anni_fa = oggi - timedelta(days=3*365)  # Circa 3 anni fa
            
            # Cerca campi data
            date_fields = [inp for inp in all_inputs if inp.get_attribute('type') == 'date']
            print(f"📅 Trovati {len(date_fields)} campi data")
            
            for inp in date_fields:
                name = inp.get_attribute('name')
                placeholder = inp.get_attribute('placeholder') or ''
                print(f"  📅 Campo data: name='{name}', placeholder='{placeholder}'")
                
                # Campo "Data concessione (da)" - imposta 3 anni fa
                if name == 'annoc' or '(da)' in placeholder.lower():
                    data_da = tre_anni_fa.strftime('%Y-%m-%d')
                    inp.send_keys(data_da)
                    print(f"✅ Data DA impostata: {data_da}")
                
                # Campo "Data concessione (a)" - imposta oggi
                elif name == 'annoc2' or '(a)' in placeholder.lower():
                    data_a = oggi.strftime('%Y-%m-%d')
                    inp.send_keys(data_a)
                    print(f"✅ Data A impostata: {data_a}")
            
            debug_pagina(driver, "03_piva_e_tipo_inseriti")
        else:
            print("❌ Nessun campo CF trovato automaticamente")
            
            # Mostra tutti i campi text per scelta manuale
            text_inputs = [inp for inp in all_inputs if inp.get_attribute("type") in ["text", "search", None]]
            if text_inputs:
                print(f"\n📝 Campi text disponibili:")
                for i, inp in enumerate(text_inputs):
                    name = inp.get_attribute("name") or f"input_{i}"
                    placeholder = inp.get_attribute("placeholder") or "N/A"
                    print(f"  {i}. {name} (placeholder: {placeholder})")
                
                try:
                    choice = int(input("Scegli numero campo (0-N): "))
                    if 0 <= choice < len(text_inputs):
                        text_inputs[choice].clear()
                        text_inputs[choice].send_keys(partita_iva)
                        print(f"✅ P.IVA inserita manualmente")
                        debug_pagina(driver, "03_piva_manuale")
                except:
                    print("❌ Scelta non valida")
        
        # Step 5: Cerca e prova a inviare form
        print("🚀 Cercando bottone submit...")
        
        submit_buttons = driver.find_elements(By.XPATH, "//input[@type='submit'] | //button[@type='submit'] | //button[contains(text(), 'Cerc')] | //input[contains(@value, 'Cerc')]")
        
        if submit_buttons:
            print(f"✅ Trovati {len(submit_buttons)} bottoni submit")
            submit_buttons[0].click()
            print("🚀 Form inviato!")
            
            time.sleep(5)
            debug_pagina(driver, "04_risultati")
            
            # Analizza risultati
            page_text = driver.page_source.lower()
            
            if "nessun risultato" in page_text or "non sono stati trovati" in page_text:
                print("ℹ️ Nessun risultato trovato")
            else:
                print("✅ Possibili risultati trovati!")
                
                # Cerca importi nella pagina
                importi = re.findall(r'€\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)', driver.page_source)
                if importi:
                    print(f"💰 Importi trovati nella pagina:")
                    totale = 0
                    for importo_str in importi:
                        try:
                            importo_num = float(importo_str.replace('.', '').replace(',', '.'))
                            if importo_num >= 100:  # Filtra importi piccoli
                                print(f"  - €{importo_str} (= €{importo_num:,.2f})")
                                totale += importo_num
                        except:
                            pass
                    
                    if totale > 0:
                        print(f"\n🎯 TOTALE STIMATO: €{totale:,.2f}")
                        
                        # Confronta con valore atteso
                        if abs(totale - 9505.95) < 1:
                            print("✅ PERFETTO! Corrisponde al valore atteso €9.505,95")
                        else:
                            print(f"⚠️ Differisce dal valore atteso €9.505,95")
        
        else:
            print("❌ Nessun bottone submit trovato")
            
            # Prova ENTER sul campo CF
            from selenium.webdriver.common.keys import Keys
            if possible_cf_fields:
                possible_cf_fields[0].send_keys(Keys.RETURN)
                print("🚀 Provato ENTER sul campo CF")
                time.sleep(5)
                debug_pagina(driver, "04_risultati_enter")
        
        print("\n📊 Fine ricerca. Controlla i file debug_*.png per i dettagli visivi.")
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        debug_pagina(driver, "99_errore")
    
    finally:
        print("🔧 Chiudendo browser...")
        time.sleep(3)  # Pausa per vedere risultati
        driver.quit()
        print("✅ Browser chiuso")

if __name__ == "__main__":
    main()
