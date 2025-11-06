#!/usr/bin/env python3
"""
Detaillierte Analyse der RGBW-Algorithmen

Zeigt die tatsächlichen Unterschiede und erklärt was passiert
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

def rgb_to_rgbw_legacy(r, g, b, saturation=1.0):
    """Legacy algorithm from current code"""
    r_f = r / 255.0
    g_f = g / 255.0
    b_f = b / 255.0
    
    max_val = max(r_f, g_f, b_f)
    sat = saturation
    
    if sat == 0:
        r_f, g_f, b_f = 0, 0, 0
        min_val = max_val
    else:
        r_f = (r_f - max_val) * saturation + max_val
        g_f = (g_f - max_val) * saturation + max_val
        b_f = (b_f - max_val) * saturation + max_val
        min_val = min(r_f, g_f, b_f)
        r_f -= min_val
        g_f -= min_val
        b_f -= min_val
    
    w = min_val * min_val  # Squaring makes it less aggressive
    
    return (int(r_f * 255), int(g_f * 255), int(b_f * 255), int(w * 255))

def rgb_to_rgbw_advanced(r, g, b, white_temp=5000, saturation=1.0):
    """Advanced algorithm from current code"""
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
        w = min_val
        r_f = r_f - (w * white_r)
        g_f = g_f - (w * white_g)
        b_f = b_f - (w * white_b)
        
        # Clamp
        r_f = max(0.0, r_f)
        g_f = max(0.0, g_f)
        b_f = max(0.0, b_f)
    
    return (int(r_f * 255), int(g_f * 255), int(b_f * 255), int(w * 255))

print("=" * 100)
print("DETAILLIERTE ANALYSE: Legacy vs Advanced RGBW Algorithmus")
print("=" * 100)
print()

# Test key colors
test_cases = [
    ("Pure White (255,255,255)", (255, 255, 255), "Wichtigster Test: Sollte neutral weiß sein"),
    ("Warm White (255,200,150)", (255, 200, 150), "Warmweißer Ton"),
    ("Light Gray (192,192,192)", (192, 192, 192), "Grau - sollte neutral sein"),
    ("Pastel Blue (150,180,220)", (150, 180, 220), "Pastellfarbe mit Weißanteil"),
]

for white_temp in [2700, 5000, 6500]:
    print(f"\n{'='*100}")
    print(f"WHITE LED TEMPERATURE: {white_temp}K")
    white_rgb = color_temp_to_rgb(white_temp)
    print(f"White LED als RGB: {white_rgb}")
    print(f"{'='*100}\n")
    
    for name, (r, g, b), description in test_cases:
        print(f"\n{name}")
        print(f"  Input RGB: ({r}, {g}, {b})")
        print(f"  {description}")
        print()
        
        # Legacy
        r_leg, g_leg, b_leg, w_leg = rgb_to_rgbw_legacy(r, g, b)
        # Simulate final color: RGB LEDs + White LED
        final_r_leg = r_leg + int(white_rgb[0] * w_leg / 255.0)
        final_g_leg = g_leg + int(white_rgb[1] * w_leg / 255.0)
        final_b_leg = b_leg + int(white_rgb[2] * w_leg / 255.0)
        
        print(f"  LEGACY:")
        print(f"    RGBW Output: ({r_leg:3}, {g_leg:3}, {b_leg:3}, {w_leg:3})")
        print(f"    Final Color: RGB({final_r_leg:3}, {final_g_leg:3}, {final_b_leg:3})")
        print(f"    Total Light: {r_leg + g_leg + b_leg + w_leg}")
        
        # Advanced
        r_adv, g_adv, b_adv, w_adv = rgb_to_rgbw_advanced(r, g, b, white_temp)
        # Simulate final color
        final_r_adv = r_adv + int(white_rgb[0] * w_adv / 255.0)
        final_g_adv = g_adv + int(white_rgb[1] * w_adv / 255.0)
        final_b_adv = b_adv + int(white_rgb[2] * w_adv / 255.0)
        
        print(f"  ADVANCED:")
        print(f"    RGBW Output: ({r_adv:3}, {g_adv:3}, {b_adv:3}, {w_adv:3})")
        print(f"    Final Color: RGB({final_r_adv:3}, {final_g_adv:3}, {final_b_adv:3})")
        print(f"    Total Light: {r_adv + g_adv + b_adv + w_adv}")
        
        # Color difference
        color_diff = math.sqrt(
            (final_r_leg - final_r_adv)**2 +
            (final_g_leg - final_g_adv)**2 +
            (final_b_leg - final_b_adv)**2
        )
        
        # Analysis
        print(f"\n  VERGLEICH:")
        print(f"    Farbdifferenz: {color_diff:.1f} (kleiner = genauer)")
        
        # Check if advanced is more accurate
        input_diff_leg = math.sqrt((r - final_r_leg)**2 + (g - final_g_leg)**2 + (b - final_b_leg)**2)
        input_diff_adv = math.sqrt((r - final_r_adv)**2 + (g - final_g_adv)**2 + (b - final_b_adv)**2)
        
        print(f"    Input→Legacy Abweichung: {input_diff_leg:.1f}")
        print(f"    Input→Advanced Abweichung: {input_diff_adv:.1f}")
        
        if input_diff_adv < input_diff_leg:
            print(f"    ✓ Advanced ist genauer!")
        else:
            print(f"    ✓ Legacy ist genauer!")
        
        # White channel usage
        white_usage_leg = w_leg / 255.0 * 100
        white_usage_adv = w_adv / 255.0 * 100
        print(f"    White-Kanal Nutzung: Legacy {white_usage_leg:.1f}%, Advanced {white_usage_adv:.1f}%")

print("\n\n" + "=" * 100)
print("ZUSAMMENFASSUNG")
print("=" * 100)
print("""
PROBLEM MIT DEM 'ADVANCED' ALGORITHMUS:

