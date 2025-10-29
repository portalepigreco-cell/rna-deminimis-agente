#!/bin/bash
# Script per vedere i log del server Flask in tempo reale

tail -f /tmp/rna_pmi_live.log | grep --line-buffered -E "STEP|URL|Scarica|Richiedi|Company Card|ERRORE|❌|⚠️|✅|Timeout|querySelector|Container|Bottone"

