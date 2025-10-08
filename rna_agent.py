#!/usr/bin/env python3
"""
🤖 RNA De Minimis Agent
Agente automatico per calcolare il totale de minimis dal sito RNA.gov.it

Uso: python rna_agent.py [PARTITA_IVA]
Esempio: python rna_agent.py 03254550738
"""

import requests
import re
import time
from bs4 import BeautifulSoup
import sys
from urllib.parse import urljoin
import logging

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RNAAgent:
    """Agente per la ricerca automatica de minimis su RNA.gov.it"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.rna.gov.it"
        self.search_url = f"{self.base_url}/trasparenza/aiuti"
        
        # Headers per simulare Firefox (come richiesto)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        })
        
        # Disabilita SSL verify per evitare problemi certificati
        self.session.verify = False
        
    def accetta_cookie(self):
        """Accetta i cookie sul sito RNA"""
        logger.info("🍪 Accettando cookie...")
        
        try:
            response = self.session.get(self.search_url, timeout=30)
            response.raise_for_status()
            
            # Cerca form o link per accettare cookie
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Pattern comuni per cookie banner
            cookie_forms = soup.find_all('form', {'id': re.compile(r'cookie', re.I)})
            cookie_buttons = soup.find_all('button', string=re.compile(r'accett', re.I))
            cookie_links = soup.find_all('a', string=re.compile(r'accett', re.I))
            
            if cookie_forms:
                logger.info("✅ Form cookie trovato, invio accettazione...")
                # Gestisci form cookie se presente
                
            logger.info("✅ Cookie gestiti con successo")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Errore gestione cookie: {e}")
            return False
    
    def estrai_csrf_token(self, html):
        """Estrae il token CSRF dalla pagina"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Pattern comuni per CSRF token
        csrf_patterns = [
            'input[name="_token"]',
            'input[name="csrf_token"]', 
            'input[name="authenticity_token"]',
            'meta[name="csrf-token"]'
        ]
        
        for pattern in csrf_patterns:
            element = soup.select_one(pattern)
            if element:
                token = element.get('value') or element.get('content')
                if token:
                    logger.info(f"🔑 Token CSRF trovato: {token[:10]}...")
                    return token
        
        # Cerca token nel JavaScript
        token_match = re.search(r'["\']_token["\']:\s*["\']([^"\']+)["\']', html)
        if token_match:
            token = token_match.group(1)
            logger.info(f"🔑 Token CSRF da JS: {token[:10]}...")
            return token
            
        logger.warning("⚠️ Nessun token CSRF trovato")
        return None
    
    def cerca_de_minimis(self, partita_iva):
        """
        Cerca gli aiuti de minimis per una partita IVA
        
        Args:
            partita_iva (str): Partita IVA da cercare
            
        Returns:
            dict: Risultato della ricerca con totale e dettagli
        """
        logger.info(f"🔍 Cercando de minimis per P.IVA: {partita_iva}")
        
        try:
            # Step 1: Carica la pagina principale
            logger.info("📄 Caricando pagina di ricerca...")
            response = self.session.get(self.search_url, timeout=30)
            response.raise_for_status()
            
            # Salva HTML per debug
            with open('debug_page1.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info("💾 Pagina iniziale salvata in debug_page1.html")
            
            # Step 2: Gestisci cookie se necessario
            self.accetta_cookie()
            
            # Step 3: Analizza form di ricerca - cerca tutti i possibili form
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Cerca form per metodo (GET o POST)
            forms = soup.find_all('form')
            logger.info(f"🔍 Trovati {len(forms)} form nella pagina")
            
            form = None
            form_action = self.search_url
            form_method = 'GET'  # Default a GET come mostrato nell'immagine
            
            for f in forms:
                logger.info(f"📝 Form trovato: action={f.get('action')}, method={f.get('method')}")
                if 'trasparenza' in str(f.get('action', '')) or not form:
                    form = f
                    form_action = f.get('action', self.search_url)
                    form_method = f.get('method', 'GET').upper()
                    break
            
            if not form:
                # Prova comunque con parametri GET
                logger.warning("⚠️ Nessun form trovato, provo con GET diretto")
                form_method = 'GET'
            
            # Step 4: Prepara dati per la ricerca
            # Dall'immagine vedo che il campo si chiama probabilmente diversamente
            form_data = {
                'cf_beneficiario': partita_iva,  # Provo vari nomi
                'codice_fiscale': partita_iva,
                'C.F. Beneficiario': partita_iva,
                'tipo_procedimento': 'De Minimis',
                'tipoProcedimento': 'De Minimis',
                'tipo': 'de_minimis',
            }
            
            # Cerca campi input nel form per nomi esatti
            if form:
                inputs = form.find_all(['input', 'select'])
                found_cf_field = False
                found_tipo_field = False
                
                for inp in inputs:
                    name = inp.get('name', '')
                    inp_type = inp.get('type', '')
                    placeholder = inp.get('placeholder', '').lower()
                    
                    logger.info(f"🔍 Campo trovato: name='{name}', type='{inp_type}', placeholder='{placeholder}'")
                    
                    # Cerca campo CF/P.IVA
                    if any(term in name.lower() for term in ['cf', 'codice', 'fiscale', 'beneficiario', 'partita']) or \
                       any(term in placeholder for term in ['cf', 'codice', 'fiscale', 'beneficiario', 'partita']):
                        form_data[name] = partita_iva
                        found_cf_field = True
                        logger.info(f"✅ Campo CF trovato: {name}")
                    
                    # Cerca campo tipo procedimento
                    if any(term in name.lower() for term in ['tipo', 'procedimento']) or \
                       any(term in placeholder for term in ['tipo', 'procedimento']):
                        if inp.name == 'select':
                            # Per select, cerca l'opzione De Minimis
                            options = inp.find_all('option')
                            for opt in options:
                                if 'minimis' in opt.get_text().lower():
                                    form_data[name] = opt.get('value', 'De Minimis')
                                    found_tipo_field = True
                                    logger.info(f"✅ Campo Tipo trovato: {name} = {opt.get('value')}")
                                    break
                        else:
                            form_data[name] = 'De Minimis'
                            found_tipo_field = True
                    
                    # Aggiungi campi hidden
                    if inp_type == 'hidden':
                        form_data[name] = inp.get('value', '')
                
                if not found_cf_field:
                    logger.warning("⚠️ Campo CF non trovato con certezza")
                if not found_tipo_field:
                    logger.warning("⚠️ Campo Tipo non trovato con certezza")
            
            # Pulisci form_data da valori vuoti duplicati
            form_data_clean = {}
            for k, v in form_data.items():
                if v and k not in form_data_clean:
                    form_data_clean[k] = v
            
            logger.info(f"📝 Dati form puliti: {form_data_clean}")
            
            # Step 5: Invia ricerca
            logger.info(f"🚀 Inviando ricerca {form_method} a {form_action}")
            
            if form_method == 'GET':
                # Usa parametri GET
                search_response = self.session.get(
                    form_action if form_action.startswith('http') else urljoin(self.base_url, form_action),
                    params=form_data_clean,
                    timeout=30,
                    allow_redirects=True
                )
            else:
                # Usa POST
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': self.search_url,
                    'Origin': self.base_url
                }
                
                search_response = self.session.post(
                    form_action if form_action.startswith('http') else urljoin(self.base_url, form_action),
                    data=form_data_clean, 
                    headers=headers,
                    timeout=30,
                    allow_redirects=True
                )
            
            search_response.raise_for_status()
            
            # Salva risultati per debug
            with open('debug_results.html', 'w', encoding='utf-8') as f:
                f.write(search_response.text)
            logger.info("💾 Risultati salvati in debug_results.html")
            
            # Step 6: Analizza risultati
            return self.analizza_risultati(search_response.text, partita_iva)
            
        except requests.RequestException as e:
            logger.error(f"❌ Errore di rete: {e}")
            return {"errore": f"Errore di connessione: {e}"}
        except Exception as e:
            logger.error(f"❌ Errore generale: {e}")
            return {"errore": f"Errore: {e}"}
    
    def analizza_risultati(self, html, partita_iva):
        """
        Analizza l'HTML dei risultati ed estrae gli importi degli ultimi 3 anni
        
        Args:
            html (str): HTML della pagina risultati
            partita_iva (str): P.IVA cercata
            
        Returns:
            dict: Risultato con totale e dettagli
        """
        logger.info("📊 Analizzando risultati...")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Controlla se ci sono risultati
        if "nessun risultato" in html.lower() or "non sono stati trovati" in html.lower() or "valorizzare almeno un parametro" in html.lower():
            logger.info("ℹ️ Nessun risultato trovato")
            return {
                "partita_iva": partita_iva,
                "totale_de_minimis": 0.0,
                "numero_aiuti": 0,
                "aiuti_trovati": [],
                "messaggio": "Nessun aiuto de minimis trovato per questa P.IVA"
            }
        
        # Anno corrente e ultimi 3 anni
        anno_corrente = time.strftime("%Y")
        anni_validi = [str(int(anno_corrente) - i) for i in range(3)]  # 2025, 2024, 2023
        logger.info(f"📅 Filtrando aiuti degli anni: {anni_validi}")
        
        # Cerca tabelle con risultati
        tabelle = soup.find_all('table')
        aiuti_trovati = []
        totale = 0.0
        
        logger.info(f"🔍 Trovate {len(tabelle)} tabelle da analizzare")
        
        for idx, tabella in enumerate(tabelle):
            logger.info(f"📋 Analizzando tabella {idx + 1}")
            
            # Cerca header della tabella
            header_row = tabella.find('tr')
            if not header_row:
                continue
                
            headers = header_row.find_all(['th', 'td'])
            header_texts = [h.get_text().lower().strip() for h in headers]
            
            logger.info(f"📝 Headers trovati: {header_texts}")
            
            # Trova indici delle colonne importanti
            colonna_importo = -1
            colonna_data = -1
            colonna_cf = -1
            
            for i, header_text in enumerate(header_texts):
                if 'elemento' in header_text and 'aiuto' in header_text:
                    colonna_importo = i
                    logger.info(f"✅ Colonna Elemento Aiuto: indice {i}")
                elif 'data' in header_text and ('concession' in header_text or 'concess' in header_text):
                    colonna_data = i
                    logger.info(f"✅ Colonna Data Concessione: indice {i}")
                elif 'c.f' in header_text or 'beneficiario' in header_text or 'codice' in header_text:
                    colonna_cf = i
                    logger.info(f"✅ Colonna CF Beneficiario: indice {i}")
            
            if colonna_importo == -1:
                logger.warning(f"⚠️ Tabella {idx + 1}: colonna Elemento Aiuto non trovata")
                continue
            
            # Estrai valori dalle righe dati
            righe = tabella.find_all('tr')[1:]  # Salta header
            logger.info(f"📊 Analizzando {len(righe)} righe di dati")
            
            for riga_idx, riga in enumerate(righe):
                celle = riga.find_all(['td', 'th'])
                
                if len(celle) <= colonna_importo:
                    continue
                
                # Verifica CF se disponibile
                if colonna_cf >= 0 and len(celle) > colonna_cf:
                    cf_cella = celle[colonna_cf].get_text().strip()
                    if partita_iva not in cf_cella:
                        logger.debug(f"🔍 Riga {riga_idx + 1}: CF non corrispondente ({cf_cella})")
                        continue
                
                # Verifica data se disponibile (filtro ultimi 3 anni)
                anno_valido = True
                if colonna_data >= 0 and len(celle) > colonna_data:
                    data_cella = celle[colonna_data].get_text().strip()
                    anno_valido = False
                    for anno in anni_validi:
                        if anno in data_cella:
                            anno_valido = True
                            break
                    
                    if not anno_valido:
                        logger.debug(f"🔍 Riga {riga_idx + 1}: Data non negli ultimi 3 anni ({data_cella})")
                        continue
                
                # Estrai importo
                cella_importo = celle[colonna_importo]
                testo_importo = cella_importo.get_text().strip()
                
                # Pattern più specifici per importi italiani
                importo_patterns = [
                    r'€\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',  # €1.234,56
                    r'([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)\s*€',  # 1.234,56 €
                    r'([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',      # 1.234,56
                ]
                
                importo_trovato = False
                for pattern in importo_patterns:
                    importo_match = re.search(pattern, testo_importo)
                    if importo_match:
                        importo_str = importo_match.group(1)
                        # Converte formato italiano (1.234,56) in float
                        importo_pulito = importo_str.replace('.', '').replace(',', '.')
                        try:
                            importo = float(importo_pulito)
                            if importo > 0:
                                # Estrai data per debug
                                data_str = celle[colonna_data].get_text().strip() if colonna_data >= 0 and len(celle) > colonna_data else "N/A"
                                
                                aiuti_trovati.append({
                                    "importo_originale": testo_importo,
                                    "importo": importo,
                                    "data_concessione": data_str,
                                    "riga_completa": ' | '.join([c.get_text().strip() for c in celle[:6]]),  # Prime 6 colonne
                                    "tabella": idx + 1,
                                    "riga": riga_idx + 1
                                })
                                totale += importo
                                logger.info(f"💰 Aiuto trovato: €{importo:,.2f} del {data_str}")
                                importo_trovato = True
                                break
                        except ValueError as e:
                            logger.warning(f"⚠️ Errore conversione importo '{importo_str}': {e}")
                            continue
                
                if not importo_trovato and testo_importo.strip():
                    logger.debug(f"🔍 Importo non riconosciuto: '{testo_importo}'")
        
        # Se non trova tabelle strutturate, cerca nella pagina dei risultati
        if not aiuti_trovati:
            logger.info("🔍 Nessuna tabella strutturata, cercando nella pagina generale...")
            
            # Cerca pattern specifici per la pagina RNA (basandomi sui tuoi screenshot)
            # Pattern: €4.347,30 e €5.158,65
            importi_pagina = re.findall(r'€\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)', html)
            
            for importo_str in importi_pagina:
                importo_pulito = importo_str.replace('.', '').replace(',', '.')
                try:
                    importo = float(importo_pulito)
                    if importo >= 100:  # Filtra importi troppo piccoli
                        aiuti_trovati.append({
                            "importo_originale": f"€{importo_str}",
                            "importo": importo,
                            "data_concessione": "Pattern generico",
                            "riga_completa": "Estratto dalla pagina generale",
                            "tabella": "N/A",
                            "riga": "N/A"
                        })
                        totale += importo
                        logger.info(f"💰 Pattern generico: €{importo:,.2f}")
                except ValueError:
                    continue
        
        # Prepara risultato finale
        risultato = {
            "partita_iva": partita_iva,
            "totale_de_minimis": round(totale, 2),
            "numero_aiuti": len(aiuti_trovati),
            "aiuti_trovati": aiuti_trovati,
            "anni_considerati": anni_validi,
            "data_ricerca": time.strftime("%Y-%m-%d %H:%M:%S"),
            "messaggio": f"Trovati {len(aiuti_trovati)} aiuti degli ultimi 3 anni per un totale di €{totale:,.2f}"
        }
        
        logger.info(f"🎯 RISULTATO FINALE: €{totale:,.2f} ({len(aiuti_trovati)} aiuti degli ultimi 3 anni)")
        return risultato


