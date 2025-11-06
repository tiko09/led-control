#!/usr/bin/env python3
"""
Test und Vergleich der RGB zu RGBW Konvertierungs-Algorithmen

Testet beide Algorithmen (legacy und advanced) mit verschiedenen Farben
und vergleicht die Ergebnisse in Bezug auf:
- Helligkeit (Gesamtlichtleistung)
- Energieeffizienz (weniger RGB, mehr W = effizienter)
- Farbgenauigkeit
"""

import sys
import os
import math

# Standalone version - no dependencies on ledcontrol module
print("Running standalone test (no ledcontrol dependencies)...")

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
    """Legacy algorithm: Uses desaturation"""
    max_val = max(r, g, b)
    sat = int(saturation * 255)
    
    if sat == 0:
        r, g, b = 0, 0, 0
        min_val = max_val
    else:
        r = (r - max_val) * saturation + max_val
        g = (g - max_val) * saturation + max_val
        b = (b - max_val) * saturation + max_val
        min_val = min(r, g, b)
        r -= min_val
        g -= min_val
        b -= min_val
    
    w = min_val * min_val / 255.0
    
    return (int(r), int(g), int(b), int(w))

def rgb_to_rgbw_advanced(r, g, b, white_temp=5000, saturation=1.0):
    """Advanced algorithm: Extract white and compensate for LED color"""
    # Normalize to 0-1
    r_f = r / 255.0
    g_f = g / 255.0
    b_f = b / 255.0
    
    min_val = min(r_f, g_f, b_f)
    w = 0.0
    
    if min_val > 0:
        # Get white LED color as RGB
        white_r, white_g, white_b = color_temp_to_rgb(white_temp)
        white_r /= 255.0
        white_g /= 255.0
        white_b /= 255.0
        
        # Normalize white color
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
        
        # Clamp to valid range
        r_f = max(0.0, r_f)
        g_f = max(0.0, g_f)
        b_f = max(0.0, b_f)
    
    # Apply saturation to white channel
    sat = int(saturation * 255)
    if sat != 255:
        if sat == 0:
            # Full desaturation: all white
            avg = (r_f + g_f + b_f) / 3.0
            r_f, g_f, b_f = 0, 0, 0
            w = avg + w
        else:
            # Partial desaturation
            avg = (r_f + g_f + b_f) / 3.0
            desat_factor = (255 - sat) / 255.0
            r_f = r_f * (sat / 255.0) + avg * desat_factor
            g_f = g_f * (sat / 255.0) + avg * desat_factor
            b_f = b_f * (sat / 255.0) + avg * desat_factor
            w = w + (avg * desat_factor * desat_factor)
    
    return (int(r_f * 255), int(g_f * 255), int(b_f * 255), int(w * 255))# Test colors
test_colors = [
    ("Pure Red", (255, 0, 0)),
    ("Pure Green", (0, 255, 0)),
    ("Pure Blue", (0, 0, 255)),
    ("Pure White", (255, 255, 255)),
    ("Warm White", (255, 200, 150)),
    ("Cool White", (200, 220, 255)),
    ("Cyan", (0, 255, 255)),
    ("Magenta", (255, 0, 255)),
    ("Yellow", (255, 255, 0)),
    ("Orange", (255, 128, 0)),
    ("Pink", (255, 128, 192)),
    ("Lavender", (200, 180, 255)),
    ("Light Gray", (192, 192, 192)),
    ("Medium Gray", (128, 128, 128)),
    ("Pastel Blue", (150, 180, 220)),
]

# Test white temperatures
white_temps = [2700, 3500, 5000, 6500]

def calculate_total_brightness(r, g, b, w):
    """Calculate total light output (sum of all channels)"""
    return r + g + b + w

def calculate_power_usage(r, g, b, w):
    """
    Estimate power usage. Assumes:
    - Each RGB LED draws proportional power
    - White LED is more efficient (less power for same brightness)
    """
    rgb_power = (r + g + b) * 1.0  # RGB power factor
    w_power = w * 0.7  # White is more efficient (30% less power)
    return rgb_power + w_power

def color_distance(color1, color2):
    """Calculate Euclidean distance between two RGB colors"""
    return math.sqrt(
        (color1[0] - color2[0])**2 +
        (color1[1] - color2[1])**2 +
        (color1[2] - color2[2])**2
    )

