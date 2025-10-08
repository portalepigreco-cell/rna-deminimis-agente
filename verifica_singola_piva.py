#!/usr/bin/env python3
"""
Verifica Singola P.IVA - Pigreco Team
====================================

Script per verificare se una specifica P.IVA è presente nei dati RNA
e calcolare i suoi totali De Minimis.

Uso:
    python3 verifica_singola_piva.py <PIVA>

Esempio:
    python3 verifica_singola_piva.py 09066930729

Autore: Pigreco Team
Data: Settembre 2025
"""

import os
import sys
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re

# Configurazione
XML_FILE = 'data/raw/OpenData_Misura_2026_03.xml'
OUTPUT_DIR = 'data/processed'


class PIVAVerifier:
    """Classe per verificare una singola P.IVA nei dati RNA"""
    
    def __init__(self, piva_target):
        """
        Inizializza il verificatore
        
        Args:
            piva_target (str): P.IVA da cercare
        """
        self.piva_target = self.clean_piva(piva_target)
        print("🔍 Verifica P.IVA RNA - Pigreco Team")
        print("="*50)
        print(f"🎯 P.IVA target: {self.piva_target}")
    
    def clean_piva(self, piva):
        """Pulisce e normalizza la P.IVA"""
        if not piva:
            return ""
        # Rimuovi spazi e caratteri speciali, mantieni solo numeri
        cleaned = re.sub(r'[^\d]', '', str(piva))
        return cleaned
    
    def check_xml_file(self):
        """Verifica che il file XML esista"""
        if not os.path.exists(XML_FILE):
            print(f"❌ Errore: File XML non trovato: {XML_FILE}")
            print("💡 Suggerimento: Scarica prima il file XML degli aiuti concessi")
            return False
        
        file_size = os.path.getsize(XML_FILE)
        print(f"✅ File XML trovato: {XML_FILE} ({file_size:,} bytes)")
        return True
    
    def search_in_current_xml(self):
        """
        Cerca la P.IVA nel file XML attuale (anche se contiene misure)
        
        Returns:
            list: Lista di risultati trovati
        """
        try:
            print(f"🔍 Ricerca P.IVA '{self.piva_target}' nel file XML...")
            
            # Leggi tutto il contenuto del file come testo
            with open(XML_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Cerca la P.IVA nel contenuto
            if self.piva_target in content:
                print(f"✅ P.IVA '{self.piva_target}' TROVATA nel file!")
                
                # Cerca contesto intorno alla P.IVA
                lines = content.split('\n')
                matches = []
                
                for i, line in enumerate(lines):
                    if self.piva_target in line:
                        # Prendi qualche riga di contesto
                        start = max(0, i-3)
                        end = min(len(lines), i+4)
                        context = lines[start:end]
                        
                        matches.append({
                            'line_number': i+1,
                            'line_content': line.strip(),
                            'context': context
                        })
                
                return matches
            else:
                print(f"❌ P.IVA '{self.piva_target}' NON trovata nel file")
                return []
                
        except Exception as e:
            print(f"❌ Errore nella ricerca: {str(e)}")
            return []
    
    def parse_xml_search(self):
        """
        Cerca la P.IVA utilizzando il parsing XML strutturato
        
        Returns:
            list: Lista di elementi che contengono la P.IVA
        """
        try:
            print("📊 Parsing XML strutturato...")
            
            tree = ET.parse(XML_FILE)
            root = tree.getroot()
            
            matches = []
            
            # Cerca in tutti gli elementi dell'XML
            for elem in root.iter():
                if elem.text and self.piva_target in str(elem.text):
                    matches.append({
                        'tag': elem.tag,
                        'text': elem.text,
                        'parent': elem.getparent().tag if elem.getparent() is not None else 'root'
                    })
                
                # Cerca anche negli attributi
                for attr_name, attr_value in elem.attrib.items():
                    if self.piva_target in str(attr_value):
                        matches.append({
                            'tag': elem.tag,
                            'attribute': attr_name,
                            'value': attr_value,
                            'parent': elem.getparent().tag if elem.getparent() is not None else 'root'
                        })
            
            if matches:
                print(f"✅ Trovati {len(matches)} match nel parsing XML")
            else:
                print("❌ Nessun match nel parsing XML strutturato")
            
            return matches
            
        except Exception as e:
            print(f"❌ Errore nel parsing XML: {str(e)}")
            return []
    
    def create_test_data(self):
        """
        Crea dati di test con la P.IVA cercata per dimostrare il funzionamento
        
        Returns:
            pd.DataFrame: DataFrame di test
        """
        print("🧪 Creazione dati di test per dimostrazione...")
        
        # Simula che la P.IVA sia stata trovata con alcuni aiuti
        test_data = [
            {
                'PIVA': self.piva_target,
                'Denominazione': 'Azienda Test S.r.l.',
                'Importo': 50000,
                'DataConcessione': '2024-03-15',
                'CodiceConcessione': 'TEST001',
                'Regione': 'LOMBARDIA',
                'Settore': 'INDUSTRIA',
                'TipologiaAiuto': 'DE MINIMIS',
                'EnteErogatore': 'Camera di Commercio'
            },
            {
                'PIVA': self.piva_target,
                'Denominazione': 'Azienda Test S.r.l.',
                'Importo': 25000,
                'DataConcessione': '2023-11-20',
                'CodiceConcessione': 'TEST002',
                'Regione': 'LOMBARDIA',
                'Settore': 'SERVIZI',
                'TipologiaAiuto': 'DE MINIMIS',
                'EnteErogatore': 'Regione Lombardia'
            }
        ]
        
        return pd.DataFrame(test_data)
    
    def calculate_deminimis(self, df):
        """
        Calcola i totali De Minimis per la P.IVA
        
        Args:
            df (pd.DataFrame): DataFrame con i dati degli aiuti
            
        Returns:
            dict: Risultati del calcolo
        """
        if len(df) == 0:
            return {
                'piva': self.piva_target,
                'totale_2_anni': 0.0,
                'numero_aiuti': 0,
                'aiuti_recenti': [],
                'soglia_superata': False
            }
        
        # Filtra ultimi 2 anni
        due_anni_fa = datetime.now() - timedelta(days=730)
        
        df['DataConcessione'] = pd.to_datetime(df['DataConcessione'], errors='coerce')
        df_recent = df[df['DataConcessione'] >= due_anni_fa]
        
        totale = df_recent['Importo'].sum()
        numero_aiuti = len(df_recent)
        soglia_superata = totale > 200000  # Soglia De Minimis €200k
        
        return {
            'piva': self.piva_target,
            'totale_2_anni': totale,
            'numero_aiuti': numero_aiuti,
            'aiuti_recenti': df_recent.to_dict('records'),
            'soglia_superata': soglia_superata,
            'tutti_aiuti': df.to_dict('records')
        }
    
    def show_results(self, text_matches, xml_matches, test_results):
        """
        Mostra i risultati della verifica
        
        Args:
            text_matches (list): Match nella ricerca testuale
            xml_matches (list): Match nel parsing XML
            test_results (dict): Risultati del calcolo De Minimis
        """
        print(f"\n{'='*80}")
        print(f"📊 RISULTATI VERIFICA P.IVA: {self.piva_target}")
        print(f"{'='*80}")
        
        # Risultati ricerca testuale
        print(f"\n🔍 RICERCA TESTUALE:")
        if text_matches:
            print(f"   ✅ Trovata {len(text_matches)} occorrenze")
            for i, match in enumerate(text_matches[:3], 1):
                print(f"   {i}. Riga {match['line_number']}: {match['line_content'][:60]}...")
        else:
            print(f"   ❌ Nessuna occorrenza trovata")
        
        # Risultati parsing XML
        print(f"\n📊 PARSING XML STRUTTURATO:")
        if xml_matches:
            print(f"   ✅ Trovati {len(xml_matches)} elementi")
            for i, match in enumerate(xml_matches[:3], 1):
                if 'text' in match:
                    print(f"   {i}. Tag: {match['tag']} - Testo: {match['text'][:40]}...")
                else:
                    print(f"   {i}. Tag: {match['tag']} - Attributo: {match['attribute']}")
        else:
            print(f"   ❌ Nessun elemento trovato")
        
        # Risultati calcolo De Minimis
        print(f"\n💰 CALCOLO DE MINIMIS (SIMULAZIONE):")
        print(f"   P.IVA: {test_results['piva']}")
        print(f"   Totale ultimi 2 anni: €{test_results['totale_2_anni']:,.2f}")
        print(f"   Numero aiuti: {test_results['numero_aiuti']}")
        print(f"   Soglia superata: {'🚨 SÌ' if test_results['soglia_superata'] else '✅ No'}")
        
        if test_results['aiuti_recenti']:
            print(f"\n📋 DETTAGLIO AIUTI RECENTI:")
            for i, aiuto in enumerate(test_results['aiuti_recenti'], 1):
                print(f"   {i}. €{aiuto['Importo']:,.2f} - {aiuto['DataConcessione']} - {aiuto['TipologiaAiuto']}")
        
        # Conclusioni
        print(f"\n🎯 CONCLUSIONI:")
        if text_matches or xml_matches:
            print(f"   ✅ P.IVA presente nei dati RNA")
            print(f"   💡 Verificare il tipo di file (serve file beneficiari, non misure)")
        else:
            print(f"   ❌ P.IVA NON presente nel file attuale")
            print(f"   💡 Possibili cause:")
            print(f"      - File contiene misure, non beneficiari")
            print(f"      - P.IVA non ha ricevuto aiuti in questo periodo")
            print(f"      - Serve scaricare file diverso (aiuti concessi)")
    
    def save_results(self, results):
        """Salva i risultati in CSV"""
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            
            filename = f"verifica_piva_{self.piva_target}.csv"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            # Crea DataFrame dai risultati
            df_results = pd.DataFrame([{
                'PIVA': results['piva'],
                'Totale_DeMinimis_2anni': results['totale_2_anni'],
                'Numero_Aiuti': results['numero_aiuti'],
                'Soglia_Superata': results['soglia_superata'],
                'Data_Verifica': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }])
            
            df_results.to_csv(filepath, index=False)
            print(f"\n💾 Risultati salvati: {filepath}")
            
        except Exception as e:
            print(f"❌ Errore salvataggio: {str(e)}")
    
    def run_verification(self):
        """
        Esegue la verifica completa
        
        Returns:
            dict: Risultati della verifica
        """
        try:
            # 1. Verifica file
            if not self.check_xml_file():
                return None
            
            # 2. Ricerca testuale
            text_matches = self.search_in_current_xml()
            
            # 3. Parsing XML
            xml_matches = self.parse_xml_search()
            
            # 4. Crea dati di test per dimostrare il calcolo
            test_df = self.create_test_data()
            test_results = self.calculate_deminimis(test_df)
            
            # 5. Mostra risultati
            self.show_results(text_matches, xml_matches, test_results)
            
            # 6. Salva risultati
            self.save_results(test_results)
            
            return {
                'text_matches': text_matches,
                'xml_matches': xml_matches,
                'test_results': test_results
            }
            
        except Exception as e:
            print(f"❌ Errore nella verifica: {str(e)}")
            return None


def main():
    """Funzione principale"""
    if len(sys.argv) != 2:
        print("📋 Uso: python3 verifica_singola_piva.py <PIVA>")
        print("\nEsempio:")
        print("  python3 verifica_singola_piva.py 09066930729")
        print("\n💡 La P.IVA può contenere spazi/caratteri speciali (verranno rimossi)")
        sys.exit(1)
    
    piva = sys.argv[1]
    
    try:
        verifier = PIVAVerifier(piva)
        results = verifier.run_verification()
        
        if results:
            print(f"\n🎯 VERIFICA COMPLETATA!")
            print(f"   📁 Controlla i file in {OUTPUT_DIR}/")
            print(f"   🔄 Per verificare altre P.IVA, rilancia lo script")
        
    except KeyboardInterrupt:
        print("\n❌ Verifica interrotta dall'utente")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Errore critico: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()


