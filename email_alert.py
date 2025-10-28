#!/usr/bin/env python3
"""
Sistema di Alert Email per RNA De Minimis
==========================================

Invia notifiche automatiche quando:
- Gli scraping RNA/Cribis falliscono
- I selettori HTML non funzionano più
- Si verificano errori critici

Email destinazione: portalepigreco@gmail.com
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime


class EmailAlert:
    """Gestore notifiche email per errori scraping"""
    
    def __init__(self):
        """Inizializza configurazione email"""
        # Credenziali email
        self.email_from = "portalepigreco@gmail.com"
        self.email_to = "portalepigreco@gmail.com"
        
        # Prova prima variabile d'ambiente, poi fallback con App Password Gmail
        self.password = os.environ.get('EMAIL_PASSWORD', 'wmbu rdgu tiyv ikpl')
        
        # Configurazione SMTP Gmail
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        
    def invia_alert_errore_rna(self, partita_iva, errore, dettagli=None, screenshot_path=None):
        """
        Invia alert per errore RNA
        
        Args:
            partita_iva (str): P.IVA ricercata
            errore (str): Messaggio di errore
            dettagli (dict): Dettagli aggiuntivi opzionali
            screenshot_path (str): Path screenshot di debug
        """
        subject = f"⚠️ ALERT RNA - Errore Scraping per {partita_iva}"
        
        body = f"""
🔴 ERRORE SCRAPING RNA
{'='*60}

⏰ Data/Ora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🏢 P.IVA: {partita_iva}
❌ Errore: {errore}

{'='*60}

POSSIBILI CAUSE:
- Il sito RNA.gov.it ha cambiato struttura HTML
- Selettori CSS/XPath non funzionano più
- Problemi di rete o timeout
- Cambiamenti nel form di ricerca

AZIONE RICHIESTA:
1. Verifica manualmente il sito: https://www.rna.gov.it/trasparenza/aiuti
2. Controlla screenshot allegato (se presente)
3. Aggiorna selettori in rna_deminimis_playwright.py

{'='*60}

DETTAGLI TECNICI:
"""
        
        if dettagli:
            for key, value in dettagli.items():
                body += f"\n{key}: {value}"
        
        body += f"""

{'='*60}

Sistema: RNA De Minimis Agente
Server: Render.com
Progetto: /rna-deminimis-agente
"""
        
        self._invia_email(subject, body, screenshot_path)
    
    def invia_alert_errore_cribis(self, partita_iva, errore, fase=None, screenshot_path=None):
        """
        Invia alert per errore Cribis
        
        Args:
            partita_iva (str): P.IVA ricercata
            errore (str): Messaggio di errore
            fase (str): Fase dove è avvenuto l'errore (login, ricerca, etc)
            screenshot_path (str): Path screenshot di debug
        """
        subject = f"⚠️ ALERT CRIBIS - Errore Scraping per {partita_iva}"
        
        body = f"""
🔴 ERRORE SCRAPING CRIBIS X
{'='*60}

⏰ Data/Ora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🏢 P.IVA: {partita_iva}
📍 Fase: {fase or 'Non specificata'}
❌ Errore: {errore}

{'='*60}

POSSIBILI CAUSE:
- Il sito Cribis X ha cambiato interfaccia
- Credenziali scadute o bloccate
- Selettori CSS/XPath non funzionano più
- Cambiamenti nel flusso di navigazione

AZIONE RICHIESTA:
1. Verifica manualmente Cribis X: https://www2.cribisx.com
2. Testa credenziali: CC838673 / (password in codice)
3. Controlla screenshot allegato (se presente)
4. Aggiorna selettori in cribis_nuova_ricerca.py o cribis_connector.py

{'='*60}