print("=" * 80)
print("RGB zu RGBW Konvertierungs-Algorithmen Vergleich")
print("=" * 80)
print()

# Test with different white temperatures
for white_temp in white_temps:
    print(f"\n{'=' * 80}")
    print(f"White LED Temperature: {white_temp}K")
    print(f"White LED RGB equivalent: {color_temp_to_rgb(white_temp)}")
    print(f"{'=' * 80}\n")
    
    total_legacy_brightness = 0
    total_legacy_power = 0
    total_advanced_brightness = 0
    total_advanced_power = 0
    
    for name, (r, g, b) in test_colors:
        # Test legacy algorithm
        r_leg, g_leg, b_leg, w_leg = rgb_to_rgbw_legacy(r, g, b)
        brightness_leg = calculate_total_brightness(r_leg, g_leg, b_leg, w_leg)
        power_leg = calculate_power_usage(r_leg, g_leg, b_leg, w_leg)
        
        # Test advanced algorithm
        r_adv, g_adv, b_adv, w_adv = rgb_to_rgbw_advanced(r, g, b, white_temp)
        brightness_adv = calculate_total_brightness(r_adv, g_adv, b_adv, w_adv)
        power_adv = calculate_power_usage(r_adv, g_adv, b_adv, w_adv)
        
        # Calculate improvements
        brightness_diff = brightness_adv - brightness_leg
        power_diff = power_leg - power_adv  # Positive = advanced is more efficient
        power_savings = (power_diff / power_leg * 100) if power_leg > 0 else 0
        
        total_legacy_brightness += brightness_leg
        total_legacy_power += power_leg
        total_advanced_brightness += brightness_adv
        total_advanced_power += power_adv
        
        print(f"{name:20} RGB({r:3}, {g:3}, {b:3})")
        print(f"  Legacy:   RGBW({r_leg:3}, {g_leg:3}, {b_leg:3}, {w_leg:3}) | Brightness: {brightness_leg:4} | Power: {power_leg:6.1f}")
        print(f"  Advanced: RGBW({r_adv:3}, {g_adv:3}, {b_adv:3}, {w_adv:3}) | Brightness: {brightness_adv:4} | Power: {power_adv:6.1f}")
        print(f"  Diff:     Brightness: {brightness_diff:+4} | Power Savings: {power_savings:+6.1f}%")
        print()
    
    # Summary for this white temperature
    total_power_savings = (total_legacy_power - total_advanced_power) / total_legacy_power * 100
    print(f"\n{'=' * 80}")
    print(f"SUMMARY @ {white_temp}K:")
    print(f"  Total Brightness - Legacy: {total_legacy_brightness}, Advanced: {total_advanced_brightness}")
    print(f"  Total Power - Legacy: {total_legacy_power:.1f}, Advanced: {total_advanced_power:.1f}")
    print(f"  Power Savings: {total_power_savings:+.1f}%")
    print(f"{'=' * 80}")

print("\n\n" + "=" * 80)
print("FAZIT:")
print("=" * 80)
print("""
Der 'Advanced' Algorithmus sollte in folgenden Fällen besser sein:

1. **Energieeffizienz**: Nutzt den weißen LED-Kanal stärker, was effizienter ist
   - Weiße LEDs sind typischerweise 30-40% effizienter als RGB
   - Bei Farben mit hohem Weißanteil (Pastell, Grau, etc.) großer Unterschied

2. **Farbgenauigkeit**: Kompensiert die Farbtemperatur der weißen LED
   - Bei 5000K neutralweiß: minimale Farbverschiebung
   - Bei 2700K warmweiß: ohne Kompensation würde alles zu warm aussehen
   - Bei 6500K kaltweiß: ohne Kompensation zu kühl

3. **Helligkeit**: Kann bei gleicher Leistung heller sein
   - Durch effizientere Nutzung des White-Kanals

EMPFEHLUNG:
- Teste beide Algorithmen mit deinen LEDs
- Achte besonders auf:
  * Weiße/graue Farben (sollten neutral aussehen)
  * Pastellfarben (sollten nicht zu warm/kalt sein)
  * Energieverbrauch/Hitzeentwicklung bei langen Animationen
""")
