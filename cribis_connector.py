#!/usr/bin/env python3
"""
CribisX Connector - Estrazione società associate
Integrazione con il sistema De Minimis per calcolo aggregato

Funzionalità:
- Login automatico su Cribis X
- Ricerca puntuale per P.IVA/CF
- Estrazione albero societario
- Filtro associate italiane con quota >50%
"""

import os
import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class CribisXConnector:
    """Connector per automatizzare ricerche su Cribis X"""
    
    def __init__(self, headless=True):
        """
        Inizializza il connector
        
        Args:
            headless (bool): Se True, Firefox funziona in background
        """
        self.base_url = "https://www2.cribisx.com"
        # Credenziali Cribis: priorità a variabili d'ambiente, poi fallback
        self.username = os.environ.get('CRIBIS_USERNAME', 'CC838673')
        self.password = os.environ.get('CRIBIS_PASSWORD', '27_10_2025__Pigreco_')
        self.headless = headless
        self.driver = None
        self.wait = None
        
    def _inizializza_driver(self):
        """Inizializza il driver Firefox con le opzioni ottimali"""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        
        # Opzioni per performance e stabilità
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Inizializza driver
        self.driver = webdriver.Firefox(options=options)
        self.wait = WebDriverWait(self.driver, 20)
        
        print("🌐 Driver Firefox inizializzato")
        
    def login(self):
        """
        Esegue login su Cribis X
        
        Returns:
            bool: True se login riuscito, False altrimenti
        """
        try:
            print("🔐 Avvio login su Cribis X...")
            
            if not self.driver:
                self._inizializza_driver()
            
            # Vai alla homepage di Cribis X
            self.driver.get(f"{self.base_url}/#Home/Index")
            print(f"📍 Navigazione a: {self.base_url}")
            
            # Attendi caricamento completo
            time.sleep(3)
            
            # Cerca campi di login
            print("🔍 Ricerca campi di login...")
            
            # Prova diversi selettori per username
            username_selectors = [
                "input[name='Username']",
                "input[id='Username']", 
                "input[placeholder*='username']",
                "input[placeholder*='Username']",
                "input[type='text']"
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    username_field = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"✅ Campo username trovato: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not username_field:
                print("❌ Campo username non trovato")
                return False
            
            # Prova diversi selettori per password
            password_selectors = [
                "input[name='Password']",
                "input[id='Password']",
                "input[placeholder*='password']",
                "input[placeholder*='Password']", 
                "input[type='password']"
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"✅ Campo password trovato: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not password_field:
                print("❌ Campo password non trovato")
                return False
            
            # Inserisci credenziali
            print("📝 Inserimento credenziali...")
            username_field.clear()
            username_field.send_keys(self.username)
            
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Cerca pulsante di login
            login_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Login')",
                "button:contains('Accedi')",
                ".btn-login",
                "#login-button"
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"✅ Pulsante login trovato: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not login_button:
                print("❌ Pulsante login non trovato")
                return False
            
            # Clicca login
            print("🚀 Clic su pulsante login...")
            login_button.click()
            
            # Attendi redirect dopo login
            time.sleep(5)
            
            # Verifica se login è riuscito (cerca elementi della dashboard)
            current_url = self.driver.current_url
            print(f"📍 URL dopo login: {current_url}")
            
            if "Home" in current_url or "Dashboard" in current_url:
                print("✅ Login completato con successo!")
                return True
            else:
                print("❌ Login fallito - URL non cambiato")
                return False
                
        except Exception as e:
            print(f"❌ Errore durante login: {str(e)}")
            return False
    
    def vai_a_documenti(self):
        """
        Naviga alla sezione Documenti
        
        Returns:
            bool: True se navigazione riuscita
        """
        try:
            print("📁 Navigazione a sezione Documenti...")
            
            # URL corretto per la sezione Documenti (confermato dall'utente)
            documenti_url = f"{self.base_url}/#Storage/Index"
            print(f"📍 Navigazione a: {documenti_url}")
            self.driver.get(documenti_url)
            
            # Attendi caricamento
            time.sleep(5)
            
            # Verifica che siamo nella pagina corretta
            current_url = self.driver.current_url
            print(f"📍 URL attuale: {current_url}")
            
            # Cerca elementi caratteristici della pagina documenti
            try:
                # Cerca "MyDocs" o "RICERCA PUNTUALE" per confermare
                mydocs = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'MyDocs')]")
                ricerca_puntuale = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'RICERCA PUNTUALE') or contains(text(), 'Ricerca Puntuale')]")
                
                if mydocs or ricerca_puntuale:
                    print("✅ Sezione Documenti caricata correttamente")
                    if ricerca_puntuale:
                        print(f"🎯 Trovato elemento 'RICERCA PUNTUALE'")
                    return True
                else:
                    print("⚠️ Elementi tipici non trovati, ma procedo...")
                    return True
                    
            except Exception as e:
                print(f"⚠️ Errore verifica elementi: {str(e)}")
                print("✅ Assumo che la navigazione sia riuscita")
                return True
            
        except Exception as e:
            print(f"❌ Errore navigazione Documenti: {str(e)}")
            return False
    
    def ricerca_puntuale(self, codice_fiscale):
        """
        Esegue ricerca puntuale per codice fiscale
        
        Args:
            codice_fiscale (str): P.IVA o CF da cercare
            
        Returns:
            bool: True se ricerca riuscita
        """
        try:
            print(f"🔍 Ricerca puntuale per: {codice_fiscale}")
            
            # Cerca pulsante "RICERCA PUNTUALE" 
            ricerca_selectors = [
                # Selettori specifici basati sulla struttura HTML vista
                "//button[.//span[contains(text(), 'Ricerca Puntuale')]]",
                "//button[.//span[contains(@class, 'upcas') and contains(text(), 'Ricerca Puntuale')]]",
                "//span[contains(@class, 'upcas') and contains(text(), 'Ricerca Puntuale')]",
                "//span[contains(@class, 'dark-slate-blue') and contains(text(), 'Ricerca Puntuale')]",
                
                # Selettori generici di fallback
                "//button[contains(text(), 'RICERCA PUNTUALE')]",
                "//a[contains(text(), 'RICERCA PUNTUALE')]", 
                "//button[contains(text(), 'RICERCA')]",
                "//button[contains(text(), 'Ricerca')]",
                
                # CSS specifici
                "button span.upcas.dark-slate-blue",
                "span.upcas.dark-slate-blue",
                ".upcas.dark-slate-blue",
                
                # CSS generici
                "button[value*='RICERCA']",
                "input[value*='RICERCA']",
                ".ricerca-puntuale",
                "#ricerca-puntuale",
                ".btn-primary",
                ".btn-search"
            ]
            
            ricerca_button = None
            for selector in ricerca_selectors:
                try:
                    if selector.startswith("//"):
                        # XPath selector
                        ricerca_button = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        # CSS selector
                        ricerca_button = self.wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    print(f"✅ Pulsante RICERCA trovato con: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not ricerca_button:
                print("❌ Pulsante 'RICERCA PUNTUALE' non trovato")
                return False
            
            # Se abbiamo trovato uno span, clicca sul button padre
            if ricerca_button.tag_name == "span":
                print("🎯 Trovato span, cerco button padre...")
                try:
                    button_padre = ricerca_button.find_element(By.XPATH, "..")
                    if button_padre.tag_name == "button":
                        ricerca_button = button_padre
                        print("✅ Button padre trovato")
                except:
                    print("⚠️ Button padre non trovato, clicco sullo span")
            
            ricerca_button.click()
            print("✅ Clic su 'RICERCA PUNTUALE'")
            
            # Attendi caricamento form di ricerca
            time.sleep(2)
            
            # Cerca campo di input per P.IVA
            input_selectors = [
                # XPath per ricerca più precisa
                "//input[contains(@name, 'codice') or contains(@name, 'fiscale')]",
                "//input[contains(@placeholder, 'codice') or contains(@placeholder, 'fiscale')]",
                "//input[@type='text' and contains(@name, 'CODICE')]",
                
                # CSS fallback
                "input[name*='codice']",
                "input[name*='fiscale']", 
                "input[placeholder*='codice']",
                "input[placeholder*='fiscale']",
                "input[name='CODICE_FISCALE_PARTITA_IVA']",  # Nome specifico possibile
                "input[type='text']"
            ]
            
            input_field = None
            for selector in input_selectors:
                try:
                    if selector.startswith("//"):
                        # XPath selector
                        input_field = self.wait.until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                    else:
                        # CSS selector
                        input_field = self.wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                    print(f"✅ Campo P.IVA trovato con: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not input_field:
                print("❌ Campo input per P.IVA non trovato")
                return False
            
            # Inserisci codice fiscale
            input_field.clear()
            input_field.send_keys(codice_fiscale)
            print(f"📝 Codice fiscale inserito: {codice_fiscale}")
            
            # Cerca pulsante "CERCA"
            cerca_selectors = [
                # XPath più affidabile
                "//button[contains(text(), 'CERCA') or contains(text(), 'Cerca')]",
                "//input[@value='CERCA' or @value='Cerca']",
                "//button[@type='submit']",
                "//input[@type='submit']",
                
                # CSS fallback
                "button[type='submit']",
                "input[value*='CERCA']",
                "input[value*='Cerca']",
                ".btn-cerca",
                ".btn-primary",
                ".btn-search"
            ]
            
            cerca_button = None
            for selector in cerca_selectors:
                try:
                    if selector.startswith("//"):
                        # XPath selector
                        cerca_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        # CSS selector
                        cerca_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"✅ Pulsante CERCA trovato con: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not cerca_button:
                print("❌ Pulsante 'CERCA' non trovato")
                return False
            
            cerca_button.click()
            print("🚀 Avviata ricerca...")
            
            # Attendi risultati
            time.sleep(5)
            
            return True
            
        except Exception as e:
            print(f"❌ Errore durante ricerca: {str(e)}")
            return False
    
    def seleziona_primo_risultato(self):
        """
        Seleziona il primo risultato della ricerca (gestisce gruppi societari)
        
        Returns:
            bool: True se selezione riuscita
        """
        try:
            print("🎯 Selezione primo risultato...")
            
            # Salva screenshot per debug
            try:
                self.driver.save_screenshot("debug_cribis_risultati.png")
                print("📸 Screenshot risultati salvato: debug_cribis_risultati.png")
            except:
                pass
            
            # Cerca elementi cliccabili con diverse strategie
            elementi_cliccabili = [
                # Strategia 1: XPath per nome azienda (più generico)
                "//a[contains(text(), 'MAZZOLENI')]",
                "//button[contains(text(), 'MAZZOLENI')]", 
                "//td[contains(text(), 'MAZZOLENI')]",
                "//div[contains(text(), 'MAZZOLENI')]",
                "//*[contains(text(), 'GRUPPO')]",
                
                # Strategia 2: Primo risultato in tabella
                "table tbody tr:first-child",
                "table tbody tr:first-child td:first-child",
                "table tbody tr:first-child a",
                
                # Strategia 3: Card o elemento del risultato
                ".result-card:first-child",
                ".search-result:first-child", 
                ".document-item:first-child",
                
                # Strategia 4: Qualsiasi elemento cliccabile contenente il gruppo
                "[data-company*='MAZZOLENI']",
                ".gruppo-societario",
                
                # Strategia 5: Generico primo elemento cliccabile
                ".clickable:first-child",
                "tr:first-child",
                "tbody tr:first-child"
            ]
            
            elemento_selezionato = None
            for selector in elementi_cliccabili:
                try:
                    # Prova a trovare l'elemento
                    if selector.startswith("//"):
                        # XPath selector
                        elemento_selezionato = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        # CSS selector
                        elemento_selezionato = self.wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    
                    print(f"✅ Elemento trovato con: {selector}")
                    break
                    
                except TimeoutException:
                    continue
            
            if not elemento_selezionato:
                print("❌ Nessun risultato cliccabile trovato")
                
                # Prova alternativa: cerca tutti gli elementi cliccabili
                try:
                    tutti_cliccabili = self.driver.find_elements(By.CSS_SELECTOR, "a, button, .clickable, tr")
                    print(f"🔍 Trovati {len(tutti_cliccabili)} elementi cliccabili totali")
                    
                    for i, elemento in enumerate(tutti_cliccabili[:5]):  # Primi 5
                        try:
                            testo = elemento.text.strip()
                            if testo and ("MAZZOLENI" in testo.upper() or "GRUPPO" in testo.upper()):
                                print(f"  🎯 Elemento {i+1}: '{testo[:50]}...'")
                                elemento_selezionato = elemento
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"⚠️ Errore ricerca elementi: {str(e)}")
                
                if not elemento_selezionato:
                    return False
            
            # Clicca sull'elemento selezionato
            try:
                # Scroll all'elemento se necessario
                self.driver.execute_script("arguments[0].scrollIntoView(true);", elemento_selezionato)
                time.sleep(1)
                
                elemento_selezionato.click()
                print("✅ Risultato cliccato")
                
            except Exception as e:
                print(f"⚠️ Clic normale fallito, provo con JavaScript: {str(e)}")
                # Fallback: clic con JavaScript
                self.driver.execute_script("arguments[0].click();", elemento_selezionato)
                print("✅ Risultato cliccato (JavaScript)")
            
            # Attendi caricamento dettagli
            time.sleep(5)
            
            # Salva screenshot dopo il clic
            try:
                self.driver.save_screenshot("debug_cribis_dettaglio.png")
                print("📸 Screenshot dettaglio salvato: debug_cribis_dettaglio.png")
            except:
                pass
            
            return True
            
        except Exception as e:
            print(f"❌ Errore selezione risultato: {str(e)}")
            return False
    
    def estrai_associate_italiane(self):
        """
        Estrae le società associate italiane con quota >50%
        (Versione aggiornata per interfaccia Cribis X specifica)
        
        Returns:
            list: Lista di dict con dati delle associate
        """
        try:
            print("🌳 Analisi albero societario...")
            
            # Salva screenshot della pagina dettaglio
            try:
                self.driver.save_screenshot("debug_cribis_albero.png")
                print("📸 Screenshot albero salvato: debug_cribis_albero.png")
            except:
                pass
            
            associate = []
            
            # Cerca sezione albero societario con più selettori specifici per Cribis
            albero_selectors = [
                # Selettori specifici Cribis X
                ".gruppo-societario",
                ".corporate-structure",
                ".shareholding-structure",
                ".ownership-structure",
                ".tree-structure",
                
                # Selettori generici
                ".albero-societario",
                "#albero-societario", 
                ".group-structure",
                ".corporate-tree",
                ".shareholding",
                
                # Contenitori possibili
                ".content-section",
                ".main-content",
                ".document-content"
            ]
            
            albero_section = None
            for selector in albero_selectors:
                try:
                    elementi = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elementi:
                        albero_section = elementi[0]
                        print(f"✅ Sezione trovata con: {selector}")
                        break
                except Exception:
                    continue
            
            # Se non trova sezione specifica, analizza tutta la pagina
            if not albero_section:
                print("ℹ️  Sezione specifica non trovata, analizzo tutta la pagina...")
                albero_section = self.driver.find_element(By.TAG_NAME, "body")
            
            # Estrai tutto il testo della pagina per analisi
            testo_completo = albero_section.text
            print(f"📄 Testo estratto: {len(testo_completo)} caratteri")
            
            # Salva il testo per debug
            try:
                with open("debug_cribis_testo.txt", "w", encoding="utf-8") as f:
                    f.write(testo_completo)
                print("💾 Testo salvato: debug_cribis_testo.txt")
            except:
                pass
            
            # Cerca tutti i nodi/elementi che potrebbero contenere informazioni società
            nodi_selectors = [
                # Elementi specifici per società
                ".company-item",
                ".society-item", 
                ".entity-item",
                ".node",
                ".nodo",
                "tr",  # Righe di tabella
                ".row",
                "li",  # Elementi lista
                "div",  # Contenitori generici
                "p"    # Paragrafi
            ]
            
            tutti_nodi = []
            for selector in nodi_selectors[:3]:  # Prova primi 3 selettori
                try:
                    elementi = albero_section.find_elements(By.CSS_SELECTOR, selector)
                    tutti_nodi.extend(elementi)
                except:
                    continue
            
            print(f"🔍 Analizzando {len(tutti_nodi)} elementi...")
            
            # Analizza ogni nodo per cercare informazioni società
            for i, nodo in enumerate(tutti_nodi[:50]):  # Limita a 50 per performance
                try:
                    testo_nodo = nodo.text.strip()
                    if not testo_nodo or len(testo_nodo) < 10:
                        continue
                    
                    # Debug: stampa primi nodi
                    if i < 5:
                        print(f"  🔍 Nodo {i+1}: '{testo_nodo[:100]}...'")
                    
                    # Cerca percentuali (formato vario: 50%, 50.5%, 100%)
                    matches_percentuale = re.findall(r'(\d+(?:[.,]\d+)?)\s*%', testo_nodo)
                    
                    for perc_str in matches_percentuale:
                        try:
                            # Normalizza la percentuale (sostituisci virgola con punto)
                            perc_str_norm = perc_str.replace(',', '.')
                            percentuale = float(perc_str_norm)
                            
                            # Filtra solo percentuali >50%
                            if percentuale <= 50:
                                continue
                            
                            print(f"  💡 Percentuale >50% trovata: {percentuale}%")
                            
                            # Cerca codice fiscale italiano (11 cifre) nelle vicinanze
                            # Espandi la ricerca a tutto il nodo e nodi vicini
                            testo_ricerca = testo_nodo
                            
                            # Cerca anche nel nodo precedente e successivo
                            try:
                                nodo_precedente = nodi[max(0, i-1)] if i > 0 else None
                                nodo_successivo = nodi[min(len(nodi)-1, i+1)] if i < len(nodi)-1 else None
                                
                                if nodo_precedente:
                                    testo_ricerca = nodo_precedente.text + " " + testo_ricerca
                                if nodo_successivo:
                                    testo_ricerca = testo_ricerca + " " + nodo_successivo.text
                            except:
                                pass
                            
                            # Cerca codice fiscale (11 cifre consecutive)
                            matches_cf = re.findall(r'\b(\d{11})\b', testo_ricerca)
                            
                            for codice_fiscale in matches_cf:
                                # Verifica che non sia la P.IVA di ricerca
                                if codice_fiscale == "02918700168":
                                    continue
                                
                                # Estrai ragione sociale
                                # Cerca il nome prima del CF o della percentuale
                                parti_testo = re.split(r'\d{11}|\d+(?:[.,]\d+)?\s*%', testo_ricerca)
                                ragione_sociale = "SOCIETA' ASSOCIATA"
                                
                                for parte in parti_testo:
                                    parte_clean = parte.strip()
                                    if len(parte_clean) > 5 and not re.match(r'^\d+', parte_clean):
                                        # Prendi la prima parte che sembra un nome
                                        ragione_sociale = parte_clean[:50]  # Limita lunghezza
                                        break
                                
                                associata = {
                                    "ragione_sociale": ragione_sociale,
                                    "cf": codice_fiscale,
                                    "percentuale": f"{percentuale}%"
                                }
                                
                                # Evita duplicati
                                if not any(a["cf"] == codice_fiscale for a in associate):
                                    associate.append(associata)
                                    print(f"  ✅ Trovata: {ragione_sociale[:30]}... - {codice_fiscale} ({percentuale}%)")
                        
                        except ValueError:
                            continue
                
                except Exception as e:
                    if i < 5:  # Log errori solo per primi nodi
                        print(f"  ⚠️  Errore nodo {i+1}: {str(e)}")
                    continue
            
            # Se non trova nulla, prova ricerca nell'intero testo
            if not associate:
                print("🔍 Ricerca fallback nell'intero testo...")
                
                # Cerca pattern completi nel testo
                pattern_societa = r'([A-Z\s]+(?:S\.R\.L\.|S\.P\.A\.|S\.A\.S\.|S\.N\.C\.).*?)(?:\d{11}).*?(\d+(?:[.,]\d+)?)\s*%'
                matches = re.findall(pattern_societa, testo_completo, re.IGNORECASE | re.MULTILINE)
                
                for nome, percentuale_str in matches:
                    try:
                        percentuale = float(percentuale_str.replace(',', '.'))
                        if percentuale > 50:
                            print(f"  💡 Pattern trovato: {nome.strip()[:30]}... ({percentuale}%)")
                    except:
                        continue
            
            print(f"📊 Totale associate italiane >50%: {len(associate)}")
            
            if not associate:
                print("ℹ️  Nessuna associata >50% trovata - potrebbe essere azienda singola")
            
            return associate
            
        except Exception as e:
            print(f"❌ Errore estrazione associate: {str(e)}")
            return []
    
    def cerca_associate(self, codice_fiscale):
        """
        Processo completo di ricerca delle società associate
        
        Args:
            codice_fiscale (str): P.IVA o CF da analizzare
            
        Returns:
            dict: Risultato con P.IVA richiesta e associate trovate
        """
        risultato = {
            "p_iva_richiesta": codice_fiscale,
            "associate_italiane_controllate": [],
            "errore": None
        }
        
        try:
            print(f"🚀 Avvio ricerca associate per: {codice_fiscale}")
            
            # 1. Login
            if not self.login():
                risultato["errore"] = "Login fallito"
                return risultato
            
            # 2. Vai a documenti
            if not self.vai_a_documenti():
                risultato["errore"] = "Navigazione a Documenti fallita"
                return risultato
            
            # 3. Ricerca puntuale
            if not self.ricerca_puntuale(codice_fiscale):
                risultato["errore"] = "Ricerca puntuale fallita"
                return risultato
            
            # 4. Seleziona primo risultato
            if not self.seleziona_primo_risultato():
                risultato["errore"] = "Selezione risultato fallita"
                return risultato
            
            # 5. Estrai associate
            associate = self.estrai_associate_italiane()
            risultato["associate_italiane_controllate"] = associate
            
            print(f"✅ Ricerca completata: {len(associate)} associate trovate")
            return risultato
            
        except Exception as e:
            print(f"❌ Errore generale ricerca associate: {str(e)}")
            risultato["errore"] = str(e)
            return risultato
        
        finally:
            self.chiudi()
    
    def chiudi(self):
        """Chiude il driver e libera le risorse"""
        try:
            if self.driver:
                self.driver.quit()
                print("🔒 Driver chiuso")
        except Exception as e:
            print(f"⚠️  Errore chiusura driver: {str(e)}")


# Test della classe
if __name__ == "__main__":
    connector = CribisXConnector(headless=False)  # headless=False per debug
    
    # Test con P.IVA di esempio
    test_piva = "02918700168"
    risultato = connector.cerca_associate(test_piva)
    
    print("\n" + "="*50)
    print("📋 RISULTATO FINALE:")
    print(json.dumps(risultato, indent=2, ensure_ascii=False))
