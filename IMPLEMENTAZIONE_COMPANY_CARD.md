# 📋 IMPLEMENTAZIONE: Navigazione Company Card Completa

## 🎯 Obiettivo
Navigare automaticamente alla Company Card Completa di Cribis e estrarre dati finanziari (ULA, Fatturato, Attivo).

---

## 1️⃣ CODICE RIUTILIZZABILE DA `cribis_nuova_ricerca.py`

### ✅ Già funzionante:

```python
# Login
def login(self):
    """Login su Cribis X - GIÀ IMPLEMENTATO"""
    # Codice esistente funziona perfettamente
    pass

# Ricerca P.IVA
def ricerca_piva(self, piva):
    """
    Cerca P.IVA nel campo ricerca
    """
    campo_ricerca = self.page.locator('input[title="Inserisci i termini da cercare"]')
    campo_ricerca.fill(piva)
    self.page.keyboard.press("Enter")
    time.sleep(2)
```

---

## 2️⃣ NUOVO METODO: `scarica_company_card_completa(cf)`

### 🔍 Flusso completo (da screenshot):

```python
def scarica_company_card_completa(self, codice_fiscale):
    """
    Scarica Company Card Completa per un codice fiscale
    
    Args:
        codice_fiscale (str): CF dell'azienda
        
    Returns:
        dict: Dati estratti o errore
    """
    try:
        print(f"📊 Download Company Card Completa per: {codice_fiscale}")
        
        # STEP 1: Ricerca CF
        print("🔍 Ricerca CF...")
        campo_ricerca = self.page.locator('input[title="Inserisci i termini da cercare"]')
        campo_ricerca.fill(codice_fiscale)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(2000)
        
        # STEP 2: Click sul nome azienda (primo risultato)
        print("🎯 Click su nome azienda...")
        nome_azienda = self.page.locator('div[class*="result"] a:first-of-type').first
        if not nome_azienda.is_visible():
            return {"errore": "Azienda non trovata"}
        
        nome_text = nome_azienda.inner_text()
        print(f"✅ Trovata: {nome_text}")
        nome_azienda.click()
        self.page.wait_for_timeout(3000)
        
        # STEP 3: Scrolla e cerca "Tutti i prodotti CRIBIS X"
        print("📜 Scroll verso il link 'Tutti i prodotti'...")
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        self.page.wait_for_timeout(1000)
        
        tutti_prodotti_link = self.page.locator('a.link-orange:has-text("Tutti i prodotti")')
        if not tutti_prodotti_link.is_visible():
            return {"errore": "Link 'Tutti i prodotti' non trovato"}
        
        # STEP 4: Click su "Tutti i prodotti" → apre modale
        print("🖱️ Click su 'Tutti i prodotti CRIBIS X'...")
        tutti_prodotti_link.click()
        self.page.wait_for_timeout(2000)
        
        # Verifica modale aperta
        modale = self.page.locator('.modal:visible')
        if not modale.is_visible():
            return {"errore": "Modale prodotti non aperta"}
        
        print("✅ Modale prodotti aperta")
        
        # STEP 5: Scroll dentro la modale verso "Company Card Completa"
        print("📜 Scroll nella modale verso Company Card Completa...")
        # Scroll a metà modale
        self.page.evaluate("""
            () => {
                const modal = document.querySelector('.modal:visible');
                if (modal) {
                    modal.scrollTop = modal.scrollHeight / 2;
                }
            }
        """)
        self.page.wait_for_timeout(1000)
        
        # STEP 6: Cerca card "Company Card Completa"
        print("🔍 Cerca card 'Company Card Completa'...")
        
        # Cerca l'elemento <em> con testo "Company Card Completa"
        card_title = self.page.locator('em:has-text("Company Card Completa")')
        if not card_title.is_visible():
            return {"errore": "Card 'Company Card Completa' non trovata"}
        
        print("✅ Card trovata")
        
        # STEP 7: Trova il bottone "Richiedi" associato alla card
        # Il bottone è dentro il contenitore della card
        # Class: "button-big corn-flower-blue-bg buy-link big-button-size-padding"
        
        # Strategia: cerca il contenitore padre della card, poi cerca il bottone dentro
        card_container = card_title.locator('..')  # Parent
        for _ in range(3):  # Risali fino a 3 livelli
            try:
                bottone_richiedi = card_container.locator('a.button-big.corn-flower-blue-bg.buy-link').first
                if bottone_richiedi.is_visible():
                    break
                card_container = card_container.locator('..')
            except:
                continue
        
        if not bottone_richiedi or not bottone_richiedi.is_visible():
            return {"errore": "Bottone 'Richiedi' non trovato"}
        
        print("✅ Bottone 'Richiedi' trovato")
        self.page.screenshot(path="debug_company_card_prima_richiedi.png")
        
        # STEP 8: Click su "Richiedi" e aspetta nuova tab o navigazione
        print("🖱️ Click su 'Richiedi'...")
        
        # Aspetta apertura nuova tab (simile a Gruppo Societario)
        with self.page.context.expect_page(timeout=180000) as new_page_info:
            bottone_richiedi.click()
            print("✅ Click eseguito, aspetto nuova tab...")
        
        new_page = new_page_info.value
        print(f"✅ Nuova tab aperta! URL: {new_page.url}")
        
        # Aspetta caricamento completo
        new_page.wait_for_load_state("domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(5000)
        
        # STEP 9: Screenshot e estrazione dati
        new_page.screenshot(path="debug_company_card_report.png")
        print("📸 Screenshot report salvato")
        
        # STEP 10: Estrae dati dalla pagina
        dati = self.estrai_dati_finanziari(new_page, codice_fiscale)
        
        # Chiudi tab report
        new_page.close()
        
        return dati
        
    except Exception as e:
        print(f"❌ Errore download Company Card: {str(e)}")
        return {"errore": str(e), "cf": codice_fiscale}
```

