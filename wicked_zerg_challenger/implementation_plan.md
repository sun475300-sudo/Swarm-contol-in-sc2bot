# Defense Logic Consolidation Plan

## Goal
Consolidate dispersed defense logic from `StrategyManager` (Emergency Mode), `EarlyDefenseSystem` (in `production_resilience.py`), `MultiBaseDefense`, and `DefeatDetection` into a single, authoritative `DefenseCoordinator`.

## Problem
Currently, multiple systems independently decide if the bot needs to defend.
- `StrategyManager` triggers Emergency Mode based on `rush_detection`.
- `ProductionResilience` triggers "Emergency Spawning Pool" independently.
- `DefeatDetection` triggers "Last Stand".
This leads to race conditions (two systems ordering units) and conflicting priorities (one building drones, another building lings).

## Proposed Changes

### 1. New Component: `DefenseCoordinator`
Create `local_training/defense_coordinator.py`.
- **Responsibilities**:
    - Centralized Threat Assessment (Rush vs. Harass vs. Doom Drop).
    - Emergency Production Authorization (tells `ProductionResilience` what to build).
    - Unit Rally Point Management (tells `CombatManager` where to go).

### 2. Integration
- **Modify `BotStepIntegrator`**:
    - Initialize `DefenseCoordinator` early.
    - Remove direct calls to `EarlyDefenseSystem` and `MultiBaseDefense`.
    - Pass `DefenseCoordinator` instructions to `ProductionManager` and `StrategyManager`.
- **Refactor `ProductionResilience`**:
    - Remove `_ensure_early_defense`.
    - Add `request_emergency_units(unit_type, count)` method called by `DefenseCoordinator`.

## Verification Plan

### Manual Verification
1.  **Simulate Rush**: Hardcode `defense_coordinator.is_under_attack = True` in `on_step`.
2.  **Observe Logs**: Verify `[DEFENSE_COORDINATOR]` logs appear and `ProductionResilience` logs "Emergency Production requested by Coordinator".
3.  **Check Conflicts**: Ensure `StrategyManager` doesn't override Coordinator's orders.

## Phase 2: Commander Learning System (Centralized Brain)
- **Goal**: "Teach" the bot by externalizing logic, builds, and timings into a data-driven "Brain" (`commander_knowledge.json`).
- **Steps**:
    1. **Design Knowledge Schema**: Define JSON structure for Build Orders, Unit Ratios, and Timing benchmarks.
    2. **Create `KnowledgeManager`**: A component to load, validate, and serve this knowledge to other systems.
    3. **Data Migration**: Move hardcoded builds (e.g., `_get_roach_rush_build`) from `BuildOrderSystem` into the JSON file.
    4. **Refactor Execution**: Update `BuildOrderSystem` and `StrategyManager` to query `KnowledgeManager` instead of using hardcoded values.
    5. **Verification**: Verify the bot executes a build order loaded purely from JSON.

## Phase 3: Centralize State (Blackboard)
- **Goal**: Allow all components to share real-time game state efficiently.
- **Steps**:
    1. Create `Blackboard` class.
    2. Refactor `BotStepIntegrator` to update Blackboard.
    3. Update managers to read from Blackboard.
    - `IntelManager` writes `enemy_locations`.
    - `DefenseCoordinator` writes `defense_status`.
    - `EconomyManager` writes `resource_surplus`.
    - All other managers read from this single source of truth.

## Phase 3: Logic Refinement (Strategy & Economy) [CURRENT FOCUS]
- **Goal**: optimize core game logic to increase win rate and resource efficiency.
- **Priority Components**:
    1.  **Dynamic Counter System (`StrategyManager`)**:
        -   **Current**: Hardcoded composition ratios.
        -   **New**: Override compositions based on `IntelManager` recommendations (e.g., Force Corruptors vs BCs).
    2.  **Smart Resource Balancer (`EconomyManager`)**:
        -   **Current**: Static saturation logic.
        -   **New**: Real-time Mineral:Gas ratio balancing (3:1 target). Dynamic gas pull-off.
    3.  **Optimum Defense Squad (`DefenseCoordinator`)**:
        -   **Current**: F2-All Army defense.
        -   **New**: Calculate threat supply -> Dispatch `Threat * 1.2` supply.
    4.  **Creep Highway (`CreepManager`)**:
        -   **Current**: Spread to enemy.
        -   **New**: Spread to connect bases first (Highway).
    5.  **SpellCaster Automation (`MicroController`)**:
        -   **Current**: No spells.
        -   **New**: Queen Transfuse, Viper Abduct/Cloud, Ravager Bile.

## Phase 4: Advanced Tactics (Pro-Level)
- **Goal**: Introduce tactical variety and unpredictability.
- **Features**:
    -   **Active Scouting**: Zergling run-by to scout tech/bases.
    -   **Rogue Tactics**: Combined Drop + Frontal Attack + Run-by.
    -   **Overlord Safety**: Flee from air threats to Spore Crawlers.
    -   **Nydus Network**: Late-game backdoor attacks.

## Phase 5: Superintelligence (Self-Learning)
-   **Real-time Opponent Modeling**: Learn enemy habits during the game.
-   **Runtime Self-Healing**: Auto-patching errors.

