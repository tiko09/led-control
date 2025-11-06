#!/bin/bash
# Quick-Check Script für RGBW Settings auf dem Raspberry Pi

# Erlaube config.json als Argument
if [ -n "$1" ] && [ -f "$1" ]; then
    CONFIG_FILE="$1"
fi

echo "========================================================================"
echo "RGBW Advanced Algorithm - Quick Check"
echo "========================================================================"
echo ""

# Prüfe ob config.json existiert - versuche verschiedene Pfade
if [ -f "$HOME/led-control/config.json" ]; then
    CONFIG_FILE="$HOME/led-control/config.json"
elif [ -f "./config.json" ]; then
    CONFIG_FILE="./config.json"
elif [ -f "/opt/led-control/config.json" ]; then
    CONFIG_FILE="/opt/led-control/config.json"
elif [ -f "$HOME/.config/led-control/config.json" ]; then
    CONFIG_FILE="$HOME/.config/led-control/config.json"
else
    # Versuche zu finden
    echo "Suche nach config.json..."
    CONFIG_FILE=$(find ~ -name "config.json" -path "*/led-control/*" 2>/dev/null | head -1)
    
    if [ -z "$CONFIG_FILE" ] || [ ! -f "$CONFIG_FILE" ]; then
        echo "❌ config.json nicht gefunden!"
        echo ""
        echo "Getestete Pfade:"
        echo "  - $HOME/led-control/config.json"
        echo "  - ./config.json"
        echo "  - /opt/led-control/config.json"
        echo "  - $HOME/.config/led-control/config.json"
        echo ""
        echo "Bitte führe das Script im led-control Verzeichnis aus oder"
        echo "gib den Pfad zur config.json als Argument an:"
        echo "  $0 /pfad/zur/config.json"
        echo ""
        exit 1
    fi
fi

echo "✓ Config gefunden: $CONFIG_FILE"
echo ""

# Extrahiere RGBW Settings
echo "AKTUELLE RGBW SETTINGS:"
echo "========================================================================="

USE_WHITE=$(grep -o '"use_white_channel"[[:space:]]*:[[:space:]]*[^,]*' "$CONFIG_FILE" | sed 's/.*: *//')
WHITE_TEMP=$(grep -o '"white_led_temperature"[[:space:]]*:[[:space:]]*[0-9]*' "$CONFIG_FILE" | sed 's/.*: *//')
ALGORITHM=$(grep -o '"rgbw_algorithm"[[:space:]]*:[[:space:]]*"[^"]*"' "$CONFIG_FILE" | sed 's/.*: *"\(.*\)"/\1/')

echo "Use White Channel:      $USE_WHITE"
echo "White LED Temperature:  ${WHITE_TEMP}K"
echo "RGBW Algorithm:         $ALGORITHM"
echo ""

# Bewertung
echo "BEWERTUNG:"
echo "========================================================================="

if [ "$USE_WHITE" = "true" ]; then
    echo "✓ White Channel ist AKTIVIERT"
else
    echo "⚠️  White Channel ist DEAKTIVIERT"
    echo "   → Aktiviere im Web-UI unter Setup → RGBW Settings"
fi

if [ "$ALGORITHM" = "advanced" ]; then
    echo "✓ Advanced Algorithm ist AKTIV (maximale Helligkeit!)"
elif [ "$ALGORITHM" = "legacy" ]; then
    echo "⚠️  Legacy Algorithm ist aktiv"
    echo "   → Wechsle zu 'Advanced' für +30-50% Helligkeit bei Weiß!"
    echo "   → Im Web-UI: Setup → RGBW Settings → Algorithm: Advanced"
else
    echo "❌ Unbekannter Algorithm: $ALGORITHM"
fi

if [ -n "$WHITE_TEMP" ]; then
    if [ "$WHITE_TEMP" -ge 4500 ] && [ "$WHITE_TEMP" -le 5500 ]; then
        echo "✓ White LED Temperature: ${WHITE_TEMP}K (Neutral - gut!)"
    elif [ "$WHITE_TEMP" -ge 2700 ] && [ "$WHITE_TEMP" -lt 4500 ]; then
        echo "ℹ️  White LED Temperature: ${WHITE_TEMP}K (Warmweiß)"
    elif [ "$WHITE_TEMP" -gt 5500 ] && [ "$WHITE_TEMP" -le 6500 ]; then
        echo "ℹ️  White LED Temperature: ${WHITE_TEMP}K (Kaltweiß)"
    else
        echo "⚠️  White LED Temperature: ${WHITE_TEMP}K (ungewöhnlicher Wert)"
    fi
else
    echo "⚠️  White LED Temperature nicht gesetzt!"
fi

echo ""
echo "EMPFEHLUNG FÜR BÜHNENEINSATZ:"
echo "========================================================================="

if [ "$USE_WHITE" = "true" ] && [ "$ALGORITHM" = "advanced" ]; then
    echo "🌟 PERFEKT! Du nutzt bereits die optimalen Einstellungen!"
    echo ""
    echo "Erwartete Verbesserungen gegenüber Legacy:"
    echo "  • Pure White:  +29% Helligkeit, 40x genauer"
    echo "  • Pastell:     +40-50% Helligkeit, 50-100x genauer"
    echo "  • Reine Farben: Keine Änderung (bleibt optimal)"
else
    echo "⚡ OPTIMIERUNG MÖGLICH!"
    echo ""
    echo "Für maximale Helligkeit & Farbgenauigkeit:"
    echo "  1. Web-UI öffnen: http://$(hostname -I | awk '{print $1}'):5000"
    echo "  2. Setup Tab → RGBW Settings"
    echo "  3. Use White Channel: ON"
    echo "  4. RGBW Algorithm: Advanced"
    echo "  5. White LED Temperature: 5000K (oder gemessen)"
    echo ""
    echo "Erwartete Verbesserung:"
    echo "  • +30-50% Helligkeit bei Weiß/Pastell"
    echo "  • 40-100x bessere Farbgenauigkeit"
    echo "  • Keine Performance-Einbuße (weiterhin ~7% CPU)"
fi

echo ""
echo "========================================================================"
echo "Weitere Checks:"
echo "========================================================================"

# Prüfe ob Service läuft
if systemctl is-active --quiet ledcontrol; then
    echo "✓ LED Control Service läuft"
else
    echo "⚠️  LED Control Service läuft NICHT"
    echo "   Starten mit: sudo systemctl start ledcontrol"
fi

# Prüfe CPU Last
if command -v top &> /dev/null; then
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    echo "ℹ️  Aktuelle CPU Last: ${CPU_USAGE}% (sollte ~7% sein im Betrieb)"
fi

# Prüfe Temperatur
if command -v vcgencmd &> /dev/null; then
    TEMP=$(vcgencmd measure_temp | sed 's/temp=\([0-9.]*\).*/\1/')
    echo "ℹ️  CPU Temperatur: ${TEMP}°C (sollte < 70°C sein)"
fi

echo ""
echo "========================================================================"
echo "Für detaillierte Setup-Anleitung siehe: RGBW_ADVANCED_SETUP.md"
echo "========================================================================"
