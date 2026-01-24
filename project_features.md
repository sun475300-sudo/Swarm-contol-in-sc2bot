# Wicked Zerg Challenger - Implemented Features

This document provides a comprehensive list of features currently implemented in the **Wicked Zerg Challenger** project, based on code analysis.

## 1. Strategy & Decision Making (`strategy_manager.py`, `rogue_tactics_manager.py`)
- **Race-Specific Strategies**: Tailored unit compositions for Terran (Bio/Mech), Protoss (Stargate/Robo), and Zerg.
- **Emergency Mode**: Automatically triggers defensively upon detecting early aggression (Rush/Cheese).
    - Stops drone production.
    - Prioritizes defensive structures (Spine Crawlers) and units (Zerglings, Queens).
- **Rogue Tactics (Pro-Gamer Emulation)**:
    - **Baneling Drops**: Overlord transport drops on enemy mineral lines.
    - **Stealth Movement**: Calculates paths along map edges to avoid detection.
    - **Larva Saving**: Hoards larva before attacks to allow for explosive reinforcement.
- **Game Phase Tracking**: Adjusts tactics based on Early (<4m), Mid (4-10m), and Late (>10m) game stages.

## 2. Combat & Micro (`combat_manager.py`, `micro_controller.py`)
- **Multitasking System**: Handles multiple simultaneous priorities:
    1.  **Base Defense**: Highest priority, pulls nearby units to defend.
    2.  **Worker Defense**: Protects drones from harassment.
    3.  **Counter Attacks**: Launches attacks when enemy fails a push.
    4.  **Air Harassment**: Uses Mutalisks to harass worker lines.
- **Advanced Micro**:
    - **Kiting/Stutter Stepping**: Ranged units attack and move to maintain distance.
    - **Concave Formation**: Pre-positions units in a concave arc before engaging.
    - **Targeting System**: Prioritizes high-threat units (Tanks, Colossi) and workers.
- **Victory Push**: Automatically attacks enemy structures when victory is calculated as probable.

## 3. Economy & Production (`economy_manager.py`, `production_resilience.py`)
- **Proactive Expansion**: Aims for specific base counts by game time (e.g., 3rd base at 4:00).
- **Macro Hatchery Logic**: Builds extra hatcheries if minerals float (>800) or larva is low.
- **Worker Optimization**:
    - **Early Split**: Optimally distributes initial 12 drones to mineral patches.
    - **Gas/Mineral Balancing**: Dynamically reassigns workers based on saturation.
    - **Long-Distance Mining**: Transfers workers from depleted bases to fresh ones.
- **Production Resilience**:
    - **Safe Training**: Retries unit production if it fails (e.g., due to larva reuse).
    - **Resource Flushing**: Rapidly spends excess resources on Zerglings/Overlords to avoid floating.

## 4. Intelligence & Scouting (`intel_manager.py`, `scouting_system.py`)
- **Build Pattern Recognition**: Identifies enemy strategies (e.g., "Terran Bio", "Protoss Stargate") and recommends counters.
- **Threat Detection**:
    - **Air Threat**: Detects air units and triggers Spore Crawler construction.
    - **Rush Detection**: Identifies early attacks based on unit proximity and timing.
- **Overlord Network**: Positions Overlords at key map points (perimeters, high ground) for vision.
- **Map Awareness**: Tracks enemy expansion locations and army movements.

## 5. Upgrades & Tech (`upgrade_manager.py`)
- **Dynamic Upgrade Path**: Prioritizes upgrades based on current unit composition (Melee vs Ranged).
- **Tech Progression**: Automates Lair -> Hive progression based on time and resource benchmarks.
- **Critical Upgrade Rush**: Prioritizes "Zergling Speed" and "Overlord Speed" above all else.

## 6. Infrastructure & Quality (`utils/logger.py`)
- **Centralized Logging**: Standardized logging system for debugging and behavior tracking.
- **Crash Resilience**: Critical managers (Production, Economy) have fallback logic to prevent bot crashes from minor errors.
