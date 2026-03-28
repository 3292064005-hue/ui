#!/usr/bin/env python3
"""
Simple test script for adaptive timer CPU monitoring
"""

import time
import psutil

def get_cpu_usage():
    """Simple CPU usage estimation"""
    return psutil.cpu_percent(interval=0.1)

def test_adaptive_timer():
    """Test adaptive timer logic"""
    min_period = 0.5
    max_period = 2.0
    target_cpu = 70.0
    current_period = 1.0

    print("Testing adaptive timer...")
    print(f"Initial period: {current_period}ms")

    # Simulate high CPU
    print("Simulating high CPU usage...")
    cpu_usage = 85.0
    if cpu_usage > target_cpu + 10.0:
        current_period = min(current_period * 1.1, max_period)
    print(f"After high CPU: {current_period}ms")

    # Simulate low CPU
    print("Simulating low CPU usage...")
    cpu_usage = 50.0
    if cpu_usage < target_cpu - 10.0:
        current_period = max(current_period * 0.9, min_period)
    print(f"After low CPU: {current_period}ms")

    print("Adaptive timer test completed successfully!")

if __name__ == "__main__":
    test_adaptive_timer()