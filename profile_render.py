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
    
    led_controller = LEDController(config)
    animation_controller = AnimationController(led_controller, config)
    
    print(f"Configuration:")
    print(f"  LED count: {config['led_count']}")
    print(f"  Frame rate: {config.get('frame_rate', 30)} FPS")
    print(f"  Animation: {config.get('current_animation', {}).get('type', 'Unknown')}")
    print(f"  Profiling {num_frames} frames...\n")
    
    # Timing storage
    timings = defaultdict(list)
    
    # Monkey-patch render functions to add timing
    original_render_frame = animation_controller.render_frame
    
    def timed_render_frame():
        t0 = time.perf_counter()
        result = original_render_frame()
        t1 = time.perf_counter()
        timings['render_frame'].append(t1 - t0)
        return result
    
    animation_controller.render_frame = timed_render_frame
    
    # Also patch the LED controller's render function
    if hasattr(led_controller, 'render_hsv'):
        original_render_hsv = led_controller.render_hsv
        
        def timed_render_hsv(*args, **kwargs):
            t0 = time.perf_counter()
            result = original_render_hsv(*args, **kwargs)
            t1 = time.perf_counter()
            timings['render_hsv'].append(t1 - t0)
            return result
        
        led_controller.render_hsv = timed_render_hsv
    
    if hasattr(led_controller, 'render_rgb'):
        original_render_rgb = led_controller.render_rgb
        
        def timed_render_rgb(*args, **kwargs):
            t0 = time.perf_counter()
            result = original_render_rgb(*args, **kwargs)
            t1 = time.perf_counter()
            timings['render_rgb'].append(t1 - t0)
            return result
        
        led_controller.render_rgb = timed_render_rgb
    
    if hasattr(led_controller, 'show'):
        original_show = led_controller.show
        
        def timed_show(*args, **kwargs):
            t0 = time.perf_counter()
            result = original_show(*args, **kwargs)
            t1 = time.perf_counter()
            timings['show'].append(t1 - t0)
            return result
        
        led_controller.show = timed_show
    
    # Run frames manually
    start_time = time.perf_counter()
    
    for i in range(num_frames):
        frame_start = time.perf_counter()
        
        animation_controller.render_frame()
        
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
    
    for key in ['total_frame', 'render_frame', 'render_hsv', 'render_rgb', 'show']:
        if key in timings and timings[key]:
            values = np.array(timings[key]) * 1000  # Convert to ms
            avg = np.mean(values)
            min_val = np.min(values)
            max_val = np.max(values)
            total_time = np.sum(values) / 1000  # Back to seconds
            percentage = (total_time / total_duration) * 100
            
            print(f"{key:<30} {avg:>10.3f}  {min_val:>10.3f}  {max_val:>10.3f}  {percentage:>8.1f}%")
    
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
    
    max_time = 0
    bottleneck = None
    
    for key in ['render_hsv', 'render_rgb', 'show']:
        if key in timings and timings[key]:
            avg_time = np.mean(timings[key]) * 1000
            if avg_time > max_time:
                max_time = avg_time
                bottleneck = key
    
    if bottleneck:
        print(f"Primary bottleneck: {bottleneck} ({max_time:.3f} ms per frame)")
        
        if bottleneck == 'show':
            print("\nThe 'show()' function (SPI transfer) is the bottleneck.")
            print("This is hardware-limited and cannot be optimized further in Python.")
            print("Possible solutions:")
            print("  - Reduce frame rate")
            print("  - Reduce LED count")
            print("  - Use hardware DMA (requires C implementation)")
        
        elif bottleneck in ['render_hsv', 'render_rgb']:
            print(f"\nThe '{bottleneck}' function is the bottleneck.")
            print("Despite NumPy vectorization, Python overhead is still significant.")
            print("Possible solutions:")
            print("  - Implement render function in Cython (50-100x faster)")
            print("  - Implement render function in C (maximum speed)")
            print("  - Use PyPy JIT compiler")


if __name__ == '__main__':
    num_frames = 300
    if len(sys.argv) > 1:
        try:
            num_frames = int(sys.argv[1])
        except ValueError:
            print(f"Invalid frame count: {sys.argv[1]}, using default of 300")
    
    profile_render_loop(num_frames)
