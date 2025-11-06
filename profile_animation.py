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
    
    # Load config
    config_path = Path(__file__).parent / 'config.json'
    if not config_path.exists():
        print("ERROR: config.json not found")
        return
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Initialize controllers
    led_controller = LEDController(config)
    animation_controller = AnimationController(led_controller, config)
    
    # Get current animation config
    current_animation = config.get('current_animation', {})
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
