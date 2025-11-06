#!/usr/bin/env python3
"""
Simple profiling script - starts animation thread and measures performance.
This is the correct way to profile since it matches production behavior.
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


def profile_animation(duration=10):
    """Profile animation for the specified duration in seconds."""
    
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
    led_pin = config.get('led_pin', 18)
    led_data_rate = config.get('led_data_rate', 800000)
    led_dma_channel = config.get('led_dma_channel', 10)
    led_pixel_order = config.get('led_pixel_order', 'GRBW')
    
    if led_count == 0:
        led_count = 144
    
    led_controller = LEDController(
        led_count=led_count,
        led_pin=led_pin,
        led_data_rate=led_data_rate,
        led_dma_channel=led_dma_channel,
        led_pixel_order=led_pixel_order
    )
    
    # Animation controller parameters
    refresh_rate = config.get('frame_rate', 60)
    global_brightness_limit = config.get('brightness_limit', 1.0)
    
    import ledcontrol.pixelmappings as pixelmappings
    mapping_func = pixelmappings.line(led_count)
    
    animation_controller = AnimationController(
        led_controller,
        refresh_rate,
        led_count,
        mapping_func,
        no_timer_reset=False,
        global_brightness_limit=global_brightness_limit
    )
    
    print(f"Configuration:")
    print(f"  LED count: {led_count}")
    print(f"  Frame rate: {refresh_rate} FPS")
    print(f"  Pixel order: {led_pixel_order}")
    
    # Load settings from config
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
    
    # Patch show() to measure SPI transfer time
    original_show = led_controller.show
    
    def timed_show(*args, **kwargs):
        t0 = time.perf_counter()
        result = original_show(*args, **kwargs)
        t1 = time.perf_counter()
        timings['show'].append(t1 - t0)
        return result
    
    led_controller.show = timed_show
    
    # Start animation thread (like production does)
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
    
    # Get frame rate
    try:
        actual_fps = animation_controller.get_frame_rate()
    except:
        actual_fps = len(timings.get('show', [])) / total_duration if total_duration > 0 else 0
    
    # Results
    print("\n" + "="*80)
    print("PROFILING RESULTS")
    print("="*80 + "\n")
    
    print(f"Duration: {total_duration:.3f}s")
    print(f"Frames: {len(timings.get('show', []))}")
    print(f"Actual FPS: {actual_fps:.1f}")
    print(f"Target FPS: {refresh_rate}\n")
    
    if not timings.get('show'):
        print("ERROR: No data collected")
        return
    
    # Statistics
    show_times = np.array(timings['show']) * 1000  # ms
    show_avg = np.mean(show_times)
    show_min = np.min(show_times)
    show_max = np.max(show_times)
    
    target_frame_time = 1000.0 / refresh_rate
    
    print("-" * 80)
    print(f"{'Metric':<40} {'Value (ms)':<15}")
    print("-" * 80)
    print(f"{'Target frame time @ ' + str(refresh_rate) + ' FPS':<40} {target_frame_time:>12.3f}")
    print(f"{'Actual SPI transfer (show) - Avg':<40} {show_avg:>12.3f}")
    print(f"{'Actual SPI transfer (show) - Min':<40} {show_min:>12.3f}")
    print(f"{'Actual SPI transfer (show) - Max':<40} {show_max:>12.3f}")
    
    overhead = target_frame_time - show_avg
    if overhead > 0:
        print(f"{'Estimated Python overhead':<40} {overhead:>12.3f}")
    else:
        print(f"{'OVERRUN - SPI alone exceeds frame time!':<40} {abs(overhead):>12.3f}")
    
    print("-" * 80)
    
    # Analysis
    print("\n" + "="*80)
    print("BOTTLENECK ANALYSIS")
    print("="*80 + "\n")
    
    spi_pct = (show_avg / target_frame_time) * 100
    
    print(f"SPI transfer takes {show_avg:.3f}ms ({spi_pct:.1f}% of target frame time)")
    
    if spi_pct > 80:
        print("\n⚠️  PRIMARY BOTTLENECK: SPI Hardware")
        print("The SPI transfer itself consumes most of the frame budget.")
        print("\nThis is hardware-limited. Solutions:")
        print(f"  - Reduce FPS (currently {refresh_rate})")
        print(f"  - Reduce LED count (currently {led_count})")
    elif overhead > 0 and overhead / target_frame_time > 0.3:
        print("\n⚠️  PRIMARY BOTTLENECK: Python Overhead")
        print("Significant time spent in Python code.")
        print("\nSolutions:")
        print("  - Optimize render functions further")
        print("  - Consider Cython/C extensions")
    else:
        if show_avg > target_frame_time:
            print("\n⚠️  CRITICAL: Frame time exceeded!")
            print("SPI alone takes longer than target frame time.")
            print("Reduce FPS or LED count.")
        else:
            print("\n✅ Performance looks reasonable")
            print("If CPU is still high, check animation thread scheduling.")


if __name__ == '__main__':
    duration = 10
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            pass
    
    profile_animation(duration)
