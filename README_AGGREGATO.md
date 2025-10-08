# 🧮 De Minimis Aggregato - Sistema Integrato

## 🎯 Obiettivo

Sistema che **automaticamente verifica società associate** tramite **Cribis X** e calcola il **De Minimis aggregato** per gruppi societari, includendo tutte le aziende italiane controllate con quota **>50%**.

---

## 🚀 Funzionalità Principali

### 🔍 **Ricerca Automatica Associate**
- Login automatico su **Cribis X** (https://www2.cribisx.com)
- Ricerca puntuale per P.IVA/CF
- Estrazione albero societario
- Filtro associate italiane **>50%**

### 📊 **Calcolo De Minimis Aggregato**
- Calcolo per **azienda principale + associate**
- Aggregazione totali di gruppo
- Soglia **€300.000** (Regime Generale De Minimis)
- **Fallback automatico** se Cribis non disponibile

### 🌐 **Interfaccia Web Avanzata**
- Input singola P.IVA
- Visualizzazione risultati **per azienda**
- Export **Markdown per ChatGPT**
- Responsive design

---

## 📁 File Principali

| File | Descrizione |
|------|-------------|
| `cribis_connector.py` | 🔗 Connector Selenium per Cribis X |
| `deminimis_aggregato.py` | 🧮 Motore calcolo aggregato |
| `inserisci_piva_aggregato.py` | 🌐 Server Flask integrato |
| `templates/inserisci_aggregato.html` | 🎨 Interfaccia web |
| `test_aggregato.py` | 🧪 Test di sistema |

---

## 🔧 Installazione e Avvio

### 1. **Preparazione Ambiente**
```bash
cd rna-deminimis-agente
source venv/bin/activate
```

### 2. **Installazione Dipendenze**
```bash
# Se non già installate
pip install selenium flask flask-cors
```

### 3. **Avvio Sistema**
```bash
python inserisci_piva_aggregato.py
```

### 4. **Accesso Interfaccia**
```
http://localhost:8080
```

---

## 🎮 Utilizzo

### 📝 **Input**
1. Inserisci **P.IVA o Codice Fiscale** (es. `02918700168`)
2. Clicca **"🧮 Calcola Aggregato"**

### ⏳ **Processo Automatico**
1. **Ricerca associate** su Cribis X
2. **Calcolo De Minimis** per ogni azienda
3. **Aggregazione risultati**

### 📊 **Output**
- **Totale gruppo** con stato (verde/giallo/rosso)
- **Dettagli per azienda** (principale + associate)
- **Lista aiuti** con data/importo/titolo
- **Export Markdown** per ChatGPT

---

## 📋 Esempio Output JSON

```json
{
  "timestamp": "2025-09-17T16:30:00",
  "p_iva_principale": "02918700168",
  "metodo": "aggregato",
  "associate_trovate": [
    {
      "ragione_sociale": "Martens Italia Srl",
      "cf": "04098200167",
      "percentuale": "100%"
    }
  ],
  "risultati_per_azienda": [
    {
      "codice_fiscale": "02918700168",
      "ragione_sociale": "AZIENDA PRINCIPALE",
      "tipo": "principale",
      "deminimis_ricevuto": 50000.0,
      "numero_aiuti": 3,
      "dettagli_aiuti": [...]
    }
  ],
  "totale_gruppo": {
    "totale_deminimis": 125000.0,
    "numero_aziende": 2,
    "numero_aiuti_totali": 8,
    "percentuale_utilizzata": 41.7,
    "margine_rimanente": 175000.0,
    "stato": "verde"
  }
}
```

---

## 🔐 Credenziali Cribis X

```
URL: https://www2.cribisx.com/#Home/Index
USER: CC838673
PASS: 26082025__Pigreco_
```

---

## 🎯 Logica Sistema

### 📍 **STEP 1: Ricerca Associate**
1. Login automatico Cribis X
2. Sezione "Documenti" → "RICERCA PUNTUALE"
3. Inserimento P.IVA
4. Selezione primo risultato
5. Analisi albero societario

### 📍 **STEP 2: Filtro Associate**
- **Percentuale > 50%**
- **Aziende italiane** (CF 11 cifre)
- **Codice Fiscale visibile**

### 📍 **STEP 3: Calcolo Aggregato**
- Calcolo De Minimis per **ogni azienda**
- **Aggregazione totali**
- Calcolo **percentuale utilizzata**
- Determinazione **stato** (verde/giallo/rosso)

### 📍 **STEP 4: Fallback**
Se Cribis non disponibile:
- **Calcolo singola azienda**
- Warning nell'interfaccia
- Metodo: `"singolo"`

---

## 🚨 Stati Sistema

| Stato | Soglia | Colore | Descrizione |
|-------|---------|--------|-------------|
| 🟢 **Verde** | < 70% | Verde | Situazione ottimale |
| 🟡 **Giallo** | 70-89% | Giallo | Attenzione |
| 🔴 **Rosso** | ≥ 90% | Rosso | Soglia critica |

---

## 📤 Export ChatGPT

Il pulsante **"📋 Copia Markdown"** genera:

```markdown
# Analisi De Minimis Aggregato - P.IVA 02918700168

## 📊 Riepilogo Gruppo
- **P.IVA Principale**: 02918700168
- **Metodo**: Calcolo Aggregato Gruppo
- **Totale De Minimis**: €125.000,00
- **Numero Aziende**: 2
- **Utilizzato**: 41.7% (€300.000)

## 🏢 Società Associate (>50%)
- **Martens Italia Srl** - 04098200167 (100%)

## 📋 Dettaglio per Azienda
### 🏠 PRINCIPALE: AZIENDA PRINCIPALE
| Data | Importo | Titolo |
|------|---------|--------|
| 15/06/2024 | €20.000,00 | Aiuto esempio... |
```

---

## 🔧 Troubleshooting

### ❌ **Errore Cribis X**
- Verifica credenziali
- Controlla connessione internet
- Il sistema usa **fallback automatico**

### ❌ **Errore calcolo RNA**
- Verifica P.IVA inserita
- Controlla disponibilità sito RNA
- Riprova dopo qualche minuto

### ❌ **Performance lente**
- Cribis X richiede **tempo per login**
- RNA può richiedere **navigazione multipagina**
- Processo normale: **2-5 minuti**

---

## 🆚 Confronto Versioni

| Caratteristica | **Singolo** | **Aggregato** |
|----------------|-------------|---------------|
| Ricerca Associate | ❌ | ✅ Cribis X |
| Calcolo Gruppo | ❌ | ✅ Automatico |
| Fallback | ❌ | ✅ Intelligente |
| Export Markdown | ✅ | ✅ Avanzato |
| Interfaccia | Semplice | Completa |

---

## 📞 Supporto

Per problemi o miglioramenti, verificare:
1. **Log del terminale** per errori dettagliati
2. **Screenshot debug** (salvati automaticamente)
3. **Database JSON** per dati storici

---

**🎉 Sistema pronto per l'uso!**
**📍 Vai su: http://localhost:8080**
