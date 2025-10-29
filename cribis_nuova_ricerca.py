#!/usr/bin/env python3
"""
CribisX Connector - NUOVA RICERCA (non archivio)
================================================

Procedura:
1. Login su Cribis X
2. Resta sulla Home
3. Cerca P.IVA nel campo principale (title="Inserisci i termini da cercare")
4. Premi INVIO
5. Clicca sul NOME dell'azienda nel primo risultato (es: "MAZZOLENI SPA")
6. Nella pagina dettaglio, clicca "Tutti i prodotti CRIBIS X"
7. Clicca "Richiedi" sotto "Gruppo Societario"
8. Aspetta generazione report
9. Estrai associate italiane >50%

Differenza con cribis_playwright_base.py:
- NON va in MyDocs/Storage (archivio)
- Genera NUOVO report (consuma crediti)
- Dati sempre aggiornati
- Prende SEMPRE il primo risultato della ricerca
"""

import json
import re
import time
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import sistema alert email
try:
    from email_alert import alert_cribis_error
    EMAIL_ALERTS_ENABLED = True
except ImportError:
    EMAIL_ALERTS_ENABLED = False
    print("⚠️ Modulo email_alert non disponibile - alert disabilitati")


class CribisNuovaRicerca:
    """Connector Cribis X per ricerche real-time (non archivio)"""
    
    def __init__(self, headless=False):
        """
        Inizializza il connector Playwright
        
        Args:
            headless (bool): Se True, browser in background
        """
        self.base_url = "https://www2.cribisx.com"
        self.username = "CC838673"
        self.password = "27_10_2025__Pigreco_"
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
    
    def _screenshot(self, path: str, descrizione: str = ""):
        """
        Salva screenshot solo in modalità debug (headless=False)
        
        Args:
            path: Percorso file screenshot
            descrizione: Descrizione per log
        """
        if not self.headless:
            try:
                self.page.screenshot(path=path)
                if descrizione:
                    print(f"📸 Screenshot: {descrizione}")
                else:
                    print(f"📸 Screenshot: {path}")
            except Exception as e:
                print(f"⚠️ Errore screenshot: {e}")
        
    def __enter__(self):
        """Context manager entry"""
        self.playwright = sync_playwright().start()
        
        # Logging per debug Playwright su Render
        import os
        print(f"🔍 DEBUG Playwright (Cribis):")
        print(f"  - PLAYWRIGHT_BROWSERS_PATH: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH', 'NON IMPOSTATO')}")
        print(f"  - Headless: {self.headless}")
        
        # Configurazione browser per ambienti cloud (Render, etc.)
        try:
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                slow_mo=500 if not self.headless else 0,  # Rallenta per debug
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
            print("✅ Browser Chromium lanciato con successo (Cribis)")
        except Exception as e:
            print(f"❌ ERRORE lancio browser (Cribis): {str(e)}")
            print(f"   Tipo errore: {type(e).__name__}")
            raise
            
        self.page = self.browser.new_page()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def login(self):
        """
        Esegue login su Cribis X
        
        Returns:
            bool: True se login riuscito
        """
        try:
            print("🔐 Avvio login su Cribis X...")
            
            # Vai alla homepage
            self.page.goto(f"{self.base_url}/#Home/Index", wait_until="domcontentloaded")
            print(f"📍 Navigazione a: {self.base_url}")
            
            # Aspetta che la pagina sia caricata
            time.sleep(3)
            
            # Salva screenshot iniziale (solo se headless=False)
            self._screenshot("debug_cribis_nuova_01_login_page.png", "Login page")
            
            # Trova campo username con selettori multipli
            selettori_username = [
                'input[name="Username"]',
                'input[id="Username"]',
                'input[placeholder*="Utente"]',
                'input[placeholder*="Username"]',
                'input[type="text"]'
            ]
            
            username_field = None
            for sel in selettori_username:
                try:
                    username_field = self.page.wait_for_selector(sel, timeout=3000)
                    if username_field:
                        print(f"✅ Campo username trovato: {sel}")
                        break
                except:
                    continue
            
            if not username_field:
                print("❌ Campo username non trovato")
                return False
            
            # Trova campo password
            selettori_password = [
                'input[name="Password"]',
                'input[id="Password"]',
                'input[placeholder*="Password"]',
                'input[type="password"]'
            ]
            
            password_field = None
            for sel in selettori_password:
                try:
                    password_field = self.page.wait_for_selector(sel, timeout=3000)
                    if password_field:
                        print(f"✅ Campo password trovato: {sel}")
                        break
                except:
                    continue
            
            if not password_field:
                print("❌ Campo password non trovato")
                return False
            
            # Inserisci credenziali
            print("📝 Inserimento credenziali...")
            username_field.fill(self.username)
            password_field.fill(self.password)
            
            # Cerca bottone login
            selettori_login = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Accedi")'
            ]
            
            login_button = None
            for sel in selettori_login:
                try:
                    login_button = self.page.wait_for_selector(sel, timeout=3000)
                    if login_button:
                        print(f"✅ Bottone login trovato: {sel}")
                        break
                except:
                    continue
            
            if not login_button:
                print("❌ Bottone login non trovato")
                return False
            
            # Clicca login
            print("🚀 Clic su login...")
            login_button.click()
            
            # Aspetta redirect e caricamento
            self.page.wait_for_load_state("networkidle")
            time.sleep(3)
            
            current_url = self.page.url
            print(f"📍 URL dopo login: {current_url}")
            
            # Salva screenshot dopo login
            self._screenshot("debug_cribis_nuova_02_dopo_login.png", "Dopo login")
            
            print("✅ Login completato con successo!")
            return True
                
        except Exception as e:
            print(f"❌ Errore durante login: {str(e)}")
            return False
    
    def cerca_nel_campo_principale(self, partita_iva):
        """
        Cerca P.IVA nel campo principale (in alto, vicino al logo)
        
        Args:
            partita_iva (str): P.IVA da cercare
            
        Returns:
            bool: True se ricerca riuscita
        """
        try:
            print(f"\n🔍 Ricerca P.IVA nel campo principale: {partita_iva}")
            
            # Vai sempre alla Home per evitare stati come sessionExpired o pagine Storage
            try:
                self.page.goto(f"{self.base_url}/#Home/Index", wait_until="domcontentloaded")
                self.page.wait_for_load_state("networkidle")
                time.sleep(1)
            except Exception:
                pass
            
            # Se per qualche motivo siamo finiti di nuovo su LogOn, prova a riloggarti
            if "LogOn" in (self.page.url or ""):
                print("⚠️  Redirect a LogOn; provo login e torno in Home...")
                if not self.login():
                    return False
                self.page.goto(f"{self.base_url}/#Home/Index", wait_until="domcontentloaded")
                time.sleep(1)
            
            # Selettore SPECIFICO fornito dall'utente
            selettori_campo = [
                'input[title="Inserisci i termini da cercare"]',  # SELETTORE PRINCIPALE
                'input[placeholder*="nome, codice cliente, partita iva"]',
                'input[placeholder*="Cerca per nome"]',
                'header input[type="text"]',
                '.search-input',
                'input.form-control[type="text"]',
                # Nuovi fallback robusti
                'input[placeholder*="partita iva"]',
                'input[placeholder*="Partita IVA"]',
                'input[placeholder*="partita"]'
            ]
            
            campo_ricerca = None
            for sel in selettori_campo:
                try:
                    campo_ricerca = self.page.wait_for_selector(sel, timeout=5000)
                    if campo_ricerca:
                        print(f"✅ Campo ricerca trovato: {sel}")
                        break
                except:
                    continue
            
            if not campo_ricerca:
                print("❌ Campo ricerca principale non trovato — provo focus via JS sul primo input visibile in header")
                try:
                    self.page.evaluate(
                        "() => { const i = document.querySelector('header input[type=\\'text\\']'); if(i){ i.focus(); } }"
                    )
                    campo_ricerca = self.page.query_selector('header input[type="text"]')
                except Exception:
                    campo_ricerca = None
                if not campo_ricerca:
                    return False
            
            # Inserisci P.IVA
            print(f"📝 Inserimento P.IVA: {partita_iva}")
            campo_ricerca.click()
            campo_ricerca.fill("")
            campo_ricerca.type(partita_iva, delay=50)
            
            # Aspetta un attimo per autocomplete
            time.sleep(1)
            
            # Salva screenshot prima di premere invio
            self._screenshot("debug_cribis_nuova_03_piva_inserita.png", "P.IVA inserita")
            
            # Premi INVIO (come richiesto dall'utente)
            print("⏎ Premendo INVIO...")
            campo_ricerca.press("Enter")
            
            # Aspetta caricamento risultati
            self.page.wait_for_load_state("networkidle")
            time.sleep(3)
            
            # Salva screenshot risultati
            self._screenshot("debug_cribis_nuova_04_risultati_cerca.png", "Risultati ricerca")
            
            print("✅ Ricerca completata")
            return True
            
        except Exception as e:
            print(f"❌ Errore durante ricerca: {str(e)}")
            return False
    
    def clicca_nome_primo_risultato(self):
        """
        Clicca sul NOME dell'azienda del primo risultato (es: "MAZZOLENI SPA")
        
        Returns:
            bool: True se click riuscito
        """
        try:
            print("\n🎯 Clic sul NOME dell'azienda del primo risultato...")
            
            # Aspetta che i risultati siano visibili
            time.sleep(2)
            
            # Selettori per il nome dell'azienda (primo risultato)
            # Basato sullo screenshot: è un link con classe specifica
            selettori_nome = [
                # Selettori specifici per il nome azienda (link blu cliccabile)
                'a[href*="Company"]:first-of-type',
                'h3 a:first-of-type',
                '.company-name:first-of-type',
                'a.company-link:first-of-type',
                
                # Cerca il primo link grande/visibile che sembra un nome azienda
                'a:has-text("SPA"):first-of-type',
                'a:has-text("SRL"):first-of-type',
                
                # Fallback: primo link con testo lungo (probabilmente nome azienda)
                'div.result a:first-of-type',
                'div[class*="result"] a:first-of-type'
            ]
            
            nome_link = None
            for sel in selettori_nome:
                try:
                    nome_link = self.page.wait_for_selector(sel, timeout=3000)
                    if nome_link:
                        testo = nome_link.inner_text()
                        print(f"✅ Nome azienda trovato: '{testo}' con selettore: {sel}")
                        break
                except:
                    continue
            
            if not nome_link:
                print("❌ Nome azienda non trovato")
                print("🔍 Cerco tutti i link grandi/visibili...")
                
                # Debug: stampa tutti i link principali
                all_links = self.page.query_selector_all('a')
                print(f"📋 Trovati {len(all_links)} link totali")
                for i, link in enumerate(all_links[:20]):
                    try:
                        text = link.inner_text().strip()
                        # Mostra solo link con testo significativo
                        if text and len(text) > 5 and len(text) < 100:
                            print(f"  {i}. '{text[:50]}'")
                    except:
                        continue
                
                return False
            
            # Scroll al nome se necessario
            nome_link.scroll_into_view_if_needed()
            time.sleep(1)
            
            # Salva screenshot prima del click
            self.page.screenshot(path="debug_cribis_nuova_05_primo_risultato.png")
            print("📸 Screenshot: debug_cribis_nuova_05_primo_risultato.png")
            
            # Clicca sul nome
            testo_nome = nome_link.inner_text()
            print(f"🖱️ Clic sul nome: '{testo_nome}'...")
            nome_link.click()
            
            # Aspetta caricamento pagina dettaglio
            self.page.wait_for_load_state("domcontentloaded")
            time.sleep(3)
            
            # Salva screenshot dopo click
            self.page.screenshot(path="debug_cribis_nuova_06_dopo_nome.png")
            print("📸 Screenshot: debug_cribis_nuova_06_dopo_nome.png")
            
            print(f"✅ Click su '{testo_nome}' completato")
            return True
            
        except Exception as e:
            print(f"❌ Errore durante click nome azienda: {str(e)}")
            return False
    
    def clicca_tutti_prodotti_cribis_dettaglio(self):
        """
        Nella pagina dettaglio, scrolla in basso e clicca "Tutti i prodotti CRIBIS X"
        
        Returns:
            bool: True se click riuscito
        """
        try:
            print("\n📦 Cercando 'Tutti i prodotti CRIBIS X' nella pagina dettaglio...")
            
            # Aspetta che la pagina sia caricata
            time.sleep(2)
            
            # SCROLL IN FONDO ALLA PAGINA (il link è in basso a destra)
            print("📜 Scrolling verso il basso...")
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
            # Selettori per il link "Tutti i prodotti CRIBIS X"
            selettori_tutti_prodotti = [
                'a:has-text("Tutti i prodotti CRIBIS X")',
                'a:has-text("Tutti i prodotti")',
                'a.link-orange:has-text("Tutti i prodotti")',
                '[class*="link"]:has-text("Tutti i prodotti")',
                'a:has-text("prodotti CRIBIS")'
            ]
            
            link_prodotti = None
            for sel in selettori_tutti_prodotti:
                try:
                    link_prodotti = self.page.wait_for_selector(sel, timeout=3000)
                    if link_prodotti:
                        print(f"✅ Link 'Tutti i prodotti CRIBIS X' trovato: {sel}")
                        break
                except:
                    continue
            
            if not link_prodotti:
                print("❌ Link 'Tutti i prodotti CRIBIS X' non trovato")
                print("🔍 Cerco tutti i link con 'prodotti'...")
                
                # Debug: stampa tutti i link
                all_links = self.page.query_selector_all('a')
                for i, link in enumerate(all_links[:30]):
                    try:
                        text = link.inner_text().strip()
                        if text and 'prodott' in text.lower():
                            print(f"  {i}. '{text[:60]}'")
                    except:
                        continue
                
                return False
            
            # Scroll al link per assicurarsi che sia visibile
            link_prodotti.scroll_into_view_if_needed()
            time.sleep(1)
            
            # Salva screenshot prima del click
            self.page.screenshot(path="debug_cribis_nuova_07_prima_tutti_prodotti.png")
            print("📸 Screenshot: debug_cribis_nuova_07_prima_tutti_prodotti.png")
            
            # Clicca sul link (si apre modale)
            print("🖱️ Clic su 'Tutti i prodotti CRIBIS X'...")
            link_prodotti.click()
            
            # Aspetta che la MODALE sia visibile
            time.sleep(3)
            
            # Salva screenshot dopo click (modale aperta)
            self.page.screenshot(path="debug_cribis_nuova_08_modale_prodotti.png")
            print("📸 Screenshot modale: debug_cribis_nuova_08_modale_prodotti.png")
            
            print("✅ Modale 'Tutti i prodotti' aperta")
            return True
            
        except Exception as e:
            print(f"❌ Errore durante click 'Tutti i prodotti CRIBIS X': {str(e)}")
            return False
    
    def richiedi_gruppo_societario(self):
        """
        Nella MODALE aperta, scrolla e cerca "Gruppo Societario" poi clicca "Richiedi"
        
        Returns:
            bool: True se click riuscito
        """
        try:
            print("\n🏢 Cercando 'Gruppo Societario' nella modale...")
            
            # Aspetta che la modale sia completamente caricata
            time.sleep(2)
            
            # SCROLL DENTRO LA MODALE per vedere "Gruppo Societario" (è in fondo)
            print("📜 Scrolling dentro la modale verso il BASSO...")
            try:
                # Trova la modale
                modale = self.page.locator('.modal-dialog, .modal-content, .modal').first
                if modale:
                    # Scroll progressivo per raggiungere "Gruppo Societario"
                    # Prima a metà
                    modale.evaluate("element => element.scrollTop = element.scrollHeight / 2")
                    time.sleep(0.5)
                    print("  📍 Scroll a 50%...")
                    
                    # Poi a 75%
                    modale.evaluate("element => element.scrollTop = element.scrollHeight * 0.75")
                    time.sleep(0.5)
                    print("  📍 Scroll a 75%...")
                    
                    # Infine fino in fondo
                    modale.evaluate("element => element.scrollTop = element.scrollHeight")
                    time.sleep(1)
                    print("✅ Scroll completato (in fondo alla modale)")
            except Exception as e:
                print(f"⚠️ Scroll modale fallito: {str(e)}, continuo comunque...")
            
            # Salva screenshot dopo scroll
            self.page.screenshot(path="debug_cribis_nuova_08b_modale_dopo_scroll.png")
            print("📸 Screenshot post-scroll: debug_cribis_nuova_08b_modale_dopo_scroll.png")
            
            # METODO SPECIFICO: Cerca la CARD di "Gruppo Societario" (header blu scuro + bottone)
            try:
                print("🔍 Cerco CARD 'Gruppo Societario' con header blu scuro...")
                
                # Trova tutti gli elementi con testo "Gruppo Societario"
                elementi_gruppo = self.page.get_by_text("Gruppo Societario", exact=True).all()
                print(f"📋 Trovati {len(elementi_gruppo)} elementi 'Gruppo Societario'")
                
                bottone_richiedi = None
                
                for i, elemento in enumerate(elementi_gruppo):
                    try:
                        if not elemento.is_visible():
                            continue
                        
                        print(f"  🔍 Analizzo elemento {i+1}...")
                        
                        # Trova il contenitore padre (la card)
                        # Risali fino a trovare un div che contiene sia il testo che il bottone
                        parent = elemento
                        for level in range(10):  # Risali max 10 livelli
                            try:
                                parent = parent.locator('..')
                                parent_html = parent.inner_html()
                                
                                # Verifica se questo parent contiene:
                                # 1. "Gruppo Societario" nel testo
                                # 2. Un bottone "Richiedi"
                                # 3. "5,90 Unità" o simile
                                if ('Gruppo Societario' in parent_html and 
                                    'Richiedi' in parent_html and 
                                    ('5,90' in parent_html or 'Unit' in parent_html)):
                                    
                                    print(f"    ✅ Trovato contenitore card al livello {level}")
                                    
                                    # Cerca il bottone "Richiedi" dentro questo parent
                                    bottoni_in_card = parent.locator('button:has-text("Richiedi"), a:has-text("Richiedi")').all()
                                    
                                    if bottoni_in_card:
                                        # Prendi il primo bottone "Richiedi" della card
                                        bottone_richiedi = bottoni_in_card[0]
                                        print(f"    ✅ Trovato bottone 'Richiedi' nella card Gruppo Societario")
                                        break
                            except:
                                break
                        
                        if bottone_richiedi:
                            break
                            
                    except Exception as e:
                        print(f"  ⚠️ Errore elemento {i+1}: {str(e)}")
                        continue
                
                if bottone_richiedi and bottone_richiedi.is_visible():
                    # Salva screenshot prima del click
                    self.page.screenshot(path="debug_cribis_nuova_09_prima_richiedi.png")
                    print("📸 Screenshot: debug_cribis_nuova_09_prima_richiedi.png")
                    
                    # Scroll al bottone per assicurarsi che sia visibile
                    bottone_richiedi.scroll_into_view_if_needed()
                    time.sleep(1)
                    
                    # Click su "Richiedi" e cattura nuova tab con expect_page
                    print("🖱️ Clic su bottone 'Richiedi' e attesa nuova tab (fino a 3 minuti)...")
                    
                    try:
                        # Usa expect_page per catturare la nuova tab quando si apre
                        # Timeout di 200 secondi (3+ minuti)
                        with self.page.context.expect_page(timeout=200000) as popup_info:
                            # Click sul bottone (force=True per bypassare overlay)
                            bottone_richiedi.click(force=True)
                            print("✅ Click eseguito, aspetto apertura nuova tab...")
                        
                        # Cattura la nuova pagina
                        nuova_tab = popup_info.value
                        print(f"✅ Nuova tab aperta! URL: {nuova_tab.url}")
                        nuova_tab_aperta = True
                        
                        # Cambia focus alla nuova tab
                        print("🔄 Cambio focus alla nuova tab...")
                        self.page = nuova_tab
                        
                    except Exception as e:
                        print(f"⚠️ Timeout o errore nell'apertura nuova tab: {str(e)}")
                        nuova_tab_aperta = False
                    
                    if nuova_tab_aperta:
                        
                        # Aspetta che la nuova tab sia caricata
                        self.page.wait_for_load_state("domcontentloaded")
                        time.sleep(3)
                        
                        print(f"📍 URL nuova tab: {self.page.url}")
                        
                        # Aspetta che il contenuto sia completamente caricato
                        print("⏳ Aspetto caricamento completo del report (può richiedere tempo)...")
                        try:
                            self.page.wait_for_load_state("networkidle", timeout=45000)
                        except:
                            print("⚠️ Timeout networkidle, continuo comunque...")
                        
                        # Aspetta extra per rendering completo
                        time.sleep(5)
                        
                        # Verifica che ci siano elementi del report (codici fiscali, nomi aziende, etc)
                        print("🔍 Verifico presenza elementi report...")
                        try:
                            # Aspetta che compaia almeno un elemento tipico del gruppo societario
                            self.page.wait_for_selector('body:has-text("Cod. Fisc."), body:has-text("Italia"), body:has-text("SRL"), body:has-text("SPA")', timeout=10000)
                            print("✅ Elementi report trovati")
                        except:
                            print("⚠️ Elementi report non trovati subito, aspetto ancora...")
                            time.sleep(5)
                    else:
                        # Nessuna nuova tab - chiudi modale e vai a MyDocs
                        print("📂 Nessuna nuova tab, il report va in MyDocs...")
                        
                        # Chiudi modale con forza - prova diversi metodi
                        print("🚪 Chiudo modale...")
                        try:
                            # Metodo 1: Cerca bottone X di chiusura
                            close_buttons = self.page.locator('.modal .close, .modal button[aria-label="Close"], .modal .modal-header button').all()
                            if close_buttons:
                                close_buttons[0].click(force=True)
                                print("✅ Modale chiusa con bottone X")
                            else:
                                # Metodo 2: ESC
                                self.page.keyboard.press("Escape")
                                print("✅ Modale chiusa con ESC")
                            time.sleep(2)
                        except Exception as e:
                            print(f"⚠️ Errore chiusura modale: {str(e)}")
                        
                        # Verifica che la modale sia chiusa
                        time.sleep(1)
                        modale_visibile = self.page.locator('.modal:visible').count()
                        print(f"📋 Modali visibili: {modale_visibile}")
                        
                        # Naviga a MyDocs/Storage dove dovrebbe apparire il report
                        print("📍 Navigazione a MyDocs...")
                        self.page.goto(f"{self.base_url}/#Storage/Index", wait_until="domcontentloaded")
                        time.sleep(3)
                        
                        # Verifica che siamo in MyDocs
                        url_attuale = self.page.url
                        print(f"📍 URL attuale: {url_attuale}")
                        
                        if "Storage" not in url_attuale:
                            print("⚠️ Non siamo in Storage, riprovo...")
                            self.page.evaluate("window.location.hash = '#Storage/Index'")
                            time.sleep(3)
                        
                        # Aspetta che la lista documenti sia caricata
                        print("⏳ Aspetto caricamento lista documenti...")
                        time.sleep(3)
                        
                        # Cerca il report appena generato (primo in lista)
                        print("🔍 Cerco report Gruppo Societario appena generato...")
                        
                        # Salva screenshot di MyDocs
                        self.page.screenshot(path="debug_cribis_nuova_10b_mydocs.png")
                        print("📸 Screenshot MyDocs: debug_cribis_nuova_10b_mydocs.png")
                        
                        # Clicca sul PRIMO documento Gruppo Societario nella lista (più recente)
                        documento_trovato = False
                        try:
                            # Strategia: cerca la prima riga con "Gruppo Societario" e clicca sul link principale
                            print("🔍 Cerco il primo 'Gruppo Societario' nella lista...")
                            
                            # Trova tutti i link che contengono nomi di aziende (esclusi "condividi", "SALVA", etc)
                            links = self.page.locator('a').all()
                            
                            for i, link in enumerate(links):
                                try:
                                    if not link.is_visible():
                                        continue
                                    
                                    # Controlla se questo link è vicino a testo "Gruppo Societario"
                                    # e non è un bottone utility
                                    href = link.get_attribute('href') or ''
                                    text = link.inner_text().strip()
                                    
                                    # Salta link utility
                                    if text in ['condividi', 'SALVA', '', 'TUTTI I FILTRI', 'RICERCA PUNTUALE']:
                                        continue
                                    
                                    # Cerca link che sembrano nomi aziende (più di 3 caratteri, non numeri)
                                    if len(text) > 3 and not text.isdigit() and href:
                                        # Verifica se nelle vicinanze c'è "Gruppo Societario"
                                        parent = link
                                        for _ in range(3):
                                            try:
                                                parent = parent.locator('..')
                                                parent_text = parent.inner_text()
                                                if 'Gruppo Societario' in parent_text and 'RICHIESTO IL' in parent_text:
                                                    print(f"✅ Trovato documento: '{text}' (link #{i})")
                                                    
                                                    # Clicca sul link
                                                    link.click()
                                                    
                                                    # Aspetta caricamento
                                                    self.page.wait_for_load_state("domcontentloaded")
                                                    time.sleep(5)
                                                    
                                                    print("✅ Documento aperto")
                                                    documento_trovato = True
                                                    break  # Esci dal loop parent
                                            except:
                                                break
                                    
                                    if documento_trovato:
                                        break  # Esci dal loop links
                                        
                                except:
                                    continue
                            
                            if not documento_trovato:
                                print("❌ Nessun documento 'Gruppo Societario' trovato")
                            
                        except Exception as e:
                            print(f"⚠️ Errore apertura report da MyDocs: {str(e)}")
                    
                    # Salva screenshot della pagina finale
                    self.page.screenshot(path="debug_cribis_nuova_10_dopo_richiedi.png")
                    print("📸 Screenshot: debug_cribis_nuova_10_dopo_richiedi.png")
                    
                    print("✅ Navigazione al report completata")
                    return True
                else:
                    print("❌ Bottone 'Richiedi' nella card non trovato")
                
            except Exception as e:
                print(f"⚠️ Metodo ricerca card fallito: {str(e)}")
            
            # FALLBACK: Metodo vecchio se il nuovo non funziona
            print("🔄 Provo metodo alternativo...")
            
            # Cerca tutti i bottoni "Richiedi" visibili
            bottoni = self.page.query_selector_all('button:has-text("Richiedi"), a:has-text("Richiedi")')
            print(f"📋 Trovati {len(bottoni)} bottoni 'Richiedi'")
            
            for i, btn in enumerate(bottoni):
                try:
                    if not btn.is_visible():
                        continue
                    
                    # Controlla se nelle vicinanze c'è "Gruppo Societario"
                    parent = btn
                    for _ in range(5):
                        try:
                            parent = parent.query_selector('..')
                            if parent:
                                parent_text = parent.inner_text()
                                if 'Gruppo Societario' in parent_text or 'GRUPPO SOCIETARIO' in parent_text:
                                    print(f"✅ Bottone {i} contiene 'Gruppo Societario' nel parent")
                                    
                                    # Salva screenshot
                                    self.page.screenshot(path="debug_cribis_nuova_09_prima_richiedi.png")
                                    
                                    # Clicca con JavaScript
                                    print("🖱️ Clic con JavaScript...")
                                    self.page.evaluate("(element) => element.click()", btn)
                                    
                                    time.sleep(3)
                                    self.page.screenshot(path="debug_cribis_nuova_10_dopo_richiedi.png")
                                    
                                    print("✅ Richiesta Gruppo Societario avviata")
                                    return True
                        except:
                            break
                except:
                    continue
            
            print("❌ Nessun bottone 'Richiedi' per 'Gruppo Societario' trovato")
            print("ℹ️ Probabilmente la società non ha un gruppo societario disponibile")
            return "NO_GRUPPO_SOCIETARIO"  # Caso specifico: prodotto non disponibile
            
        except Exception as e:
            print(f"❌ Errore durante richiesta Gruppo Societario: {str(e)}")
            return False
    
    def aspetta_generazione_report(self, timeout=60):
        """
        Aspetta che il report venga generato
        
        Args:
            timeout (int): Tempo massimo di attesa in secondi
            
        Returns:
            bool: True se report generato
        """
        try:
            print(f"\n⏳ Attesa generazione report (max {timeout} secondi)...")
            
            start_time = time.time()
            
            # Possibili indicatori di completamento
            indicatori_completamento = [
                # Elementi che indicano che il report è pronto
                'text="Gruppo Societario"',
                '.corporate-structure',
                '.gruppo-societario',
                'text="Cod. Fisc."',
                'text="Italia"'
            ]
            
            # Possibili indicatori di caricamento
            indicatori_loading = [
                '.loading',
                '.spinner',
                'text="Caricamento"',
                'text="Generazione in corso"'
            ]
            
            while time.time() - start_time < timeout:
                # Controlla se ci sono indicatori di loading
                has_loading = False
                for sel in indicatori_loading:
                    try:
                        elementi = self.page.query_selector_all(sel)
                        if elementi:
                            has_loading = True
                            break
                    except:
                        continue
                
                # Controlla se il report è pronto
                report_ready = False
                for sel in indicatori_completamento:
                    try:
                        elementi = self.page.query_selector_all(sel)
                        if elementi and len(elementi) > 0:
                            report_ready = True
                            break
                    except:
                        continue
                
                elapsed = int(time.time() - start_time)
                
                if report_ready and not has_loading:
                    print(f"✅ Report generato in {elapsed} secondi")
                    break
                
                # Progress indicator
                if elapsed % 5 == 0:
                    print(f"   ⏳ {elapsed}/{timeout} secondi...")
                
                time.sleep(1)
            
            # Salva screenshot finale
            self.page.screenshot(path="debug_cribis_nuova_11_report_generato.png")
            print("📸 Screenshot: debug_cribis_nuova_11_report_generato.png")
            
            # Aspetta extra per sicurezza
            time.sleep(3)
            
            print("✅ Generazione completata")
            return True
            
        except Exception as e:
            print(f"❌ Errore durante attesa report: {str(e)}")
            return False
    
    def estrai_associate_italiane(self):
        """
        Estrae le società associate italiane con quota >50%
        
        RIUTILIZZA la stessa logica di cribis_playwright_base.py
        
        Returns:
            list: Lista di dict con dati delle associate
        """
        try:
            print("\n🌳 Analisi albero societario...")
            
            # Salva screenshot dell'albero
            self.page.screenshot(path="debug_cribis_nuova_12_albero.png")
            print("📸 Screenshot: debug_cribis_nuova_12_albero.png")
            
            associate = []
            
            # Prende tutto il testo della pagina
            body_text = self.page.locator("body").inner_text()
            
            # Salva testo per debug
            with open("debug_cribis_nuova_testo.txt", "w", encoding="utf-8") as f:
                f.write(body_text)
            print(f"💾 Testo salvato: debug_cribis_nuova_testo.txt ({len(body_text)} caratteri)")
            
            # Pattern migliorato: cattura Nome + CF + percentuale in un colpo solo
            # Formato: "NOME SOCIETA\nCod. Fisc.: 12345678901 - Italia\n...%"
            pattern_societa = r'(?:^|\n)(?:\d+(?:\.\d+)?\s+)?([A-Z][A-Z\s\.\-&]+?)\s*\n\s*Cod\.\s*Fisc\.\s*:\s*(\d{11})\s*-\s*Italia'
            
            matches = re.findall(pattern_societa, body_text, re.MULTILINE)
            print(f"🔍 Trovate {len(matches)} società italiane nel gruppo")
            
            # Dizionario CF -> Nome per lookup veloce
            cf_to_nome = {}
            for nome, cf in matches:
                nome_pulito = nome.strip()
                # Rimuove numeri iniziali e spazi extra
                nome_pulito = re.sub(r'^\d+(?:\.\d+)?\s+', '', nome_pulito).strip()
                cf_to_nome[cf] = nome_pulito
                print(f"   • {cf}: {nome_pulito}")
            
            # Estrae tutte le occorrenze di CF + percentuale
            # Pattern: "Cod. Fisc.: 12345678901 - Italia" seguito da percentuale
            cf_perc_pattern = r'Cod\.\s*Fisc\.\s*:\s*(\d{11})\s*-\s*Italia.*?(\d+(?:\.\d+)?)\s*%'
            cf_percentuali = re.findall(cf_perc_pattern, body_text, re.DOTALL)
            
            print(f"\n🔍 Trovate {len(cf_percentuali)} occorrenze CF + percentuale")
            
            # Processa ogni coppia (CF, percentuale)
            for cf, perc_str in cf_percentuali:
                try:
                    percentuale_numerica = float(perc_str)
                    
                    # Verifica quota rilevante (≥25% per PMI)
                    if percentuale_numerica < 25:
                        continue
                    
                    # Determina categoria
                    if percentuale_numerica > 50:
                        categoria = "collegata"
                    else:
                        categoria = "partner"
                    
                    # Recupera nome (se disponibile, altrimenti usa nome generico)
                    nome = cf_to_nome.get(cf, f"SOCIETÀ {cf}")
                    
                    percentuale_str = f"{percentuale_numerica}%"
                    
                    print(f"\n📊 Analisi CF {cf}:")
                    print(f"   Nome: {nome}")
                    print(f"   Italiana: ✅")
                    print(f"   Quota: {percentuale_str}")
                    print(f"   Categoria: {categoria}")
                    
                    # Evita duplicati
                    if not any(a["cf"] == cf for a in associate):
                        associate.append({
                            "ragione_sociale": nome.upper(),
                            "cf": cf,
                            "percentuale": percentuale_str,
                            "percentuale_numerica": percentuale_numerica,
                            "categoria": categoria
                        })
                        emoji = "🔗" if categoria == "collegata" else "🤝"
                        print(f"   ✅ {emoji} AGGIUNTA: {nome} ({categoria})")
                    else:
                        print(f"   ⚠️  Già presente, skip duplicato")
                
                except Exception as e:
                    print(f"   ❌ Errore processamento CF {cf}: {e}")
                    continue
            
            # Separa collegate e partner
            collegate = [a for a in associate if a.get('categoria') == 'collegata']
            partner = [a for a in associate if a.get('categoria') == 'partner']
            
            print(f"\n📊 RIEPILOGO GRUPPO SOCIETARIO:")
            print(f"   🔗 Società collegate (>50%): {len(collegate)}")
            for r in collegate:
                print(f"      • {r['ragione_sociale']} - {r['cf']} ({r['percentuale']})")
            
            print(f"   🤝 Società partner (25-50%): {len(partner)}")
            for r in partner:
                print(f"      • {r['ragione_sociale']} - {r['cf']} ({r['percentuale']})")
            
            print(f"   📊 Totale: {len(associate)} società italiane ≥25%")
                
            return associate
            
        except Exception as e:
            print(f"❌ Errore estrazione associate: {str(e)}")
            return []
    
    def cerca_associate(self, partita_iva):
        """
        Processo completo di ricerca delle società associate (NUOVA PROCEDURA)
        
        Args:
            partita_iva (str): P.IVA o CF da analizzare
            
        Returns:
            dict: Risultato con P.IVA richiesta e associate trovate
        """
        risultato = {
            "p_iva_richiesta": partita_iva,
            "associate_italiane_controllate": [],
            "errore": None
        }
        
        try:
            print(f"🚀 Avvio NUOVA ricerca associate per: {partita_iva}")
            print("="*60)
            
            # 1. Login (solo se non già loggato)
            if not self.page or not self.page.url or "cribisx.com" not in self.page.url:
                print("🔐 Effettuo login...")
                if not self.login():
                    risultato["errore"] = "Login fallito"
                    
                    # Invia alert email
                    if EMAIL_ALERTS_ENABLED:
                        try:
                            print("📧 Invio alert email per errore login Cribis...")
                            alert_cribis_error(
                                partita_iva=partita_iva,
                                errore="Login fallito - Possibile cambio interfaccia Cribis X",
                                fase="Login",
                                screenshot_path="debug_cribis_nuova_01_login_page.png" if os.path.exists("debug_cribis_nuova_01_login_page.png") else None
                            )
                        except Exception as email_err:
                            print(f"⚠️ Errore invio alert email: {email_err}")
                    
                    return risultato
            else:
                print("✅ Già loggato, skip login")
            
            # 2. Cerca nel campo principale
            if not self.cerca_nel_campo_principale(partita_iva):
                risultato["errore"] = "Ricerca nel campo principale fallita"
                
                # Invia alert email
                if EMAIL_ALERTS_ENABLED:
                    try:
                        print("📧 Invio alert email per errore ricerca Cribis...")
                        alert_cribis_error(
                            partita_iva=partita_iva,
                            errore="Campo ricerca principale non trovato - Possibile cambio interfaccia",
                            fase="Ricerca P.IVA",
                            screenshot_path="debug_cribis_nuova_02_dopo_login.png" if os.path.exists("debug_cribis_nuova_02_dopo_login.png") else None
                        )
                    except Exception as email_err:
                        print(f"⚠️ Errore invio alert email: {email_err}")
                
                return risultato
            
            # 3. Clicca sul NOME dell'azienda (primo risultato)
            if not self.clicca_nome_primo_risultato():
                risultato["errore"] = "Click nome azienda fallito"
                
                # Invia alert email
                if EMAIL_ALERTS_ENABLED:
                    try:
                        print("📧 Invio alert email per errore click nome...")
                        alert_cribis_error(
                            partita_iva=partita_iva,
                            errore="Nome azienda nel primo risultato non trovato - Layout risultati cambiato",
                            fase="Selezione Risultato",
                            screenshot_path="debug_cribis_nuova_04_risultati_cerca.png" if os.path.exists("debug_cribis_nuova_04_risultati_cerca.png") else None
                        )
                    except Exception as email_err:
                        print(f"⚠️ Errore invio alert email: {email_err}")
                
                return risultato
            
            # 4. Nella pagina dettaglio, clicca "Tutti i prodotti CRIBIS X"
            if not self.clicca_tutti_prodotti_cribis_dettaglio():
                risultato["errore"] = "Click 'Tutti i prodotti CRIBIS X' fallito"
                return risultato
            
            # 5. Richiedi Gruppo Societario (si apre in nuova tab e aspetta caricamento)
            gruppo_result = self.richiedi_gruppo_societario()
            if gruppo_result == "NO_GRUPPO_SOCIETARIO":
                # Caso specifico: prodotto non disponibile per questa società
                risultato["errore"] = None
                risultato["associate_italiane_controllate"] = []
                risultato["messaggio"] = "La società non ha collegate"
                print("ℹ️ Nessun gruppo societario disponibile per questa P.IVA")
                return risultato
            elif not gruppo_result:
                # Errore tecnico generico
                risultato["errore"] = "Richiesta Gruppo Societario fallita"
                return risultato
            
            # 6. Estrai associate (il report è già caricato nella nuova tab)
            associate = self.estrai_associate_italiane()
            risultato["associate_italiane_controllate"] = associate
            
            print("\n" + "="*60)
            print(f"✅ Ricerca completata: {len(associate)} associate trovate")
            return risultato
            
        except Exception as e:
            print(f"❌ Errore generale ricerca associate: {str(e)}")
            risultato["errore"] = str(e)
            
            # Invia alert per errore generico non gestito
            if EMAIL_ALERTS_ENABLED:
                try:
                    print("📧 Invio alert email per errore generico Cribis...")
                    alert_cribis_error(
                        partita_iva=partita_iva,
                        errore=f"Errore non gestito: {str(e)}",
                        fase="Errore Generico",
                        screenshot_path="debug_cribis_nuova_12_albero.png" if os.path.exists("debug_cribis_nuova_12_albero.png") else None
                    )
                except Exception as email_err:
                    print(f"⚠️ Errore invio alert email: {email_err}")
            
            return risultato
    
    def scarica_company_card_completa(self, codice_fiscale: str) -> dict:
        """
        Apre la Company Card Completa della società richiesta e:
        - estrae i dati dalla pagina (HTML-first)
        - prova a scaricare anche il PDF tramite il link "Scarica" in alto a destra
        
        Args:
            codice_fiscale (str): CF dell'azienda
            
        Returns:
            dict: Dati estratti dalla pagina web
        """
        try:
            print(f"\n{'='*70}")
            print(f"📊 Estrazione dati web per: {codice_fiscale}")
            print(f"{'='*70}\n")
            
            # STEP 0: Assicurati di essere sulla pagina principale
            print("🔄 STEP 0: Torna alla pagina principale...")
            pages = self.browser.contexts[0].pages
            if len(pages) > 1:
                for page in pages[1:]:
                    page.close()
                self.page = pages[0]
                print(f"   ✅ Chiuse {len(pages)-1} tab extra")
            
            if "Home" not in self.page.url:
                self.page.goto(f"{self.base_url}/#Home/Index", wait_until="networkidle")
                self.page.wait_for_timeout(2000)
            
            print("   ✅ Sulla pagina principale\n")
            
            # STEP 1: Ricerca CF
            print("🔍 STEP 1: Ricerca CF...")
            campo_ricerca = self.page.locator('input[title="Inserisci i termini da cercare"]')
            campo_ricerca.fill(codice_fiscale)
            self.page.keyboard.press("Enter")
            self.page.wait_for_timeout(2000)
            
            # STEP 2: Click sul nome azienda (primo risultato)
            print("🎯 STEP 2: Click su nome azienda...")
            nome_azienda = self.page.locator('div[class*="result"] a:first-of-type').first
            
            if not nome_azienda.is_visible():
                return {
                    "errore": "Azienda non trovata nei risultati",
                    "cf": codice_fiscale,
                    "stato_dati": "errore"
                }
            
            nome_text = nome_azienda.inner_text()
            print(f"✅ Trovata: {nome_text}")
            nome_azienda.click()
            self.page.wait_for_timeout(3000)
            
            # STEP 3: Apri Company Card Completa (Richiedi)
            print("📄 STEP 3: Apro Company Card Completa (Richiedi)...")
            print(f"   📍 URL corrente prima modale: {self.page.url}")
            
            if not self.clicca_tutti_prodotti_cribis_dettaglio():
                print("⚠️  Impossibile aprire 'Tutti i prodotti' - provo comunque estrazione dalla pagina dettaglio")
            else:
                print("   ✅ Modale 'Tutti i prodotti' aperta")
                # Cerca nella modale la card "Company Card Completa" e clicca "Richiedi"
                try:
                    print("   🔎 STEP 3.1: Cerco card 'Company Card Completa' nella modale...")
                    
                    # Prova diversi selettori per la modale
                    modale = None
                    for modal_sel in ['.modal-dialog', '.modal-content', '.modal', '[role="dialog"]']:
                        try:
                            modale = self.page.locator(modal_sel).first
                            if modale.count() > 0:
                                print(f"   ✅ Modale trovata con selettore: {modal_sel}")
                                break
                        except Exception as e:
                            print(f"   ⚠️  Selettore {modal_sel} non funziona: {e}")
                            continue
                    
                    if not modale or modale.count() == 0:
                        print("   ❌ Nessuna modale trovata!")
                        # Prova a cercare direttamente nella pagina
                        print("   🔍 Provo a cercare 'Company Card Completa' direttamente nella pagina...")
                        modale = None  # Forza ricerca nella pagina principale
                    else:
                        # scroll in fondo
                        try:
                            print("   📜 Scrolling modale verso il basso...")
                            modale.evaluate("element => element.scrollTop = element.scrollHeight")
                            time.sleep(1)
                        except Exception as e:
                            print(f"   ⚠️  Errore scroll modale: {e}")
                        
                        # trova bottone Richiedi all'interno della card
                        print("   🔎 STEP 3.2: Cerco testo 'Company Card Completa'...")
                        card_sel = None
                        try:
                            # Prova diversi selettori per il testo
                            for text_sel in [
                                "text=Company Card Completa",
                                "text=COMPANY CARD COMPLETA",
                                "text=Company Card",
                                '.card:has-text("Company Card Completa")',
                                '*:has-text("Company Card Completa")'
                            ]:
                                try:
                                    card_sel = modale.locator(text_sel).first if modale else self.page.locator(text_sel).first
                                    if card_sel.count() > 0 and card_sel.is_visible():
                                        print(f"   ✅ Card trovata con: {text_sel}")
                                        break
                                except Exception:
                                    continue
                            
                            if not card_sel or card_sel.count() == 0:
                                print("   ❌ Card 'Company Card Completa' non trovata nella modale!")
                                # Screenshot debug
                                try:
                                    self.page.screenshot(path=f"debug_card_non_trovata_{codice_fiscale}.png", full_page=True)
                                    print(f"   📸 Screenshot salvato: debug_card_non_trovata_{codice_fiscale}.png")
                                except Exception:
                                    pass
                        except Exception as card_err:
                            print(f"   ⚠️  Errore ricerca card: {card_err}")
                            card_sel = None
                        
                        # Se la card è stata trovata, cerca Richiedi risalendo dalla card
                        if card_sel and card_sel.count() > 0:
                            print("   🔎 STEP 3.3: Cerco bottone 'Richiedi' nella card...")
                            parent = card_sel
                            bottone_trovato = False
                            
                            for i in range(8):
                                try:
                                    print(f"   🔄 Tentativo {i+1}/8: risalgo al parent...")
                                    parent = parent.locator('..')
                                    
                                    # Prova diversi selettori per il bottone
                                    selettori_btn = [
                                        'button:has-text("Richiedi")',
                                        'a:has-text("Richiedi")',
                                        'button.btn:has-text("Richiedi")',
                                        'a.btn:has-text("Richiedi")',
                                        '*[role="button"]:has-text("Richiedi")',
                                        '*:has-text("Richiedi")'
                                    ]
                                    
                                    btns = []
                                    for btn_sel in selettori_btn:
                                        try:
                                            btns_found = parent.locator(btn_sel).all()
                                            if btns_found:
                                                btns.extend(btns_found)
                                                print(f"   ✅ Trovati {len(btns_found)} bottoni con selettore: {btn_sel}")
                                        except Exception:
                                            continue
                                    
                                    if btns:
                                        print(f"   ✅ Totale {len(btns)} bottoni 'Richiedi' trovati!")
                                        try:
                                            print("   🖱️  STEP 3.4: Click su 'Richiedi' (attendo nuova tab, timeout 3min)...")
                                            with self.page.context.expect_page(timeout=180000) as popup_info:
                                                btns[0].click(force=True)
                                            print("   ✅ Nuova tab rilevata!")
                                            nuova_tab = popup_info.value
                                            self.page = nuova_tab
                                            print(f"   📍 URL nuova tab: {self.page.url}")
                                            self.page.wait_for_load_state("domcontentloaded")
                                            print("   ✅ Pagina caricata, sono sulla Company Card Completa!")
                                            bottone_trovato = True
                                            break
                                        except Exception as e:
                                            print(f"   ❌ Errore click o attesa nuova tab: {e}")
                                            import traceback
                                            traceback.print_exc()
                                    else:
                                        print(f"   ⚠️  Nessun bottone 'Richiedi' trovato a livello {i+1}")
                                except Exception as e:
                                    print(f"   ⚠️  Errore livello {i+1}: {e}")
                                    break
                            
                            if not bottone_trovato:
                                print("   ⚠️  Bottone 'Richiedi' non trovato risalendo dalla card, provo ricerca diretta...")
                                # Fallback: cerca "Richiedi" direttamente nella modale o pagina
                                try:
                                    search_area = modale if modale and modale.count() > 0 else self.page
                                    selettori_diretti = [
                                        'button:has-text("Richiedi")',
                                        'a:has-text("Richiedi")',
                                        'button:has-text("RICHIEDI")',
                                        'a:has-text("RICHIEDI")',
                                        '*[role="button"]:has-text("Richiedi")'
                                    ]
                                    for btn_sel_diretto in selettori_diretti:
                                        try:
                                            btns_diretti = search_area.locator(btn_sel_diretto).all()
                                            if btns_diretti:
                                                print(f"   ✅ Trovato bottone 'Richiedi' con ricerca diretta: {btn_sel_diretto}")
                                                try:
                                                    print("   🖱️  Click su 'Richiedi' (ricerca diretta, attendo nuova tab)...")
                                                    with self.page.context.expect_page(timeout=180000) as popup_info:
                                                        btns_diretti[0].click(force=True)
                                                    print("   ✅ Nuova tab rilevata!")
                                                    nuova_tab = popup_info.value
                                                    self.page = nuova_tab
                                                    print(f"   📍 URL nuova tab: {self.page.url}")
                                                    self.page.wait_for_load_state("domcontentloaded")
                                                    print("   ✅ Pagina caricata, sono sulla Company Card Completa!")
                                                    bottone_trovato = True
                                                    break
                                                except Exception as e:
                                                    print(f"   ⚠️  Errore click (ricerca diretta): {e}")
                                                    continue
                                        except Exception:
                                            continue
                                except Exception as e:
                                    print(f"   ⚠️  Errore ricerca diretta: {e}")
                                
                                if not bottone_trovato:
                                    print("   ❌ Bottone 'Richiedi' NON TROVATO dopo tutti i tentativi!")
                                    # Screenshot finale
                                    try:
                                        self.page.screenshot(path=f"debug_richiedi_non_trovato_{codice_fiscale}.png", full_page=True)
                                        print(f"   📸 Screenshot salvato: debug_richiedi_non_trovato_{codice_fiscale}.png")
                                    except Exception:
                                        pass
                        else:
                            # Card non trovata: cerca Richiedi direttamente nella modale/pagina
                            print("   ⚠️  Card non trovata, provo ricerca diretta di 'Richiedi'...")
                            bottone_trovato = False
                            try:
                                search_area = modale if modale and modale.count() > 0 else self.page
                                selettori_diretti = [
                                    'button:has-text("Richiedi")',
                                    'a:has-text("Richiedi")',
                                    'button:has-text("RICHIEDI")',
                                    'a:has-text("RICHIEDI")',
                                    '*[role="button"]:has-text("Richiedi")'
                                ]
                                for btn_sel_diretto in selettori_diretti:
                                    try:
                                        btns_diretti = search_area.locator(btn_sel_diretto).all()
                                        if btns_diretti:
                                            print(f"   ✅ Trovato bottone 'Richiedi' (senza card): {btn_sel_diretto}")
                                            try:
                                                print("   🖱️  Click su 'Richiedi' (senza card, attendo nuova tab)...")
                                                with self.page.context.expect_page(timeout=180000) as popup_info:
                                                    btns_diretti[0].click(force=True)
                                                print("   ✅ Nuova tab rilevata!")
                                                nuova_tab = popup_info.value
                                                self.page = nuova_tab
                                                print(f"   📍 URL nuova tab: {self.page.url}")
                                                self.page.wait_for_load_state("domcontentloaded")
                                                print("   ✅ Pagina caricata, sono sulla Company Card Completa!")
                                                bottone_trovato = True
                                                break
                                            except Exception as e:
                                                print(f"   ⚠️  Errore click (senza card): {e}")
                                                continue
                                    except Exception:
                                        continue
                                
                                if not bottone_trovato:
                                    print("   ❌ Bottone 'Richiedi' non trovato nemmeno con ricerca diretta!")
                            except Exception as e:
                                print(f"   ⚠️  Errore ricerca diretta (senza card): {e}")
                                        
                except Exception as e:
                    print(f"   ❌ ERRORE nella selezione Company Card Completa: {e}")
                    import traceback
                    traceback.print_exc()
            
            print(f"   📍 URL dopo STEP 3: {self.page.url}")

            # STEP 4: Estrai dati dalla pagina attuale (Company Card se aperta, altrimenti dettaglio)
            print("📊 STEP 4: Estrazione dati dalla pagina web...")
            
            # Cerca sezione dati finanziari nella pagina
            html_content = self.page.content()
            
            # Estrai dati usando regex dalla pagina HTML
            dati_estratti = self._estrai_dati_finanziari_da_pagina(html_content, codice_fiscale)

            # STEP 5: Prova download PDF dalla pagina corrente
            try:
                pdf_res = self.scarica_pdf_company_card_corrente(codice_fiscale)
                if pdf_res.get("success"):
                    dati_estratti["pdf_filename"] = pdf_res.get("filename")
                else:
                    dati_estratti["pdf_note"] = pdf_res.get("reason")
            except Exception as e:
                dati_estratti["pdf_note"] = f"Errore download PDF: {e}"
            
            print(f"✅ Dati estratti: {dati_estratti}")
            
            return dati_estratti
            
        except Exception as e:
            print(f"❌ Errore estrazione dati web: {e}")
            return {
                "errore": f"Errore estrazione: {str(e)}",
                "cf": codice_fiscale,
                "stato_dati": "errore"
            }
    
    def _estrai_dati_finanziari_da_pagina(self, html_content: str, cf: str) -> dict:
        """
        Estrae dati finanziari direttamente dal contenuto HTML della pagina.
        
        Args:
            html_content (str): Contenuto HTML della pagina
            cf (str): Codice fiscale per debug
            
        Returns:
            dict: Dati finanziari estratti
        """
        try:
            # Cerca pattern comuni per dati finanziari
            personale = None
            fatturato = None
            attivo = None
            
            # Pattern per personale (ULA, dipendenti, etc.)
            personale_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:ULA|dipendenti|personale)',
                r'personale[:\s]*(\d+(?:\.\d+)?)',
                r'dipendenti[:\s]*(\d+(?:\.\d+)?)'
            ]
            
            for pattern in personale_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    personale = float(match.group(1).replace('.', '').replace(',', '.'))
                    break
            
            # Pattern per fatturato
            fatturato_patterns = [
                r'fatturato[:\s]*(\d+(?:\.\d+){0,2}(?:,\d+)?)',
                r'ricavi[:\s]*(\d+(?:\.\d+){0,2}(?:,\d+)?)',
                r'(\d+(?:\.\d+){0,2}(?:,\d+)?)\s*(?:€|euro)'
            ]
            
            for pattern in fatturato_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    valore_str = match.group(1).replace('.', '').replace(',', '.')
                    fatturato = float(valore_str)
                    break
            
            # Pattern per attivo (bilancio)
            attivo_patterns = [
                r'attivo[:\s]*(\d+(?:\.\d+){0,2}(?:,\d+)?)',
                r'totale\s*attivo[:\s]*(\d+(?:\.\d+){0,2}(?:,\d+)?)',
                r'bilancio[:\s]*(\d+(?:\.\d+){0,2}(?:,\d+)?)'
            ]
            
            for pattern in attivo_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    valore_str = match.group(1).replace('.', '').replace(',', '.')
                    attivo = float(valore_str)
                    break
            
            # Determina stato dati
            if personale is not None and fatturato is not None and attivo is not None:
                stato_dati = "completi"
            elif personale is not None or fatturato is not None or attivo is not None:
                stato_dati = "parziali"
            else:
                stato_dati = "assenti"
            
            return {
                "cf": cf,
                "personale": personale,
                "fatturato": fatturato,
                "attivo": attivo,
                "anno_riferimento": "N/D",
                "stato_dati": stato_dati,
                "fonte": "pagina_web"
            }
            
        except Exception as e:
            print(f"❌ Errore parsing HTML: {e}")
            return {
                "cf": cf,
                "personale": None,
                "fatturato": None,
                "attivo": None,
                "anno_riferimento": "N/D",
                "stato_dati": "errore",
                "fonte": "pagina_web"
            }

    def scarica_pdf_company_card_corrente(self, codice_fiscale: str) -> dict:
        """
        Scarica il PDF della Company Card Completa dalla pagina corrente
        quando è presente il link "Scarica" in alto a destra.

        Nota: questa funzione assume che ci si trovi già nella pagina
        della Company Card Completa. Se il link non è presente, restituisce
        un risultato non bloccante con messaggio esplicativo.

        Args:
            codice_fiscale (str): CF/P.IVA per nominare il file

        Returns:
            dict: { success, path, filename, reason }
        """
        try:
            print(f"⬇️  STEP 5: Tentativo download PDF per {codice_fiscale}...")
            print(f"   📍 URL pagina corrente: {self.page.url}")
            
            # Assicura cartella downloads/
            downloads_dir = os.path.join(os.getcwd(), 'downloads')
            os.makedirs(downloads_dir, exist_ok=True)

            # Costruisci nome file
            from datetime import datetime
            data_str = datetime.now().strftime('%Y%m%d')
            filename = f"CompanyCard_{codice_fiscale}_{data_str}.pdf"
            target_path = os.path.join(downloads_dir, filename)

            # Possibili selettori del link "Scarica" (header della Company Card)
            possibili_scarica = [
                # Struttura precisa indicata: ul.list.operations > li:nth-child(2) > a[href*='/Storage/Pdf/']
                "ul.list.operations li:nth-child(2) a[href*='/Storage/Pdf/']",
                # Varianti nell'header destro
                "div.col-md-4.align-right.upcas ul.list.operations li:nth-child(2) a[href*='/Storage/Pdf/']",
                # Generici robusti
                'a:has-text("Scarica")',
                'a.label-silver.align-right:has-text("Scarica")',
                "a[href*='/Storage/Pdf/']",
                'text=SCARICA',
                # XPATH: primo <a> che contiene esattamente il testo Scarica
                "xpath=(//a[normalize-space(text())='Scarica'])[1]",
                # XPATH: risalita dal testo 'Scarica' all'antenato <a>
                "xpath=(//*/text()[contains(., 'Scarica')]/ancestor::a)[1]"
            ]

            link = None
            selettore_usato = None
            print(f"   🔎 Provo {len(possibili_scarica)} selettori per trovare link 'Scarica'...")
            
            for idx, sel in enumerate(possibili_scarica, 1):
                try:
                    print(f"   🔄 Tentativo {idx}/{len(possibili_scarica)}: {sel[:60]}...")
                    link = self.page.wait_for_selector(sel, timeout=4000)
                    if link:
                        is_vis = link.is_visible()
                        print(f"      {'✅ Link trovato e visibile!' if is_vis else '⚠️  Link trovato ma non visibile'}")
                        if is_vis:
                            selettore_usato = sel
                            break
                        else:
                            print(f"      ⚠️  Elemento non visibile, provo prossimo selettore...")
                            link = None
                except Exception as e:
                    print(f"      ❌ Non trovato: {str(e)[:80]}")
                    continue

            if not link:
                print("   ⚠️  Selettori principali falliti, ultimo tentativo con get_by_text...")
                # Ultimo tentativo: cerca un elemento con testo 'Scarica' e risali al link più vicino
                try:
                    txt = self.page.get_by_text("Scarica", exact=False).first
                    if txt:
                        is_vis_txt = txt.is_visible()
                        print(f"   {'✅ Testo Scarica trovato' if is_vis_txt else '⚠️  Testo Scarica trovato ma non visibile'}")
                        if is_vis_txt:
                            candidate = txt.locator("xpath=ancestor::a[1]")
                            if candidate:
                                is_vis_cand = candidate.is_visible()
                                print(f"   {'✅ Link candidato trovato!' if is_vis_cand else '⚠️  Link candidato non visibile'}")
                                if is_vis_cand:
                                    link = candidate
                                    selettore_usato = "get_by_text + ancestor::a"
                except Exception as e:
                    print(f"   ❌ Ultimo tentativo fallito: {e}")

            if not link:
                print("   ❌ Link 'Scarica' NON TROVATO nella pagina!")
                print("   📸 Faccio screenshot per debug...")
                try:
                    debug_screenshot = f"debug_scarica_non_trovato_{codice_fiscale}.png"
                    self.page.screenshot(path=debug_screenshot, full_page=True)
                    print(f"   📸 Screenshot salvato: {debug_screenshot}")
                    
                    # Prova anche a vedere tutti i link nella pagina
                    try:
                        all_links = self.page.locator('a').all()
                        print(f"   🔗 Trovati {len(all_links)} link totali nella pagina")
                        scarica_texts = []
                        for i, lnk in enumerate(all_links[:20]):  # Primi 20
                            try:
                                txt = lnk.inner_text().strip()
                                if 'scarica' in txt.lower():
                                    href = lnk.get_attribute('href') or 'N/A'
                                    scarica_texts.append(f"   Link {i}: '{txt}' -> href={href[:60]}")
                            except:
                                pass
                        if scarica_texts:
                            print("   🔍 Link che contengono 'scarica':")
                            for s in scarica_texts:
                                print(s)
                        else:
                            print("   ⚠️  Nessun link con testo 'scarica' trovato nei primi 20 link")
                    except Exception as e:
                        print(f"   ⚠️  Errore analisi link: {e}")
                except Exception as e:
                    print(f"   ⚠️  Errore screenshot: {e}")
                    
                return {
                    "success": False,
                    "reason": "Link 'Scarica' non trovato nella pagina",
                    "path": None,
                    "filename": None
                }
            
            print(f"   ✅ Link 'Scarica' trovato! (Selettore: {selettore_usato})")
            try:
                href_link = link.get_attribute('href')
                print(f"   🔗 href del link: {href_link[:100] if href_link else 'N/A'}")
            except:
                pass

            # Attendi evento download e clicca (timeout alto per PDF grandi)
            print("   🖱️  Click su link 'Scarica' (attendo evento download, timeout 2 minuti)...")
            try:
                with self.page.expect_download(timeout=120000) as download_info:
                    link.click(force=True)
                download = download_info.value
                print("   ✅ Evento download ricevuto!")

                # Salva su percorso target
                print(f"   💾 Salvo PDF in: {target_path}")
                download.save_as(target_path)
                
                # Verifica che il file esista
                if os.path.exists(target_path):
                    file_size = os.path.getsize(target_path)
                    print(f"   ✅ PDF salvato con successo! Dimensione: {file_size:,} bytes ({file_size/1024:.1f} KB)")
                else:
                    print(f"   ⚠️  File non trovato dopo save_as!")

                return {
                    "success": True,
                    "path": target_path,
                    "filename": filename
                }
            except Exception as click_err:
                print(f"   ❌ Errore durante click o download: {click_err}")
                import traceback
                traceback.print_exc()
                raise

        except PlaywrightTimeout:
            print("   ❌ TIMEOUT: Download non completato entro 2 minuti")
            return {
                "success": False,
                "reason": "Timeout download PDF",
                "path": None,
                "filename": None
            }
        except Exception as e:
            print(f"   ❌ ERRORE download PDF: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "reason": f"Errore download: {e}",
                "path": None,
                "filename": None
            }


# ============================================================================
# FUNZIONI DI TEST
# ============================================================================

def test_cerca_associate():
    """Test della funzione cerca_associate"""
    test_piva = "04143180984"  # POZZI MILANO SPA
    
    print(f"🧪 Test ricerca associate per P.IVA: {test_piva}")
    print("="*60)
    
    risultato = cerca_associate_nuova_procedura(test_piva, headless=False)
    
    print("\n" + "="*60)
    print("📊 RISULTATO FINALE:")
    print("="*60)
    print(json.dumps(risultato, indent=2, ensure_ascii=False))
    
    # Mostra risultati in formato leggibile
    if risultato.get("errore"):
        print(f"\n❌ ERRORE: {risultato['errore']}")
    elif risultato["associate_italiane_controllate"]:
        print("\n✅ Aziende collegate con quota > 50%:")
        for r in risultato["associate_italiane_controllate"]:
            print(f"   • {r['ragione_sociale']} – CF: {r['cf']} ({r['percentuale']})")
    else:
        print("\nℹ️  Nessuna associata >50% trovata")
    
    print("\n📸 Screenshot salvati: debug_cribis_nuova_*.png")
    print("💾 Testo salvato: debug_cribis_nuova_testo.txt")
