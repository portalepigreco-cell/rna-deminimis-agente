// SCRIPT VELOCE RNA DE MINIMIS
// Copia e incolla questo script nella console del browser quando sei sulla pagina dei risultati RNA

console.log("🔍 Cercando valori Elemento Aiuto...");

// Cerca tutte le celle che contengono importi
const cells = document.querySelectorAll('td, th');
let totale = 0;
let valoriTrovati = [];

cells.forEach(cell => {
    const testo = cell.textContent.trim();
    
    // Pattern per importi in euro (es: 1.234,56 o €1.234,56)
    const importoMatch = testo.match(/€?\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?)\s*€?/);
    
    if (importoMatch && 
        !testo.toLowerCase().includes('partita') && 
        !testo.toLowerCase().includes('codice') &&
        !testo.toLowerCase().includes('data')) {
        
        // Converte formato italiano in numero
        let valore = importoMatch[1].replace(/\./g, '').replace(',', '.');
        let numero = parseFloat(valore);
        
        if (!isNaN(numero) && numero > 10) { // Filtra valori troppo piccoli
            totale += numero;
            valoriTrovati.push({
                testo: testo,
                valore: numero
            });
            console.log(`✅ Trovato: ${testo} → €${numero.toFixed(2)}`);
        }
    }
});

console.log("\n" + "=".repeat(50));
console.log(`🎯 TOTALE DE MINIMIS: €${totale.toLocaleString('it-IT', {minimumFractionDigits: 2})}`);
console.log(`📊 Numero aiuti trovati: ${valoriTrovati.length}`);
console.log(`📅 P.IVA: 03254550738`);
console.log("=".repeat(50));

// Copia il risultato negli appunti
const risultato = `P.IVA 03254550738 - Totale De Minimis: €${totale.toLocaleString('it-IT', {minimumFractionDigits: 2})} (${valoriTrovati.length} aiuti)`;
navigator.clipboard.writeText(risultato);
console.log("📋 Risultato copiato negli appunti!");

return totale;