Sistema: RNA De Minimis Agente
Server: Render.com
Progetto: /rna-deminimis-agente
"""
        
        self._invia_email(subject, body, screenshot_path)
    
    def invia_alert_risultati_sospetti(self, partita_iva, motivo):
        """
        Invia alert per risultati anomali (non errori critici)
        
        Args:
            partita_iva (str): P.IVA ricercata
            motivo (str): Perché i risultati sono sospetti
        """
        subject = f"⚠️ Risultati Sospetti RNA - {partita_iva}"
        
        body = f"""
⚠️ RISULTATI SOSPETTI
{'='*60}

⏰ Data/Ora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🏢 P.IVA: {partita_iva}
🔍 Motivo: {motivo}

{'='*60}

Questa è una notifica informativa, non un errore critico.
Verifica manualmente se necessario.

Sistema: RNA De Minimis Agente
"""
        
        self._invia_email(subject, body)
    
    def _invia_email(self, subject, body, attachment_path=None):
        """
        Invia email con SMTP Gmail
        
        Args:
            subject (str): Oggetto email
            body (str): Corpo email
            attachment_path (str): Path file da allegare (screenshot)
        """
        try:
            # Crea messaggio
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            msg['Subject'] = subject
            
            # Aggiungi corpo
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Aggiungi allegato se presente
            if attachment_path and os.path.exists(attachment_path):
                try:
                    with open(attachment_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename={os.path.basename(attachment_path)}'
                        )
                        msg.attach(part)
                    print(f"📎 Allegato aggiunto: {attachment_path}")
                except Exception as e:
                    print(f"⚠️ Errore allegato: {str(e)}")
            
            # Connessione SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            
            # Login
            server.login(self.email_from, self.password)
            
            # Invia
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email inviata con successo a {self.email_to}")
            print(f"   Oggetto: {subject}")
            return True
            
        except Exception as e:
            # Se l'invio email fallisce, logga ma non bloccare l'applicazione
            print(f"❌ Errore invio email: {str(e)}")
            return False


# Istanza globale per uso semplice
_alert_instance = None

def get_alert():
    """Ottieni istanza singleton EmailAlert"""
    global _alert_instance
    if _alert_instance is None:
        _alert_instance = EmailAlert()
    return _alert_instance


# Funzioni di utilità per uso rapido
def alert_rna_error(partita_iva, errore, **kwargs):
    """Shortcut per alert errore RNA"""
    get_alert().invia_alert_errore_rna(partita_iva, errore, **kwargs)

def alert_cribis_error(partita_iva, errore, **kwargs):
    """Shortcut per alert errore Cribis"""
    get_alert().invia_alert_errore_cribis(partita_iva, errore, **kwargs)

def alert_risultati_sospetti(partita_iva, motivo):
    """Shortcut per alert risultati sospetti"""
    get_alert().invia_alert_risultati_sospetti(partita_iva, motivo)


# Test del modulo
if __name__ == "__main__":
    print("🧪 TEST SISTEMA EMAIL ALERT")
    print("="*60)
    
    alert = EmailAlert()
    
    # Test 1: Alert errore RNA
    print("\n📧 Test 1: Invio alert errore RNA...")
    alert.invia_alert_errore_rna(
        partita_iva="02279960419",
        errore="Selettore input[name='cfBen'] non trovato",
        dettagli={
            "URL": "https://www.rna.gov.it/trasparenza/aiuti",
            "Timeout": "60s",
            "Browser": "Chromium/Playwright"
        }
    )
    
    # Test 2: Alert errore Cribis
    print("\n📧 Test 2: Invio alert errore Cribis...")
    alert.invia_alert_errore_cribis(
        partita_iva="02918700168",
        errore="Login fallito - campo username non trovato",
        fase="Login"
    )
    
    # Test 3: Alert risultati sospetti
    print("\n📧 Test 3: Invio alert risultati sospetti...")
    alert.invia_alert_risultati_sospetti(
        partita_iva="12345678901",
        motivo="0 aiuti trovati per P.IVA che dovrebbe averne"
    )
    
    print("\n" + "="*60)
    print("✅ Test completati - Controlla inbox portalepigreco@gmail.com")

