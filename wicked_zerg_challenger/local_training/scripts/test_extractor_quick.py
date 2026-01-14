#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test of ReplayBuildOrderExtractor"""

import sys
from pathlib import Path

# Add script directory to sys.path
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from replay_build_order_learner import ReplayBuildOrderExtractor

# Initialize extractor
extractor = ReplayBuildOrderExtractor()

# Get first replay
replays = extractor.scan_replays()
if not replays:
    print("[ERROR] No replays found!")
    sys.exit(1)

replay_path = replays[0]
print(f"Testing with: {replay_path.name}")

# Extract build order
build_order = extractor.extract_build_order(replay_path)

if build_order:
    print(f"\n[OK] Build order extracted successfully!")
    print(f"Player: {build_order.get('player_name', 'Unknown')}")
    print(f"Map: {build_order.get('map_name', 'Unknown')}")
    print(f"\nTimings found ({len(build_order.get('timings', {}))}):")
    for param_name, timing_data in build_order.get('timings', {}).items():
        supply = timing_data.get('supply', 0)
        time = timing_data.get('time', 0)
        print(f"  - {param_name}: supply={supply}, time={time:.1f}s")
    
    # Check specifically for Extractor
    if 'gas_supply' in build_order.get('timings', {}):
        print(f"\n[SUCCESS] Extractor (gas_supply) found!")
    else:
        print(f"\n[WARNING] Extractor (gas_supply) not found in timings")
else:
    print(f"\n[ERROR] Failed to extract build order")
