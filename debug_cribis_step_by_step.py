#!/usr/bin/env python3
"""
Debug step-by-step Cribis X per capire dove si inceppa
"""

import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def debug_cribis_step_by_step():
    """Debug passo-passo dell'interfaccia Cribis X"""
    
    print("🔍 DEBUG CRIBIS X - STEP BY STEP")
    print("="*50)
    
    # Browser visibile per debug
    options = Options()
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Firefox(options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # STEP 1: Homepage
        print("📍 STEP 1: Caricamento homepage...")
        driver.get("https://www2.cribisx.com/#Home/Index")
        time.sleep(3)
        
        driver.save_screenshot("debug_step1_homepage.png")
        print("✅ Homepage caricata")
        print(f"   URL: {driver.current_url}")
        
        # STEP 2: Login
        print("\n📍 STEP 2: Login...")
        
        # Trova campi login
        try:
            username_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")))
            password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            login_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
            
            # Inserisci credenziali
            username_field.clear()
            username_field.send_keys("CC838673")
            password_field.clear()
            password_field.send_keys("26082025__Pigreco_")
            
            driver.save_screenshot("debug_step2_credenziali_inserite.png")
            print("✅ Credenziali inserite")
            
            # Login
            login_button.click()
            time.sleep(5)
            
            driver.save_screenshot("debug_step3_dopo_login.png")
            print("✅ Login effettuato")
            print(f"   URL: {driver.current_url}")
            
        except Exception as e:
            print(f"❌ Errore login: {str(e)}")
            return
        
        # STEP 3: Navigazione a Documenti
        print("\n📍 STEP 3: Navigazione a Documenti...")
        
        try:
            documenti_url = "https://www2.cribisx.com/#Storage/Index"
            driver.get(documenti_url)
            time.sleep(3)
            
            driver.save_screenshot("debug_step4_documenti.png")
            print("✅ Sezione Documenti caricata")
            print(f"   URL: {driver.current_url}")
            
        except Exception as e:
            print(f"❌ Errore navigazione: {str(e)}")
            return
        
        # STEP 4: Analisi pagina Documenti
        print("\n📍 STEP 4: Analisi elementi pagina Documenti...")
        
        # Salva HTML completo
        with open("debug_step4_documenti.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("✅ HTML salvato: debug_step4_documenti.html")
        
        # Analizza tutti i pulsanti
        buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"\n🔍 Trovati {len(buttons)} pulsanti:")
        for i, btn in enumerate(buttons):
            try:
                text = btn.text.strip()
                classes = btn.get_attribute("class") or ""
                btn_id = btn.get_attribute("id") or ""
                if text or classes or btn_id:
                    print(f"  {i+1}. Text: '{text}' | Class: '{classes}' | ID: '{btn_id}'")
            except Exception as e:
                print(f"  {i+1}. Errore lettura pulsante: {str(e)}")
        
        # Analizza tutti i link
        links = driver.find_elements(By.TAG_NAME, "a")
        print(f"\n🔍 Trovati {len(links)} link:")
        for i, link in enumerate(links[:15]):  # Prime 15
            try:
                text = link.text.strip()
                href = link.get_attribute("href") or ""
                classes = link.get_attribute("class") or ""
                if text and len(text) > 2:
                    print(f"  {i+1}. Text: '{text}' | Href: '{href[:50]}...' | Class: '{classes}'")
            except Exception as e:
                print(f"  {i+1}. Errore lettura link: {str(e)}")
        
        # Cerca specificamente elementi con "RICERCA"
        print(f"\n🔍 Ricerca elementi con 'RICERCA':")
        
        try:
            # XPath per tutti gli elementi contenenti "RICERCA"
            elementi_ricerca = driver.find_elements(By.XPATH, "//*[contains(text(), 'RICERCA')]")
            print(f"Trovati {len(elementi_ricerca)} elementi con 'RICERCA':")
            for i, elem in enumerate(elementi_ricerca):
                try:
                    tag = elem.tag_name
                    text = elem.text.strip()
                    classes = elem.get_attribute("class") or ""
                    print(f"  {i+1}. Tag: {tag} | Text: '{text}' | Class: '{classes}'")
                except Exception as e:
                    print(f"  {i+1}. Errore lettura elemento: {str(e)}")
                    
        except Exception as e:
            print(f"❌ Errore ricerca RICERCA: {str(e)}")
        
        # Cerca elementi con "PUNTUALE"
        print(f"\n🔍 Ricerca elementi con 'PUNTUALE':")
        
        try:
            elementi_puntuale = driver.find_elements(By.XPATH, "//*[contains(text(), 'PUNTUALE')]")
            print(f"Trovati {len(elementi_puntuale)} elementi con 'PUNTUALE':")
            for i, elem in enumerate(elementi_puntuale):
                try:
                    tag = elem.tag_name
                    text = elem.text.strip()
                    classes = elem.get_attribute("class") or ""
                    print(f"  {i+1}. Tag: {tag} | Text: '{text}' | Class: '{classes}'")
                except Exception as e:
                    print(f"  {i+1}. Errore lettura elemento: {str(e)}")
                    
        except Exception as e:
            print(f"❌ Errore ricerca PUNTUALE: {str(e)}")
        
        # Cerca input fields
        print(f"\n🔍 Ricerca campi input:")
        
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"Trovati {len(inputs)} campi input:")
        for i, inp in enumerate(inputs):
            try:
                input_type = inp.get_attribute("type") or ""
                name = inp.get_attribute("name") or ""
                placeholder = inp.get_attribute("placeholder") or ""
                value = inp.get_attribute("value") or ""
                if input_type != "hidden":  # Salta input nascosti
                    print(f"  {i+1}. Type: {input_type} | Name: '{name}' | Placeholder: '{placeholder}' | Value: '{value}'")
            except Exception as e:
                print(f"  {i+1}. Errore lettura input: {str(e)}")
        
        # Salva tutto il testo della pagina
        body_text = driver.find_element(By.TAG_NAME, "body").text
        with open("debug_step4_testo_completo.txt", "w", encoding="utf-8") as f:
            f.write(body_text)
        print(f"\n✅ Testo completo salvato: debug_step4_testo_completo.txt")
        
        print(f"\n📊 RIEPILOGO:")
        print(f"   • URL attuale: {driver.current_url}")
        print(f"   • Pulsanti: {len(buttons)}")
        print(f"   • Link: {len(links)}")
        print(f"   • Input: {len(inputs)}")
        print(f"   • Elementi 'RICERCA': {len(elementi_ricerca) if 'elementi_ricerca' in locals() else 0}")
        print(f"   • Elementi 'PUNTUALE': {len(elementi_puntuale) if 'elementi_puntuale' in locals() else 0}")
        
        print(f"\n📁 File salvati:")
        print(f"   • debug_step*.png (screenshot)")
        print(f"   • debug_step4_documenti.html (HTML)")
        print(f"   • debug_step4_testo_completo.txt (testo)")
        
    except Exception as e:
        print(f"❌ Errore generale: {str(e)}")
        driver.save_screenshot("debug_errore.png")
    
    finally:
        input("\n⏸️  Premi INVIO per chiudere il browser e vedere i risultati...")
        driver.quit()

if __name__ == "__main__":
    debug_cribis_step_by_step()
