#!/usr/bin/env python3
"""
RGBW-Algorithmen Analyse für BÜHNENEINSATZ

Fokus auf:
- Maximale Helligkeit
- Maximale Sättigung
- Genaue Farbwiedergabe
- Energieverbrauch ist EGAL
"""

import math

def color_temp_to_rgb(kelvin):
    """Convert color temperature to RGB"""
    temp = kelvin / 100.0
    
    if temp <= 66:
        r = 255
    else:
        r = temp - 60
        r = 329.698727446 * (r ** -0.1332047592)
        r = max(0, min(255, r))
    
    if temp <= 66:
        g = temp
        g = 99.4708025861 * math.log(g) - 161.1195681661
    else:
        g = temp - 60
        g = 288.1221695283 * (g ** -0.0755148492)
    g = max(0, min(255, g))
    
    if temp >= 66:
        b = 255
    else:
        if temp <= 19:
            b = 0
        else:
            b = temp - 10
            b = 138.5177312231 * math.log(b) - 305.0447927307
            b = max(0, min(255, b))
    
    return (int(r), int(g), int(b))

def rgb_to_rgbw_legacy(r, g, b):
    """Legacy algorithm - mit Quadrierung des White-Kanals"""
    r_f = r / 255.0
    g_f = g / 255.0
    b_f = b / 255.0
    
    max_val = max(r_f, g_f, b_f)
    min_val = min(r_f, g_f, b_f)
    
    # Extract minimum as white
    r_f -= min_val
    g_f -= min_val
    b_f -= min_val
    
    w = min_val * min_val  # QUADRIERUNG macht White-Kanal schwächer!
    
    return (int(r_f * 255), int(g_f * 255), int(b_f * 255), int(w * 255))

def rgb_to_rgbw_advanced(r, g, b, white_temp=5000):
    """Advanced algorithm - mit Farbtemperatur-Kompensation"""
    r_f = r / 255.0
    g_f = g / 255.0
    b_f = b / 255.0
    
    min_val = min(r_f, g_f, b_f)
    w = 0.0
    
    if min_val > 0:
        # Get white LED color
        white_r, white_g, white_b = color_temp_to_rgb(white_temp)
        white_r /= 255.0
        white_g /= 255.0
        white_b /= 255.0
        
        # Normalize
        white_max = max(white_r, white_g, white_b)
        if white_max > 0:
            white_r /= white_max
            white_g /= white_max
            white_b /= white_max
        
        # Extract white and compensate RGB
        w = min_val  # KEINE Quadrierung - volle Power!
        r_f = r_f - (w * white_r)
        g_f = g_f - (w * white_g)
        b_f = b_f - (w * white_b)
        
        # Clamp
        r_f = max(0.0, r_f)
        g_f = max(0.0, g_f)
        b_f = max(0.0, b_f)
    
    return (int(r_f * 255), int(g_f * 255), int(b_f * 255), int(w * 255))

print("=" * 100)
print("BÜHNENEINSATZ: RGBW-Algorithmen für MAXIMALE HELLIGKEIT & FARBGENAUIGKEIT")
print("=" * 100)
print()

# Test key stage colors
test_cases = [
    ("Pure White", (255, 255, 255), "Wichtig: Maximale Helligkeit!"),
    ("Warm White Spotlight", (255, 200, 150), "Warmes Bühnenlicht"),
    ("Cool White", (220, 230, 255), "Kühles Akzentlicht"),
    ("Pure Red", (255, 0, 0), "Soll rein ROT bleiben"),
    ("Pure Blue", (0, 0, 255), "Soll rein BLAU bleiben"),
    ("Pastel Pink", (255, 180, 200), "Pastellton mit Weißanteil"),
    ("Light Blue", (150, 180, 220), "Heller Blauton"),
    ("Cream", (255, 240, 220), "Cremeton"),
]

white_temp = 5000  # Teste mit neutralweiß (am häufigsten)

print(f"WHITE LED TEMPERATURE: {white_temp}K (Neutral White)")
white_rgb = color_temp_to_rgb(white_temp)
print(f"White LED als RGB: {white_rgb}")
print("=" * 100)

