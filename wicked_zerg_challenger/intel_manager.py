#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intel Manager - lightweight information manager with update/on_step bridge.
"""

from __future__ import annotations

import asyncio
from typing import Optional


class IntelManager:
    """Collects intel and bridges update() to on_step()."""

    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0
        self.update_interval = 8
        self.enemy_race_name: Optional[str] = None

        # Enemy composition tracking
        self.enemy_army_supply = 0
        self.enemy_worker_count = 0
        self.enemy_base_count = 0
        self.enemy_tech_buildings = set()
        self.scouted_locations = set()

        # Threat tracking
        self._under_attack = False
        self._attack_position = None
        self._last_attack_time = 0.0
        self._threat_level = "none"  # none, light, medium, heavy, critical
        self._high_threat_units_detected = False

        # Enemy unit type counts
        self.enemy_unit_counts = {}

        # High threat unit types
        self._high_threat_types = {
            "SIEGETANK", "SIEGETANKSIEGED", "THOR", "BATTLECRUISER",
            "COLOSSUS", "DISRUPTOR", "IMMORTAL", "ARCHON",
            "ULTRALISK", "BROODLORD", "RAVAGER", "LURKER", "LURKERMP",
            "LIBERATOR", "LIBERATORAG", "WIDOWMINE", "HIGHTEMPLAR"
        }

        # ★ NEW: Destructible structures tracking
        self.destructible_rocks = []  # 파괴 가능한 중립 구조물
        self.all_enemy_structures = []  # 모든 적 구조물 (승리 조건용)
        self._last_structure_update = 0.0

    async def on_step(self, iteration: int) -> None:
        if iteration - self.last_update < self.update_interval:
            return
        self.last_update = iteration

        try:
            result = self.update(iteration)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            return

    def update(self, iteration: int) -> None:
        # Update enemy race
        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race is None:
            self.enemy_race_name = None
        elif hasattr(enemy_race, "name"):
            self.enemy_race_name = str(enemy_race.name)
        else:
            self.enemy_race_name = str(enemy_race)

        # Update enemy unit composition
        self._update_enemy_composition()

        # Update threat status
        self._update_threat_status()

        # ★ NEW: Update destructible structures
        self._update_destructible_structures()

        # ★ NEW: Update all enemy structures
        self._update_all_enemy_structures()

    def _update_enemy_composition(self) -> None:
        """Track enemy army composition."""
        enemy_units = getattr(self.bot, "enemy_units", [])
        enemy_structures = getattr(self.bot, "enemy_structures", [])

        # Count enemy units by type
        self.enemy_unit_counts = {}
        self.enemy_army_supply = 0
        self.enemy_worker_count = 0

        worker_names = {'SCV', 'PROBE', 'DRONE'}
        for unit in enemy_units:
            type_name = getattr(unit.type_id, "name", str(unit.type_id))
            self.enemy_unit_counts[type_name] = self.enemy_unit_counts.get(type_name, 0) + 1

            # Estimate supply
            supply = getattr(unit, "supply_cost", 1)
            if type_name.upper() in worker_names:
                self.enemy_worker_count += 1
            else:
                self.enemy_army_supply += supply

        # Count enemy bases
        base_types = {'COMMANDCENTER', 'COMMANDCENTERFLYING', 'ORBITALCOMMAND',
                     'ORBITALCOMMANDFLYING', 'PLANETARYFORTRESS',
                     'NEXUS', 'HATCHERY', 'LAIR', 'HIVE'}
        self.enemy_base_count = sum(
            1 for s in enemy_structures
            if getattr(s.type_id, "name", "").upper() in base_types
        )

        # Track tech buildings with detailed categorization
        tech_buildings = {'FACTORY', 'STARPORT', 'ARMORY', 'FUSIONCORE',
                         'ROBOTICSFACILITY', 'STARGATE', 'DARKSHRINE',
                         'TEMPLARARCHIVE', 'FLEETBEACON', 'TWILIGHTCOUNCIL',
                         'SPIRE', 'GREATERSPIRE', 'INFESTATIONPIT',
                         'BANELINGNEST', 'ROACHWARREN', 'HYDRALISKDEN'}
        self.enemy_tech_buildings = {
            getattr(s.type_id, "name", "").upper()
            for s in enemy_structures
            if getattr(s.type_id, "name", "").upper() in tech_buildings
        }

        # Detect enemy build pattern
        self._detect_enemy_build_pattern(enemy_structures, enemy_units)

    def _update_threat_status(self) -> None:
        """Check if we're under attack with improved detection."""
        enemy_units = getattr(self.bot, "enemy_units", [])
        townhalls = getattr(self.bot, "townhalls", [])

        if not townhalls:
            self._under_attack = False
            return

        current_time = getattr(self.bot, "time", 0.0)

        # High-threat unit types (detect earlier)
        high_threat_units = {
            'ZERGLING', 'MARINE', 'ZEALOT', 'REAPER', 'ADEPT',
            'BANELING', 'ROACH', 'STALKER', 'MARAUDER',
            'SIEGETANK', 'SIEGETANKSIEGED', 'LIBERATOR', 'WIDOWMINE'
        }

        # Check for enemies near our bases with dynamic range
        for th in townhalls:
            for enemy in enemy_units:
                try:
                    enemy_type = getattr(enemy.type_id, "name", "").upper()

                    # Dynamic detection range based on threat level
                    # High-threat units: 35 range (detect earlier)
                    # Normal units: 30 range
                    detection_range = 35 if enemy_type in high_threat_units else 30

                    # Early game (< 3min): Even more sensitive detection
                    if current_time < 180:
                        detection_range = 40

                    if enemy.distance_to(th.position) < detection_range:
                        self._under_attack = True
                        self._attack_position = enemy.position
                        self._last_attack_time = current_time

                        # Check if high threat unit
                        if enemy_type in self._high_threat_types:
                            self._high_threat_units_detected = True
                            self._threat_level = "critical"
                        elif self._threat_level not in ["critical", "heavy"]:
                            self._threat_level = "medium"

                        # Log early attack detection
                        if current_time < 180 and self.bot.iteration % 100 == 0:
                            print(f"[INTEL] [{int(current_time)}s] EARLY ATTACK: {enemy_type} detected at {detection_range} range!")

                        # Continue checking other enemies to properly assess threat level
                except Exception:
                    continue

        # Clear attack flag after 10 seconds of no enemies
        if current_time - self._last_attack_time > 10:
            self._under_attack = False
            self._attack_position = None
            self._threat_level = "none"
            self._high_threat_units_detected = False

    def is_under_attack(self) -> bool:
        """Check if any base is under attack."""
        return self._under_attack

    def get_attack_position(self):
        """Get position where attack is happening."""
        return self._attack_position

    def get_enemy_army_supply(self) -> int:
        """Get estimated enemy army supply."""
        return self.enemy_army_supply

    def get_enemy_composition(self) -> dict:
        """Get enemy unit type counts."""
        return self.enemy_unit_counts.copy()

    def has_enemy_tech(self, tech_name: str) -> bool:
        """Check if enemy has specific tech building."""
        return tech_name.upper() in self.enemy_tech_buildings

    def get_threat_level(self) -> str:
        """Get current threat level: none, light, medium, heavy, critical."""
        return self._threat_level

    def has_high_threat_units(self) -> bool:
        """Check if high-threat units (Siege Tanks, Colossi, etc.) are detected."""
        return self._high_threat_units_detected

    def is_major_attack(self) -> bool:
        """Check if this is a major attack (critical threat level or high-threat units)."""
        return self._threat_level == "critical" or self._high_threat_units_detected

    def _detect_enemy_build_pattern(self, enemy_structures, enemy_units) -> None:
        """
        Detect enemy build pattern based on tech buildings and units.

        Patterns:
        - Terran: Bio (Barracks), Mech (Factory), Air (Starport)
        - Protoss: Gateway, Robo, Stargate
        - Zerg: Pool first, Hatch first, Ling/Bane, Roach/Hydra
        """
        game_time = getattr(self.bot, "time", 0)

        # Count structures by type
        structure_counts = {}
        for s in enemy_structures:
            name = getattr(s.type_id, "name", "").upper()
            structure_counts[name] = structure_counts.get(name, 0) + 1

        # Detect pattern
        detected_pattern = "unknown"
        recommended_response = []

        # === TERRAN DETECTION ===
        if "BARRACKS" in structure_counts:
            barracks_count = structure_counts.get("BARRACKS", 0)
            factory_count = structure_counts.get("FACTORY", 0)
            starport_count = structure_counts.get("STARPORT", 0)

            if starport_count >= 1 and factory_count >= 1:
                # Mech or BC rush
                detected_pattern = "terran_mech"
                recommended_response = ["hydralisk", "corruptor", "viper"]
            elif barracks_count >= 3:
                # Bio (Marine/Marauder/Medivac)
                detected_pattern = "terran_bio"
                recommended_response = ["baneling", "zergling", "ultralisk"]
            elif factory_count >= 2:
                # Tank/Hellion
                detected_pattern = "terran_factory"
                recommended_response = ["mutalisk", "ravager", "swarmhost"]

            # Early aggression detection
            if barracks_count >= 2 and game_time < 180:
                detected_pattern = "terran_rush"
                recommended_response = ["zergling", "spine_crawler", "queen"]

        # === PROTOSS DETECTION ===
        elif "GATEWAY" in structure_counts or "NEXUS" in structure_counts:
            gateway_count = structure_counts.get("GATEWAY", 0)
            robo_count = structure_counts.get("ROBOTICSFACILITY", 0)
            stargate_count = structure_counts.get("STARGATE", 0)
            twilight = "TWILIGHTCOUNCIL" in structure_counts

            if stargate_count >= 1:
                # Stargate (Oracle, Void Ray, Carrier)
                detected_pattern = "protoss_stargate"
                recommended_response = ["hydralisk", "corruptor", "spore_crawler"]
            elif robo_count >= 1:
                # Robo (Immortal, Colossus)
                detected_pattern = "protoss_robo"
                recommended_response = ["hydralisk", "roach", "corruptor"]
            elif twilight:
                # Twilight (Blink Stalker, Charge Zealot)
                detected_pattern = "protoss_twilight"
                recommended_response = ["roach", "hydralisk", "lurker"]
            elif gateway_count >= 3:
                # Gateway all-in
                detected_pattern = "protoss_gateway"
                recommended_response = ["roach", "zergling", "spine_crawler"]

            # Proxy detection
            if gateway_count >= 1 and game_time < 150:
                detected_pattern = "protoss_proxy"
                recommended_response = ["zergling", "spine_crawler", "queen"]

        # === ZERG DETECTION ===
        elif "SPAWNINGPOOL" in structure_counts or "HATCHERY" in structure_counts:
            baneling_nest = "BANELINGNEST" in structure_counts
            roach_warren = "ROACHWARREN" in structure_counts
            spire = "SPIRE" in structure_counts or "GREATERSPIRE" in structure_counts

            if spire:
                detected_pattern = "zerg_muta"
                recommended_response = ["hydralisk", "spore_crawler", "queen"]
            elif roach_warren and not baneling_nest:
                detected_pattern = "zerg_roach"
                recommended_response = ["roach", "ravager", "hydralisk"]
            elif baneling_nest:
                detected_pattern = "zerg_ling_bane"
                recommended_response = ["baneling", "zergling", "roach"]

            # 12 pool detection
            pool_count = structure_counts.get("SPAWNINGPOOL", 0)
            hatch_count = structure_counts.get("HATCHERY", 0) + structure_counts.get("LAIR", 0) + structure_counts.get("HIVE", 0)
            if pool_count >= 1 and hatch_count <= 1 and game_time < 120:
                detected_pattern = "zerg_12pool"
                recommended_response = ["zergling", "spine_crawler", "queen"]

        # Store detected pattern
        self._enemy_build_pattern = detected_pattern
        self._recommended_response = recommended_response

        # Log detection (every 30 seconds)
        if game_time > 0 and int(game_time) % 30 == 0 and self.bot.iteration % 22 == 0:
            if detected_pattern != "unknown":
                print(f"[INTEL] [{int(game_time)}s] Enemy build: {detected_pattern}")
                print(f"[INTEL] Recommended counter: {recommended_response}")

    def get_enemy_build_pattern(self) -> str:
        """Get detected enemy build pattern."""
        return getattr(self, "_enemy_build_pattern", "unknown")

    def get_recommended_response(self) -> list:
        """Get recommended unit composition to counter enemy build."""
        return getattr(self, "_recommended_response", [])

    def record_scouted_location(self, location) -> None:
        """Record a location that has been scouted."""
        self.scouted_locations.add(location)

    def _update_destructible_structures(self) -> None:
        """
        ★ NEW: 파괴 가능한 중립 구조물 감지

        Destructible Rocks, Debris 등 확장 경로를 막는 구조물 추적
        """
        try:
            current_time = getattr(self.bot, "time", 0.0)

            # 5초마다 업데이트
            if current_time - self._last_structure_update < 5.0:
                return

            self._last_structure_update = current_time

            # 파괴 가능한 구조물 타입
            destructible_types = {
                "DESTRUCTIBLEROCK6X6", "DESTRUCTIBLEROCKSVERTICAL",
                "DESTRUCTIBLEROCKSHORIZONTAL", "DESTRUCTIBLEDEBRIS6X6",
                "DESTRUCTIBLEDEBRISRAMPLEFT", "DESTRUCTIBLEDEBRISRAMPRIGHT"
            }

            # 모든 중립 유닛에서 파괴 가능한 구조물 찾기
            destructible_list = []
            all_units = getattr(self.bot, "all_units", [])

            for unit in all_units:
                try:
                    # 적군도 아니고 아군도 아닌 유닛 = 중립
                    if not hasattr(unit, "is_mine") or unit.is_mine:
                        continue
                    if not hasattr(unit, "is_enemy") or unit.is_enemy:
                        continue

                    type_name = getattr(unit.type_id, "name", "").upper()

                    # 파괴 가능한 구조물인지 확인
                    if any(dest_type in type_name for dest_type in destructible_types):
                        destructible_list.append(unit)
                except Exception:
                    continue

            self.destructible_rocks = destructible_list

            # 로그 (처음 발견 시만)
            if destructible_list and current_time < 60 and self.bot.iteration % 100 == 0:
                print(f"[INTEL] [{int(current_time)}s] ★ {len(destructible_list)} destructible rocks detected!")

        except Exception:
            pass

    def _update_all_enemy_structures(self) -> None:
        """
        ★ NEW: 모든 적 구조물 추적 (승리 조건용)

        모든 적 건물을 파괴해야 승리할 수 있음
        """
        try:
            enemy_structures = getattr(self.bot, "enemy_structures", [])
            self.all_enemy_structures = list(enemy_structures)

            current_time = getattr(self.bot, "time", 0.0)

            # 10초마다 적 구조물 수 로그
            if int(current_time) % 30 == 0 and self.bot.iteration % 22 == 0:
                if len(self.all_enemy_structures) > 0:
                    print(f"[INTEL] [{int(current_time)}s] Enemy structures remaining: {len(self.all_enemy_structures)}")
        except Exception:
            pass

    def get_destructible_rocks(self) -> list:
        """파괴 가능한 중립 구조물 목록 반환."""
        return self.destructible_rocks.copy()

    def get_closest_destructible_rock(self, position):
        """주어진 위치에서 가장 가까운 파괴 가능한 구조물 반환."""
        if not self.destructible_rocks:
            return None

        try:
            return min(self.destructible_rocks, key=lambda rock: rock.distance_to(position))
        except Exception:
            return None

    def get_all_enemy_structures(self) -> list:
        """모든 적 구조물 목록 반환 (승리 조건용)."""
        return self.all_enemy_structures.copy()

    def get_enemy_structure_count(self) -> int:
        """남은 적 구조물 수 반환."""
        return len(self.all_enemy_structures)
