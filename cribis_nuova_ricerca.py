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
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


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
        self.password = "26082025__Pigreco_"
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
            
            # Selettore SPECIFICO fornito dall'utente
            selettori_campo = [
                'input[title="Inserisci i termini da cercare"]',  # SELETTORE PRINCIPALE
                'input[placeholder*="nome, codice cliente, partita iva"]',
                'input[placeholder*="Cerca per nome"]',
                'header input[type="text"]',
                '.search-input',
                'input.form-control[type="text"]'
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
                print("❌ Campo ricerca principale non trovato")
                return False
            
            # Inserisci P.IVA
            print(f"📝 Inserimento P.IVA: {partita_iva}")
            campo_ricerca.fill(partita_iva)
            
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
            return False
            
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
            
            # Pattern per codici fiscali italiani (11 cifre)
            cf_pattern = r'Cod\.\s*Fisc\.\s*:\s*(\d{11})'
            codici_fiscali = re.findall(cf_pattern, body_text)
            
            print(f"🔍 Trovati {len(codici_fiscali)} codici fiscali: {codici_fiscali}")
            
            # Per ogni codice fiscale, cerca il contesto
            for cf in codici_fiscali:
                try:
                    # Trova elementi che contengono questo CF
                    cf_elements = self.page.locator(f"*:has-text('{cf}')").all()
                    
                    for element in cf_elements:
                        try:
                            element_text = element.inner_text()
                            
                            # DEVE contenere "Italia" per essere italiana
                            if "Italia" not in element_text:
                                continue
                            
                            # Estrae nome società (riga prima di "Cod. Fisc.")
                            lines = element_text.split('\n')
                            nome = "SOCIETÀ NON IDENTIFICATA"
                            
                            for i, line in enumerate(lines):
                                if "Cod. Fisc." in line and i > 0:
                                    nome = lines[i-1].strip()
                                    # Rimuove numeri iniziali (es: "1 MARTENS ITALIA SRL" → "MARTENS ITALIA SRL")
                                    nome = re.sub(r'^\d+\.?\d*\s*', '', nome)
                                    break
                            
                            # Cerca percentuali nel testo (formato X% o XX.X%)
                            percentuali = re.findall(r'(\d+(?:\.\d+)?)\s*%', element_text)
                            
                            # Verifica quota maggioritaria (>50%)
                            has_majority = False
                            percentuale_str = "N/A"
                            
                            for p in percentuali:
                                try:
                                    perc_val = float(p)
                                    if perc_val > 50:
                                        has_majority = True
                                        percentuale_str = f"{perc_val}%"
                                        break
                                except:
                                    continue
                            
                            print(f"\n📊 Analisi CF {cf}:")
                            print(f"   Nome: {nome}")
                            print(f"   Italiana: ✅")
                            print(f"   Maggioritaria: {'✅' if has_majority else '❌'} ({percentuale_str})")
                            
                            # Aggiunge se soddisfa tutti i criteri
                            if has_majority:
                                # Evita duplicati
                                if not any(a["cf"] == cf for a in associate):
                                    associate.append({
                                        "ragione_sociale": nome.upper(),
                                        "cf": cf,
                                        "percentuale": percentuale_str
                                    })
                                    print(f"   ✅ AGGIUNTA: {nome}")
                            
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    continue
            
            print(f"\n📊 Totale associate italiane >50%: {len(associate)}")
            for r in associate:
                print(f"   • {r['ragione_sociale']} - {r['cf']} ({r['percentuale']})")
                
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
            
            # 1. Login
            if not self.login():
                risultato["errore"] = "Login fallito"
                return risultato
            
            # 2. Cerca nel campo principale
            if not self.cerca_nel_campo_principale(partita_iva):
                risultato["errore"] = "Ricerca nel campo principale fallita"
                return risultato
            
            # 3. Clicca sul NOME dell'azienda (primo risultato)
            if not self.clicca_nome_primo_risultato():
                risultato["errore"] = "Click nome azienda fallito"
                return risultato
            
            # 4. Nella pagina dettaglio, clicca "Tutti i prodotti CRIBIS X"
            if not self.clicca_tutti_prodotti_cribis_dettaglio():
                risultato["errore"] = "Click 'Tutti i prodotti CRIBIS X' fallito"
                return risultato
            
            # 5. Richiedi Gruppo Societario (si apre in nuova tab e aspetta caricamento)
            if not self.richiedi_gruppo_societario():
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
            return risultato


# Funzione wrapper per usare con il sistema esistente
def cerca_associate_nuova_procedura(partita_iva, headless=False):
    """
    Wrapper per integrazione con sistema esistente
    
    Args:
        partita_iva (str): P.IVA da analizzare
        headless (bool): Browser in background
        
    Returns:
        dict: Risultato ricerca associate
    """
    with CribisNuovaRicerca(headless=headless) as cribis:
        return cribis.cerca_associate(partita_iva)


# Test standalone
if __name__ == "__main__":
    print("🧪 TEST CRIBIS X - NUOVA PROCEDURA")
    print("="*60)
    print("\nProcedura:")
    print("1. Login")
    print("2. Cerca P.IVA nel campo principale")
    print("3. Premi INVIO")
    print("4. Clicca sul NOME dell'azienda (primo risultato)")
    print("5. Pagina dettaglio → Clicca 'Tutti i prodotti CRIBIS X'")
    print("6. Clicca 'Richiedi' sotto 'Gruppo Societario'")
    print("7. Aspetta generazione report")
    print("8. Estrai associate italiane >50%")
    print("="*60)
    
    # Test con P.IVA di esempio
    test_piva = "04703370165"
    
    print(f"\n🎯 Test con P.IVA: {test_piva}")
    print("⚠️  Browser visibile per debug (headless=False)\n")
    
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

