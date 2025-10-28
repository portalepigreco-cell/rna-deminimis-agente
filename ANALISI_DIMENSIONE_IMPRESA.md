# 📊 ANALISI IMPLEMENTAZIONE: DIMENSIONE D'IMPRESA PMI

## 🎯 OBIETTIVO
Calcolare la dimensione d'impresa (Micro/Piccola/Media/Grande) secondo la Raccomandazione UE 2003/361/CE a partire da una P.IVA, aggregando dati di imprese collegate e partner.

---

## 1️⃣ COMPONENTI ESISTENTI DA RIUTILIZZARE

### ✅ Già implementato in `cribis_nuova_ricerca.py`:

| Funzionalità | Stato | Note |
|-------------|-------|------|
| Login Cribis X | ✅ Completo | `login()` funzionante |
| Download Gruppo Societario | ✅ Completo | `cerca_associate()` genera report |
| Estrazione CF italiani | ✅ Completo | Regex + parsing HTML |
| Estrazione percentuale partecipazione | ✅ Parziale | Solo >50%, serve estendere a 25-50% |
| Filtro società italiane | ✅ Completo | Verifica presenza "Italia" |
| Estrazione nome società | ✅ Completo | Parsing nome azienda |

### ❌ Da implementare EX-NOVO:

| Funzionalità | Priorità | Complessità |
|-------------|----------|-------------|
| Download Company Card Complete | 🔴 Alta | Media |
| Estrazione dati finanziari (Fatturato, Attivo) | 🔴 Alta | Alta |
| Estrazione numero dipendenti (ULA) | 🔴 Alta | Media |
| Download bilanci | 🟡 Media | Alta |
| Parsing PDF bilanci | 🟡 Media | Molto Alta |
| Calcolo aggregati PMI | 🔴 Alta | Bassa |
| Classificazione impresa | 🔴 Alta | Bassa |
| Generazione report PDF | 🟢 Bassa | Media |

---

## 2️⃣ STRATEGIA IMPLEMENTAZIONE

### Opzione A: **Approccio Completo con PDF** (⏱️ Tempo: 3-5 giorni)
1. Scarica Company Card + Bilanci in PDF
2. Parsing PDF con OCR/regex per estrarre dati
3. Validazione dati estratti
4. Calcolo aggregati

**PRO**: Dati più accurati, archivio completo
**CONTRO**: Parsing PDF complesso e fragile, richiede OCR

### Opzione B: **Approccio Pragmatico HTML-First** (⏱️ Tempo: 1-2 giorni) ⭐ CONSIGLIATO
1. Naviga alla Company Card HTML (senza PDF)
2. Estrae dati direttamente dalla pagina web
3. Salva screenshot come backup
4. Calcolo aggregati

**PRO**: Più veloce, più stabile, meno dipendenze
**CONTRO**: Meno "documentazione" formale

---

## 3️⃣ ARCHITETTURA PROPOSTA

### 📂 Nuovo file: `dimensione_impresa_pmi.py`

```python
class CalcolatoreDimensionePMI:
    def __init__(self, headless=True):
        # Riutilizza CribisNuovaRicerca per login + gruppo
        self.cribis = CribisNuovaRicerca(headless)
    
    def estrai_gruppo_completo(self, partita_iva):
        """
        Estrae società collegate (>50%) e partner (25-50%)
        Returns: {
            "collegate": [{"cf": ..., "perc": 100.0, "nome": ...}],
            "partner": [{"cf": ..., "perc": 35.0, "nome": ...}]
        }
        """
    
    def estrai_dati_finanziari(self, codice_fiscale):
        """
        Naviga alla Company Card e estrae:
        - Numero dipendenti (ULA)
        - Fatturato ultimo anno
        - Attivo patrimoniale
        Returns: {"personale": 12, "fatturato": 2500000, "attivo": 1800000}
        """
    
    def calcola_aggregati(self, core, collegate, partner):
        """
        Formula UE:
        - ULA_agg = core + SUM(collegate*100%) + SUM(partner*quota%)
        - Fatturato_agg = idem
        - Attivo_agg = idem
        """
    
    def classifica_impresa(self, ula_agg, fatturato_agg, attivo_agg):
        """
        Soglie UE:
        - Micro: ULA<10 E (fatturato≤2M O attivo≤2M)
        - Piccola: ULA<50 E (fatturato≤10M O attivo≤10M)
        - Media: ULA<250 E (fatturato≤50M O attivo≤43M)
        - Grande: altrimenti
        """
```

### 🌐 Nuovo endpoint Flask in `web_finale.py`:

