#!/usr/bin/env python3
"""
RNA De Minimis Calculator (Playwright)
Sostituisce Selenium/Geckodriver con Playwright per maggiore stabilità.
"""

from datetime import datetime, timedelta
import re
import io
import csv
import os
from playwright.sync_api import sync_playwright

# Import sistema alert email
try:
    from email_alert import alert_rna_error
    EMAIL_ALERTS_ENABLED = True
except ImportError:
    EMAIL_ALERTS_ENABLED = False
    print("⚠️ Modulo email_alert non disponibile - alert disabilitati")


class RNACalculator:
    """Calcolatore automatico de minimis RNA con Playwright"""

    def __init__(self, headless: bool = True, slow_mo_ms: int = 0):
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self.url = "https://www.rna.gov.it/trasparenza/aiuti"

    def _parse_importo_it(self, text: str) -> float | None:
        if not text:
            return None
        match = re.search(r"([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2}))", text)
        if not match:
            return None
        value = match.group(1).replace(".", "").replace(",", ".")
        try:
            amount = float(value)
            return amount if amount > 0 else None
        except ValueError:
            return None

    def calcola_deminimis(self, partita_iva: str) -> dict:
        oggi = datetime.now()
        tre_anni_fa = oggi - timedelta(days=3 * 365)

        with sync_playwright() as p:
            # Logging per debug Playwright su Render
            import os
            print(f"🔍 DEBUG Playwright:")
            print(f"  - PLAYWRIGHT_BROWSERS_PATH: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH', 'NON IMPOSTATO')}")
            print(f"  - Headless: {self.headless}")
            print(f"  - Chromium path: {p.chromium.executable_path if hasattr(p.chromium, 'executable_path') else 'N/A'}")
            
            # Configurazione browser per ambienti cloud (Render, etc.)
            try:
                browser = p.chromium.launch(
                    headless=self.headless, 
                    slow_mo=self.slow_mo_ms,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu'
                    ]
                )
                print("✅ Browser Chromium lanciato con successo")
            except Exception as e:
                print(f"❌ ERRORE lancio browser: {str(e)}")
                print(f"   Tipo errore: {type(e).__name__}")
                raise
            page = browser.new_page()

            try:
                page.goto(self.url, wait_until="domcontentloaded", timeout=60000)

                # Chiudi cookie se presente
                try:
                    # diversi possibili testi del bottone
                    cookie_btn = page.locator("xpath=//button[contains(., 'Accett') or contains(., 'accett') or contains(., 'OK')]")
                    if cookie_btn.first.is_visible():
                        cookie_btn.first.click()
                except Exception:
                    pass

                # Ricarica per mostrare il form, come da flusso verificato
                page.goto(self.url, wait_until="domcontentloaded", timeout=60000)

                # Compila form: campo CF/P.IVA
                cf_input = page.locator("input[name='cfBen']")
                cf_input.fill(partita_iva)

                # Tipo: De Minimis
                page.select_option("select[name='tipp']", label="De Minimis")

                # Date: estendiamo a 6 anni per garantire presenza dati, filtreremo a 3 anni
                sei_anni_fa = oggi - timedelta(days=6 * 365)
                try:
                    page.fill("input[name='annoc']", sei_anni_fa.strftime('%d/%m/%Y'))
                    page.fill("input[name='annoc2']", oggi.strftime('%d/%m/%Y'))
                except Exception:
                    # Fallback ISO
                    try:
                        page.fill("input[name='annoc']", sei_anni_fa.strftime('%Y-%m-%d'))
                        page.fill("input[name='annoc2']", oggi.strftime('%Y-%m-%d'))
                    except Exception:
                        pass

                # Invia ricerca
                submit = page.locator("xpath=//input[@type='submit'] | //button[@type='submit']").first
                submit.click()
                # Attendi che appaiano risultati o messaggio
                try:
                    page.wait_for_selector("table", timeout=60000)
                    page.wait_for_selector("table tbody tr td", timeout=60000)
                except Exception:
                    pass
                # Ulteriore attesa per popolamento DataTables
                page.wait_for_timeout(5000)
                # Polling: attendi finché compare almeno un simbolo euro nella tabella (max ~10s)
                has_euro = False
                try:
                    for _ in range(40):  # fino a ~20s
                        has_euro = page.evaluate(
                            """
                            () => {
                              const t = document.querySelector('#trasparenzaAiuti') || document.querySelector('table');
                              if (!t) return false;
                              const txt = t.innerText || '';
                              if (!txt.includes('€')) return false;
                              const body = t.querySelector('tbody');
                              if (!body) return false;
                              return body.querySelectorAll('tr').length > 0;
                            }
                            """
                        )
                        if has_euro:
                            break
                        page.wait_for_timeout(500)
                except Exception:
                    pass

                # Salva debug post-submit
                try:
                    page.screenshot(path="debug_rna_post_submit.png", full_page=True)
                    with open("debug_rna_post_submit.html", "w", encoding="utf-8") as f:
                        f.write(page.content())
                except Exception:
                    pass

                tutti_aiuti: list[dict] = []
                max_pagine = 10
                pagina = 1
                date_vecchie_consecutive = 0

                def estrai_dalla_pagina() -> tuple[list[dict], bool]:
                    aiuti: list[dict] = []
                    continua = True
                    try:
                        # Seleziona la tabella corretta per header "Elemento Aiuto"
                        candidate_tables = page.locator("table").all()
                        table = None
                        for t in candidate_tables:
                            try:
                                hdr_nodes = t.locator("thead th, tr th").all()
                                headers_lower = [h.inner_text().strip().lower() for h in hdr_nodes]
                                header_text = " ".join(headers_lower)
                                if ("elemento" in header_text and "aiuto" in header_text) or ("data" in header_text and "concessione" in header_text) or ("importo" in header_text):
                                    table = t
                                    break
                            except Exception:
                                continue
                        if not table or not table.is_visible():
                            return aiuti, False

                        rows = table.locator("tbody tr").all()
                        if not rows:
                            rows = table.locator("tr").all()
                        if len(rows) < 2:
                            return aiuti, False

                        # Primo tentativo: estrazione lato client con JS (header -> index per "Elemento Aiuto")
                        try:
                            js_results = page.evaluate(
                                """
                                () => {
                                  const tbl = document.querySelector('#trasparenzaAiuti') || document.querySelector('table');
                                  const out = [];
                                  if (!tbl) return out;
                                  const thead = tbl.querySelector('thead');
                                  const headers = thead ? Array.from(thead.querySelectorAll('th')).map(th => th.innerText.trim().toLowerCase()) : [];
                                  const findIdx = (pred) => headers.findIndex(h => pred(h));
                                  const idxData = findIdx(h => h.includes('data') && h.includes('concessione'));
                                  const idxImporto = findIdx(h => h.includes('elemento') && h.includes('aiuto'));
                                  const idxTitolo = findIdx(h => h.includes('titolo'));
                                  const rows = tbl.querySelectorAll('tbody tr');
                                  rows.forEach(tr => {
                                    const cells = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
                                    if (cells.length < 3) return;
                                    const dateCell = idxData >= 0 ? (cells[idxData] || '') : (cells.map(t => (t.match(/\b\d{2}\/\d{2}\/\d{4}\b/)||[])[0]).find(Boolean) || '');
                                    const importoCell = idxImporto >= 0 ? (cells[idxImporto] || '') : (cells.find(t => t.includes('€')) || '');
                                    const titoloCell = idxTitolo >= 0 ? (cells[idxTitolo] || '') : (cells[2] || '');
                                    out.push({ data: dateCell, importoTxt: importoCell, titolo: titoloCell });
                                  });
                                  return out;
                                }
                                """
                            )
                            # Converte risultati JS in aiuti strutturati
                            for item in js_results or []:
                                data_txt = item.get('data') or ''
                                if not data_txt:
                                    continue
                                try:
                                    data_conc = datetime.strptime(data_txt, "%d/%m/%Y")
                                except Exception:
                                    continue
                                if data_conc < tre_anni_fa:
                                    date_vecchie_consecutive_nonlocal[0] += 1
                                    if date_vecchie_consecutive_nonlocal[0] >= 3:
                                        continua = False
                                        break
                                    continue
                                else:
                                    date_vecchie_consecutive_nonlocal[0] = 0

                                importo = self._parse_importo_it(item.get('importoTxt') or '')
                                if not importo:
                                    continue
                                titolo = (item.get('titolo') or '').strip() or 'N/A'
                                aiuti.append({
                                    "data_concessione": data_txt,
                                    "importo": importo,
                                    "titolo_misura": titolo,
                                    "data": data_txt,
                                })
                            # Se abbiamo trovato aiuti via JS, ritorna subito
                            if aiuti:
                                return aiuti, True
                        except Exception:
                            pass

                        # Secondo tentativo: parsing diretto dell'HTML della tabella (regex)
                        try:
                            for _ in range(20):  # ~10s
                                html = page.evaluate("() => (document.querySelector('#trasparenzaAiuti')||{}).outerHTML || '';")
                                if not html or '€' not in html:
                                    page.wait_for_timeout(500)
                                    continue
                                # Estrai righe
                                import re as _re
                                # Trova tutte le date dd/mm/yyyy
                                date_list = _re.findall(r"(\d{2}/\d{2}/\d{4})", html)
                                # Trova tutti gli importi formattati IT con euro nella tabella
                                importi_list = _re.findall(r"€\s*[0-9.]+,[0-9]{2}", html)
                                # Trova titoli Grezzi (colonna Titolo Misura)
                                titoli_list = _re.findall(r">\s*([^<]{3,100})\s*</td>", html)
                                # Associa per posizione prudente: usa numero minimo tra liste
                                n = min(len(date_list), len(importi_list))
                                for i in range(n):
                                    data_txt = date_list[i]
                                    try:
                                        data_conc = datetime.strptime(data_txt, "%d/%m/%Y")
                                    except Exception:
                                        continue
                                    if data_conc < tre_anni_fa:
                                        continue
                                    importo = self._parse_importo_it(importi_list[i])
                                    if not importo:
                                        continue
                                    titolo = titoli_list[i] if i < len(titoli_list) else 'N/A'
                                    aiuti.append({
                                        "data_concessione": data_txt,
                                        "importo": importo,
                                        "titolo_misura": titolo,
                                        "data": data_txt,
                                    })
                                if aiuti:
                                    return aiuti, True
                                page.wait_for_timeout(500)
                        except Exception:
                            pass

                        # Terzo tentativo: fallback Scarica CSV (se polling trova € ma non importi)
                        print(f"🔍 Debug: aiuti={len(aiuti)}, has_euro={has_euro}")
                        if not aiuti and has_euro:
                            print("📥 Attivazione fallback CSV...")
                            try:
                                with page.expect_download() as dl_info:
                                    # Link visibile in basso: SCARICA CSV
                                    btn = page.locator("xpath=//a[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'SCARICA CSV')]").first
                                    if btn and btn.is_visible():
                                        btn.click()
                                    else:
                                        raise Exception('Scarica CSV non trovato')
                                download = dl_info.value
                                # Salva CSV su file temporaneo e leggi il contenuto (Download non ha .content())
                                import tempfile
                                import os as _os
                                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as _tmp_csv:
                                    download.save_as(_tmp_csv.name)
                                    with open(_tmp_csv.name, 'r', encoding='utf-8', errors='ignore') as _f:
                                        text = _f.read()
                                    _os.unlink(_tmp_csv.name)
                                # Parse CSV italiano: cerca header Elemento Aiuto e Data Concessione
                                reader = csv.reader(io.StringIO(text), delimiter=';')
                                headers = next(reader, [])
                                headers_low = [h.strip().lower() for h in headers]
                                try:
                                    idx_importo = headers_low.index('elemento aiuto')
                                except ValueError:
                                    idx_importo = -1
                                try:
                                    idx_data = headers_low.index('data concessione')
                                except ValueError:
                                    idx_data = -1
                                for row in reader:
                                    if not row or (idx_importo == -1 or idx_data == -1) or idx_importo >= len(row) or idx_data >= len(row):
                                        continue
                                    data_txt = row[idx_data].strip()
                                    try:
                                        data_conc = datetime.strptime(data_txt, '%d/%m/%Y')
                                    except Exception:
                                        continue
                                    if data_conc < tre_anni_fa:
                                        continue
                                    importo = self._parse_importo_it(row[idx_importo])
                                    if not importo:
                                        continue
                                    aiuti.append({
                                        'data_concessione': data_txt,
                                        'importo': importo,
                                        'titolo_misura': '',
                                        'data': data_txt,
                                    })
                                if aiuti:
                                    return aiuti, True
                            except Exception as e:
                                print(f"❌ Errore fallback CSV: {e}")
                                pass

                        # Header: trova indici
                        # Ricava header: se non in tbody, prendi thead
                        header_nodes = table.locator("thead th").all()
                        if not header_nodes:
                            header_nodes = rows[0].locator("th").all()
                        headers = [h.inner_text().strip().lower() for h in header_nodes]
                        has_thead = len(table.locator("thead th").all()) > 0
                        def idx_of(predicate):
                            for i, t in enumerate(headers):
                                if predicate(t):
                                    return i
                            return -1

                        data_idx = idx_of(lambda t: ("data" in t and "concessione" in t))
                        importo_idx = idx_of(lambda t: (("elemento" in t and "aiuto" in t) or ("importo" in t)))
                        titolo_idx = idx_of(lambda t: ("titolo" in t and ("misura" in t or "progetto" in t)))
                        if titolo_idx == -1:
                            titolo_idx = 2 if len(headers) > 2 else -1
                        if data_idx == -1:
                            data_idx = 6
                        if importo_idx == -1:
                            importo_idx = len(headers) - 1 if headers else -1

                        start_index = 0 if has_thead else 1
                        for r in rows[start_index:]:
                            cells = r.locator("td").all()
                            if len(cells) < 3:
                                # Tabelle compatte: prova un parsing più tollerante
                                pass
                            # Cerca data in qualunque cella se l'indice non è affidabile
                            data_txt = ""
                            candidates = []
                            if data_idx < len(cells):
                                try:
                                    candidates.append(cells[data_idx].inner_text().strip())
                                except Exception:
                                    pass
                            # Aggiungi tutte le celle per ricerca regex
                            for c in cells:
                                try:
                                    txt = c.inner_text().strip()
                                    if txt:
                                        candidates.append(txt)
                                except Exception:
                                    continue
                            for txt in candidates:
                                m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", txt)
                                if m:
                                    data_txt = m.group(1)
                                    break
                            if not data_txt:
                                continue
                            try:
                                data_conc = datetime.strptime(data_txt, "%d/%m/%Y")
                            except Exception:
                                continue
                            if data_conc < tre_anni_fa:
                                date_vecchie_consecutive_nonlocal[0] += 1
                                if date_vecchie_consecutive_nonlocal[0] >= 3:
                                    continua = False
                                    break
                                continue
                            else:
                                date_vecchie_consecutive_nonlocal[0] = 0

                            importo_txt = cells[importo_idx].inner_text().strip() if importo_idx < len(cells) else ""
                            importo = self._parse_importo_it(importo_txt)
                            if not importo:
                                # Fallback: cerca la prima cella con simbolo euro
                                for c in cells:
                                    txt = c.inner_text().strip()
                                    if "€" in txt or "," in txt:
                                        imp = self._parse_importo_it(txt)
                                        if imp:
                                            importo = imp
                                            break
                            if not importo:
                                continue
                            titolo = cells[titolo_idx].inner_text().strip() if 0 <= titolo_idx < len(cells) else "N/A"
                            aiuti.append({
                                "data_concessione": data_txt,
                                "importo": importo,
                                "titolo_misura": titolo,
                                "data": data_txt,
                            })
                    except Exception:
                        pass
                    return aiuti, continua

                # trick per mutare nel nested scope
                date_vecchie_consecutive_nonlocal = [0]

                while pagina <= max_pagine:
                    aiuti_pagina, continua = estrai_dalla_pagina()
                    tutti_aiuti.extend(aiuti_pagina)
                    if not continua:
                        break
                    # Vai pagina successiva: DataTables next
                    try:
                        next_btn = page.locator("a.paginate_button.next")
                        if next_btn.is_visible():
                            cls = next_btn.get_attribute("class") or ""
                            if "disabled" not in cls:
                                next_btn.click()
                                page.wait_for_load_state("domcontentloaded", timeout=30000)
                                pagina += 1
                                continue
                    except Exception:
                        pass
                    # Prova numeri pagina
                    avanzato = False
                    for n in [2, 3, 4, 5]:
                        try:
                            num_btn = page.locator(f"xpath=//a[contains(@class,'paginate_button') and text()='{n}']")
                            if num_btn.is_visible():
                                num_btn.click()
                                page.wait_for_load_state("domcontentloaded", timeout=30000)
                                pagina += 1
                                avanzato = True
                                break
                        except Exception:
                            continue
                    if not avanzato:
                        break

                # Fallback CSV se nessun aiuto trovato
                if not tutti_aiuti:
                    try:
                        with page.expect_download() as dl_info:
                            btn = page.locator("xpath=//a[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'SCARICA CSV')]").first
                            if btn and btn.is_visible():
                                btn.click()
                            else:
                                raise Exception('Scarica CSV non trovato')
                        download = dl_info.value
                        # Salva il file temporaneamente e leggilo
                        import tempfile
                        import os
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
                            download.save_as(tmp.name)
                            with open(tmp.name, 'r', encoding='utf-8', errors='ignore') as f:
                                text = f.read()
                            os.unlink(tmp.name)
                        # Parse CSV italiano
                        reader = csv.reader(io.StringIO(text), delimiter=',')
                        headers = next(reader, [])
                        headers_low = [h.strip().lower().strip('"') for h in headers]
                        try:
                            idx_importo = next(i for i, h in enumerate(headers_low) if 'elemento aiuto' in h)
                        except StopIteration:
                            idx_importo = -1
                        try:
                            idx_data = next(i for i, h in enumerate(headers_low) if 'data concessione' in h)
                        except StopIteration:
                            idx_data = -1
                        for row in reader:
                            if not row or (idx_importo == -1 or idx_data == -1) or idx_importo >= len(row) or idx_data >= len(row):
                                continue
                            data_txt = row[idx_data].strip()
                            try:
                                data_conc = datetime.strptime(data_txt, '%d/%m/%Y')
                            except Exception:
                                continue
                            if data_conc < tre_anni_fa:
                                continue
                            importo = self._parse_importo_it(row[idx_importo])
                            if not importo:
                                continue
                            tutti_aiuti.append({
                                'data_concessione': data_txt,
                                'importo': importo,
                                'titolo_misura': '',
                                'data': data_txt,
                            })
                    except Exception as e:
                        pass

                totale = round(sum(a["importo"] for a in tutti_aiuti), 2)
                soglia = 300000.0
                risultato = {
                    "partita_iva": partita_iva,
                    "totale_de_minimis": totale,
                    "numero_aiuti": len(tutti_aiuti),
                    "aiuti_trovati": tutti_aiuti,
                    "soglia_superata": totale > soglia,
                    "margine_rimanente": round(max(0, soglia - totale), 2),
                    "soglia_limite": soglia,
                    "percentuale_utilizzata": round((totale / soglia) * 100, 1) if soglia else 0.0,
                    "data_ricerca": oggi.strftime("%d/%m/%Y %H:%M"),
                    "pagine_analizzate": pagina,
                }
                return risultato

            except Exception as e:
                errore_msg = f"Errore Playwright: {e}"
                
                # Invia alert email se abilitato
                if EMAIL_ALERTS_ENABLED:
                    try:
                        # Verifica se è un errore critico (selettori non funzionano)
                        errore_str = str(e).lower()
                        if any(keyword in errore_str for keyword in ['timeout', 'selector', 'element', 'not found']):
                            print("📧 Invio alert email per errore critico RNA...")
                            alert_rna_error(
                                partita_iva=partita_iva,
                                errore=errore_msg,
                                dettagli={
                                    "Tipo Errore": type(e).__name__,
                                    "URL": self.url,
                                    "Browser": "Chromium/Playwright",
                                    "Headless": str(self.headless)
                                },
                                screenshot_path="debug_rna_post_submit.png" if os.path.exists("debug_rna_post_submit.png") else None
                            )
                    except Exception as email_err:
                        print(f"⚠️ Errore invio alert email: {email_err}")
                
                return {
                    "errore": errore_msg,
                    "partita_iva": partita_iva,
                    "totale_de_minimis": 0.0,
                    "numero_aiuti": 0,
                    "aiuti_trovati": [],
                    "margine_rimanente": 300000.0,
                    "data_ricerca": oggi.strftime("%d/%m/%Y %H:%M"),
                }
            finally:
                browser.close()