Der Advanced-Algorithmus kompensiert zwar die Farbtemperatur der weißen LED,
aber er hat einige Probleme:

1. **Höherer Energieverbrauch**: Er erzeugt mehr Gesamthelligkeit (R+G+B+W)
   - Das liegt daran, dass er den White-Kanal voll nutzt PLUS noch RGB addiert
   - Legacy reduziert RGB und quadriert den White-Wert (macht ihn weicher)

2. **Farbverschiebung bei nicht-neutralen White-LEDs**:
   - Bei 2700K (warmweiß): Kompensation funktioniert, aber viel RGB bleibt übrig
   - Bei 6500K (kaltweiß): Ähnliches Problem
   - Nur bei 5000K (neutral) ist die Kompensation wirklich sinnvoll

3. **Helligkeit nicht konstant**:
   - Gleicher RGB-Input führt zu unterschiedlicher Gesamthelligkeit
   - Das ist für Animationen problematisch

EMPFEHLUNG:

Der Advanced-Algorithmus macht nur Sinn wenn:
- Deine White-LEDs nahe 5000K sind (neutral weiß)
- Du bereit bist, höheren Energieverbrauch zu akzeptieren
- Die exakte Farbwiedergabe wichtiger ist als Effizienz

Der Legacy-Algorithmus ist besser wenn:
- Du Energie sparen willst
- Du die White-LEDs sanft einblenden willst (quadratische Kurve)
- Konsistente Helligkeit wichtig ist

VERBESSERUNGSVORSCHLAG:

Ein optimaler Algorithmus sollte:
1. White-Kanal nutzen wo sinnvoll (bei desaturierten Farben)
2. RGB-Helligkeit durch White-Helligkeit ersetzen (nicht addieren!)
3. Farbtemperatur nur kompensieren wenn White-LED nicht neutral ist
4. Gesamthelligkeit konstant halten
""")