```python
@app.route('/calcola_dimensione_pmi', methods=['POST'])
def calcola_dimensione_pmi():
    data = request.get_json()
    piva = data.get('partita_iva')
    
    calc = CalcolatoreDimensionePMI(headless=True)
    risultato = calc.calcola_completo(piva)
    
    return jsonify(risultato)
```

### 🎨 Nuovo tab in `templates/finale.html`:

```html
<button class="mode-btn" onclick="switchMode('pmi')">Dimensione PMI</button>

<div id="pmi-mode" class="mode-content">
    <label>Partita IVA:</label>
    <input type="text" id="piva-pmi" maxlength="11">
    <button class="btn" onclick="calcolaDimensionePMI()">
        📊 Calcola Dimensione
    </button>
</div>
```

---

## 4️⃣ SFIDE TECNICHE

### 🔴 CRITICHE

1. **Navigazione Company Card Cribis**
   - Serve trovare il link corretto per ogni CF
   - Formato URL: `https://www2.cribisx.com/#CompanyCard/View/[ID]`
   - **Soluzione**: Cercare CF in search → cliccare primo risultato

2. **Estrazione dati finanziari**
   - Struttura HTML variabile tra aziende
   - Dati potrebbero non essere disponibili
   - **Soluzione**: Selettori multipli + fallback a "N/D"

3. **Gestione società estere**
   - UE richiede solo imprese UE nel calcolo
   - **Soluzione**: Filtro già esistente su "Italia"

### 🟡 MEDIE

4. **Timeout e performance**
   - Gruppo con 20 società = 20 Company Card da scaricare
   - **Soluzione**: Parallelizzazione o cache intermedia

5. **Dati mancanti**
   - Startup senza bilanci, società in liquidazione
   - **Soluzione**: Valori 0 con flag "dati_incompleti"

---

## 5️⃣ ROADMAP IMPLEMENTAZIONE

### FASE 1: Core (Giorno 1)
- [ ] Creare `dimensione_impresa_pmi.py`
- [ ] Estendere estrazione percentuali (25-50% partner)
- [ ] Navigazione Company Card per singolo CF
- [ ] Estrazione ULA/Fatturato/Attivo da HTML

### FASE 2: Aggregazione (Giorno 1-2)
- [ ] Calcolo formule UE aggregati
- [ ] Classificazione Micro/Piccola/Media/Grande
- [ ] Gestione errori e dati mancanti

### FASE 3: Integrazione Web (Giorno 2)
- [ ] Endpoint Flask `/calcola_dimensione_pmi`
- [ ] Nuovo tab UI
- [ ] Loading indicator (processo può durare 2-5 minuti)
- [ ] Output JSON formattato

### FASE 4: Testing & Refine (Giorno 2-3)
- [ ] Test con 5-10 P.IVA reali
- [ ] Validazione calcoli vs manuale
- [ ] Ottimizzazioni performance

---

## 6️⃣ DATI DI OUTPUT

### JSON Esempio:

```json
{
  "cliente": {
    "partita_iva": "04143180984",
    "ragione_sociale": "POZZI MILANO SPA",
    "personale": 28,
    "fatturato": 8500000,
    "attivo": 7200000
  },
  "collegate": [
    {
      "cf": "04270390984",
      "nome": "POZZI LOGISTICA SRL",
      "percentuale": 100.0,
      "personale": 5,
      "fatturato": 1200000,
      "attivo": 800000
    }
  ],
  "partner": [
    {
      "cf": "03304320983",
      "nome": "PARTNER SRL",
      "percentuale": 35.0,
      "personale": 12,
      "fatturato": 3000000,
      "attivo": 2000000
    }
  ],
  "aggregati": {
    "personale_totale": 37.2,
    "fatturato_totale": 10750000,
    "attivo_totale": 8700000
  },
  "classificazione": "Piccola Impresa",
  "soglie_rispettate": {
    "personale_ok": true,
    "fatturato_ok": true,
    "attivo_ok": true
  },
  "data_calcolo": "2025-10-28 14:30:15",
  "note": "Calcolo basato su dati Cribis Company Card"
}
```

---

## 7️⃣ DOMANDE PER L'UTENTE

Prima di procedere:

1. **Priorità dati**: Preferisci approccio HTML (veloce ma meno formale) o PDF+OCR (lento ma documentato)?

2. **Gestione dati mancanti**: Se una collegata non ha bilanci/dati, come procediamo?
   - Salto società
   - Assume 0
   - Errore e blocco

3. **Formato output**: Oltre al JSON, serve anche PDF o Excel per il cliente?

4. **Tempistiche**: Quanto tempo abbiamo per l'implementazione?

