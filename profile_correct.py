#!/usr/bin/env python3
"""
Korrektes Profiling-Script für LED-Control Performance-Analyse.
Misst die tatsächliche Performance wie in Production.
"""

import time
import sys
import json
import numpy as np
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from ledcontrol.ledcontroller import LEDController
from ledcontrol.animationcontroller import AnimationController


def profile(duration=10):
    """Profile animation for specified duration."""
    
    # Load config
    config_path = None
    for filename in ['ledcontrol-dev.json', 'config.json', 'ledcontrol.json']:
        path = Path(__file__).parent / filename
        if path.exists():
            config_path = path
            break
    
    if not config_path:
        print("ERROR: No config file found")
        return
    
    print(f"Using config: {config_path.name}\n")
    
    with open(config_path) as f:
        config = json.load(f)
    
    # LED controller parameters
    led_count = config.get('led_count', 144)
    if led_count == 0:
        led_count = 144
    
    led_controller = LEDController(
        led_count=led_count,
        led_pin=config.get('led_pin', 18),
        led_data_rate=config.get('led_data_rate', 800000),
        led_dma_channel=config.get('led_dma_channel', 10),
        led_pixel_order=config.get('led_pixel_order', 'GRBW')
    )
    
    # Animation controller
    refresh_rate = config.get('frame_rate', 60)
    
    import ledcontrol.pixelmappings as pixelmappings
    
    animation_controller = AnimationController(
        led_controller,
        refresh_rate,
        led_count,
        pixelmappings.line(led_count),
        no_timer_reset=False,
        global_brightness_limit=config.get('brightness_limit', 1.0)
    )
    
    print(f"Configuration:")
    print(f"  LED count: {led_count}")
    print(f"  Frame rate: {refresh_rate} FPS")
    print(f"  Pixel order: {config.get('led_pixel_order', 'GRBW')}")
    
    # Load settings
    if 'settings' in config:
        animation_controller.update_settings(config['settings'])
    
    # Load custom functions
    if 'functions' in config:
        for k, v in config['functions'].items():
            if not v.get('default', True) and 'source' in v:
                try:
                    animation_controller.set_pattern_function(int(k), v['source'])
                except:
                    pass
    
    # Load palettes
    if 'palettes' in config:
        for k, v in config['palettes'].items():
            try:
                animation_controller.set_palette(int(k), v)
            except:
                pass
        animation_controller.calculate_palette_tables()
    
    print(f"  Profiling for {duration} seconds...\n")
    
    # Timing storage
    timings = defaultdict(list)
    
    # Patch render() to measure total LED update time
    original_render = led_controller.render
    
    def timed_render():
        t0 = time.perf_counter()
        result = original_render()
        t1 = time.perf_counter()
        timings['render'].append(t1 - t0)
        return result
    
    led_controller.render = timed_render
    
    # Also try to patch the underlying show() if using wrapper
    if hasattr(led_controller, '_leds') and hasattr(led_controller._leds, 'show'):
        original_show = led_controller._leds.show
        
        def timed_show():
            t0 = time.perf_counter()
            result = original_show()
            t1 = time.perf_counter()
            timings['spi_show'].append(t1 - t0)
            return result
        
        led_controller._leds.show = timed_show
    
    # Start animation thread
    animation_controller.begin_animation_thread()
    
    print("Animation running, collecting data...")
    
    # Let it run
    start_time = time.perf_counter()
    last_print = start_time
    
    while time.perf_counter() - start_time < duration:
        time.sleep(0.1)
        
        now = time.perf_counter()
        if now - last_print >= 1.0:
            elapsed = now - start_time
            print(f"  {elapsed:.1f}/{duration}s...")
            last_print = now
    
    # Stop
    animation_controller.end_animation()
    
    total_duration = time.perf_counter() - start_time
    
    # Get actual frame rate
    try:
        actual_fps = animation_controller.get_frame_rate()
    except:
        actual_fps = len(timings.get('render', [])) / total_duration if total_duration > 0 else 0
    
    # Results
    print("\n" + "="*80)
    print("PROFILING RESULTS")
    print("="*80 + "\n")
    
    print(f"Duration: {total_duration:.3f}s")
    print(f"Frames: {len(timings.get('render', []))}")
    print(f"Actual FPS: {actual_fps:.1f}")
    print(f"Target FPS: {refresh_rate}\n")
    
    if not timings.get('render'):
        print("ERROR: No data collected")
        return
    
    # Calculate statistics
    target_frame_time = 1000.0 / refresh_rate  # ms
    
    render_times = np.array(timings['render']) * 1000  # ms
    render_avg = np.mean(render_times)
    render_min = np.min(render_times)
    render_max = np.max(render_times)
    
    print("-" * 80)
    print(f"{'Metric':<45} {'Value (ms)':<15}")
    print("-" * 80)
    print(f"{'Target frame time @ ' + str(refresh_rate) + ' FPS':<45} {target_frame_time:>12.3f}")
    print(f"{'LED render() - Average':<45} {render_avg:>12.3f}")
    print(f"{'LED render() - Min':<45} {render_min:>12.3f}")
    print(f"{'LED render() - Max':<45} {render_max:>12.3f}")
    
    # If we measured SPI show separately
    if timings.get('spi_show'):
        spi_times = np.array(timings['spi_show']) * 1000
        spi_avg = np.mean(spi_times)
        spi_min = np.min(spi_times)
        spi_max = np.max(spi_times)
        
        print(f"{'  └─ SPI show() - Average':<45} {spi_avg:>12.3f}")
        print(f"{'  └─ SPI show() - Min':<45} {spi_min:>12.3f}")
        print(f"{'  └─ SPI show() - Max':<45} {spi_max:>12.3f}")
        
        render_overhead = render_avg - spi_avg
        print(f"{'  └─ Render overhead (not in SPI)':<45} {render_overhead:>12.3f}")
    
    frame_budget_remaining = target_frame_time - render_avg
    if frame_budget_remaining > 0:
        print(f"{'Frame budget remaining for Python':<45} {frame_budget_remaining:>12.3f}")
    else:
        print(f"{'OVERRUN - Render exceeds frame budget by':<45} {abs(frame_budget_remaining):>12.3f}")
    
    print("-" * 80)
    
    # Analysis
    print("\n" + "="*80)
    print("BOTTLENECK ANALYSIS")
    print("="*80 + "\n")
    
    render_pct = (render_avg / target_frame_time) * 100
    
    print(f"LED render() takes {render_avg:.3f}ms ({render_pct:.1f}% of frame budget)")
    
    if timings.get('spi_show'):
        spi_pct = (spi_avg / target_frame_time) * 100
        render_overhead_pct = ((render_avg - spi_avg) / target_frame_time) * 100
        
        print(f"  - SPI transfer: {spi_avg:.3f}ms ({spi_pct:.1f}% of frame budget)")
        print(f"  - Render overhead: {render_overhead:.3f}ms ({render_overhead_pct:.1f}% of frame budget)")
    
    print()
    
    if render_pct > 80:
        print("⚠️  CRITICAL: LED render() consumes >80% of frame budget!")
        
        if timings.get('spi_show'):
            spi_pct_of_render = (spi_avg / render_avg) * 100
            
            if spi_pct_of_render > 70:
                print("\n→ PRIMARY BOTTLENECK: SPI Hardware Transfer")
                print("  The hardware SPI transfer itself is the limiting factor.")
                print("\n  Hardware-limited. Solutions:")
                print(f"    • Reduce FPS (currently {refresh_rate})")
                print(f"    • Reduce LED count (currently {led_count})")
                print("    • Pi5 SPI is already optimized, little room for improvement")
            else:
                print("\n→ PRIMARY BOTTLENECK: Render Overhead")
                print("  Significant time spent in render logic (not SPI).")
                print("\n  Solutions:")
                print("    • The NumPy optimization helped, but overhead remains")
                print("    • Consider Cython for render functions")
                print("    • Batch operations are already implemented")
        else:
            print("\n→ LED render() is the bottleneck")
            print("  Could not measure SPI separately to determine root cause.")
            
    elif frame_budget_remaining < 0:
        print("⚠️  WARNING: Render exceeds frame budget!")
        print("\n  Solutions:")
        print(f"    • Reduce target FPS from {refresh_rate}")
        print(f"    • Reduce LED count from {led_count}")
    else:
        print("✅ LED render() performance looks reasonable")
        print(f"\n  {frame_budget_remaining:.3f}ms ({(frame_budget_remaining/target_frame_time)*100:.1f}%) remaining")
        print("  for animation calculations and Python overhead.")
        
        if actual_fps < refresh_rate * 0.9:
            print("\n  ⚠️  Note: Actual FPS is below target!")
            print("  This suggests the animation thread scheduling or update_leds()")
            print("  calculations are consuming the remaining time budget.")


if __name__ == '__main__':
    duration = 10
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            pass
    
    profile(duration)
