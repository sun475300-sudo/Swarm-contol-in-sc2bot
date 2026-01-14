#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test replay extraction to debug build order extraction"""

import sc2reader
from pathlib import Path

replay_path = list(Path("D:/replays/replays").glob("*.SC2Replay"))[0]
print(f"Testing replay: {replay_path.name}")

replay = sc2reader.load_replay(str(replay_path), load_map=True)

# Find Zerg player
zerg_player = None
for player in replay.players:
    if hasattr(player, 'play_race') and str(player.play_race).lower() == 'zerg':
        zerg_player = player
        print(f"Found Zerg player: {zerg_player.name}")
        break

if not zerg_player:
    print("No Zerg player found!")
    exit(1)

# Check UnitBornEvent
unit_to_parameter = {
    "Hatchery": "natural_expansion_supply",
    "Extractor": "gas_supply",
    "SpawningPool": "spawning_pool_supply",
    "RoachWarren": "roach_warren_supply",
    "HydraliskDen": "hydralisk_den_supply",
    "Lair": "lair_supply",
    "Hive": "hive_supply",
}

# Get player IDs
zerg_pid = zerg_player.pid if hasattr(zerg_player, 'pid') else None
print(f"Zerg player PID: {zerg_pid}")

found_units = []
unit_born_count = 0
all_zerg_buildings = {}  # Track all Zerg buildings found
for event in replay.events:
    if hasattr(event, '__class__') and 'UnitBorn' in str(event.__class__):
        unit_born_count += 1
        
        # Check if this unit belongs to Zerg player
        is_zerg_unit = False
        if hasattr(event, 'control_pid'):
            is_zerg_unit = event.control_pid == zerg_pid
        elif hasattr(event, 'unit_controller'):
            # Try to match by controller
            pass
        
        if is_zerg_unit:
            unit_name = None
            if hasattr(event, 'unit') and hasattr(event.unit, 'name'):
                unit_name = event.unit.name
                # Track all buildings (check if it's a building)
                if hasattr(event.unit, 'is_building') and event.unit.is_building:
                    all_zerg_buildings[unit_name] = all_zerg_buildings.get(unit_name, 0) + 1
        
        if unit_born_count <= 10 and is_zerg_unit:  # Debug first 10 Zerg units
            print(f"\nUnitBornEvent #{unit_born_count} (Zerg):")
            if hasattr(event, 'unit') and hasattr(event.unit, 'name'):
                print(f"  Unit name: {event.unit.name}")
                if hasattr(event.unit, 'is_building'):
                    print(f"  Is building: {event.unit.is_building}")
            if hasattr(event, 'second'):
                print(f"  Time: {event.second}s")
        
        if is_zerg_unit:
            unit_name = None
            if hasattr(event, 'unit'):
                unit = event.unit
                if hasattr(unit, 'name'):
                    unit_name = unit.name
                elif hasattr(unit, 'unit_type'):
                    unit_name = str(unit.unit_type)
            elif hasattr(event, 'unit_type_name'):
                unit_name = event.unit_type_name
            elif hasattr(event, 'unit_type'):
                unit_name = str(event.unit_type)
            
            if unit_name:
                time = getattr(event, 'second', getattr(event, 'frame', 0) / 16.0)
                if unit_name in unit_to_parameter:
                    found_units.append((unit_name, time, unit_to_parameter[unit_name]))
                    print(f"  ? Found {unit_name} at {time}s -> {unit_to_parameter[unit_name]}")
                elif unit_born_count <= 10:
                    print(f"  - {unit_name} (not in mapping)")

print(f"\nTotal UnitBornEvents: {unit_born_count}")
print(f"Total found in mapping: {len(found_units)}")
for unit_name, time, param in found_units[:10]:
    print(f"  {param}: {unit_name} at {time:.1f}s")

print(f"\n=== All Zerg Buildings Found ===")
for building_name, count in sorted(all_zerg_buildings.items()):
    print(f"  {building_name}: {count} times")

print(f"\n=== Checking for Extractor variants ===")
extractor_variants = []
for event in replay.events:
    if hasattr(event, '__class__') and 'UnitBorn' in str(event.__class__):
        if hasattr(event, 'control_pid') and event.control_pid == zerg_pid:
            if hasattr(event, 'unit') and hasattr(event.unit, 'name'):
                unit_name = event.unit.name
                # Check for any gas-related buildings
                if 'extractor' in unit_name.lower() or 'gas' in unit_name.lower() or 'vespene' in unit_name.lower():
                    if hasattr(event, 'second'):
                        extractor_variants.append((unit_name, event.second))
                    elif hasattr(event, 'frame'):
                        extractor_variants.append((unit_name, event.frame / 16.0))

if extractor_variants:
    print(f"Found {len(extractor_variants)} gas-related buildings:")
    for unit_name, time in extractor_variants[:10]:
        print(f"  {unit_name} at {time:.1f}s")
else:
    print("No gas-related buildings found in UnitBornEvents")
