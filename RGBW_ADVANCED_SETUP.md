#!/bin/bash
# Setup-Anleitung für Advanced RGBW-Algorithmus auf dem Raspberry Pi

cat << 'EOF'
================================================================================
ADVANCED RGBW-ALGORITHMUS AKTIVIEREN - ANLEITUNG FÜR RASPBERRY PI
================================================================================

Der Advanced-Algorithmus ist bereits im Code implementiert! 
Du musst ihn nur über die Web-UI aktivieren.

SCHRITT 1: Web-Interface öffnen
================================================================================
1. Öffne im Browser: http://[deine-pi-ip]:5000
2. Gehe zum Tab "Setup" (oben rechts)

SCHRITT 2: White LED Temperatur bestimmen
================================================================================
Du hast SK6812-RGBW LEDs. Der White-Kanal hat eine bestimmte Farbtemperatur.

METHODE A - Visueller Test (empfohlen):
---------------------------------------
1. Im Setup → "RGBW Settings" → "Use White Channel": EIN
2. Wähle erstmal "Legacy" Algorithmus
3. Gehe zum "Control" Tab
4. Stelle eine Animation mit viel Weiß ein (z.B. "Static White")
5. Achte auf die Farbe:
   
   Zu WARM/GELBLICH?  → White LEDs sind ~2700-3500K (Warmweiß)
   NEUTRAL?           → White LEDs sind ~5000K (Neutralweiß) ← HÄUFIGSTE
   Zu KALT/BLÄULICH?  → White LEDs sind ~6500K (Kaltweiß)

METHODE B - Datenblatt:
-----------------------
Suche in deinem LED-Datenblatt nach "CCT" oder "Color Temperature"
SK6812-RGBW sind meist: 5000K (neutralweiß)

SCHRITT 3: Advanced-Algorithmus aktivieren
================================================================================
1. Im Setup → "RGBW Settings":
   
   ┌─────────────────────────────────────────────────┐
   │ Use White Channel in Animations        [✓] ON  │
   ├─────────────────────────────────────────────────┤
   │ RGBW Algorithm                                  │
   │ [v] Advanced (White Extraction)     ← WÄHLEN!  │
   ├─────────────────────────────────────────────────┤
   │ White LED Color Temperature                     │
   │ ├─────────────●─────────────┤  5000K ← EINSTELLEN! │
   │ 2700K                      6500K                │
   └─────────────────────────────────────────────────┘

2. Klicke außerhalb oder Tab-Taste → Settings werden automatisch gespeichert

SCHRITT 4: Farbkalibrierung (wichtig!)
================================================================================
1. Im Setup → "Color Calibration" → "Test Color Correction": ON
2. Du siehst jetzt den Weißpunkt deiner RGB-Subpixel
3. Stelle die Werte ein bis es NEUTRAL WEISS aussieht:
   
   Für SK6812-RGBW typische Werte:
   - Red Channel Correction:   255
   - Green Channel Correction: 190-200
   - Blue Channel Correction:  170-180

4. "Test Color Correction": OFF

SCHRITT 5: Testen
================================================================================
1. Gehe zu "Control" Tab
2. Teste verschiedene Animationen:
   
   TESTE BESONDERS:
   - "Static White" → sollte HELL und NEUTRAL sein (kein Gelbstich!)
   - "Static Color" → stelle helles Rosa/Pink ein → sollte korrekt aussehen
   - "Palette Cycle" → achte auf helle/weiße Bereiche
   - Deine Bühnenanimationen

3. Vergleiche mit Legacy:
   - Schalte zurück zu "Legacy" Algorithm
   - Du solltest DEUTLICH sehen:
     * Advanced ist HELLER bei Weiß/Pastell (30-50%!)
     * Advanced hat bessere Farbwiedergabe
     * Reine Farben (Rot/Blau) sind gleich

SCHRITT 6: Settings speichern
================================================================================
Die Settings werden automatisch in config.json gespeichert.
Bei Neustart werden sie wiederhergestellt.

Prüfen kannst du das mit:
   cat ~/led-control/config.json | grep -A2 "rgbw"

Sollte zeigen:
   "use_white_channel": true,
   "white_led_temperature": 5000,
   "rgbw_algorithm": "advanced"

TROUBLESHOOTING
================================================================================

Problem: "Weiß sieht komisch aus / Farbstich"
Lösung: 
  1. Prüfe White LED Temperature (2700K/5000K/6500K)
  2. Prüfe Color Correction Werte
  3. Teste mit Calibration=ON um RGB-Subpixel zu sehen

Problem: "Advanced nicht viel heller als Legacy"
Lösung:
  Teste mit HELLEN Farben! Bei gesättigten Farben (Rot/Blau) ist kein 
  Unterschied. Der Unterschied zeigt sich bei:
  - Weiß, Grau
  - Pastell (Rosa, Hellblau, Creme)
  - Desaturierte Farben

Problem: "Settings werden nicht gespeichert"
Lösung:
  1. Prüfe Schreibrechte: ls -la ~/led-control/config.json
  2. Prüfe ob Service läuft: sudo systemctl status ledcontrol
  3. Schaue ins Log: sudo journalctl -u ledcontrol -f

PERFORMANCE-CHECK
================================================================================
Nach Aktivierung solltest du prüfen:

1. CPU-Last:
   - Im Discovery Tab → sollte weiterhin ~7% sein
   - Advanced-Algorithmus ist NICHT langsamer!

2. Temperatur (wichtig bei max Helligkeit!):
   ssh pi@[deine-ip]
   vcgencmd measure_temp
   
   Sollte < 70°C sein unter Last

3. Stromversorgung:
   - Bei max Helligkeit (viel Weiß): ~8-9A @ 5V
   - Prüfe ob Netzteil ausreicht
   - Achte auf Spannungsabfall bei langen Strips

BÜHNEN-OPTIMIERUNG
================================================================================

Für maximale Performance:
1. Brightness im Control Tab auf 100%
2. Use White Channel: ON
3. RGBW Algorithm: Advanced
4. FPS: 60 (schon optimal nach Optimierung!)

Für maximale Helligkeit bei Weiß:
- Nutze "Static White" Animation
- Mit Advanced: ~30% heller als vorher!
- Achte auf Kühlung!

NÄCHSTE SCHRITTE
================================================================================
Nach erfolgreicher Aktivierung kannst du:

1. Eigene Farbpaletten erstellen (Control → Palettes)
2. Animationen anpassen (Control → Functions)
3. ArtNet für DMX-Steuerung aktivieren (Setup → ArtNet)
4. Weitere Pis hinzufügen (Discovery → Add Pi)

================================================================================
Viel Erfolg mit deinem Setup! 🎭
================================================================================
EOF