5. **Test**: Hai già alcune P.IVA di prova da usare per testare?

---

## 📌 DECISIONI UTENTE

✅ **Confermate**:
1. **Approccio**: HTML-First (veloce e stabile)
2. **Dati mancanti**: Restituire messaggio "La società non ha dati finanziari"
3. **Output PDF**: Opzionale, da implementare in seguito
4. **Tempistiche**: Senza fretta, priorità alla qualità
5. **P.IVA test**: `04143180984` (Pozzi Milano SPA)

---

## 8️⃣ DETTAGLI TECNICI NAVIGAZIONE CRIBIS

### 🔍 Flusso Company Card Completa (da screenshot):

```
1. Cerca P.IVA/CF nel campo ricerca
2. Clicca sul nome azienda nel primo risultato
3. Nella pagina dettaglio, cerca link "Tutti i prodotti CRIBIS X"
4. Clicca su link → si apre modale
5. Nella modale, cerca card "Company Card Completa"
6. Clicca bottone "Richiedi" con class "button-big corn-flower-blue-bg buy-link"
7. Aspetta apertura nuova tab o navigazione al report
8. Estrae dati dalla pagina HTML del report
```

### 🎯 Selettori CSS chiave:

```python
SELETTORI_CRIBIS = {
    "campo_ricerca": 'input[title="Inserisci i termini da cercare"]',
    "nome_primo_risultato": 'div[class*="result"] a:first-of-type',
    "tutti_prodotti_link": 'a.link-orange:has-text("Tutti i prodotti")',
    "modale_prodotti": '.modal:visible',
    "card_company_card": 'em:has-text("Company Card Completa")',
    "bottone_richiedi": 'a.button-big.corn-flower-blue-bg.buy-link',
    
    # Dati finanziari (da verificare nella pagina report)
    "dipendenti": [
        'div:has-text("Dipendenti")',
        'span:has-text("ULA")',
        'td:has-text("Personale")'
    ],
    "fatturato": [
        'div:has-text("Fatturato")',
        'td:has-text("Ricavi")',
        'span:has-text("Valore produzione")'
    ],
    "attivo": [
        'div:has-text("Totale attivo")',
        'td:has-text("Attivo patrimoniale")'
    ]
}
```

---

## 9️⃣ STRUTTURA DATI INTERNI

### 📊 Oggetto Società (interno):

```python
{
    "cf": "04143180984",
    "ragione_sociale": "POZZI MILANO SPA",
    "tipo_relazione": "core",  # core | collegata | partner
    "percentuale": 100.0,
    "dati_finanziari": {
        "personale_ula": 28,
        "fatturato": 8500000,
        "attivo_patrimoniale": 7200000,
        "anno_riferimento": "2024",
        "fonte": "Company Card Completa Cribis"
    },
    "stato_dati": "completi",  # completi | parziali | assenti
    "note": ""
}
```

### 🧮 Calcolo Aggregati UE:

```python
def calcola_aggregati_ue(core, collegate, partner):
    """
    Formula Raccomandazione 2003/361/CE:
    
    personale_totale = personale_core + 
                       SUM(personale_collegata × 100%) + 
                       SUM(personale_partner × quota%)
    
    fatturato_totale = [stessa formula]
    attivo_totale = [stessa formula]
    
    Returns:
        {
            "personale_agg": float,
            "fatturato_agg": float,
            "attivo_agg": float,
            "dettaglio_calcolo": {
                "core": {...},
                "collegate_contributo": float,
                "partner_contributo": float
            }
        }
    """
```

### 🏆 Classificazione PMI (Soglie UE):

```python
SOGLIE_UE = {
    "micro": {
        "personale": 10,
        "fatturato": 2_000_000,
        "attivo": 2_000_000,
        "operatore": "AND"  # personale<10 AND (fatturato≤2M OR attivo≤2M)
    },
    "piccola": {
        "personale": 50,
        "fatturato": 10_000_000,
        "attivo": 10_000_000,
        "operatore": "AND"
    },
    "media": {
        "personale": 250,
        "fatturato": 50_000_000,
        "attivo": 43_000_000,
        "operatore": "AND"
    }
    # Se supera media → Grande
}

def classifica(personale_agg, fatturato_agg, attivo_agg):
    if personale_agg < 10 and (fatturato_agg <= 2M or attivo_agg <= 2M):
        return "Microimpresa"
    elif personale_agg < 50 and (fatturato_agg <= 10M or attivo_agg <= 10M):
        return "Piccola Impresa"
    elif personale_agg < 250 and (fatturato_agg <= 50M or attivo_agg <= 43M):
        return "Media Impresa"
    else:
        return "Grande Impresa"
```

