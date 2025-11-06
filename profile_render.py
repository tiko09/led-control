#!/usr/bin/env python3
"""
Simple profiling script to measure individual function timings in render loop.
This manually times key operations to identify bottlenecks.
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


def profile_render_loop(num_frames=300):
    """Profile individual render operations."""
    
    # Load config - try different possible filenames
    config_path = None
    for filename in ['ledcontrol-dev.json', 'config.json', 'ledcontrol.json']:
        path = Path(__file__).parent / filename
        if path.exists():
            config_path = path
            break
    
    if not config_path:
        print("ERROR: No config file found (tried ledcontrol-dev.json, config.json, ledcontrol.json)")
        return
    
    print(f"Using config: {config_path.name}\n")
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Extract LED controller parameters with defaults matching __init__.py
    led_count = config.get('led_count', 144)  # Will be overridden by command line in production
    led_pin = config.get('led_pin', 18)
    led_data_rate = config.get('led_data_rate', 800000)
    led_dma_channel = config.get('led_dma_channel', 10)
    led_pixel_order = config.get('led_pixel_order', 'GRBW')
    
    # If config doesn't have these values, try to read from systemd service or use defaults
    # For profiling, we'll just use sensible defaults
    if led_count == 0:
        print("WARNING: led_count not configured, using default of 144")
        led_count = 144
    
    led_controller = LEDController(
        led_count=led_count,
        led_pin=led_pin,
        led_data_rate=led_data_rate,
        led_dma_channel=led_dma_channel,
        led_pixel_order=led_pixel_order
    )
    
    # For AnimationController, we need to extract the right parameters
    refresh_rate = config.get('frame_rate', 60)
    global_brightness_limit = config.get('brightness_limit', 1.0)
    
    # Import pixelmappings
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
    
    # Load controller settings from config
    if 'functions' in config:
        animation_controller._settings['functions'] = config['functions']
    if 'palettes' in config:
        animation_controller._settings['palettes'] = config['palettes']
    if 'current_animation' in config:
        animation_controller._settings['current_animation'] = config['current_animation']
    if 'global_brightness' in config:
        animation_controller._settings['global_brightness'] = config['global_brightness']
    if 'on' in config:
        animation_controller._settings['on'] = config['on']
    
    current_animation = animation_controller._settings.get('current_animation', {})
    if not current_animation:
        print("WARNING: No animation configured, using default")
    else:
        print(f"  Animation: {current_animation.get('type', 'Unknown')}")
    
    print(f"  Profiling {num_frames} frames...\n")
    
    # Timing storage
    timings = defaultdict(list)
    
    # We don't need to monkey-patch since we'll call update_leds directly
    # Just patch show() to measure SPI transfer time
    if hasattr(led_controller, 'show'):
        original_show = led_controller.show
        
        def timed_show(*args, **kwargs):
            t0 = time.perf_counter()
            result = original_show(*args, **kwargs)
            t1 = time.perf_counter()
            timings['show'].append(t1 - t0)
            return result
        
        led_controller.show = timed_show
    
    # Don't start the timer thread, we'll call update_leds manually
    # Just initialize the timer values
    animation_controller._start = time.perf_counter()
    animation_controller._time = 0
    
    # Run frames manually by calling update_leds
    start_time = time.perf_counter()
    
    for i in range(num_frames):
        frame_start = time.perf_counter()
        
        # Call update_leds directly (without timer thread)
        animation_controller.update_leds()
        
        frame_end = time.perf_counter()
        timings['total_frame'].append(frame_end - frame_start)
        
        if (i + 1) % 100 == 0:
            print(f"  Rendered {i + 1}/{num_frames} frames...")
    
    end_time = time.perf_counter()
    total_duration = end_time - start_time
    
    # Print results
    print("\n" + "="*80)
    print("TIMING RESULTS")
    print("="*80 + "\n")
    
    print(f"Total duration: {total_duration:.3f} seconds")
    print(f"Frames rendered: {num_frames}")
    print(f"Average FPS: {num_frames / total_duration:.1f}")
    print(f"Target FPS: {config.get('frame_rate', 30)}\n")
    
    print("-" * 80)
    print(f"{'Operation':<30} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Total %':<10}")
    print("-" * 80)
    
    for key in ['total_frame', 'show']:
        if key in timings and timings[key]:
            values = np.array(timings[key]) * 1000  # Convert to ms
            avg = np.mean(values)
            min_val = np.min(values)
            max_val = np.max(values)
            total_time = np.sum(values) / 1000  # Back to seconds
            percentage = (total_time / total_duration) * 100
            
            print(f"{key:<30} {avg:>10.3f}  {min_val:>10.3f}  {max_val:>10.3f}  {percentage:>8.1f}%")
    
    print("-" * 80)
    
    # Calculate time NOT in show() - this is the Python overhead
    if 'total_frame' in timings and 'show' in timings:
        total_frame_time = np.mean(timings['total_frame']) * 1000
        show_time = np.mean(timings['show']) * 1000
        overhead_time = total_frame_time - show_time
        overhead_pct = (overhead_time / total_frame_time) * 100
        
        print(f"{'Python overhead (not in show)':<30} {overhead_time:>10.3f}  {'':>10}  {'':>10}  {overhead_pct:>8.1f}%")
        print("-" * 80)
    
    # Calculate overhead
    if 'total_frame' in timings and timings['total_frame']:
        total_avg = np.mean(timings['total_frame']) * 1000
        accounted = 0
        
        for key in ['render_frame', 'render_hsv', 'render_rgb', 'show']:
            if key in timings and timings[key]:
                accounted += np.mean(timings[key]) * 1000
        
        overhead = total_avg - accounted
        print(f"\nUnaccounted overhead per frame: {overhead:.3f} ms")
        print(f"This includes: timer overhead, function calls, frame scheduling, etc.\n")
    
    # Identify bottleneck
    print("="*80)
    print("BOTTLENECK ANALYSIS")
    print("="*80 + "\n")
    
    if 'show' in timings and 'total_frame' in timings:
        show_time = np.mean(timings['show']) * 1000
        total_time = np.mean(timings['total_frame']) * 1000
        overhead_time = total_time - show_time
        
        show_pct = (show_time / total_time) * 100
        overhead_pct = (overhead_time / total_time) * 100
        
        print(f"Per-frame breakdown:")
        print(f"  Total frame time:    {total_time:.3f} ms (100%)")
        print(f"  SPI transfer (show): {show_time:.3f} ms ({show_pct:.1f}%)")
        print(f"  Python overhead:     {overhead_time:.3f} ms ({overhead_pct:.1f}%)")
        print()
        
        if show_pct > 60:
            print("PRIMARY BOTTLENECK: SPI transfer (show)")
            print("The hardware SPI transfer is taking most of the time.")
            print("This is hardware-limited and difficult to optimize further.")
            print("\nPossible solutions:")
            print("  - Reduce frame rate (current: {} FPS)".format(refresh_rate))
            print("  - Reduce LED count (current: {} LEDs)".format(led_count))
            print("  - The Pi5 SPI is already very fast, little room for improvement")
        elif overhead_pct > 60:
            print("PRIMARY BOTTLENECK: Python overhead")
            print("Most time is spent in Python code (animation calculations, rendering).")
            print("\nPossible solutions:")
            print("  - Implement hot paths in Cython (50-100x faster)")
            print("  - Implement render functions in C (maximum speed)")
            print("  - Use PyPy JIT compiler")
            print("  - Profile deeper with cProfile to find specific slow functions")
        else:
            print("BALANCED LOAD")
            print("Time is split between SPI transfer and Python overhead.")
            print("Both areas would benefit from optimization.")


if __name__ == '__main__':
    num_frames = 300
    if len(sys.argv) > 1:
        try:
            num_frames = int(sys.argv[1])
        except ValueError:
            print(f"Invalid frame count: {sys.argv[1]}, using default of 300")
    
    profile_render_loop(num_frames)
