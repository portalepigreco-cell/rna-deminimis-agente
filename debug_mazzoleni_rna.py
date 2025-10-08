#!/usr/bin/env python3
"""
Debug specifico per verificare perché MAZZOLENI (02918700168) 
risulta €0 invece di €45.368,50 nel calcolo De Minimis
"""

from rna_deminimis import RNACalculator
import json

def debug_mazzoleni_rna():
    """Debug dettagliato per il calcolo RNA di MAZZOLENI"""
    
    print("🔍 DEBUG MAZZOLENI RNA - Calcolo De Minimis")
    print("="*60)
    print("P.IVA: 02918700168")
    print("Atteso: €45.368,50 (basato su immagine utente)")
    print("Calcolato dal sistema: €0")
    print("="*60)
    
    # Test diretto con RNACalculator
    calculator = RNACalculator()
    
    try:
        print("\n🚀 AVVIO CALCOLO DIRETTO...")
        risultato = calculator.calcola_deminimis("02918700168")
        
        print(f"\n📊 RISULTATO COMPLETO:")
        print(json.dumps(risultato, indent=2, ensure_ascii=False))
        
        print(f"\n📈 RIEPILOGO:")
        print(f"   Errore: {risultato.get('errore', 'N/A')}")
        print(f"   De Minimis: €{risultato.get('deminimis_ricevuto', 0):,.2f}")
        print(f"   Numero aiuti: {risultato.get('numero_aiuti', 0)}")
        print(f"   Data ricerca: {risultato.get('data_ricerca', 'N/A')}")
        
        # Analisi dettagli aiuti
        dettagli = risultato.get('dettagli_aiuti', [])
        if dettagli:
            print(f"\n📋 DETTAGLI AIUTI ({len(dettagli)} trovati):")
            totale_verificato = 0
            for i, aiuto in enumerate(dettagli, 1):
                importo = aiuto.get('importo', 0)
                data = aiuto.get('data_concessione', 'N/A')
                titolo = aiuto.get('titolo_misura', 'N/A')[:50] + "..."
                
                print(f"   {i}. €{importo:,.2f} - {data} - {titolo}")
                totale_verificato += importo
                
            print(f"\n✅ TOTALE VERIFICATO: €{totale_verificato:,.2f}")
            
            if totale_verificato != risultato.get('deminimis_ricevuto', 0):
                print(f"⚠️  DISCREPANZA: Sistema={risultato.get('deminimis_ricevuto', 0)}, Manuale={totale_verificato}")
        else:
            print("\n❌ NESSUN AIUTO TROVATO!")
            print("   Possibili cause:")
            print("   • Filtro 'De Minimis' non applicato")
            print("   • Filtro data troppo restrittivo")
            print("   • Problemi navigazione pagine")
            print("   • Parsing HTML errato")
        
        # Controlla se ci sono errori specifici
        if risultato.get('errore'):
            print(f"\n🚨 ERRORE RILEVATO:")
            print(f"   {risultato['errore']}")
            
    except Exception as e:
        print(f"\n❌ ERRORE DURANTE DEBUG:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()

def test_manuale_filtri():
    """Test manuale dei filtri per capire il problema"""
    
    print("\n" + "="*60)
    print("🧪 TEST MANUALE FILTRI")
    print("="*60)
    
    calculator = RNACalculator()
    
    try:
        # Test con filtri diversi
        filtri_test = [
            {"descrizione": "Nessun filtro", "filtri": {}},
            {"descrizione": "Solo De Minimis", "filtri": {"tipo": "De Minimis"}},
            {"descrizione": "Solo data 2024-2025", "filtri": {"anni": [2024, 2025]}},
            {"descrizione": "De Minimis + data", "filtri": {"tipo": "De Minimis", "anni": [2024, 2025]}}
        ]
        
        for test in filtri_test:
            print(f"\n🔬 {test['descrizione']}:")
            
            # Qui dovremmo modificare RNACalculator per accettare filtri opzionali
            # Per ora facciamo il test standard
            risultato = calculator.calcola_deminimis("02918700168")
            
            print(f"   Risultato: €{risultato.get('deminimis_ricevuto', 0):,.2f}")
            print(f"   Aiuti: {risultato.get('numero_aiuti', 0)}")
            
    except Exception as e:
        print(f"❌ Errore test filtri: {str(e)}")

if __name__ == "__main__":
    debug_mazzoleni_rna()
    test_manuale_filtri()