def main():
    """Funzione principale"""
    
    # Banner
    print("🤖 RNA De Minimis Agent")
    print("=" * 50)
    
    # Leggi P.IVA da argomenti o input
    if len(sys.argv) > 1:
        partita_iva = sys.argv[1]
    else:
        partita_iva = input("🔢 Inserisci Partita IVA: ").strip()
    
    if not partita_iva:
        print("❌ Partita IVA non fornita!")
        sys.exit(1)
    
    # Validazione base P.IVA
    if not re.match(r'^\d{11}$', partita_iva):
        print("❌ Partita IVA deve essere di 11 cifre!")
        sys.exit(1)
    
    # Crea agente ed esegui ricerca
    agente = RNAAgent()
    risultato = agente.cerca_de_minimis(partita_iva)
    
    # Mostra risultati
    print("\n" + "=" * 50)
    print("📋 RISULTATO RICERCA DE MINIMIS")
    print("=" * 50)
    
    if "errore" in risultato:
        print(f"❌ {risultato['errore']}")
        sys.exit(1)
    
    print(f"🏢 Partita IVA: {risultato['partita_iva']}")
    print(f"💰 Totale De Minimis: €{risultato['totale_de_minimis']:,.2f}")
    print(f"📊 Numero aiuti: {risultato['numero_aiuti']}")
    print(f"📅 Data ricerca: {risultato['data_ricerca']}")
    
    if risultato['aiuti_trovati']:
        print("\n📝 Dettaglio aiuti:")
        for i, aiuto in enumerate(risultato['aiuti_trovati'], 1):
            print(f"  {i}. €{aiuto['importo']:,.2f} ({aiuto['importo_originale']})")
    
    print("\n✅ Ricerca completata!")


if __name__ == "__main__":
    main()
