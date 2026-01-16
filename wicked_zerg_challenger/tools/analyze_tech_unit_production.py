#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze why high tech units are not being produced"""

import sys

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

def analyze_tech_unit_issues():
    """Analyze potential issues with tech unit production"""

    print("=" * 70)
    print("High Tech Unit Production Analysis")
    print("=" * 70)

    print("\n[1] Tech Building Construction Requirements")
    print("-" * 70)
    print("Roach Warren:")
    print("  - Requirements: Spawning Pool (optional), game time > 180s")
    print("  - Cost: 150 minerals, 0 gas")
    print("  - Location: production_resilience.py (Line 526, 552, 565)")

    print("\nHydralisk Den:")
    print("  - Requirements: Lair or Hive (MANDATORY!), game time > 240s")
    print("  - Cost: 100 minerals, 100 gas")
    print("  - Location: production_resilience.py (Line 541, 578)")
    print("  - WARNING: Without Lair, Hydralisk Den cannot produce Hydralisks!")

    print("\nLair:")
    print("  - Requirements: Spawning Pool ready, Hatchery ready, game time > 120s")
    print("  - Cost: 150 minerals, 100 gas")
    print("  - Location: production_manager.py (Line 2850-2880)")
    print("  - WARNING: Gas income check required (extractor + vespene >= 50)")

    print("\n[2] Tech Unit Production Conditions")
    print("-" * 70)
    print("Roach Production:")
    print("  - Requirements: Roach Warren ready, can_afford(ROACH), supply_left >= 2")
    print("  - Cost: 75 minerals, 25 gas")
    print("  - Location: production_manager.py (Line 2997-3006)")

    print("\nHydralisk Production:")
    print("  - Requirements: Hydralisk Den ready + Lair exists, can_afford(HYDRALISK), supply_left >= 2")
    print("  - Cost: 100 minerals, 50 gas")
    print("  - Location: production_manager.py (Line 2986-2995)")
    print("  - WARNING: Without Lair, Hydralisk Den cannot produce Hydralisks!")

    print("\n[3] Potential Issues")
    print("-" * 70)
    print("1. Lair Upgrade Failure:")
    print("   - Gas shortage (100 gas required)")
    print("   - Extractor not built or no workers assigned")
    print("   - Spawning Pool not completed")
    print("   - Hatchery might be morphing")

    print("\n2. Emergency Flush Logic Only Produces Zerglings:")
    print("   - production_resilience.py (Line 60-108): Forces Zergling production when minerals > 500")
    print("   - production_manager.py (Line 1443-1502): _flush_resources() prioritizes Zerglings")
    print("   - PROBLEM: Tech unit production opportunities may be blocked by Zergling production")

    print("\n3. Resource Shortage:")
    print("   - Hydralisk: 100M + 50G required")
    print("   - Roach: 75M + 25G required")
    print("   - Insufficient gas income prevents tech unit production")

    print("\n4. Supply Shortage:")
    print("   - supply_left < 2 prevents tech unit production")
    print("   - Overlord production delay causes supply block")

    print("\n5. Tech Building Construction Order Issue:")
    print("   - Hydralisk Den built without Lair")
    print("   - Hydralisk Den exists but cannot produce without Lair")

    print("\n6. Production Priority Issue:")
    print("   - Zergling production may have higher priority than tech units")
    print("   - production_manager.py (Line 3014-3016): Zergling production before tech units")

    print("\n[4] Solutions")
    print("-" * 70)
    print("1. Strengthen Lair Upgrade:")
    print("   - Improve gas income check logic")
    print("   - Increase Extractor construction priority")
    print("   - Add retry logic for failed Lair upgrades")

    print("\n2. Improve Emergency Flush Logic:")
    print("   - Produce tech units when tech buildings are ready")
    print("   - Include Roach/Hydralisk in addition to Zerglings")

    print("\n3. Improve Tech Building Construction Order:")
    print("   - Verify Lair construction first")
    print("   - Strengthen Lair existence check before Hydralisk Den construction")

    print("\n4. Adjust Production Priority:")
    print("   - Prioritize tech unit production when tech buildings are ready")
    print("   - Increase tech unit production priority over Zerglings")

    print("\n" + "=" * 70)
    print("Analysis Complete")
    print("=" * 70)

if __name__ == "__main__":
 analyze_tech_unit_issues()