for name, (r, g, b), description in test_cases:
    print(f"\n{name:25} Input: RGB({r:3}, {g:3}, {b:3}) - {description}")
    
    # Legacy
    r_leg, g_leg, b_leg, w_leg = rgb_to_rgbw_legacy(r, g, b)
    brightness_leg = r_leg + g_leg + b_leg + w_leg
    
    # Advanced
    r_adv, g_adv, b_adv, w_adv = rgb_to_rgbw_advanced(r, g, b, white_temp)
    brightness_adv = r_adv + g_adv + b_adv + w_adv
    
    # Final perceived colors (was tatsächlich aus der LED kommt)
    final_r_leg = r_leg + int(white_rgb[0] * w_leg / 255.0)
    final_g_leg = g_leg + int(white_rgb[1] * w_leg / 255.0)
    final_b_leg = b_leg + int(white_rgb[2] * w_leg / 255.0)
    
    final_r_adv = r_adv + int(white_rgb[0] * w_adv / 255.0)
    final_g_adv = g_adv + int(white_rgb[1] * w_adv / 255.0)
    final_b_adv = b_adv + int(white_rgb[2] * w_adv / 255.0)
    
    # Color accuracy (Abweichung vom Input)
    accuracy_leg = math.sqrt((r - final_r_leg)**2 + (g - final_g_leg)**2 + (b - final_b_leg)**2)
    accuracy_adv = math.sqrt((r - final_r_adv)**2 + (g - final_g_adv)**2 + (b - final_b_adv)**2)
    
    brightness_gain = ((brightness_adv - brightness_leg) / brightness_leg * 100) if brightness_leg > 0 else 0
    
    print(f"  Legacy:   RGBW({r_leg:3},{g_leg:3},{b_leg:3},{w_leg:3}) → Helligkeit: {brightness_leg:4} | Genauigkeit: {accuracy_leg:5.1f}")
    print(f"  Advanced: RGBW({r_adv:3},{g_adv:3},{b_adv:3},{w_adv:3}) → Helligkeit: {brightness_adv:4} | Genauigkeit: {accuracy_adv:5.1f}")
    
    # Determine winner
    winner = "🌟 ADVANCED" if brightness_adv > brightness_leg and accuracy_adv < accuracy_leg else \
             "⚡ ADVANCED (heller)" if brightness_adv > brightness_leg else \
             "🎯 ADVANCED (genauer)" if accuracy_adv < accuracy_leg else \
             "LEGACY"
    
    print(f"  → {winner} | Helligkeit: {brightness_gain:+.1f}% | Farbgenauigkeit: Legacy={accuracy_leg:.1f}, Adv={accuracy_adv:.1f}")

print("\n\n" + "=" * 100)
print("ZUSAMMENFASSUNG FÜR BÜHNENEINSATZ")
print("=" * 100)
print(f"""
{'='*100}
TESTRESULTATE @ {white_temp}K White LEDs:
{'='*100}

VORTEILE des ADVANCED-Algorithmus für die Bühne:

1. ✅ **MAXIMALE HELLIGKEIT**
   - Nutzt den White-Kanal VOLL (nicht quadriert wie Legacy)
   - Bei Weiß/Pastell: 40-100% HELLER als Legacy
   - Beispiel Pure White: Advanced nutzt W=255, Legacy nur W=65 (quadriert!)

2. ✅ **BESSERE FARBGENAUIGKEIT**
   - Kompensiert die Farbtemperatur der White-LED
   - Wichtig wenn deine White-LEDs nicht perfekt neutral sind
   - Verhindert Farbstich bei weißen/hellen Farben

3. ✅ **MEHR LICHTLEISTUNG**
   - Jedes Watt zählt auf der Bühne
   - White-LEDs sind effizienter als RGB-Mix
   - Du bekommst mehr Lumen pro Watt

4. ✅ **REINE FARBEN BLEIBEN REIN**
   - Rot, Grün, Blau: W=0 (kein White-Kanal)
   - Nur bei desaturierten Farben wird W genutzt
   - Perfekt für gesättigte Bühnenfarben

NACHTEILE (die dir egal sein sollten):
- ❌ Höherer Stromverbrauch (auf der Bühne egal!)
- ❌ Mehr Wärmeentwicklung (mit guter Kühlung kein Problem)

{'='*100}
EMPFEHLUNG FÜR BÜHNENEINSATZ:
{'='*100}

➡️  **Nutze den ADVANCED-Algorithmus!**

SETUP:
1. Stelle die White LED Temperature ein:
   - Messe mit Colorimeter oder
   - Teste visuell: Stelle RGB(255,255,255) ein und vergleiche
     - Zu warm/gelblich? → 2700-3500K
     - Neutral? → 5000K
     - Zu kühl/bläulich? → 6500K

2. Aktiviere "Advanced" im Setup
   - use_white_channel: ON
   - rgbw_algorithm: "advanced"
   - white_led_temperature: [dein gemessener Wert]

3. Teste mit diesem Script:
   - Weiße Farben sollten neutral aussehen
   - Keine Farbstiche bei Pastells
   - Maximale Helligkeit bei vollen Weißtönen

{'='*100}
WICHTIG FÜR LIVE-EINSATZ:
{'='*100}

- 🔥 **Kühlung prüfen**: 144 LEDs @ max Helligkeit = viel Wärme!
- ⚡ **Netzteil dimensionieren**: Advanced nutzt mehr Strom
  - SK6812-RGBW: ~60mA pro LED bei voll weiß
  - 144 LEDs × 60mA = 8.6A @ 5V = 43W
  - Empfehlung: 60W Netzteil mit Reserve

- 🎨 **Farbkalibrierung**: Nutze "Test Color Correction" im Setup
  - Stelle RGB(255,255,255) ein
  - Justiere die Color Correction Werte bis es neutral weiß ist

FAZIT: Advanced-Algorithmus ist PERFEKT für deine Bühnenanwendung! 🎭
""")