---

## 🔟 PIANO IMPLEMENTAZIONE DETTAGLIATO

### FASE 1: Preparazione (30 min)
- [ ] Creare file `dimensione_impresa_pmi.py`
- [ ] Setup classe `CalcolatoreDimensionePMI`
- [ ] Import e riutilizzo `CribisNuovaRicerca`

### FASE 2: Estensione Gruppo Societario (2-3 ore)
- [ ] Modificare `cribis_nuova_ricerca.py`:
  - Estendere regex percentuali per catturare 25-50%
  - Dividere risultati in `collegate` (>50%) e `partner` (25-50%)
  - Salvare percentuale esatta (non solo >50%)
  
```python
# PRIMA (attuale):
if perc_val > 50:
    has_majority = True
    
# DOPO (nuovo):
if perc_val >= 25:
    if perc_val > 50:
        categoria = "collegata"
    else:
        categoria = "partner"
    societa["categoria"] = categoria
    societa["percentuale_numerica"] = perc_val
```

### FASE 3: Navigazione Company Card (4-5 ore)
- [ ] Creare metodo `naviga_company_card(cf)`
  - Ricerca CF
  - Clic nome azienda
  - Apertura "Tutti i prodotti"
  - Clic "Company Card Completa"
  - Aspetta caricamento report
  - Screenshot debug

### FASE 4: Estrazione Dati Finanziari (3-4 ore)
- [ ] Creare metodo `estrai_dati_finanziari(page)`
  - Cerca sezione "Basic Data" o "Dati principali"
  - Estrae ULA/Dipendenti (regex: `\d+\s*Unità`)
  - Estrae Fatturato (regex: `€?\s*[\d.,]+`)
  - Estrae Attivo Patrimoniale
  - Gestione valori assenti → `None`
  - Validazione numeri (rimozione punti/virgole)

### FASE 5: Calcoli Aggregati (2 ore)
- [ ] Implementare `calcola_aggregati()`
- [ ] Implementare `classifica_impresa()`
- [ ] Generare report JSON completo

### FASE 6: Integrazione Web (3 ore)
- [ ] Endpoint Flask `/calcola_dimensione_pmi`
- [ ] Nuovo tab UI
- [ ] Loading con progress (può durare 5-10 minuti)
- [ ] Output formattato

### FASE 7: Testing (3-4 ore)
- [ ] Test P.IVA: 04143180984
- [ ] Test casi edge:
  - Società senza dati
  - Solo collegate, nessun partner
  - Gruppo molto grande (>20 società)
- [ ] Validazione calcoli manuali

---

## 🎯 OUTPUT FINALE ATTESO

```json
{
  "risultato": "success",
  "partita_iva_richiesta": "04143180984",
  "data_calcolo": "2025-10-28 15:30:00",
  
  "impresa_principale": {
    "cf": "04143180984",
    "ragione_sociale": "POZZI MILANO SPA",
    "personale": 28,
    "fatturato": 8500000,
    "attivo": 7200000,
    "stato_dati": "completi"
  },
  
  "societa_collegate": [
    {
      "cf": "04270390984",
      "nome": "POZZI LOGISTICA SRL",
      "percentuale": 100.0,
      "personale": 5,
      "fatturato": 1200000,
      "attivo": 800000,
      "stato_dati": "completi"
    }
  ],
  
  "societa_partner": [
    {
      "cf": "03304320983",
      "nome": "PARTNER SRL",
      "percentuale": 35.0,
      "personale": 12,
      "fatturato": 3000000,
      "attivo": 2000000,
      "contributo_percentuale": 35.0,
      "stato_dati": "completi"
    }
  ],
  
  "aggregati_ue": {
    "personale_totale": 37.2,
    "fatturato_totale": 10750000,
    "attivo_totale": 8700000,
    "dettaglio_calcolo": {
      "core": 28,
      "collegate_100%": 5,
      "partner_pro_quota": 4.2
    }
  },
  
  "classificazione": {
    "dimensione": "Piccola Impresa",
    "soglie_rispettate": {
      "personale": {"valore": 37.2, "soglia": 50, "ok": true},
      "fatturato": {"valore": 10750000, "soglia": 10000000, "ok": false},
      "attivo": {"valore": 8700000, "soglia": 10000000, "ok": true}
    },
    "note": "Classificata come Piccola Impresa: personale<50 e attivo≤10M"
  },
  
  "societa_senza_dati": [],
  "warning": [],
  "tempo_elaborazione_secondi": 187
}
```

Procediamo? 🚀

