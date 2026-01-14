# -*- coding: utf-8 -*-
"""
Spell Unit Manager - Optimized targeting for spell units (Infestor, Viper)

CRITICAL: Spell units require less frequent targeting updates than regular units
to reduce CPU load and allow proper spell cooldown management.

Features:
- Infestor: Neural Parasite, Fungal Growth
- Viper: Abduct, Parasitic Bomb, Blinding Cloud
- Optimized targeting cycle (16 frames instead of every frame)
"""

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from wicked_zerg_bot_pro import WickedZergBotPro

from sc2.ids.ability_id import AbilityId  # type: ignore
from sc2.ids.unit_typeid import UnitTypeId  # type: ignore
from sc2.position import Point2  # type: ignore
from sc2.unit import Unit  # type: ignore


class SpellUnitManager:
    """
    Spell Unit Manager - Optimized spell unit control

    CRITICAL: Spell units are controlled less frequently (16 frames) than regular units
    to reduce CPU load and allow proper spell cooldown management.
    """

    def __init__(self, bot: "WickedZergBotPro"):
        self.bot = bot
        self.last_spell_update_frame: int = 0
        self.spell_update_interval: int = 16  # Update every 16 frames (~0.7 seconds)

        # Spell cooldown tracking
        from typing import Dict
        self.infestor_last_spell: Dict[int, float] = {}  # unit tag -> last spell time
        self.viper_last_spell: Dict[int, float] = {}  # unit tag -> last spell time

        # Spell cooldowns (seconds)
        self.NEURAL_PARASITE_COOLDOWN = 1.5
        self.FUNGAL_GROWTH_COOLDOWN = 1.0
        self.ABDUCT_COOLDOWN = 1.0
        self.PARASITIC_BOMB_COOLDOWN = 1.0
        self.BLINDING_CLOUD_COOLDOWN = 1.0

    async def update(self, iteration: int):
        """
        Update spell units (called less frequently than regular units)

        Args:
            iteration: Current game iteration
        """
        # Only update every N frames to reduce CPU load
        if iteration - self.last_spell_update_frame < self.spell_update_interval:
            return

        self.last_spell_update_frame = iteration

        try:
            # Update Infestors
            await self._update_infestors()

            # Update Vipers
            await self._update_vipers()
        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] SpellUnitManager.update() error: {e}")

    async def _update_infestors(self):
        """Update Infestor spell usage"""
        b = self.bot

        infestors = b.units(UnitTypeId.INFESTOR).ready
        if not infestors.exists:
            return

        enemy_units = getattr(b, "enemy_units", [])
        if not enemy_units:
            return

        current_time = b.time

        for infestor in infestors:
            infestor_tag = infestor.tag

            # Check if spell is on cooldown
            last_spell_time = self.infestor_last_spell.get(infestor_tag, 0.0)
            time_since_spell = current_time - last_spell_time

            # Neural Parasite (high priority targets)
            if time_since_spell >= self.NEURAL_PARASITE_COOLDOWN:
                # Find high-value targets (Siege Tanks, Colossus, etc.)
                high_value_targets = [
                    e for e in enemy_units
                    if e.type_id in [
                        UnitTypeId.SIEGETANKSIEGED,
                        UnitTypeId.COLOSSUS,
                        UnitTypeId.BATTLECRUISER,
                        UnitTypeId.CARRIER,
                    ]
                ]

                if high_value_targets:
                    # Use closer_than API for performance
                    if hasattr(enemy_units, 'closer_than'):
                        nearby_targets = list(enemy_units.closer_than(9.0, infestor.position))
                    else:
                        nearby_targets = [e for e in high_value_targets if infestor.distance_to(e) < 9.0]

                    if nearby_targets:
                        target = nearby_targets[0]
                        if infestor.energy >= 100:  # Neural Parasite costs 100 energy
                            try:
                                await b.do(infestor(AbilityId.NEURALPARASITE_NEURALPARASITE, target))
                                self.infestor_last_spell[infestor_tag] = current_time
                                continue
                            except Exception:
                                pass

            # Fungal Growth (area damage)
            if time_since_spell >= self.FUNGAL_GROWTH_COOLDOWN:
                # Find clumped enemy units
                if hasattr(enemy_units, 'closer_than'):
                    nearby_enemies = list(enemy_units.closer_than(10.0, infestor.position))
                else:
                    nearby_enemies = [e for e in enemy_units if infestor.distance_to(e) < 10.0]

                if len(nearby_enemies) >= 3:  # At least 3 enemies for fungal
                    # Find best position to hit multiple enemies
                    best_target = self._find_best_fungal_target(infestor, nearby_enemies)
                    if best_target and infestor.energy >= 75:  # Fungal costs 75 energy
                        try:
                            await b.do(infestor(AbilityId.FUNGALGROWTH_FUNGALGROWTH, best_target))
                            self.infestor_last_spell[infestor_tag] = current_time
                        except Exception:
                            pass

    async def _update_vipers(self):
        """Update Viper spell usage"""
        b = self.bot

        vipers = b.units(UnitTypeId.VIPER).ready
        if not vipers.exists:
            return

        enemy_units = getattr(b, "enemy_units", [])
        if not enemy_units:
            return

        current_time = b.time

        for viper in vipers:
            viper_tag = viper.tag

            # Check if spell is on cooldown
            last_spell_time = self.viper_last_spell.get(viper_tag, 0.0)
            time_since_spell = current_time - last_spell_time

            # Abduct (pull high-value targets)
            if time_since_spell >= self.ABDUCT_COOLDOWN:
                # Find high-value targets
                high_value_targets = [
                    e for e in enemy_units
                    if e.type_id in [
                        UnitTypeId.SIEGETANKSIEGED,
                        UnitTypeId.COLOSSUS,
                        UnitTypeId.THOR,
                        UnitTypeId.BATTLECRUISER,
                    ]
                ]

                if high_value_targets:
                    # Use closer_than API for performance
                    if hasattr(enemy_units, 'closer_than'):
                        nearby_targets = list(enemy_units.closer_than(11.0, viper.position))
                    else:
                        nearby_targets = [e for e in high_value_targets if viper.distance_to(e) < 11.0]

                    if nearby_targets:
                        target = nearby_targets[0]
                        if viper.energy >= 75:  # Abduct costs 75 energy
                            try:
                                await b.do(viper(AbilityId.ABDUCT_ABDUCT, target))
                                self.viper_last_spell[viper_tag] = current_time
                                continue
                            except Exception:
                                pass

            # Parasitic Bomb (air units)
            if time_since_spell >= self.PARASITIC_BOMB_COOLDOWN:
                air_targets = [
                    e for e in enemy_units
                    if e.is_flying and e.type_id in [
                        UnitTypeId.BANSHEE,
                        UnitTypeId.VIKING,
                        UnitTypeId.MEDIVAC,
                        UnitTypeId.VOIDRAY,
                        UnitTypeId.PHOENIX,
                        UnitTypeId.CARRIER,
                    ]
                ]

                if air_targets:
                    if hasattr(enemy_units, 'closer_than'):
                        nearby_air = list(enemy_units.closer_than(14.0, viper.position))
                    else:
                        nearby_air = [e for e in air_targets if viper.distance_to(e) < 14.0]

                    if nearby_air:
                        target = nearby_air[0]
                        if viper.energy >= 125:  # Parasitic Bomb costs 125 energy
                            try:
                                await b.do(viper(AbilityId.PARASITICBOMB_PARASITICBOMB, target))
                                self.viper_last_spell[viper_tag] = current_time
                                continue
                            except Exception:
                                pass

            # Blinding Cloud (ground units)
            if time_since_spell >= self.BLINDING_CLOUD_COOLDOWN:
                ground_targets = [
                    e for e in enemy_units
                    if not e.is_flying and e.type_id in [
                        UnitTypeId.SIEGETANKSIEGED,
                        UnitTypeId.MARINE,
                        UnitTypeId.MARAUDER,
                    ]
                ]

                if ground_targets:
                    if hasattr(enemy_units, 'closer_than'):
                        nearby_ground = list(enemy_units.closer_than(12.0, viper.position))
                    else:
                        nearby_ground = [e for e in ground_targets if viper.distance_to(e) < 12.0]

                    if nearby_ground:
                        # Find clumped ground units
                        best_position = self._find_best_blinding_cloud_position(viper, nearby_ground)
                        if best_position and viper.energy >= 100:  # Blinding Cloud costs 100 energy
                            try:
                                await b.do(viper(AbilityId.BLINDINGCLOUD_BLINDINGCLOUD, best_position))
                                self.viper_last_spell[viper_tag] = current_time
                            except Exception:
                                pass

    def _find_best_fungal_target(self, infestor: Unit, enemies: List[Unit]) -> Optional[Point2]:
        """Find best position for Fungal Growth to hit multiple enemies"""
        if not enemies:
            return None

        # Find position that hits most enemies (within 2.5 radius)
        best_position = None
        max_hits = 0

        for enemy in enemies[:10]:  # Limit to 10 enemies for performance
            hits = sum(1 for e in enemies if e.distance_to(enemy.position) <= 2.5)
            if hits > max_hits:
                max_hits = hits
                best_position = enemy.position

        return best_position

    def _find_best_blinding_cloud_position(self, viper: Unit, enemies: List[Unit]) -> Optional[Point2]:
        """Find best position for Blinding Cloud to cover multiple enemies"""
        if not enemies:
            return None

        # Find center of enemy cluster
        if len(enemies) == 1:
            return enemies[0].position

        # Calculate centroid
        total_x = sum(e.position.x for e in enemies)
        total_y = sum(e.position.y for e in enemies)
        centroid = Point2((total_x / len(enemies), total_y / len(enemies)))

        return centroid
