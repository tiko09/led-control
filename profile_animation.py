#!/usr/bin/env python3
"""
Profiling script to identify performance bottlenecks in LED animations.
Run this on the Pi5 with an active animation to see where CPU time is spent.
"""

import cProfile
import pstats
import io
import time
import sys
import json
from pathlib import Path

# Add ledcontrol to path
sys.path.insert(0, str(Path(__file__).parent))

from ledcontrol.ledcontroller import LEDController
from ledcontrol.animationcontroller import AnimationController


def profile_animation(duration=10):
    """Profile an animation for the specified duration in seconds."""
    
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
    led_count = config.get('led_count', 144)
    led_pin = config.get('led_pin', 18)
    led_data_rate = config.get('led_data_rate', 800000)
    led_dma_channel = config.get('led_dma_channel', 10)
    led_pixel_order = config.get('led_pixel_order', 'GRBW')
    
    if led_count == 0:
        print("WARNING: led_count not configured, using default of 144")
        led_count = 144
    
    # Initialize controllers
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
    
    # Get current animation config
    current_animation = animation_controller._settings.get('current_animation', {})
    if not current_animation:
        print("ERROR: No animation configured")
        return
    
    print(f"Profiling animation: {current_animation.get('type', 'Unknown')}")
    print(f"LED count: {config['led_count']}")
    print(f"Frame rate: {config.get('frame_rate', 30)} FPS")
    print(f"Duration: {duration} seconds\n")
    
    # Create profiler
    profiler = cProfile.Profile()
    
    # Start animation
    animation_controller.start()
    
    # Profile for specified duration
    print("Starting profiling...")
    profiler.enable()
    time.sleep(duration)
    profiler.disable()
    
    # Stop animation
    animation_controller.stop()
    
    # Print results
    print("\n" + "="*80)
    print("PROFILING RESULTS")
    print("="*80 + "\n")
    
    # Sort by cumulative time
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats('cumulative')
    
    print("Top 30 functions by CUMULATIVE time:")
    print("-" * 80)
    ps.print_stats(30)
    print(s.getvalue())
    
    # Sort by total time
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats('tottime')
    
    print("\n" + "="*80)
    print("Top 30 functions by TOTAL time (excluding subcalls):")
    print("-" * 80)
    ps.print_stats(30)
    print(s.getvalue())
    
    # Calculate actual frame rate
    total_calls = ps.total_calls
    actual_fps = total_calls / duration if duration > 0 else 0
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total function calls: {total_calls}")
    print(f"Duration: {duration} seconds")
    print(f"Estimated frames rendered: ~{int(actual_fps * duration / 10)}")  # Rough estimate
    
    # Save detailed results to file
    output_file = Path(__file__).parent / 'profile_results.txt'
    with open(output_file, 'w') as f:
        ps = pstats.Stats(profiler, stream=f)
        ps.strip_dirs()
        ps.sort_stats('cumulative')
        f.write("="*80 + "\n")
        f.write("PROFILING RESULTS - SORTED BY CUMULATIVE TIME\n")
        f.write("="*80 + "\n\n")
        ps.print_stats(50)
        
        ps.sort_stats('tottime')
        f.write("\n" + "="*80 + "\n")
        f.write("PROFILING RESULTS - SORTED BY TOTAL TIME\n")
        f.write("="*80 + "\n\n")
        ps.print_stats(50)
    
    print(f"\nDetailed results saved to: {output_file}")


if __name__ == '__main__':
    duration = 10
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print(f"Invalid duration: {sys.argv[1]}, using default of 10 seconds")
    
    profile_animation(duration)