---

## 3️⃣ METODO ESTRAZIONE DATI FINANZIARI

```python
def estrai_dati_finanziari(self, page, codice_fiscale):
    """
    Estrae ULA, Fatturato e Attivo dalla Company Card HTML
    
    Args:
        page: Playwright page object
        codice_fiscale: CF dell'azienda
        
    Returns:
        dict: {
            "cf": str,
            "ragione_sociale": str,
            "personale_ula": int | None,
            "fatturato": float | None,
            "attivo_patrimoniale": float | None,
            "anno_riferimento": str,
            "stato_dati": "completi" | "parziali" | "assenti"
        }
    """
    try:
        print(f"📊 Estrazione dati finanziari per {codice_fiscale}...")
        
        # Salva HTML per debug
        html_content = page.content()
        with open(f"debug_company_card_{codice_fiscale}.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        dati = {
            "cf": codice_fiscale,
            "ragione_sociale": "N/D",
            "personale_ula": None,
            "fatturato": None,
            "attivo_patrimoniale": None,
            "anno_riferimento": "N/D",
            "stato_dati": "assenti"
        }
        
        # ESTRAZIONE RAGIONE SOCIALE
        try:
            # Cerca nel title o header principale
            ragione_sociale_elem = page.locator('h1, h2, .company-name, .ragione-sociale').first
            if ragione_sociale_elem.is_visible():
                dati["ragione_sociale"] = ragione_sociale_elem.inner_text().strip()
        except:
            pass
        
        # ESTRAZIONE NUMERO DIPENDENTI (ULA)
        print("🔍 Cerca numero dipendenti/ULA...")
        dipendenti_pattern = r'(\d+(?:[.,]\d+)?)\s*(?:Unità|ULA|dipendenti|addetti)'
        
        # Cerca in vari selettori possibili
        selettori_dipendenti = [
            'div:has-text("Dipendenti")',
            'td:has-text("Personale")',
            'span:has-text("ULA")',
            '.employee-count',
            'div:has-text("Numero addetti")'
        ]
        
        for sel in selettori_dipendenti:
            try:
                elem = page.locator(sel).first
                if elem.is_visible():
                    text = elem.inner_text()
                    match = re.search(dipendenti_pattern, text, re.IGNORECASE)
                    if match:
                        ula_str = match.group(1).replace(',', '.')
                        dati["personale_ula"] = int(float(ula_str))
                        print(f"✅ ULA trovato: {dati['personale_ula']}")
                        break
            except:
                continue
        
        # ESTRAZIONE FATTURATO
        print("🔍 Cerca fatturato...")
        fatturato_pattern = r'€?\s*([\d.,]+)\s*(?:€|euro|EUR)?'
        
        selettori_fatturato = [
            'td:has-text("Fatturato")',
            'div:has-text("Ricavi")',
            'span:has-text("Valore della produzione")',
            '.revenue',
            'div:has-text("Totale ricavi")'
        ]
        
        for sel in selettori_fatturato:
            try:
                elem = page.locator(sel).first
                if elem.is_visible():
                    text = elem.inner_text()
                    # Cerca importo in formato italiano (1.234.567,89)
                    match = re.search(r'([\d.]+,\d{2})', text)
                    if match:
                        importo_str = match.group(1).replace('.', '').replace(',', '.')
                        dati["fatturato"] = float(importo_str)
                        print(f"✅ Fatturato trovato: €{dati['fatturato']:,.2f}")
                        break
            except:
                continue
        
        # ESTRAZIONE ATTIVO PATRIMONIALE
        print("🔍 Cerca attivo patrimoniale...")
        
        selettori_attivo = [
            'td:has-text("Totale attivo")',
            'div:has-text("Attivo patrimoniale")',
            'span:has-text("Totale attività")',
            '.total-assets'
        ]
        
        for sel in selettori_attivo:
            try:
                elem = page.locator(sel).first
                if elem.is_visible():
                    text = elem.inner_text()
                    match = re.search(r'([\d.]+,\d{2})', text)
                    if match:
                        importo_str = match.group(1).replace('.', '').replace(',', '.')
                        dati["attivo_patrimoniale"] = float(importo_str)
                        print(f"✅ Attivo trovato: €{dati['attivo_patrimoniale']:,.2f}")
                        break
            except:
                continue
        
        # ANNO RIFERIMENTO
        try:
            # Cerca anno (2023, 2024, etc)
            anno_match = re.search(r'20\d{2}', html_content)
            if anno_match:
                dati["anno_riferimento"] = anno_match.group(0)
        except:
            pass
        
        # STATO DATI
        dati_presenti = sum([
            dati["personale_ula"] is not None,
            dati["fatturato"] is not None,
            dati["attivo_patrimoniale"] is not None
        ])
        
        if dati_presenti == 3:
            dati["stato_dati"] = "completi"
        elif dati_presenti > 0:
            dati["stato_dati"] = "parziali"
        else:
            dati["stato_dati"] = "assenti"
        
        print(f"📊 Dati estratti: {dati_presenti}/3")
        print(f"   Stato: {dati['stato_dati']}")
        
        return dati
        
    except Exception as e:
        print(f"❌ Errore estrazione dati: {str(e)}")
        return {
            "cf": codice_fiscale,
            "errore": str(e),
            "stato_dati": "errore"
        }
```

