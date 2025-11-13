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
        # Credenziali Cribis: priorità a variabili d'ambiente, poi fallback
        self.username = os.environ.get('CRIBIS_USERNAME', 'CC838673')
        self.password = os.environ.get('CRIBIS_PASSWORD', '27_10_2025__Pigreco_')
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
    
    def _check_and_handle_session_expired(self):
        """
        Verifica se la sessione è scaduta e, in caso, esegue re-login.
        Controlla anche se il campo di ricerca è accessibile.
        
        Returns:
            bool: True se la sessione è valida (o è stato fatto re-login con successo)
        """
        current_url = self.page.url
        
        # Verifica 1: URL indica sessione scaduta?
        if "sessionExpired" in current_url or "LogOn" in current_url:
            print("⚠️  Sessione scaduta rilevata da URL, eseguo re-login automatico...")
            try:
                if not self.login():
                    print("❌ Re-login automatico fallito")
                    return False
                print("✅ Re-login automatico completato con successo")
                return True
            except Exception as e:
                print(f"❌ Errore durante re-login automatico: {e}")
                return False
        
        # Verifica 2: Siamo sulla Home page?
        if "Home" not in current_url:
            print(f"⚠️  Non sono sulla Home (URL: {current_url}), navigo...")
            try:
                self.page.goto(f"{self.base_url}/#Home/Index", wait_until="domcontentloaded")
                time.sleep(2)
                # Ricontrolla URL dopo navigazione
                if "sessionExpired" in self.page.url or "LogOn" in self.page.url:
                    print("⚠️  Redirect a sessione scaduta, eseguo re-login...")
                    if not self.login():
                        return False
                    return True
            except Exception as e:
                print(f"⚠️  Errore navigazione Home: {e}")
                return False
        
        # Verifica 3: Il campo di ricerca è presente?
        try:
            campo = self.page.query_selector('input[title="Inserisci i termini da cercare"]')
            if not campo:
                print("⚠️  Campo ricerca non trovato, possibile sessione invalida, tento re-login...")
                if not self.login():
                    return False
                return True
        except Exception:
            pass
        
        return True
    
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
            time.sleep(5)  # Aumentato timeout per Render
            
            current_url = self.page.url
            print(f"📍 URL dopo login: {current_url}")
            
            # Salva screenshot dopo login
            self._screenshot("debug_cribis_nuova_02_dopo_login.png", "Dopo login")
            
            # VERIFICA se il login è effettivamente riuscito
            # Controlla URL o presenza di elementi tipici della dashboard
            login_riuscito = False
            
            # Verifica 1: URL deve cambiare e non essere più su LogOn
            if "LogOn" not in current_url and ("Home" in current_url or "Dashboard" in current_url or "#" in current_url):
                login_riuscito = True
                print("✅ Login verificato: URL cambiato correttamente")
            
            # Verifica 2: Cerca elementi tipici della pagina dopo login (menu, ricerca, ecc.)
            if not login_riuscito:
                try:
                    # Cerca elementi che sono presenti solo dopo login
                    elementi_post_login = [
                        'input[placeholder*="Cerca"]',
                        'input[placeholder*="Ricerca"]',
                        '.menu',
                        '#search',
                        '[class*="search"]'
                    ]
                    for sel in elementi_post_login:
                        try:
                            elem = self.page.wait_for_selector(sel, timeout=2000)
                            if elem:
                                login_riuscito = True
                                print(f"✅ Login verificato: trovato elemento post-login ({sel})")
                                break
                        except:
                            continue
                except Exception:
                    pass
            
            if not login_riuscito:
                # Retry UNA VOLTA: ricarica Home e riprova login (gestisce glitch di Render/lentezza)
                print("⚠️  Login non verificato, eseguo un retry rapido...")
                try:
                    self.page.goto(f"{self.base_url}/#Home/Index", wait_until="domcontentloaded")
                    time.sleep(2)
                except Exception:
                    pass
                # Prova a trovare di nuovo i campi
                try:
                    u = self.page.wait_for_selector('input[name="Username"], input[id="Username"], input[placeholder*="Utente"], input[placeholder*="Username"], input[type="text"]', timeout=3000)
                    p = self.page.wait_for_selector('input[name="Password"], input[id="Password"], input[placeholder*="Password"], input[type="password"]', timeout=3000)
                    if u and p:
                        u.fill(self.username)
                        p.fill(self.password)
                        self.page.click('button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Accedi")')
                        self.page.wait_for_load_state("networkidle")
                        time.sleep(5)
                        current_url = self.page.url
                        if "LogOn" not in current_url:
                            login_riuscito = True
                            print("✅ Login verificato al retry")
                except Exception:
                    pass
            
            if not login_riuscito:
                print("❌ Login fallito: URL o elementi non corrispondono a sessione autenticata")
                print(f"   URL attuale: {current_url}")
                return False
            
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
            
            # Verifica e gestisce eventuali session expired
            if not self._check_and_handle_session_expired():
                print("❌ Impossibile ripristinare la sessione")
                return False
            
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
            
            # Fallback 2: ARIA role textbox con nome contenente 'cerca/ricerca/partita'
            if not campo_ricerca:
                try:
                    locator = self.page.get_by_role("textbox", name=re.compile("cerca|ricerca|partita", re.I))
                    campo_ricerca = locator.first.element_handle(timeout=3000)
                    if campo_ricerca:
                        print("✅ Campo ricerca trovato via role=textbox (nome contiene cerca/ricerca/partita)")
                except Exception:
                    campo_ricerca = None

            # Fallback 3: Scansione di tutti gli input di testo/search visibili (priorità header/nav)
            if not campo_ricerca:
                try:
                    handle = self.page.evaluate_handle(
                        "() => {\n"
                        "  function visibile(el){ const r=el.getBoundingClientRect(); const style=getComputedStyle(el); return r.width>150 && r.height>20 && style.visibility!=='hidden' && style.display!=='none'; }\n"
                        "  const candidati = Array.from(document.querySelectorAll('input[type=\\'search\\'], input[type=\\'text\\']'))\n"
                        "    .filter(el => !el.disabled && !el.readOnly && visibile(el));\n"
                        "  const scored = candidati.map(el => {\n"
                        "    const ph=(el.getAttribute('placeholder')||'').toLowerCase();\n"
                        "    const ttl=(el.getAttribute('title')||'').toLowerCase();\n"
                        "    const inHeader = !!el.closest('header, nav');\n"
                        "    const match = (ph.includes('cerca')||ph.includes('ricerca')||ph.includes('partita')||ttl.includes('cerca')||ttl.includes('partita'));\n"
                        "    let score = (inHeader?5:0) + (match?3:0) + (el.type==='search'?2:0);\n"
                        "    return {el, score};\n"
                        "  }).sort((a,b)=>b.score-a.score);\n"
                        "  return scored.length? scored[0].el : null;\n"
                        "}"
                    )
                    if handle:
                        campo_ricerca = handle.as_element()
                        if campo_ricerca:
                            print("✅ Campo ricerca trovato via scansione input visibili")
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
            
            # Clicca sul nome (con fallback robusti)
            testo_nome = nome_link.inner_text()
            print(f"🖱️ Clic sul nome: '{testo_nome}'...")
            try:
                # Tentativo standard
                nome_link.click(timeout=30000)
            except Exception as click_err:
                print(f"⚠️ Click standard fallito: {click_err}. Provo scroll+force...")
                try:
                    # Scroll e click forzato
                    nome_link.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    nome_link.click(force=True, timeout=15000)
                except Exception as force_err:
                    print(f"⚠️ Click force fallito: {force_err}. Provo via JS...")
                    try:
                        # Click via JavaScript
                        self.page.evaluate("el => el.click()", nome_link)
                    except Exception as js_err:
                        print(f"⚠️ Click JS fallito: {js_err}. Provo navigando su href...")
                        # Ultimo fallback: vai direttamente all'href del link
                        href = nome_link.get_attribute('href')
                        if not href:
                            raise
                        if href.startswith('/'):
                            base = 'https://www2.cribisx.com'
                            href = base + href
                        print(f"➡️  Navigo direttamente su: {href}")
                        self.page.goto(href, wait_until='domcontentloaded')
            
            # Attendi caricamento pagina dettaglio
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
                        time.sleep(2)
                        
                        print(f"📍 URL nuova tab: {self.page.url}")
                        
                        # SOSTITUITO: invece di sleep fissi, usa il metodo intelligente che aspetta la generazione
                        print("⏳ Aspetto che il report 'Gruppo Societario' sia completamente generato...")
                        print("   (Cribis può impiegare fino a 3 minuti per report complessi)")
                        
                        if not self.aspetta_generazione_report(timeout=180):  # 3 minuti
                            print("⚠️  Timeout generazione report (180s), continuo comunque...")
                            print("   Il report potrebbe non essere completo")
                        else:
                            print("✅ Report 'Gruppo Societario' completamente generato e pronto!")
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
        Aspetta che il report 'Gruppo Societario' venga completamente generato.
        Verifica la presenza di elementi chiave come codici fiscali e nomi società.
        
        Args:
            timeout (int): Tempo massimo di attesa in secondi (default 60)
            
        Returns:
            bool: True se report generato completamente
        """
        try:
            print(f"⏳ Attesa generazione report (max {timeout} secondi)...")
            
            start_time = time.time()
            last_progress = 0
            
            # Indicatori che il report è completo (più specifici)
            indicatori_completamento = [
                'Cod. Fisc.',           # Colonna codici fiscali
                'Italia',               # Paese società
                '%',                    # Percentuali di partecipazione
                'Diretto',              # Tipo partecipazione
                'SRL',                  # Forme societarie comuni
                'SPA'
            ]
            
            # Indicatori di caricamento in corso
            indicatori_loading = [
                'loading',
                'spinner',
                'Caricamento',
                'Generazione in corso',
                'Attendere'
            ]
            
            while time.time() - start_time < timeout:
                elapsed = int(time.time() - start_time)
                
                # Progress indicator ogni 10 secondi
                if elapsed >= last_progress + 10:
                    print(f"   ⏳ {elapsed}/{timeout} secondi trascorsi...")
                    last_progress = elapsed
                
                try:
                    # Controlla se ci sono ancora indicatori di loading
                    page_content = self.page.content()
                    has_loading = any(ind.lower() in page_content.lower() for ind in indicatori_loading)
                    
                    if has_loading:
                        print(f"   🔄 Rilevato caricamento in corso...")
                        time.sleep(2)
                        continue
                    
                    # Conta quanti indicatori di completamento sono presenti
                    indicatori_trovati = sum(1 for ind in indicatori_completamento if ind in page_content)
                    
                    # Report pronto se abbiamo almeno 4 indicatori su 6
                    if indicatori_trovati >= 4:
                        print(f"✅ Report pronto! Trovati {indicatori_trovati}/{len(indicatori_completamento)} indicatori")
                        
                        # Aspetta extra per rendering completo
                        time.sleep(3)
                        
                        # Salva screenshot finale
                        try:
                            self.page.screenshot(path="debug_cribis_nuova_11_report_generato.png")
                            print("📸 Screenshot: debug_cribis_nuova_11_report_generato.png")
                        except:
                            pass
                        
                        return True
                    
                    # Se abbiamo almeno 2 indicatori, siamo sulla strada giusta
                    if indicatori_trovati >= 2:
                        print(f"   📊 Parzialmente caricato ({indicatori_trovati}/{len(indicatori_completamento)} indicatori)")
                    
                except Exception as e:
                    print(f"   ⚠️  Errore verifica completamento: {e}")
                
                # Attendi 2 secondi prima del prossimo controllo
                time.sleep(2)
            
            # Timeout raggiunto senza completamento
            elapsed_total = int(time.time() - start_time)
            print(f"⚠️  Timeout raggiunto ({elapsed_total}s) - report potrebbe non essere completo")
            
            # Salva screenshot anche in caso di timeout
            try:
                self.page.screenshot(path="debug_cribis_nuova_11_report_timeout.png")
                print("📸 Screenshot timeout: debug_cribis_nuova_11_report_timeout.png")
            except:
                pass
            
            return False
            
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
            
            # Pattern migliorato: cattura Nome + CF + P.IVA + percentuale
            # Formato: "NOME SOCIETA\nCod. Fisc.: 12345678901 - Italia\n P. IVA: 12345678901\n...%"
            pattern_societa = r'(?:^|\n)(?:\d+(?:\.\d+)?\s+)?([A-Z][A-Z\s\.\-&]+?)\s*\n\s*Cod\.\s*Fisc\.\s*:\s*(\d{11})\s*-\s*Italia'
            
            matches = re.findall(pattern_societa, body_text, re.MULTILINE)
            print(f"🔍 Trovate {len(matches)} società italiane nel gruppo")
            
            # Dizionari CF -> Nome e CF -> P.IVA per lookup veloce
            cf_to_nome = {}
            cf_to_piva = {}
            for nome, cf in matches:
                nome_pulito = nome.strip()
                # Rimuove numeri iniziali e spazi extra
                nome_pulito = re.sub(r'^\d+(?:\.\d+)?\s+', '', nome_pulito).strip()
                cf_to_nome[cf] = nome_pulito
                
                # Cerca P.IVA associata a questo CF nel testo
                # Pattern: cerca "P. IVA:" o "P.IVA:" dopo il CF
                piva_pattern = rf'Cod\.\s*Fisc\.\s*:\s*{cf}\s*-\s*Italia.*?P\.?\s*IVA\s*:?\s*(\d{{11}})'
                piva_match = re.search(piva_pattern, body_text, re.DOTALL | re.IGNORECASE)
                if piva_match:
                    piva = piva_match.group(1)
                    cf_to_piva[cf] = piva
                    print(f"   • {cf} (P.IVA: {piva}): {nome_pulito}")
                else:
                    print(f"   • {cf} (P.IVA: N/D): {nome_pulito}")
            
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
                        # Recupera P.IVA (se disponibile)
                        piva = cf_to_piva.get(cf)
                        
                        associate.append({
                            "ragione_sociale": nome.upper(),
                            "cf": cf,
                            "piva": piva,  # Aggiunta P.IVA (può essere None)
                            "percentuale": percentuale_str,
                            "percentuale_numerica": percentuale_numerica,
                            "categoria": categoria
                        })
                        emoji = "🔗" if categoria == "collegata" else "🤝"
                        piva_info = f" | P.IVA: {piva}" if piva else " | P.IVA: N/D"
                        print(f"   ✅ {emoji} AGGIUNTA: {nome} ({categoria}){piva_info}")
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
                
                # Alert email DISABILITATO: ora gestiamo automaticamente sessione scaduta con retry
                # if EMAIL_ALERTS_ENABLED:
                #     try:
                #         print("📧 Invio alert email per errore ricerca Cribis...")
                #         alert_cribis_error(
                #             partita_iva=partita_iva,
                #             errore="Campo ricerca principale non trovato - Possibile cambio interfaccia",
                #             fase="Ricerca P.IVA",
                #             screenshot_path="debug_cribis_nuova_02_dopo_login.png" if os.path.exists("debug_cribis_nuova_02_dopo_login.png") else None
                #         )
                #     except Exception as email_err:
                #         print(f"⚠️ Errore invio alert email: {email_err}")
                
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
    
    def scarica_company_card_completa(self, codice_fiscale: str, partita_iva: str = None) -> dict:
        """
        Apre la Company Card Completa della società richiesta ed estrae i dati finanziari.
        
        Estrazione dati:
        1. Priorità: estrazione DOM diretta (XPath precisi sulla tabella bilancio)
        2. Fallback: regex su HTML se DOM non restituisce valori
        
        Args:
            codice_fiscale (str): CF dell'azienda
            partita_iva (str, optional): P.IVA dell'azienda (preferita per la ricerca). Se non fornita, usa CF.
            
        Returns:
            dict: Dati finanziari estratti (personale, fatturato, attivo)
        """
        # Retry logic per gestire session expired
        max_retries = 2
        for attempt in range(max_retries):
            try:
                return self._scarica_company_card_completa_internal(codice_fiscale, partita_iva)
            except Exception as e:
                error_msg = str(e)
                if "SESSION_EXPIRED:" in error_msg:
                    if attempt < max_retries - 1:
                        print(f"\n{'='*70}")
                        print(f"🔄 TENTATIVO {attempt + 2}/{max_retries}: Sessione scaduta, eseguo re-login...")
                        print(f"{'='*70}\n")
                        # Re-login
                        try:
                            self.page.goto(f"{self.base_url}/#Home/Index", wait_until="domcontentloaded")
                            time.sleep(2)
                            if "LogOn" in self.page.url or "sessionExpired" in self.page.url:
                                if not self.login():
                                    print("❌ Re-login fallito!")
                                    raise Exception("Re-login fallito dopo session expired")
                                print("✅ Re-login completato con successo!")
                            else:
                                print("✅ Sessione già valida dopo navigazione a Home")
                        except Exception as login_err:
                            print(f"❌ Errore durante re-login: {login_err}")
                            if attempt < max_retries - 1:
                                print("⏳ Attendo 5 secondi prima di riprovare...")
                                time.sleep(5)
                                continue
                            else:
                                raise
                        # Attendi un po' prima di riprovare
                        print("⏳ Attendo 3 secondi prima di riprovare l'operazione...")
                        time.sleep(3)
                        continue
                    else:
                        print(f"❌ Tutti i tentativi ({max_retries}) falliti a causa di session expired")
                        raise
                else:
                    # Per altri errori, propaga subito
                    raise
        
        # Se arriviamo qui senza risultato, errore generico
        raise Exception("Operazione fallita dopo tutti i tentativi")
    
    def _scarica_company_card_completa_internal(self, codice_fiscale: str, partita_iva: str = None) -> dict:
        """
        Implementazione interna di scarica_company_card_completa (usata per retry logic).
        
        Args:
            codice_fiscale (str): CF dell'azienda
            partita_iva (str, optional): P.IVA dell'azienda
            
        Returns:
            dict: Dati finanziari estratti
        """
        try:
            # Usa P.IVA se disponibile, altrimenti CF
            codice_ricerca = partita_iva if partita_iva else codice_fiscale
            tipo_codice = "P.IVA" if partita_iva else "CF"
            
            print(f"\n{'='*70}")
            print(f"📊 Estrazione dati web per: {codice_ricerca} ({tipo_codice})")
            if partita_iva and codice_fiscale != partita_iva:
                print(f"   ℹ️ CF associato: {codice_fiscale}")
            print(f"{'='*70}\n")
            
            # Verifica sessione prima di iniziare
            if not self._check_and_handle_session_expired():
                raise Exception("SESSION_EXPIRED:Impossibile ripristinare la sessione all'inizio dell'operazione")
            
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
            
            # STEP 1: Ricerca codice (P.IVA o CF)
            print(f"🔍 STEP 1: Ricerca {tipo_codice}...")
            campo_ricerca = self.page.locator('input[title="Inserisci i termini da cercare"]')
            campo_ricerca.fill(codice_ricerca)
            self.page.keyboard.press("Enter")
            
            # Attendi caricamento risultati (aumentato da 2s a 5s)
            print("   ⏳ Attendo caricamento risultati (5s)...")
            self.page.wait_for_timeout(5000)
            
            # STEP 2: Click sul nome azienda (primo risultato)
            print("🎯 STEP 2: Click su nome azienda...")
            nome_azienda = self.page.locator('div[class*="result"] a:first-of-type').first
            
            # Verifica se l'azienda è visibile (con timeout di 3s)
            try:
                is_visible = nome_azienda.is_visible(timeout=3000)
            except:
                is_visible = False
            
            if not is_visible:
                print("   ⚠️  Primo risultato non visibile, provo selettori alternativi...")
                # Prova selettori alternativi
                selettori_alternativi = [
                    'div.result a:first-of-type',
                    'div.results a:first-of-type',
                    'a[href*="Purchase/Company"]',
                    '.search-result a:first-of-type'
                ]
                
                for sel in selettori_alternativi:
                    try:
                        alt_azienda = self.page.locator(sel).first
                        if alt_azienda.is_visible(timeout=2000):
                            nome_azienda = alt_azienda
                            is_visible = True
                            print(f"   ✅ Trovata con selettore: {sel}")
                            break
                    except:
                        continue
            
            if not is_visible:
                # Screenshot per debug
                try:
                    screenshot_path = f"debug_no_results_{codice_ricerca}.png"
                    self.page.screenshot(path=screenshot_path, full_page=True)
                    print(f"   📸 Screenshot salvato: {screenshot_path}")
                except:
                    pass
                
                print(f"   ❌ Azienda {codice_ricerca} ({tipo_codice}) non trovata nei risultati")
                print(f"   💡 Possibili cause: società cessata, inattiva, o codice errato")
                
                return {
                    "errore": "Azienda non trovata nei risultati",
                    "cf": codice_fiscale,
                    "piva": partita_iva,
                    "codice_ricerca": codice_ricerca,
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
                
                # Attendi caricamento modale
                print("   ⏳ Attendo caricamento modale (3 sec)...")
                time.sleep(3)
                self.page.wait_for_load_state("domcontentloaded")
                
                # Screenshot di debug
                try:
                    self.page.screenshot(path=f"debug_modale_aperta_{codice_fiscale}.png", full_page=True)
                    print(f"   📸 Screenshot modale salvato: debug_modale_aperta_{codice_fiscale}.png")
                except Exception as e:
                    print(f"   ⚠️  Errore screenshot: {e}")
                
                # DEBUG: Verifica HTML della pagina
                print(f"   🔍 URL dopo apertura modale: {self.page.url}")
                page_title = self.page.title()
                print(f"   🔍 Titolo pagina: {page_title}")
                
                # Cerca nella modale la card "Company Card Completa" e clicca "Richiedi"
                try:
                    print("   🔎 STEP 3.1: Cerco card 'Company Card Completa' nella modale...")
                    
                    # DEBUG: Conta tutte le modali presenti
                    print("   🔍 DEBUG: Verifico presenza modali...")
                    for modal_sel in ['.modal-dialog', '.modal-content', '.modal', '[role="dialog"]']:
                        count = self.page.locator(modal_sel).count()
                        print(f"      Selettore '{modal_sel}': {count} elementi trovati")
                    
                    # Prova diversi selettori per la modale
                    modale = None
                    # CRITICO: La modale prodotti ha class="modal fade in modal-marker" con display:block
                    # Cerchiamo PRIMA quella specifica, poi fallback a visibili
                    
                    # METODO 1: Cerca modale con class specifica "modal fade in" (quella attiva)
                    try:
                        modale_attiva = self.page.locator('.modal.fade.in, .modal.in, .modal-marker:has(.all-prod-marker)').first
                        try:
                            modale_attiva_count = modale_attiva.count()
                        except:
                            modale_attiva_count = 0
                        if modale_attiva_count > 0:
                            # Verifica che contenga "Richiedi un prodotto"
                            modal_text_test = modale_attiva.inner_text()
                            if "Richiedi un prodotto CRIBIS X" in modal_text_test or "all-prod-marker" in str(modale_attiva):
                                modale = modale_attiva.locator('.modal-dialog, .modal-content').first
                                try:
                                    modale_dialog_count = modale.count()
                                except:
                                    modale_dialog_count = 0
                                if modale_dialog_count > 0:
                                    print("   ✅ Modale PRODOTTI trovata con selettore '.modal.fade.in'!")
                            else:
                                print(f"   ⚠️  Modale .fade.in non è quella dei prodotti (testo: '{modal_text_test[:50]}...')")
                    except Exception as e:
                        print(f"   ⚠️  Errore cercando .modal.fade.in: {e}")
                    
                    # METODO 2: Se non trovata, cerca tra tutte le modali quella con "Richiedi un prodotto"
                    if not modale:
                        print("   🔍 Metodo 2: Cerco tra tutte le modali quella con 'Richiedi un prodotto'...")
                        for modal_sel in ['.modal-dialog', '.modal-content', '.modal', '[role="dialog"]']:
                            try:
                                # Cerca solo modali VISIBILI (la modale prodotti è visibile, quella di conferma può essere nascosta)
                                all_modals_visible = self.page.locator(f'{modal_sel}:visible').all()
                                print(f"   🔍 Selettore '{modal_sel}:visible': {len(all_modals_visible)} modali VISIBILI trovate")
                            
                                if len(all_modals_visible) == 0:
                                    # Fallback: prova tutte le modali (anche nascoste)
                                    all_modals_visible = self.page.locator(modal_sel).all()
                                    print(f"   🔍 Fallback: '{modal_sel}' (tutte): {len(all_modals_visible)} modali totali")
                                
                                # Cerca tra tutte le modali quella con "Richiedi un prodotto" o "Company Card"
                                for i, modal_candidate in enumerate(all_modals_visible):
                                    try:
                                        # Verifica se è visibile
                                        is_visible = modal_candidate.evaluate("el => el.offsetParent !== null && window.getComputedStyle(el).display !== 'none'")
                                        
                                        if not is_visible:
                                            print(f"   ⚠️  Modale #{i+1} non è visibile, salto")
                                            continue
                                        
                                        modal_text = modal_candidate.inner_text()
                                        modal_html_preview = modal_candidate.evaluate("el => el.innerHTML.substring(0, 300)")
                                        
                                        # Verifica se questa è la modale dei prodotti
                                        is_prodotti = (
                                            "Richiedi un prodotto CRIBIS X" in modal_text or
                                            "Company Card Completa" in modal_text or
                                            "business-report-container" in modal_html_preview or
                                            "prod-box-marker" in modal_html_preview
                                        )
                                        
                                        if is_prodotti:
                                            modale = modal_candidate
                                            print(f"   ✅ Modale PRODOTTI trovata! (selettore: {modal_sel}, modale #{i+1}, VISIBILE)")
                                            
                                            # DEBUG: Verifica contenuto modale
                                            card_count = modale.locator('div.business-report-container').count()
                                            print(f"   📊 Card business-report trovate nella modale: {card_count}")
                                            
                                            if "Company Card Completa" in modal_text:
                                                print("   ✅ Testo 'Company Card Completa' presente nella modale!")
                                            else:
                                                print("   ⚠️  'Company Card Completa' non presente, ma modale prodotti corretta")
                                            
                                            break
                                        else:
                                            print(f"   ⚠️  Modale #{i+1} non è quella dei prodotti (è: '{modal_text[:50]}...')")
                                    except Exception as debug_err:
                                        print(f"   ⚠️  Errore debug modale #{i+1}: {debug_err}")
                                        continue
                                
                                if modale:
                                    break
                            except Exception as e:
                                print(f"   ⚠️  Selettore {modal_sel} non funziona: {e}")
                                continue
                    
                    # FALLBACK FINALE: Se non trova ancora, prendi la modale con più card business-report
                    if not modale:
                        print("   🔍 Fallback finale: cerco modale con più card business-report...")
                        best_modal = None
                        best_count = 0
                        for modal_sel in ['.modal-dialog:visible', '.modal-content:visible']:
                            try:
                                all_modals = self.page.locator(modal_sel).all()
                                for modal_candidate in all_modals:
                                    card_count = modal_candidate.locator('div.business-report-container').count()
                                    if card_count > best_count:
                                        best_count = card_count
                                        best_modal = modal_candidate
                            except:
                                continue
                        
                        if best_modal and best_count > 0:
                            modale = best_modal
                            print(f"   ✅ Modale trovata con {best_count} card business-report (FALLBACK)")
                    
                    if not modale:
                        print("   ❌ Nessuna modale trovata!")
                        
                        # DEBUG: Screenshot e HTML pagina completa
                        try:
                            self.page.screenshot(path=f"debug_no_modale_{codice_fiscale}.png", full_page=True)
                            print(f"   📸 Screenshot NO modale salvato: debug_no_modale_{codice_fiscale}.png")
                        except:
                            pass
                        
                        # Prova a cercare direttamente nella pagina
                        print("   🔍 Provo a cercare 'Company Card Completa' direttamente nella pagina...")
                        modale = None  # Forza ricerca nella pagina principale
                    else:
                        # STEP 3.0: Espandi sezione "Basic Data" se collassata (Company Card Completa è lì)
                        print("   🔍 STEP 3.0: Verifico se sezione 'Basic Data' è espansa...")
                        try:
                            # Cerca link "Altri Basic Data" e cliccalo per espandere
                            link_altri_basic = modale.locator('a:has-text("Altri Basic Data"), a.report-generico-modal:has-text("Basic")').first
                            try:
                                link_altri_basic_count = link_altri_basic.count()
                            except:
                                link_altri_basic_count = 0
                            if link_altri_basic_count > 0:
                                print("   📂 Trovato link 'Altri Basic Data', lo clicco per espandere...")
                                link_altri_basic.click()
                                time.sleep(2)  # Attendi espansione
                                print("   ✅ Sezione espansa")
                        except Exception as e:
                            print(f"   ⚠️  Link 'Altri Basic Data' non trovato o già espanso: {e}")
                        
                        # Scroll in fondo per vedere tutto
                        try:
                            print("   📜 Scrolling modale verso il basso...")
                            modale.evaluate("element => element.scrollTop = element.scrollHeight")
                            time.sleep(1)
                        except Exception as e:
                            print(f"   ⚠️  Errore scroll modale: {e}")
                        
                        # METODO SEMPLIFICATO: tutte le card hanno struttura identica, differenza è solo il testo in <em>
                        print("   🔎 STEP 3.2: Cerco container con em='Company Card Completa'...")
                        card_container = None
                        bottone_richiedi = None
                        container_count = 0
                        bottone_count = 0
                        
                        try:
                            # Metodo diretto: trova il container che contiene em con "Company Card Completa"
                            print("   🔍 Cerco: div.business-report-container.prod-box-marker:has(em:has-text('Company Card Completa'))...")
                            
                            # Usa timeout esplicito per evitare blocchi
                            try:
                                card_container = modale.locator(
                                    'div.business-report-container.prod-box-marker:has(em:has-text("Company Card Completa"))'
                                ).first
                                
                                # Controllo container (senza timeout - count() non lo supporta)
                                # Usa timeout sul locator stesso invece
                                container_count = card_container.count()
                                print(f"   🔍 Container count: {container_count}")
                            except Exception as timeout_err:
                                print(f"   ⚠️  Timeout o errore nella ricerca container: {timeout_err}")
                                container_count = 0
                                card_container = None
                            
                            if container_count > 0 and card_container:
                                print("   ✅ Container 'Company Card Completa' trovato!")
                                
                                # DEBUG: Mostra HTML del container
                                try:
                                    container_html = card_container.evaluate("el => el.innerHTML.substring(0, 800)")
                                    print(f"   📄 DEBUG Container HTML (prime 800 char):\n{container_html}")
                                except Exception as e:
                                    print(f"   ⚠️  Errore estrazione HTML container: {e}")
                                
                                # DEBUG: Conta bottoni nel container
                                try:
                                    btn_container_count = card_container.locator('.business-report-button-container').count()
                                    print(f"   🔍 DEBUG: .business-report-button-container trovati nel container: {btn_container_count}")
                                    
                                    all_links = card_container.locator('a').count()
                                    all_buttons = card_container.locator('button').count()
                                    print(f"   🔍 DEBUG: Link <a> nel container: {all_links}, Button <button>: {all_buttons}")
                                except Exception as e:
                                    print(f"   ⚠️  Errore conteggio elementi: {e}")
                                
                                # Cerca il bottone "Richiedi" dentro questo container specifico
                                print("   🔍 Cerco bottone 'Richiedi' dentro il container...")
                                try:
                                    bottone_richiedi = card_container.locator('.business-report-button-container a, .business-report-button-container button').first
                                    bottone_count = bottone_richiedi.count()
                                    print(f"   🔍 Bottone count: {bottone_count}")
                                except Exception as btn_timeout_err:
                                    print(f"   ⚠️  Timeout o errore nella ricerca bottone: {btn_timeout_err}")
                                    bottone_count = 0
                                    bottone_richiedi = None
                                
                                if bottone_count > 0 and bottone_richiedi:
                                    # Verifica che il testo del bottone sia "Richiedi"
                                    btn_text = bottone_richiedi.inner_text().strip()
                                    if 'richiedi' in btn_text.lower():
                                        print(f"   ✅ Bottone 'Richiedi' trovato nel container! (Testo: '{btn_text}')")
                                    else:
                                        print(f"   ⚠️  Bottone nel container ma testo diverso: '{btn_text}'")
                                        bottone_richiedi = None
                                else:
                                    print("   ⚠️  Nessun bottone in .business-report-button-container, provo ricerca generica nel container...")
                                    
                                    # DEBUG: Mostra tutti i link/button trovati
                                    try:
                                        all_btns = card_container.locator('a, button').all()
                                        print(f"   🔍 DEBUG: Trovati {len(all_btns)} elementi a/button nel container")
                                        for i, btn in enumerate(all_btns[:5]):  # Prime 5
                                            try:
                                                btn_text_debug = btn.inner_text().strip()
                                                btn_href = btn.get_attribute('href') or ''
                                                print(f"      [{i+1}] Testo: '{btn_text_debug}' | Href: {btn_href[:50]}")
                                            except:
                                                pass
                                    except Exception as e:
                                        print(f"   ⚠️  Errore debug bottoni: {e}")
                                    
                                    try:
                                        bottone_richiedi = card_container.locator('a:has-text("Richiedi"), button:has-text("Richiedi")').first
                                        generic_btn_count = bottone_richiedi.count()
                                        if generic_btn_count > 0:
                                            print("   ✅ Bottone 'Richiedi' trovato (ricerca generica nel container)!")
                                            bottone_count = generic_btn_count  # Aggiorna bottone_count
                                        else:
                                            print("   ❌ Bottone 'Richiedi' NON TROVATO neanche con ricerca generica!")
                                            bottone_richiedi = None
                                            bottone_count = 0
                                    except Exception as generic_err:
                                        print(f"   ⚠️  Errore ricerca generica bottone: {generic_err}")
                                        bottone_richiedi = None
                                        bottone_count = 0
                            if card_container is None:
                                print("   ❌ Container con 'Company Card Completa' NON trovato!")
                                # Fallback: prova con JavaScript
                                print("   🔍 Fallback: ricerca con JavaScript...")
                                try:
                                    container_info = modale.evaluate("""
                                        () => {
                                            const containers = document.querySelectorAll('div.business-report-container.prod-box-marker');
                                            for (let container of containers) {
                                                const em = container.querySelector('em.dark-slate-blue, em');
                                                if (em && em.textContent.trim() === 'Company Card Completa') {
                                                    const button = container.querySelector('.business-report-button-container a');
                                                    return {
                                                        found: true,
                                                        hasButton: button !== null,
                                                        buttonText: button ? button.textContent.trim() : null
                                                    };
                                                }
                                            }
                                            return { found: false };
                                        }
                                    """)
                                    
                                    if container_info and container_info.get('found'):
                                        print(f"   ✅ Container trovato con JavaScript! Bottone: {container_info.get('hasButton')}")
                                        if container_info.get('hasButton'):
                                            # Trova il container con il testo esatto
                                            card_container = None
                                            all_containers = modale.locator('div.business-report-container.prod-box-marker').all()
                                            for container in all_containers:
                                                try:
                                                    em_text = container.locator('em').first.inner_text().strip()
                                                    if em_text == 'Company Card Completa':
                                                        card_container = container
                                                        bottone_richiedi = container.locator('.business-report-button-container a').first
                                                        try:
                                                            js_btn_count = bottone_richiedi.count()
                                                            if js_btn_count > 0:
                                                                print("   ✅ Container e bottone trovati con JavaScript filtering!")
                                                                bottone_count = js_btn_count  # Aggiorna bottone_count
                                                                container_count = 1  # Container trovato
                                                                break
                                                        except Exception:
                                                            bottone_richiedi = None
                                                            bottone_count = 0
                                                except:
                                                    continue
                                except Exception as js_err:
                                    print(f"   ⚠️  Fallback JavaScript fallito: {js_err}")
                            
                            if card_container and bottone_richiedi and (bottone_count or 0) > 0:
                                print("   ✅ Card container E bottone 'Richiedi' trovati con successo!")
                                card_sel = card_container.first  # Per compatibilità con codice esistente
                            else:
                                # Se il container è stato trovato ma il bottone dentro NO, è un errore critico
                                if card_container and container_count > 0 and (not bottone_richiedi or (bottone_count or 0) == 0):
                                    print("   ❌ ERRORE CRITICO: Container 'Company Card Completa' TROVATO ma bottone 'Richiedi' MANCANTE!")
                                    print("      Questo indica un cambiamento nella struttura HTML della card.")
                                    try:
                                        self.page.screenshot(path=f"debug_bottone_mancante_nel_container_{codice_fiscale}.png", full_page=True)
                                        print(f"   📸 Screenshot salvato: debug_bottone_mancante_nel_container_{codice_fiscale}.png")
                                    except Exception:
                                        pass
                                    raise Exception(f"Container 'Company Card Completa' trovato ma bottone 'Richiedi' mancante per CF {codice_fiscale}. Impossibile continuare.")
                                
                                print("   ❌ Container o bottone NON trovati!")
                                card_sel = None
                                bottone_richiedi = None
                                
                        except Exception as container_err:
                            print(f"   ❌ Errore ricerca container: {container_err}")
                            import traceback
                            traceback.print_exc()
                            card_sel = None
                            bottone_richiedi = None
                        
                        # Screenshot debug se non trovato
                        if not card_container or not bottone_richiedi:
                            print("   ❌ Card 'Company Card Completa' NON trovata nella modale!")
                            try:
                                self.page.screenshot(path=f"debug_card_non_trovata_{codice_fiscale}.png", full_page=True)
                                print(f"   📸 Screenshot salvato: debug_card_non_trovata_{codice_fiscale}.png")
                            except Exception:
                                pass
                        
                        # STEP 3.3: Usa bottone_richiedi se già trovato, altrimenti cerca risalendo dal card_sel
                        bottone_trovato = False
                        
                        # Usa bottone_count se disponibile
                        bottone_check = (bottone_count or 0) > 0
                        if not bottone_check and bottone_richiedi:
                            try:
                                bottone_check = bottone_richiedi.count() > 0
                            except:
                                bottone_check = False
                        
                        if bottone_richiedi and bottone_check:
                            print("   🔎 STEP 3.3: Bottone 'Richiedi' già trovato con selettori precisi!")
                            btns = [bottone_richiedi]
                            
                            # Salta il loop di ricerca, vai direttamente al click
                            try:
                                print("   🖱️  STEP 3.4: Click su 'Richiedi' (già trovato, attendo nuova tab o cambio URL)...")
                                url_prima_click = self.page.url
                                
                                try:
                                    # Prova prima con expect_page (nuova tab)
                                    with self.page.context.expect_page(timeout=30000) as popup_info:  # 30s per nuova tab
                                        btns[0].click(force=True)
                                    print("   ✅ Nuova tab rilevata!")
                                    nuova_tab = popup_info.value
                                    self.page = nuova_tab
                                    self.page.wait_for_load_state("domcontentloaded")
                                    url_dopo_click = self.page.url
                                except Exception as timeout_err:
                                    # Se non si apre nuova tab, verifica se l'URL nella stessa tab è cambiato
                                    print(f"   ⚠️  Nessuna nuova tab rilevata entro 30s, verifico se URL cambiato nella stessa tab...")
                                    self.page.wait_for_load_state("domcontentloaded")
                                    time.sleep(2)  # Attendi eventuale redirect
                                    url_dopo_click = self.page.url
                                
                                print(f"   📍 URL dopo click: {url_dopo_click}")
                                
                                # VERIFICA CRITICA: deve essere la pagina Company Card Completa
                                # Escludi esplicitamente DocumentUnavailable
                                if ("/Storage/Document/" in url_dopo_click and "DocumentUnavailable" not in url_dopo_click) or "Company Card" in self.page.title():
                                    print("   ✅ VERIFICATO: Sono sulla Company Card Completa!")
                                    bottone_trovato = True
                                elif "DocumentUnavailable" in url_dopo_click:
                                    print(f"   ❌ ERRORE CRITICO: Documento non disponibile!")
                                    print(f"      URL ottenuto: {url_dopo_click}")
                                    raise Exception(f"Documento 'Company Card Completa' non disponibile per questo CF. URL: {url_dopo_click}")
                                elif "sessionExpired" in url_dopo_click or "LogOn" in url_dopo_click:
                                    print(f"   ⚠️  SESSIONE SCADUTA! URL: {url_dopo_click}")
                                    print(f"      Tento re-login e riprovo l'operazione...")
                                    raise Exception(f"SESSION_EXPIRED:{url_dopo_click}")
                                else:
                                    print(f"   ❌ ERRORE CRITICO: URL non corrisponde a Company Card!")
                                    print(f"      URL atteso: contiene '/Storage/Document/' (escludendo DocumentUnavailable)")
                                    print(f"      URL ottenuto: {url_dopo_click}")
                                    raise Exception(f"Pagina errata dopo click 'Richiedi': {url_dopo_click}")
                            except Exception as e:
                                print(f"   ❌ Errore click o attesa nuova tab: {e}")
                                import traceback
                                traceback.print_exc()
                                raise
                        
                        elif card_sel:
                            try:
                                card_sel_count = card_sel.count()
                            except:
                                card_sel_count = 0
                            
                            if card_sel_count > 0:
                                print("   🔎 STEP 3.3: Cerco bottone 'Richiedi' risalendo dalla card (metodo legacy)...")
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
                                                print("   🖱️  STEP 3.4: Click su 'Richiedi' (attendo nuova tab o cambio URL)...")
                                                url_prima_click = self.page.url
                                                
                                                try:
                                                    # Prova prima con expect_page (nuova tab)
                                                    with self.page.context.expect_page(timeout=30000) as popup_info:  # 30s per nuova tab
                                                        btns[0].click(force=True)
                                                    print("   ✅ Nuova tab rilevata!")
                                                    nuova_tab = popup_info.value
                                                    self.page = nuova_tab
                                                    self.page.wait_for_load_state("domcontentloaded")
                                                    url_dopo_click = self.page.url
                                                except Exception as timeout_err:
                                                    # Se non si apre nuova tab, verifica se l'URL nella stessa tab è cambiato
                                                    print(f"   ⚠️  Nessuna nuova tab rilevata entro 30s, verifico se URL cambiato nella stessa tab...")
                                                    self.page.wait_for_load_state("domcontentloaded")
                                                    time.sleep(2)  # Attendi eventuale redirect
                                                    url_dopo_click = self.page.url
                                                
                                                print(f"   📍 URL dopo click: {url_dopo_click}")
                                                
                                                # VERIFICA CRITICA: deve essere la pagina Company Card Completa
                                                # Escludi esplicitamente DocumentUnavailable
                                                if ("/Storage/Document/" in url_dopo_click and "DocumentUnavailable" not in url_dopo_click) or "Company Card" in self.page.title():
                                                    print("   ✅ VERIFICATO: Sono sulla Company Card Completa!")
                                                    bottone_trovato = True
                                                    break
                                                elif "DocumentUnavailable" in url_dopo_click:
                                                    print(f"   ❌ ERRORE CRITICO: Documento non disponibile!")
                                                    print(f"      URL ottenuto: {url_dopo_click}")
                                                    raise Exception(f"Documento 'Company Card Completa' non disponibile per questo CF. URL: {url_dopo_click}")
                                                elif "sessionExpired" in url_dopo_click or "LogOn" in url_dopo_click:
                                                    print(f"   ⚠️  SESSIONE SCADUTA! URL: {url_dopo_click}")
                                                    print(f"      Tento re-login e riprovo l'operazione...")
                                                    raise Exception(f"SESSION_EXPIRED:{url_dopo_click}")
                                                else:
                                                    print(f"   ❌ ERRORE CRITICO: URL non corrisponde a Company Card!")
                                                    print(f"      URL atteso: contiene '/Storage/Document/' (escludendo DocumentUnavailable)")
                                                    print(f"      URL ottenuto: {url_dopo_click}")
                                                    raise Exception(f"Pagina errata dopo click 'Richiedi': {url_dopo_click}")
                                                
                                            except Exception as e:
                                                print(f"   ❌ Errore click o attesa nuova tab: {e}")
                                                import traceback
                                                traceback.print_exc()
                                                # NON continuare: il processo deve bloccarsi qui
                                                raise
                                        else:
                                            print(f"   ⚠️  Nessun bottone 'Richiedi' trovato a livello {i+1}")
                                    except Exception as e:
                                        print(f"   ⚠️  Errore livello {i+1}: {e}")
                                        break
                            
                                if not bottone_trovato:
                                    print("   ⚠️  Bottone 'Richiedi' non trovato risalendo dalla card, provo ricerca diretta...")
                                    # Fallback: cerca "Richiedi" direttamente nella modale o pagina
                                    try:
                                        try:
                                            modale_count = modale.count() if modale else 0
                                        except:
                                            modale_count = 0
                                        search_area = modale if modale and modale_count > 0 else self.page
                                        
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
                                                    # CRITICO: Verifica che il bottone sia DENTRO un container con "Company Card Completa"
                                                    print(f"   🔍 Trovati {len(btns_diretti)} bottoni 'Richiedi', verifico quale è per Company Card Completa...")
                                                    bottone_corretto = None
                                                    
                                                    for btn in btns_diretti:
                                                        try:
                                                            # Risali fino al container business-report
                                                            parent_container = btn.locator('xpath=ancestor::div[contains(@class, "business-report-container")]').first
                                                            if parent_container.count() > 0:
                                                                # Verifica che il container abbia "Company Card Completa" nel tag <em>
                                                                em_tag = parent_container.locator('em').first
                                                                if em_tag.count() > 0:
                                                                    em_text = em_tag.inner_text().strip()
                                                                    if em_text == 'Company Card Completa':
                                                                        bottone_corretto = btn
                                                                        print(f"   ✅ Bottone CORRETTO trovato (dentro container 'Company Card Completa')!")
                                                                        break
                                                        except Exception:
                                                            continue
                                                    
                                                    if not bottone_corretto:
                                                        print(f"   ⚠️  Nessun bottone 'Richiedi' corretto trovato con selettore {btn_sel_diretto}, provo successivo...")
                                                        continue
                                                    
                                                    try:
                                                        print("   🖱️  Click su 'Richiedi' (ricerca diretta, attendo nuova tab o cambio URL)...")
                                                        url_prima_click = self.page.url
                                                        
                                                        try:
                                                            # Prova prima con expect_page (nuova tab)
                                                            with self.page.context.expect_page(timeout=30000) as popup_info:  # 30s per nuova tab
                                                                bottone_corretto.click(force=True)
                                                            print("   ✅ Nuova tab rilevata!")
                                                            nuova_tab = popup_info.value
                                                            self.page = nuova_tab
                                                            self.page.wait_for_load_state("domcontentloaded")
                                                            url_dopo_click = self.page.url
                                                        except Exception as timeout_err:
                                                            # Se non si apre nuova tab, verifica se l'URL nella stessa tab è cambiato
                                                            print(f"   ⚠️  Nessuna nuova tab rilevata entro 30s, verifico se URL cambiato nella stessa tab...")
                                                            self.page.wait_for_load_state("domcontentloaded")
                                                            time.sleep(2)  # Attendi eventuale redirect
                                                            url_dopo_click = self.page.url
                                                        
                                                        print(f"   📍 URL dopo click: {url_dopo_click}")
                                                        
                                                        # VERIFICA CRITICA: deve essere la pagina Company Card Completa
                                                        # Escludi esplicitamente DocumentUnavailable
                                                        if ("/Storage/Document/" in url_dopo_click and "DocumentUnavailable" not in url_dopo_click) or "Company Card" in self.page.title():
                                                            print("   ✅ VERIFICATO: Sono sulla Company Card Completa!")
                                                            bottone_trovato = True
                                                            break
                                                        elif "DocumentUnavailable" in url_dopo_click:
                                                            print(f"   ❌ ERRORE CRITICO: Documento non disponibile!")
                                                            print(f"      URL ottenuto: {url_dopo_click}")
                                                            raise Exception(f"Documento 'Company Card Completa' non disponibile per questo CF. URL: {url_dopo_click}")
                                                        elif "sessionExpired" in url_dopo_click or "LogOn" in url_dopo_click:
                                                            print(f"   ⚠️  SESSIONE SCADUTA! URL: {url_dopo_click}")
                                                            print(f"      Tento re-login e riprovo l'operazione...")
                                                            raise Exception(f"SESSION_EXPIRED:{url_dopo_click}")
                                                        else:
                                                            print(f"   ❌ ERRORE CRITICO: URL non corrisponde a Company Card!")
                                                            raise Exception(f"Pagina errata dopo click 'Richiedi' (ricerca diretta): {url_dopo_click}")
                                                    except Exception as e:
                                                        print(f"   ❌ Errore click (ricerca diretta): {e}")
                                                        import traceback
                                                        traceback.print_exc()
                                                        raise  # Blocca esecuzione
                                            except Exception:
                                                continue
                                    except Exception as e:
                                        print(f"   ⚠️  Errore ricerca diretta: {e}")
                                
                                if not bottone_trovato:
                                    print("   ❌ ERRORE CRITICO: Bottone 'Richiedi' NON TROVATO dopo tutti i tentativi!")
                                    # Screenshot finale
                                    try:
                                        self.page.screenshot(path=f"debug_richiedi_non_trovato_{codice_fiscale}.png", full_page=True)
                                        print(f"   📸 Screenshot salvato: debug_richiedi_non_trovato_{codice_fiscale}.png")
                                    except Exception:
                                        pass
                                    # BLOCCA ESECUZIONE: non possiamo continuare senza aprire Company Card
                                    raise Exception(f"Bottone 'Richiedi' per Company Card Completa non trovato per CF {codice_fiscale}. Impossibile continuare.")
                        else:
                            # Card non trovata: cerca Richiedi direttamente nella modale/pagina
                            print("   ⚠️  Card non trovata, provo ricerca diretta di 'Richiedi'...")
                            bottone_trovato = False
                            try:
                                try:
                                    modale_count_final = modale.count() if modale else 0
                                except:
                                    modale_count_final = 0
                                search_area = modale if modale and modale_count_final > 0 else self.page
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
                                            # CRITICO: Verifica che ogni bottone sia DENTRO un container con "Company Card Completa"
                                            print(f"   🔍 Trovati {len(btns_diretti)} bottoni 'Richiedi', verifico quale è per Company Card Completa...")
                                            bottone_corretto = None
                                            
                                            for btn in btns_diretti:
                                                try:
                                                    # Trova il container parent che contiene "Company Card Completa"
                                                    # Risali fino al container business-report
                                                    parent_container = btn.locator('xpath=ancestor::div[contains(@class, "business-report-container")]').first
                                                    if parent_container.count() > 0:
                                                        # Verifica che il container abbia "Company Card Completa" nel tag <em>
                                                        em_tag = parent_container.locator('em').first
                                                        if em_tag.count() > 0:
                                                            em_text = em_tag.inner_text().strip()
                                                            if em_text == 'Company Card Completa':
                                                                bottone_corretto = btn
                                                                print(f"   ✅ Bottone CORRETTO trovato (dentro container 'Company Card Completa')!")
                                                                break
                                                except Exception:
                                                    continue
                                            
                                            if not bottone_corretto:
                                                print(f"   ❌ Nessun bottone 'Richiedi' trovato dentro container 'Company Card Completa'!")
                                                continue
                                            
                                            try:
                                                print("   🖱️  Click su 'Richiedi' (senza card, attendo nuova tab o cambio URL nella stessa tab)...")
                                                url_prima_click = self.page.url
                                                
                                                try:
                                                    # Prova prima con expect_page (nuova tab)
                                                    with self.page.context.expect_page(timeout=30000) as popup_info:  # 30s per nuova tab
                                                        bottone_corretto.click(force=True)
                                                    print("   ✅ Nuova tab rilevata!")
                                                    nuova_tab = popup_info.value
                                                    self.page = nuova_tab
                                                    self.page.wait_for_load_state("domcontentloaded")
                                                    url_dopo_click = self.page.url
                                                except Exception as timeout_err:
                                                    # Se non si apre nuova tab, verifica se l'URL nella stessa tab è cambiato
                                                    print(f"   ⚠️  Nessuna nuova tab rilevata entro 30s, verifico se URL cambiato nella stessa tab...")
                                                    self.page.wait_for_load_state("domcontentloaded")
                                                    time.sleep(2)  # Attendi eventuale redirect
                                                    url_dopo_click = self.page.url
                                                
                                                print(f"   📍 URL dopo click: {url_dopo_click}")
                                                
                                                # VERIFICA CRITICA: deve essere la pagina Company Card Completa
                                                # Escludi esplicitamente DocumentUnavailable
                                                if ("/Storage/Document/" in url_dopo_click and "DocumentUnavailable" not in url_dopo_click) or "Company Card" in self.page.title():
                                                    print("   ✅ VERIFICATO: Sono sulla Company Card Completa!")
                                                    bottone_trovato = True
                                                    break
                                                elif "DocumentUnavailable" in url_dopo_click:
                                                    print(f"   ❌ ERRORE CRITICO: Documento non disponibile!")
                                                    print(f"      URL ottenuto: {url_dopo_click}")
                                                    raise Exception(f"Documento 'Company Card Completa' non disponibile per questo CF. URL: {url_dopo_click}")
                                                elif "sessionExpired" in url_dopo_click or "LogOn" in url_dopo_click:
                                                    print(f"   ⚠️  SESSIONE SCADUTA! URL: {url_dopo_click}")
                                                    print(f"      Tento re-login e riprovo l'operazione...")
                                                    raise Exception(f"SESSION_EXPIRED:{url_dopo_click}")
                                                else:
                                                    print(f"   ❌ ERRORE CRITICO: URL non corrisponde a Company Card!")
                                                    print(f"      URL atteso: contiene '/Storage/Document/' (escludendo DocumentUnavailable)")
                                                    print(f"      URL ottenuto: {url_dopo_click}")
                                                    raise Exception(f"Pagina errata dopo click 'Richiedi' (senza card): {url_dopo_click}")
                                            except Exception as e:
                                                print(f"   ❌ Errore click (senza card): {e}")
                                                import traceback
                                                traceback.print_exc()
                                                raise  # Blocca esecuzione
                                    except Exception:
                                        continue
                                
                                if not bottone_trovato:
                                    print("   ❌ ERRORE CRITICO: Bottone 'Richiedi' non trovato nemmeno con ricerca diretta!")
                                    try:
                                        self.page.screenshot(path=f"debug_richiedi_non_trovato_senza_card_{codice_fiscale}.png", full_page=True)
                                        print(f"   📸 Screenshot salvato: debug_richiedi_non_trovato_senza_card_{codice_fiscale}.png")
                                    except Exception:
                                        pass
                                    # BLOCCA ESECUZIONE
                                    raise Exception(f"Bottone 'Richiedi' per Company Card Completa non trovato (senza card) per CF {codice_fiscale}. Impossibile continuare.")
                            except Exception as e:
                                print(f"   ❌ ERRORE ricerca diretta (senza card): {e}")
                                raise  # Propaga l'errore per bloccare
                                        
                except Exception as e:
                    print(f"   ❌ ERRORE CRITICO nella selezione Company Card Completa: {e}")
                    import traceback
                    traceback.print_exc()
                    # Propaga l'errore per bloccare l'esecuzione
                    raise
            
            url_dopo_step3 = self.page.url
            print(f"   📍 URL dopo STEP 3: {url_dopo_step3}")
            
            # STEP 3.5: Verifica se c'è una pagina di configurazione per selezionare i campi
            # Se presente, seleziona: Dipendenti, Fatturato, Totale Attività
            print("🔧 STEP 3.5: Verifica pagina configurazione campi...")
            try:
                self.page.wait_for_load_state("domcontentloaded")
                time.sleep(2)  # Attendi eventuale caricamento JS
                
                # Cerca elementi che indicano una pagina di configurazione/selezione campi
                # Pattern comuni: checkbox, form, select, campi da selezionare
                page_text = self.page.inner_text("body").lower()
                page_html = self.page.content()
                
                # Verifica se siamo su una pagina di configurazione (non ancora sulla Company Card)
                is_config_page = (
                    "seleziona" in page_text or
                    "selezionare" in page_text or
                    "campi" in page_text or
                    "configura" in page_text or
                    "opzioni" in page_text or
                    "checkbox" in page_html.lower() or
                    'type="checkbox"' in page_html or
                    "form" in page_html.lower() and "select" in page_html.lower()
                ) and "/Storage/Document/" not in url_dopo_step3
                
                if is_config_page:
                    print("   ✅ Pagina di configurazione rilevata! Seleziono i campi richiesti...")
                    
                    # Campi da selezionare per il calcolo dimensione d'impresa
                    campi_da_selezionare = [
                        "Dipendenti",
                        "Fatturato", 
                        "Totale Attività"
                    ]
                    
                    # Cerca e seleziona ogni campo
                    campi_selezionati = 0
                    for campo_nome in campi_da_selezionare:
                        try:
                            # Metodo 1: Cerca checkbox o input con label contenente il nome del campo
                            # Pattern: label con testo "Dipendenti", "Fatturato", "Totale Attività"
                            selettori_campo = [
                                f'input[type="checkbox"][id*="{campo_nome.lower()}" i]',
                                f'input[type="checkbox"][name*="{campo_nome.lower()}" i]',
                                f'input[type="checkbox"][value*="{campo_nome.lower()}" i]',
                                f'label:has-text("{campo_nome}") input[type="checkbox"]',
                                f'label:has-text("{campo_nome}") + input[type="checkbox"]',
                                f'//label[contains(text(), "{campo_nome}")]/following-sibling::input[@type="checkbox"]',
                                f'//label[contains(text(), "{campo_nome}")]/preceding-sibling::input[@type="checkbox"]',
                                f'//input[@type="checkbox"][following-sibling::label[contains(text(), "{campo_nome}")]]',
                                f'//input[@type="checkbox"][preceding-sibling::label[contains(text(), "{campo_nome}")]]',
                            ]
                            
                            campo_trovato = False
                            for sel in selettori_campo:
                                try:
                                    if sel.startswith('//'):
                                        # XPath
                                        checkbox = self.page.locator(f'xpath={sel}').first
                                    else:
                                        # CSS selector
                                        checkbox = self.page.locator(sel).first
                                    
                                    if checkbox.count() > 0 and checkbox.is_visible(timeout=2000):
                                        # Verifica se è già selezionato
                                        is_checked = checkbox.is_checked()
                                        if not is_checked:
                                            checkbox.check()
                                            print(f"   ✅ Campo '{campo_nome}' selezionato (selettore: {sel[:50]})")
                                        else:
                                            print(f"   ✅ Campo '{campo_nome}' già selezionato")
                                        campo_trovato = True
                                        campi_selezionati += 1
                                        break
                                except Exception:
                                    continue
                            
                            if not campo_trovato:
                                print(f"   ⚠️  Campo '{campo_nome}' non trovato con selettori standard, provo ricerca generica...")
                                # Metodo 2: Cerca nel testo della pagina e risali al checkbox più vicino
                                try:
                                    label_elem = self.page.get_by_text(campo_nome, exact=False).first
                                    if label_elem and label_elem.is_visible(timeout=2000):
                                        # Cerca checkbox nelle vicinanze
                                        parent = label_elem.locator('xpath=ancestor::*[contains(@class, "form-group") or contains(@class, "field") or contains(@class, "checkbox")]').first
                                        if parent.count() > 0:
                                            checkbox = parent.locator('input[type="checkbox"]').first
                                            if checkbox.count() > 0:
                                                if not checkbox.is_checked():
                                                    checkbox.check()
                                                    print(f"   ✅ Campo '{campo_nome}' selezionato (ricerca generica)")
                                                else:
                                                    print(f"   ✅ Campo '{campo_nome}' già selezionato (ricerca generica)")
                                                campo_trovato = True
                                                campi_selezionati += 1
                                except Exception as gen_err:
                                    print(f"   ⚠️  Ricerca generica fallita per '{campo_nome}': {gen_err}")
                        
                        except Exception as campo_err:
                            print(f"   ⚠️  Errore selezione campo '{campo_nome}': {campo_err}")
                            continue
                    
                    print(f"   📊 Campi selezionati: {campi_selezionati}/{len(campi_da_selezionare)}")
                    
                    # Cerca e clicca il bottone di conferma/invio (es. "Conferma", "Genera", "Richiedi", "Invia")
                    try:
                        bottone_conferma_selettori = [
                            'button:has-text("Conferma")',
                            'button:has-text("Genera")',
                            'button:has-text("Richiedi")',
                            'button:has-text("Invia")',
                            'button[type="submit"]',
                            'input[type="submit"]',
                            'button.btn-primary',
                            'button.btn-success',
                            '.btn-primary',
                            '.btn-success'
                        ]
                        
                        bottone_conferma_trovato = False
                        for btn_sel in bottone_conferma_selettori:
                            try:
                                btn = self.page.locator(btn_sel).first
                                if btn.count() > 0 and btn.is_visible(timeout=2000):
                                    btn.click()
                                    print(f"   ✅ Bottone conferma cliccato (selettore: {btn_sel})")
                                    bottone_conferma_trovato = True
                                    # Attendi caricamento nuova pagina
                                    self.page.wait_for_load_state("domcontentloaded")
                                    time.sleep(2)
                                    url_dopo_step3 = self.page.url
                                    print(f"   📍 URL dopo conferma: {url_dopo_step3}")
                                    break
                            except Exception:
                                continue
                        
                        if not bottone_conferma_trovato:
                            print("   ⚠️  Bottone conferma non trovato (forse la selezione è automatica)")
                    except Exception as btn_err:
                        print(f"   ⚠️  Errore click bottone conferma: {btn_err}")
                else:
                    print("   ℹ️  Nessuna pagina di configurazione rilevata (forse selezione automatica o già configurata)")
            
            except Exception as config_err:
                print(f"   ⚠️  Errore gestione pagina configurazione (non critico): {config_err}")
                # Non bloccare l'esecuzione, continua comunque
            
            # VERIFICA FINALE CRITICA: dobbiamo essere sulla Company Card Completa
            # Escludi esplicitamente DocumentUnavailable
            if "DocumentUnavailable" in url_dopo_step3:
                print(f"   ❌ ERRORE CRITICO: Documento non disponibile!")
                print(f"      URL ottenuto: {url_dopo_step3}")
                raise Exception(f"Documento 'Company Card Completa' non disponibile per questo CF. URL: {url_dopo_step3}")
            elif "/Storage/Document/" not in url_dopo_step3:
                print(f"   ❌ ERRORE CRITICO: Non siamo sulla Company Card Completa!")
                print(f"      URL atteso: contenente '/Storage/Document/'")
                print(f"      URL attuale: {url_dopo_step3}")
                # Controlla anche il titolo della pagina
                try:
                    page_title = self.page.title()
                    print(f"      Titolo pagina: {page_title}")
                    if "Company Card" not in page_title:
                        raise Exception(f"STEP 3 fallito: non siamo sulla Company Card Completa. URL: {url_dopo_step3}, Titolo: {page_title}")
                except Exception as title_err:
                    raise Exception(f"STEP 3 fallito: non siamo sulla Company Card Completa. URL: {url_dopo_step3}. Errore verifica titolo: {title_err}")
            else:
                print(f"   ✅ VERIFICATO: Siamo sulla Company Card Completa (URL contiene '/Storage/Document/')")

            # STEP 4: Apri tab "Bilanci" se presente (i dati finanziari sono spesso lì)
            print("📊 STEP 4: Apertura tab 'Bilanci' (se presente)...")
            try:
                # Cerca tab "Bilanci" usando get_by_text (Playwright) e CSS selectors
                tab_trovato = False
                # Metodo 1: Playwright locator get_by_text
                try:
                    tab_loc = self.page.get_by_text("Bilanci", exact=False).first
                    if tab_loc and tab_loc.is_visible(timeout=3000):
                        tab_loc.click()
                        print("   ✅ Tab 'Bilanci' aperto (via get_by_text)")
                        tab_trovato = True
                        time.sleep(2)  # Attendi caricamento JS
                except:
                    pass
                
                # Metodo 2: CSS selectors fallback
                if not tab_trovato:
                    tab_selettori = [
                        '[data-tab="bilanci"]',
                        '[data-tab="Bilanci"]',
                        '.tab[data-tab*="bilanci" i]',
                        '*[class*="bilanci" i][role="tab"]',
                        'button[class*="bilanci" i]',
                        'a[class*="bilanci" i]',
                    ]
                    for sel in tab_selettori:
                        try:
                            tab_btn = self.page.wait_for_selector(sel, timeout=2000)
                            if tab_btn and tab_btn.is_visible():
                                tab_btn.click()
                                print(f"   ✅ Tab 'Bilanci' aperto (selettore CSS: {sel[:50]})")
                                tab_trovato = True
                                time.sleep(2)  # Attendi caricamento JS
                                break
                        except:
                            continue
                
                if not tab_trovato:
                    print("   ⚠️  Tab 'Bilanci' non trovato (forse dati già visibili o struttura diversa)")
            except Exception as tab_err:
                print(f"   ⚠️  Errore apertura tab Bilanci (non critico): {tab_err}")
            
            # STEP 5: Estrai dati dalla pagina attuale (Company Card con tab Bilanci aperto)
            print("📊 STEP 5: Estrazione dati dalla pagina web...")
            
            # 5a) TENTATIVO 1: Estrazione DOM diretta con XPath (più robusto della sola regex)
            try:
                dati_estratti = self._estrai_dati_finanziari_da_dom(self.page, codice_fiscale)
            except Exception as dom_err:
                print(f"   ⚠️  Estrazione DOM non riuscita: {dom_err}")
                dati_estratti = {"cf": codice_fiscale, "personale": None, "fatturato": None, "attivo": None, "stato_dati": "assenti", "fonte": "pagina_web"}
            
            # 5b) TENTATIVO 2: Se DOM non ha trovato nulla, fallback a regex su HTML
            if (dati_estratti.get("personale") is None and dati_estratti.get("fatturato") is None and dati_estratti.get("attivo") is None):
                print("   ⚠️  DOM non ha restituito valori → fallback regex su HTML")
                html_content = self.page.content()
                dati_estratti = self._estrai_dati_finanziari_da_pagina(html_content, codice_fiscale)
            
            print(f"✅ Dati estratti: {dati_estratti}")
            
            return dati_estratti
            
        except Exception as e:
            # ERRORE CRITICO: Se è un errore di navigazione/bottone/pagina, PROPAGA invece di restituire dict
            # Questi errori devono BLOCCARE il processo, non continuare con dati vuoti
            error_msg = str(e).lower()
            # Frasi specifiche che indicano errori CRITICI (blocca processo)
            errori_critici = [
                "bottone 'richiedi'",
                "richiedi.*non trovato",
                "pagina errata dopo click",
                "non siamo sulla company card",
                "container.*trovato.*bottone.*mancante",
                "impossibile continuare",
                "step 3 fallito",
                "bottone.*company card.*non trovato"
            ]
            
            # Verifica se contiene una frase critica (match parziale più preciso)
            is_critico = (
                ("bottone" in error_msg and ("richiedi" in error_msg or "non trovato" in error_msg)) or
                "pagina errata" in error_msg or
                "non siamo sulla company card" in error_msg or
                "impossibile continuare" in error_msg or
                "step 3 fallito" in error_msg or
                ("container" in error_msg and "trovato" in error_msg and "mancante" in error_msg)
            )
            
            if is_critico:
                print(f"❌ ERRORE CRITICO (propago): {e}")
                import traceback
                traceback.print_exc()
                # PROPAGA l'eccezione per bloccare il processo
                raise
            
            # Per altri errori non critici, restituisci dict (es. dati finanziari non trovati nella pagina)
            print(f"❌ Errore estrazione dati web (non critico): {e}")
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
            # Normalizza spazi non standard e separatori (nbsp, thin space)
            html_norm = (html_content
                .replace('\u00A0', ' ')
                .replace('&nbsp;', ' ')
                .replace('\u202F', ' ')
                .replace('\u2009', ' ')
            )
            # Helper per normalizzare numeri: rimuove separatori migliaia (., spazio) e converte virgola in punto
            def parse_num(s: str) -> float:
                cleaned = s.replace('.', '').replace(' ', '').replace('\u00A0', '').replace('\u202F', '').replace('\u2009', '')
                cleaned = cleaned.replace(',', '.')
                return float(cleaned)
            # Helper per label con tag HTML in mezzo (es. "VALORE <b>DELLA</b> PRODUZIONE")
            def label_pat(label: str) -> str:
                parts = re.split(r"\s+", label.strip())
                return r"\s+".join([re.escape(p) for p in parts[:-1]] + [re.escape(parts[-1])]).replace(r"\s+", r"\s+(?:<[^>]+>\s*)*")
            # Cerca pattern comuni per dati finanziari
            personale = None
            fatturato = None
            attivo = None
            
            # Pattern per personale: cerca "DIPENDENTI" nella tabella sintesi bilancio
            # Priorità a "DIPENDENTI" esatto (come nella tabella), poi fallback generico
            numero = r"([0-9][0-9\.\s\u00A0\u202F\u2009]*?,?[0-9]{0,2})"
            personale_patterns = [
                rf'DIPENDENTI[^>]*?>\s*{numero}',
                rf'DIPENDENTI[^<]*?<td[^>]*>{numero}',
                rf'DIPENDENTI[\s\S]{{0,200}}?{numero}\s*(?:</td>|</div>|2024)',
                rf'{numero}\s*(?:ULA|dipendenti|personale)',
                rf'personale[:\s]*{numero}',
                rf'dipendenti[:\s]*{numero}'
            ]
            
            for pattern in personale_patterns:
                match = re.search(pattern, html_norm, re.IGNORECASE)
                if match:
                    try:
                        personale = parse_num(match.group(1))
                        print(f"   ✅ Personale (DIPENDENTI) trovato: {personale}")
                        break
                    except ValueError:
                        continue
            
            # Pattern per fatturato
            # NOTE: evitiamo pattern generici in € che catturano capitale sociale. Copriamo tabelle <td> e label con tag.
            lp_fatt = label_pat("FATTURATO")
            lp_ricavi = label_pat("RICAVI")
            lp_val_prod = label_pat("VALORE DELLA PRODUZIONE")
            lp_ricavi_prest = label_pat("RICAVI DELLE VENDITE E DELLE PRESTAZIONI")
            fatturato_patterns = [
                rf'{lp_fatt}[^<]*?<td[^>]*>\s*{numero}',
                rf'{lp_ricavi}[^<]*?<td[^>]*>\s*{numero}',
                rf'{lp_val_prod}[^<]*?<td[^>]*>\s*{numero}',
                rf'{lp_ricavi_prest}[^<]*?<td[^>]*>\s*{numero}',
                rf'fatturato[:\s]*{numero}',
                rf'ricavi[:\s]*{numero}',
                rf'valore\s+della\s+produzione[:\s]*{numero}',
                rf'valore\s+produzione[:\s]*{numero}',
                rf'ricavi\s+delle\s+vendite\s+e\s+delle\s+prestazioni[:\s]*{numero}',
                rf'ricavi\s+vendite[:\s]*{numero}'
            ]
            
            for pattern in fatturato_patterns:
                match = re.search(pattern, html_norm, re.IGNORECASE)
                if match:
                    candidato = parse_num(match.group(1))
                    # Heuristica: il fatturato plausibile è in genere > 50.000 € per società attive;
                    # se < 50k manteniamo ma proviamo ancora altri pattern per cercare un valore più credibile.
                    if candidato >= 50000:
                        fatturato = candidato
                        break
                    else:
                        fatturato = candidato  # tieni come fallback, ma non interrompere: cerca un valore migliore
            
            # Pattern per attivo: cerca "TOTALE ATTIVITÀ" nella tabella sintesi bilancio
            # Priorità a "TOTALE ATTIVITÀ" esatto (come nella tabella), poi fallback generico
            attivo_patterns = [
                rf'TOTALE\s+ATTIVIT[ÀA][^>]*?>\s*{numero}',
                rf'TOTALE\s+ATTIVIT[ÀA][^<]*?<td[^>]*>\s*{numero}',
                rf'TOTALE\s+ATTIVIT[ÀA][\s\S]{{0,200}}?{numero}\s*(?:</td>|</div>|2024)',
                rf'attivo[:\s]*{numero}',
                rf'totale\s*attivo[:\s]*{numero}',
                rf'bilancio[:\s]*{numero}'
            ]
            
            for pattern in attivo_patterns:
                match = re.search(pattern, html_norm, re.IGNORECASE)
                if match:
                    try:
                        attivo = parse_num(match.group(1))
                        print(f"   ✅ Attivo (TOTALE ATTIVITÀ) trovato: {attivo:,.2f}")
                        break
                    except ValueError:
                        continue
            
            # Raccogli anche valori grezzi aggiuntivi per debug/validazione
            raw_vals = {}
            raw_text = {}
            def estrai_con_varianti(nome_chiave: str, varianti_labels: list):
                nonlocal raw_vals
                for v in varianti_labels:
                    pat = rf"{v}[:\s]*{numero}"
                    m = re.search(pat, html_norm, re.IGNORECASE)
                    if m:
                        try:
                            raw_vals[nome_chiave] = parse_num(m.group(1))
                            return
                        except Exception:
                            continue
            def estrai_testo(nome_chiave: str, varianti_labels: list):
                """Estrae testo alfanumerico dopo una label (tollerando tag HTML)."""
                nonlocal raw_text
                for v in varianti_labels:
                    pat = rf"{label_pat(v)}\s*[:\-]?\s*(?:</?[^>]+>\s*)*([^<\n\r]+)"
                    m = re.search(pat, html_norm, re.IGNORECASE)
                    if m:
                        value = m.group(1).strip()
                        # pulizia minima
                        value = re.sub(r"\s+", " ", value)
                        raw_text[nome_chiave] = value
                        return
            # Sezione sintesi bilancio e legali (subset utile)
            estrai_con_varianti("ricavi", ["ricavi", "ricavi delle vendite e delle prestazioni", "ricavi vendite"]) 
            estrai_con_varianti("valore_produzione", ["valore della produzione", "valore produzione"]) 
            estrai_con_varianti("cash_flow", ["cash flow"]) 
            estrai_con_varianti("utile_perdita", ["utile/perdita", "utile o perdita", "risultato d'esercizio"]) 
            estrai_con_varianti("patrimonio_netto", ["patrimonio netto"]) 
            estrai_con_varianti("immobilizzazioni", ["immobilizzazioni"]) 
            estrai_con_varianti("tfr", ["tfr", "trattamento di fine rapporto"]) 
            estrai_con_varianti("capitale_sociale_deliberato", ["capitale sociale deliberato"]) 
            estrai_con_varianti("capitale_sociale_sottoscritto", ["capitale sociale sottoscritto"]) 
            estrai_con_varianti("capitale_sociale_versato", ["capitale sociale versato"]) 

            # Dati legali / impresa (testuali)
            estrai_testo("codice_fiscale", ["codice fiscale"]) 
            estrai_testo("partita_iva", ["partita iva"]) 
            estrai_testo("cciaa_rea", ["cciaa / rea", "cciaa", "rea"]) 
            estrai_testo("data_costituzione", ["data costituzione"]) 
            estrai_testo("data_inizio_attivita", ["data inizio attività", "data inizio attivita"]) 
            estrai_testo("natura_giuridica", ["natura giuridica"]) 
            estrai_testo("stato_attivita", ["stato attività", "stato attivita"]) 
            estrai_testo("sede_legale", ["sede legale"]) 
            estrai_testo("pec", ["email certificata (pec)", "pec"]) 
            estrai_testo("forma_amministrativa", ["forma amministrativa"]) 
            estrai_con_varianti("numero_amministratori", ["numero amministratori in carica"]) 

            # Dipendenti e UL
            estrai_con_varianti("addetti_attuali", ["addetti attuali"]) 
            estrai_con_varianti("anno_rilevazione_addetti", ["anno rilevazione"]) 
            estrai_con_varianti("valore_medio_addetti", ["valore medio addetti"]) 

            # Bilancio multi-anno (principali voci)
            estrai_con_varianti("totale_passivita", ["totale passività", "totale passivita"]) 
            estrai_con_varianti("debiti_banche", ["debiti verso banche"]) 
            estrai_con_varianti("debiti_fornitori", ["debiti verso fornitori"]) 
            estrai_con_varianti("ebitda", ["margine operativo lordo", "ebitda"]) 
            estrai_con_varianti("ebit", ["ebit", "risultato operativo"]) 
            estrai_con_varianti("oneri_finanziari", ["oneri finanziari"]) 
            estrai_con_varianti("proventi_finanziari", ["proventi finanziari"]) 
            estrai_con_varianti("utile_ante_imposte", ["utile ante imposte"]) 

            # Determina stato dati
            if personale is not None and fatturato is not None and attivo is not None:
                stato_dati = "completi"
            elif personale is not None or fatturato is not None or attivo is not None:
                stato_dati = "parziali"
            else:
                stato_dati = "assenti"
            
            risultato = {
                "cf": cf,
                "personale": personale,
                "fatturato": fatturato,
                "attivo": attivo,
                "anno_riferimento": "N/D",
                "stato_dati": stato_dati,
                "fonte": "pagina_web",
                "valori_grezzi": raw_vals,
                "valori_grezzi_testo": raw_text
            }

            # Dump di debug automatico se dati non completi o DEBUG abilitato
            try:
                import os, json
                debug_on = os.environ.get("CRIBIS_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
                if debug_on or stato_dati != "completi":
                    from datetime import datetime
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    base = os.path.join(os.getcwd(), "downloads", "debug")
                    os.makedirs(base, exist_ok=True)
                    html_path = os.path.join(base, f"{cf}_{ts}.html")
                    json_path = os.path.join(base, f"{cf}_{ts}.json")
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(risultato, f, ensure_ascii=False, indent=2)
                    print(f"   🧪 DEBUG salvato: {html_path} | {json_path}")
            except Exception as _:
                pass

            return risultato
            
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

    # METODO DEPRECATO: non più usato (estrazione diretta dal DOM più efficace)
    # Il metodo _estrai_dati_finanziari_da_pdf è stato rimosso
    # Motivo: estrazione DOM più veloce, affidabile e senza timeout

    def _estrai_dati_finanziari_da_dom(self, page, cf: str) -> dict:
        """
        Estrae i dati finanziari leggendo direttamente dal DOM con XPath (Company Card).
        
        Struttura standard della tabella:
        - Tabella: table.itrade-table (o table.table-responsive.itrade-list.itrade-table)
        - Tbody: tbody.steel
        - Righe: ogni riga ha un <td> con il label nella prima colonna
        - Valori: 3 <td> seguenti con valori per 2024, 2023, 2022 (primo = 2024)
        
        Campi da estrarre:
        - Dipendenti: personale (ULA)
        - Fatturato: fatturato
        - Totale Attività: attivo
        
        Se una cella è vuota, il dato non è disponibile (None).
        """
        def norm_num(s: str):
            """Normalizza stringa numerica: rimuove separatori migliaia e converte virgola in punto."""
            if s is None or not s.strip():
                return None
            s = s.replace('\u00A0', ' ').replace('\u202F', ' ').replace('\u2009', ' ').strip()
            # Rimuove punti (separatori migliaia) e spazi, converte virgola in punto
            s = s.replace('.', '').replace(' ', '').replace(',', '.')
            try:
                return float(s)
            except:
                return None
        
        def estrai_valore_da_riga(label_testo: str, anno_index: int = 1) -> float:
            """
            Estrae il valore dalla riga della tabella che contiene il label specificato.
            
            Args:
                label_testo: Testo del label da cercare (es. "Dipendenti", "Fatturato", "Totale Attività")
                anno_index: Indice della colonna (1=2024, 2=2023, 3=2022). Default 1 (2024).
            
            Returns:
                float | None: Valore normalizzato o None se non trovato/vuoto
            """
            try:
                # XPath: trova la riga <tr> che contiene un <td> con il testo del label
                # Poi prendi il <td> all'indice specificato (primo dopo il label = 2024)
                # La struttura è: <tr><td>Label</td><td>2024</td><td>2023</td><td>2022</td></tr>
                xpath_riga = f"//tbody[@class='steel']//tr[td[normalize-space()='{label_testo}']]"
                
                # Prova prima con tbody.steel (struttura standard)
                riga = page.locator(f"xpath={xpath_riga}").first
                if riga.count() == 0:
                    # Fallback: cerca in qualsiasi tbody
                    xpath_riga_fallback = f"//table//tbody//tr[td[normalize-space()='{label_testo}']]"
                    riga = page.locator(f"xpath={xpath_riga_fallback}").first
                
                if riga.count() > 0:
                    # Prendi il <td> all'indice specificato (anno_index = 1 per 2024)
                    # Il primo <td> è il label (indice 0), quindi anno_index=1 è il secondo <td> (2024)
                    celle = riga.locator("td").all()
                    if len(celle) > anno_index:
                        cella_valore = celle[anno_index]
                        if cella_valore.is_visible(timeout=1000):
                            testo = (cella_valore.inner_text() or '').strip()
                            # Se la cella è vuota, il dato non è disponibile
                            if not testo:
                                return None
                            return norm_num(testo)
            except Exception as e:
                # Log silenzioso per debug (non blocca l'estrazione)
                pass
            return None
        
        # Estrai valori per anno 2024 (indice 1, primo dopo il label)
        # Nota: "Dipendenti" può essere scritto con maiuscole/minuscole variabili
        valore_dip = None
        for label_variante in ["Dipendenti", "DIPENDENTI", "dipendenti"]:
            valore_dip = estrai_valore_da_riga(label_variante, anno_index=1)
            if valore_dip is not None:
                break
        
        # Fatturato: cerca prima "Fatturato", poi fallback a "Ricavi" o "Valore della produzione"
        valore_fatturato = estrai_valore_da_riga("Fatturato", anno_index=1)
        if valore_fatturato is None:
            # Fallback: cerca "Ricavi"
            valore_ricavi = estrai_valore_da_riga("Ricavi", anno_index=1)
            if valore_ricavi is not None and valore_ricavi >= 50000:
                valore_fatturato = valore_ricavi
            else:
                # Fallback: cerca "Valore della produzione"
                valore_val_prod = estrai_valore_da_riga("Valore della produzione", anno_index=1)
                if valore_val_prod is not None and valore_val_prod >= 50000:
                    valore_fatturato = valore_val_prod
        
        # Totale Attività
        valore_attivo = estrai_valore_da_riga("Totale Attività", anno_index=1)
        if valore_attivo is None:
            # Fallback: cerca varianti
            for label_variante in ["TOTALE ATTIVITÀ", "Totale attività", "TOTALE ATTIVITA"]:
                valore_attivo = estrai_valore_da_riga(label_variante, anno_index=1)
                if valore_attivo is not None:
                    break
        
        # Assegna valori finali
        personale = valore_dip
        fatturato = valore_fatturato
        attivo = valore_attivo
        
        # Log risultati
        if personale is not None:
            print(f"   ✅ Personale (Dipendenti) trovato: {personale}")
        else:
            print(f"   ⚠️  Personale (Dipendenti) non disponibile")
        
        if fatturato is not None:
            print(f"   ✅ Fatturato trovato: {fatturato:,.2f}")
        else:
            print(f"   ⚠️  Fatturato non disponibile")
        
        if attivo is not None:
            print(f"   ✅ Attivo (Totale Attività) trovato: {attivo:,.2f}")
        else:
            print(f"   ⚠️  Attivo (Totale Attività) non disponibile")
        
        # Determina stato dati
        stato = "completi" if all(x is not None for x in [personale, fatturato, attivo]) else ("parziali" if any(x is not None for x in [personale, fatturato, attivo]) else "assenti")
        
        # DEBUG: Salva HTML se dati assenti o parziali
        if stato != "completi":
            try:
                import os, json
                from datetime import datetime
                html_content = page.content()
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                base = os.path.join(os.getcwd(), "downloads", "debug")
                os.makedirs(base, exist_ok=True)
                html_path = os.path.join(base, f"{cf}_{ts}_dom.html")
                json_path = os.path.join(base, f"{cf}_{ts}_dom.json")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "cf": cf,
                        "personale": personale,
                        "fatturato": fatturato,
                        "attivo": attivo,
                        "stato_dati": stato,
                        "fonte": "pagina_web_dom"
                    }, f, ensure_ascii=False, indent=2)
                print(f"   🧪 DEBUG DOM salvato: {html_path} | {json_path}")
            except Exception as debug_err:
                print(f"   ⚠️ Errore salvataggio debug: {debug_err}")
        
        return {
            "cf": cf,
            "personale": personale,
            "fatturato": fatturato,
            "attivo": attivo,
            "anno_riferimento": "2024",  # Usiamo sempre l'anno più recente (2024)
            "stato_dati": stato,
            "fonte": "pagina_web_dom"
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
            # Evita doppio download per lo stesso CF nella stessa sessione
            if codice_fiscale in self._pdf_downloaded_by_cf:
                return {"success": True, "path": None, "filename": None, "reason": "già_scaricato"}

            print(f"⬇️  STEP 5: Tentativo download PDF per {codice_fiscale}...")
            print(f"   📍 URL pagina corrente: {self.page.url}")

            # Guardia: siamo ancora nella pagina di ricerca o in pagina errore?
            current_url = (self.page.url or "").lower()
            if "#/search/company/" in current_url or "/storage/documentunavailable" in current_url:
                print("   ⚠️  Non siamo nella Company Card completa (pagina di ricerca o documento non disponibile).")
                return {
                    "success": False,
                    "reason": "non_nella_company_card",
                    "path": None,
                    "filename": None
                }
            
            # Assicura cartella downloads/
            downloads_dir = os.path.join(os.getcwd(), 'downloads')
            os.makedirs(downloads_dir, exist_ok=True)

            # Costruisci nome file
            from datetime import datetime
            data_str = datetime.now().strftime('%Y%m%d')
            filename = f"CompanyCard_{codice_fiscale}_{data_str}.pdf"
            target_path = os.path.join(downloads_dir, filename)

            # Se il file esiste già ed è >0, evita nuovi tentativi (idempotente)
            try:
                if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                    self._pdf_downloaded_by_cf.add(codice_fiscale)
                    return {"success": True, "path": target_path, "filename": filename, "reason": "gia_presente_su_disco"}
            except Exception:
                pass

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

            # Ricerca con backoff configurabile: usa env CRIBIS_PDF_FIND_MAX_S (default 30s)
            try:
                max_find_s = int(os.environ.get("CRIBIS_PDF_FIND_MAX_S", "30"))
            except Exception:
                max_find_s = 30
            # Distribuzione semplice dei tentativi: 5s, 5s, 10s, 10s,  
            # poi finché non superiamo il massimo consentito
            candidate_steps = [5, 5, 10, 10, 15, 20, 30]
            backoff_steps = []
            total = 0
            for s in candidate_steps:
                if total + s > max_find_s:
                    break
                backoff_steps.append(s)
                total += s
            if not backoff_steps:
                backoff_steps = [5]  # fallback minimo
            for wait_s in backoff_steps:
                # prova tutti i selettori ad ogni giro
                for idx, sel in enumerate(possibili_scarica, 1):
                    try:
                        print(f"   🔄 Tentativo {sel[:60]}...")
                        link_candidate = self.page.wait_for_selector(sel, timeout=3000)
                        if link_candidate and link_candidate.is_visible():
                            link = link_candidate
                            selettore_usato = sel
                            break
                    except Exception:
                        pass
                if link:
                    break
                print(f"   ⏳ Link 'Scarica' non ancora pronto, attendo {wait_s}s e riprovo...")
                time.sleep(wait_s)

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
            print("   🖱️  Click su link 'Scarica' (attendo evento download, timeout 3 minuti)...")
            # Ciclo retry su download + verifica dimensione file
            max_attempts = 3
            last_err = None
            for attempt in range(1, max_attempts + 1):
                try:
                    with self.page.expect_download(timeout=180000) as download_info:
                        link.click(force=True)
                    download = download_info.value
                    print("   ✅ Evento download ricevuto!")

                    print(f"   💾 Salvo PDF in: {target_path}")
                    download.save_as(target_path)

                    # Verifica file > 0
                    if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                        file_size = os.path.getsize(target_path)
                        print(f"   ✅ PDF salvato! Dimensione: {file_size:,} bytes")
                        self._pdf_downloaded_by_cf.add(codice_fiscale)
                        return {"success": True, "path": target_path, "filename": filename}
                    else:
                        print("   ⚠️  File vuoto o non presente dopo save_as - provo fallback diretto via href")
                        # Fallback diretto via href
                        try:
                            href = link.get_attribute('href')
                            if href:
                                if href.startswith('/'):
                                    href = f"{self.base_url}{href}"
                                print(f"   🌐 Download diretto via href: {href}")
                                resp = self.page.context.request.get(href, timeout=180000)
                                if resp.ok:
                                    with open(target_path, 'wb') as f:
                                        f.write(resp.body())
                                    if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                                        file_size = os.path.getsize(target_path)
                                        print(f"   ✅ PDF salvato via href! Dimensione: {file_size:,} bytes")
                                        self._pdf_downloaded_by_cf.add(codice_fiscale)
                                        return {"success": True, "path": target_path, "filename": filename}
                                else:
                                    print(f"   ❌ GET href fallita: status {resp.status}")
                        except Exception as href_err:
                            print(f"   ❌ Fallback href errore: {href_err}")
                        last_err = Exception("file_vuoto")
                except Exception as click_err:
                    print(f"   ❌ Errore durante click o download (tentativo {attempt}/{max_attempts}): {click_err}")
                    # Fallback diretto via href anche in caso di eccezione
                    try:
                        href = link.get_attribute('href')
                        if href:
                            if href.startswith('/'):
                                href = f"{self.base_url}{href}"
                            print(f"   🌐 Download diretto via href dopo eccezione: {href}")
                            resp = self.page.context.request.get(href, timeout=180000)
                            if resp.ok:
                                with open(target_path, 'wb') as f:
                                    f.write(resp.body())
                                if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                                    file_size = os.path.getsize(target_path)
                                    print(f"   ✅ PDF salvato via href! Dimensione: {file_size:,} bytes")
                                    self._pdf_downloaded_by_cf.add(codice_fiscale)
                                    return {"success": True, "path": target_path, "filename": filename}
                            else:
                                print(f"   ❌ GET href fallita: status {resp.status}")
                    except Exception as href_err:
                        print(f"   ❌ Fallback href errore: {href_err}")
                    last_err = click_err

                # Backoff tra tentativi
                wait_between = max(4, min(12, 6 * attempt))
                print(f"   🔁 Retry tra {wait_between}s...")
                time.sleep(wait_between)

            # Se arrivo qui, tutti i tentativi falliti
            raise last_err or Exception("Download fallito")

        except PlaywrightTimeout:
            # Se il file è già presente su disco, considera esito positivo idempotente
            if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                self._pdf_downloaded_by_cf.add(codice_fiscale)
                print("   ⚠️ TIMEOUT ma file presente su disco: considero scaricato")
                return {"success": True, "path": target_path, "filename": filename, "reason": "timeout_ma_presente"}
            print("   ❌ TIMEOUT: Download non completato entro 3 minuti")
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
    
    cribis = CribisNuovaRicerca(headless=False)
    risultato = cribis.cerca_associate(test_piva)
    
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
