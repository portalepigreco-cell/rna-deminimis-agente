#!/usr/bin/env python3
"""
Debug specifico per P.IVA MAZZOLENI
Analizza cosa trova nell'albero societario
"""

import time
from playwright.sync_api import sync_playwright

def debug_mazzoleni():
    """Debug dettagliato per MAZZOLENI"""
    
    print("🔍 DEBUG MAZZOLENI - Analisi Albero Societario")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()
        
        try:
            # Login
            print("🔐 Login...")
            page.goto("https://www2.cribisx.com/#Home/Index")
            page.fill("input[type='text']", "CC838673")
            page.fill("input[type='password']", "26082025__Pigreco_")
            page.click("input[type='submit']")
            page.wait_for_url("https://www2.cribisx.com/#Home/Index")
            
            # Vai a documenti
            print("📁 Documenti...")
            page.goto("https://www2.cribisx.com/#Storage/Index")
            page.wait_for_selector("text=MyDocs")
            
            # Ricerca puntuale
            print("🔍 Ricerca MAZZOLENI...")
            page.get_by_text("Ricerca Puntuale").click()
            page.fill('input[placeholder="Codice Fiscale / Partita IVA"]', "02918700168")
            page.click("button:has-text('Cerca')")
            time.sleep(3)
            
            # Clicca su Gruppo Societario
            print("🎯 Clic Gruppo Societario...")
            page.click('a.doc-type:has-text("Gruppo Societario")')
            page.wait_for_selector("text=Gruppo Societario")
            time.sleep(5)  # Aspetta caricamento completo
            
            print("\n" + "="*60)
            print("📊 ANALISI ALBERO SOCIETARIO")
            print("="*60)
            
            # Salva screenshot
            page.screenshot(path="debug_mazzoleni_albero.png")
            print("📸 Screenshot salvato: debug_mazzoleni_albero.png")
            
            # Salva HTML completo
            with open("debug_mazzoleni_albero.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("💾 HTML salvato: debug_mazzoleni_albero.html")
            
            # ANALISI 1: Cerca tutti i div.node-content
            print("\n🔍 ANALISI 1: Tutti i div.node-content")
            node_contents = page.locator("div.node-content").all()
            print(f"   Trovati {len(node_contents)} div.node-content")
            
            for i, node in enumerate(node_contents[:10]):  # Prime 10
                try:
                    text = node.inner_text()
                    print(f"\n   Node {i+1}:")
                    print(f"   Text: '{text[:200]}...'")
                    if "Cod. Fisc" in text:
                        print(f"   ✅ Contiene 'Cod. Fisc'")
                    if "%" in text:
                        print(f"   ✅ Contiene percentuale")
                    if "Italia" in text:
                        print(f"   ✅ Contiene 'Italia'")
                except Exception as e:
                    print(f"   ❌ Errore lettura node {i+1}: {str(e)}")
            
            # ANALISI 2: Cerca div che contengono "Cod. Fisc"
            print(f"\n🔍 ANALISI 2: div:has-text('Cod. Fisc')")
            cod_fisc_divs = page.locator("div:has-text('Cod. Fisc')").all()
            print(f"   Trovati {len(cod_fisc_divs)} div con 'Cod. Fisc'")
            
            for i, div in enumerate(cod_fisc_divs[:5]):
                try:
                    text = div.inner_text()
                    print(f"\n   Div {i+1} con Cod.Fisc:")
                    print(f"   Text: '{text}'")
                except Exception as e:
                    print(f"   ❌ Errore: {str(e)}")
            
            # ANALISI 3: Cerca il selettore originale
            print(f"\n🔍 ANALISI 3: div.node-content div:has-text('Cod. Fisc')")
            original_selector = page.locator("div.node-content div:has-text('Cod. Fisc')").all()
            print(f"   Trovati {len(original_selector)} elementi con selettore originale")
            
            # ANALISI 4: Cerca tutti gli elementi con percentuali
            print(f"\n🔍 ANALISI 4: Elementi con percentuali")
            percentage_elements = page.locator("*:has-text('%')").all()
            print(f"   Trovati {len(percentage_elements)} elementi con '%'")
            
            for i, elem in enumerate(percentage_elements[:10]):
                try:
                    text = elem.inner_text()
                    if any(char.isdigit() for char in text) and "%" in text:
                        print(f"   {i+1}. '{text.strip()}'")
                except:
                    continue
            
            # ANALISI 5: Cerca codici fiscali (11 cifre)
            print(f"\n🔍 ANALISI 5: Codici fiscali (11 cifre)")
            body_text = page.locator("body").inner_text()
            
            import re
            codici_fiscali = re.findall(r'\b(\d{11})\b', body_text)
            print(f"   Trovati {len(codici_fiscali)} codici fiscali:")
            for cf in set(codici_fiscali):  # Rimuove duplicati
                print(f"   • {cf}")
            
            # ANALISI 6: Cerca parole chiave
            print(f"\n🔍 ANALISI 6: Parole chiave nell'albero")
            keywords = ["Mazzoleni", "Martens", "Italia", "Società", "Srl", "Spa"]
            for keyword in keywords:
                elements = page.locator(f"*:has-text('{keyword}')").all()
                print(f"   '{keyword}': {len(elements)} elementi")
            
            # ANALISI 7: Struttura HTML specifica
            print(f"\n🔍 ANALISI 7: Struttura HTML dell'albero")
            tree_containers = [
                ".tree", ".orgchart", ".hierarchy", ".corporate-tree",
                ".gruppo-societario", ".shareholding", "[class*='tree']",
                "[class*='org']", "[class*='chart']"
            ]
            
            for selector in tree_containers:
                try:
                    elements = page.locator(selector).all()
                    if elements:
                        print(f"   Trovato container: {selector} ({len(elements)} elementi)")
                except:
                    continue
            
            print(f"\n💾 SALVATAGGIO DATI COMPLETI:")
            
            # Salva tutto il testo per analisi offline
            with open("debug_mazzoleni_testo_completo.txt", "w", encoding="utf-8") as f:
                f.write(body_text)
            print("   • debug_mazzoleni_testo_completo.txt")
            
            # Salva HTML dell'albero specifico se trovato
            try:
                tree_section = page.locator("*:has-text('Gruppo Societario')").first
                if tree_section:
                    tree_html = tree_section.inner_html()
                    with open("debug_mazzoleni_tree_section.html", "w", encoding="utf-8") as f:
                        f.write(tree_html)
                    print("   • debug_mazzoleni_tree_section.html")
            except:
                pass
            
            print(f"\n✅ ANALISI COMPLETATA!")
            print(f"📁 File generati per analisi dettagliata:")
            print(f"   • debug_mazzoleni_albero.png (screenshot)")
            print(f"   • debug_mazzoleni_albero.html (HTML completo)")
            print(f"   • debug_mazzoleni_testo_completo.txt (testo)")
            
        except Exception as e:
            print(f"❌ Errore durante debug: {str(e)}")
            page.screenshot(path="debug_mazzoleni_errore.png")
        
        finally:
            input("\n⏸️ Premi INVIO per chiudere...")
            browser.close()

if __name__ == "__main__":
    debug_mazzoleni()