---

## 4️⃣ TEST MANUALE

### Script di test standalone:

```python
# test_company_card.py

from cribis_nuova_ricerca import CribisNuovaRicerca

def test_company_card():
    """Test download Company Card Completa"""
    
    cf_test = "04143180984"  # Pozzi Milano SPA
    
    print(f"🧪 TEST Company Card Completa per: {cf_test}\n")
    
    cribis = CribisNuovaRicerca(headless=False)  # Visibile per debug
    
    try:
        # Login
        print("1️⃣ Login...")
        cribis._inizializza_browser()
        cribis.login()
        
        # Download Company Card
        print(f"\n2️⃣ Download Company Card per {cf_test}...")
        risultato = cribis.scarica_company_card_completa(cf_test)
        
        # Mostra risultati
        print("\n" + "="*60)
        print("📊 RISULTATI:")
        print("="*60)
        
        if "errore" in risultato:
            print(f"❌ ERRORE: {risultato['errore']}")
        else:
            print(f"✅ Ragione Sociale: {risultato.get('ragione_sociale', 'N/D')}")
            print(f"👥 Personale ULA: {risultato.get('personale_ula', 'N/D')}")
            print(f"💰 Fatturato: €{risultato.get('fatturato', 0):,.2f}")
            print(f"🏦 Attivo: €{risultato.get('attivo_patrimoniale', 0):,.2f}")
            print(f"📅 Anno: {risultato.get('anno_riferimento', 'N/D')}")
            print(f"📊 Stato dati: {risultato.get('stato_dati', 'N/D')}")
        
        print("\n✅ Test completato!")
        
    except Exception as e:
        print(f"\n❌ Errore nel test: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        input("\nPremi INVIO per chiudere...")
        cribis.close()

if __name__ == "__main__":
    test_company_card()
```

**Esecuzione**:
```bash
cd /Users/marcocassani/Documents/Pigreco/rna-deminimis-agente
python test_company_card.py
```

---

## 5️⃣ CHECKLIST IMPLEMENTAZIONE

### Prima di iniziare:
- [ ] Backup del codice attuale
- [ ] Verificare che `cribis_nuova_ricerca.py` funzioni

### Fase 1: Aggiunta metodo base
- [ ] Aggiungere `scarica_company_card_completa()` a `CribisNuovaRicerca`
- [ ] Test login + navigazione modale
- [ ] Verificare apertura nuova tab

### Fase 2: Estrazione dati
- [ ] Aggiungere `estrai_dati_finanziari()`
- [ ] Test estrazione ULA
- [ ] Test estrazione Fatturato
- [ ] Test estrazione Attivo

### Fase 3: Testing
- [ ] Test con P.IVA: 04143180984
- [ ] Test con società senza dati
- [ ] Verifica screenshot di debug
- [ ] Validazione numeri estratti

---

## 6️⃣ DOMANDE APERTE

1. **Dove salvare screenshot debug?**
   - Cartella `debug_screenshots/` ?
   - O root directory?

2. **Se Company Card costa crediti Cribis, continuare?**
   - Confermare con utente prima del test

3. **Timeout: quanto aspettare per caricamento report?**
   - Attualmente: 180s (3 minuti)
   - Aumentare a 300s (5 minuti)?

---

**Pronto per iniziare implementazione?** 🚀

