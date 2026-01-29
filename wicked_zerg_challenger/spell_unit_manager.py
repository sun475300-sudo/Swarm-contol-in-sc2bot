# -*- coding: utf-8 -*-
"""
Spell Unit Manager - Optimized targeting for spell units

CRITICAL: Spell units require less frequent targeting updates than regular units
to reduce CPU load and allow proper spell cooldown management.

Features:
- ★ Ravager: Corrosive Bile (부식성 담즙) - 건물/중갑 유닛 파괴 ★
- Infestor: Neural Parasite, Fungal Growth
- Viper: Abduct, Parasitic Bomb, Blinding Cloud, Consume
- Baneling: Explode (자폭)
- Overseer: Contaminate
- Optimized targeting cycle (12 frames instead of every frame)
"""

from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
    from sc2.unit import Unit
else:
    # Runtime imports
    try:
        from sc2.ids.ability_id import AbilityId
        from sc2.ids.unit_typeid import UnitTypeId
        from sc2.position import Point2
        from sc2.unit import Unit
    except ImportError:
        Unit = None
        Point2 = None
        UnitTypeId = None
        AbilityId = None


class SpellUnitManager:
    """
    Spell Unit Manager - Optimized spell unit control

    CRITICAL: Spell units are controlled less frequently (16 frames) than regular units
    to reduce CPU load and allow proper spell cooldown management.
    """

    def __init__(self, bot: "WickedZergBotPro"):
        self.bot = bot
        self.last_spell_update_frame: int = 0
        self.spell_update_interval: int = 12  # ★ 16 → 12 프레임 (더 빠른 반응)

        # Spell cooldown tracking
        from typing import Dict

        self.infestor_last_spell: Dict[int, float] = {}  # unit tag -> last spell time
        self.viper_last_spell: Dict[int, float] = {}  # unit tag -> last spell time
        self.viper_last_consume: Dict[int, float] = {}  # ★ FIXED: Viper consume tracking
        self.ravager_last_bile: Dict[int, float] = {}  # ★ NEW: Ravager bile tracking
        self.baneling_exploded: set = set()  # ★ NEW: Baneling explode tracking
        self.overseer_last_contaminate: Dict[int, float] = {}  # ★ NEW: Overseer contaminate

        # ★ NEW: Infestor Tactics Controller (Burrow Movement) ★
        try:
            from combat.infestor_tactics import InfestorTacticsController
            self.infestor_tactics = InfestorTacticsController()
        except ImportError:
            self.infestor_tactics = None

        # Spell cooldowns (seconds)
        self.NEURAL_PARASITE_COOLDOWN = 1.5
        self.FUNGAL_GROWTH_COOLDOWN = 1.0
        self.ABDUCT_COOLDOWN = 1.0
        self.PARASITIC_BOMB_COOLDOWN = 1.0
        self.BLINDING_CLOUD_COOLDOWN = 1.0
        self.CONSUME_COOLDOWN = 1.0
        self.CORROSIVE_BILE_COOLDOWN = 7.0  # ★ NEW: Ravager bile cooldown
        self.CONTAMINATE_COOLDOWN = 1.0  # ★ NEW: Overseer contaminate

        self.consume_energy_threshold = 50

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
            # ★ UPDATE RAVAGERS (HIGHEST PRIORITY - 가장 흔한 스킬 유닛)
            await self._update_ravagers()

            # Update Infestors
            await self._update_infestors()

            # Update Vipers
            await self._update_vipers()

            # ★ UPDATE BANELINGS (자폭)
            await self._update_banelings()

            # ★ UPDATE OVERSEERS (오염)
            await self._update_overseers()
        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] SpellUnitManager.update() error: {e}")

    async def _update_infestors(self):
        """
        Update Infestor tactics and spell usage

        Features:
        - Burrow movement for infiltration and flanking
        - Neural Parasite on high-value targets
        - Fungal Growth on clumped units
        """
        b = self.bot

        infestors = b.units(UnitTypeId.INFESTOR).ready
        if not infestors.exists:
            return

        enemy_units = getattr(b, "enemy_units", [])
        if not enemy_units:
            return

        current_time = b.time

        # ★ BURROW MOVEMENT TACTICS: Infiltration and flanking ★
        if self.infestor_tactics:
            await self.infestor_tactics.execute_burrow_tactics(
                infestors,
                enemy_units,
                b,
                current_time
            )

        for infestor in infestors:
            infestor_tag = infestor.tag

            # Check if spell is on cooldown
            last_spell_time = self.infestor_last_spell.get(infestor_tag, 0.0)
            time_since_spell = current_time - last_spell_time

            # Neural Parasite (high priority targets)
            if time_since_spell >= self.NEURAL_PARASITE_COOLDOWN:
                high_value_ids = self._unit_type_ids(
                    [
                        "SIEGETANKSIEGED",
                        "SIEGETANK",
                        "COLOSSUS",
                        "IMMORTAL",
                        "DISRUPTOR",
                        "HIGHTEMPLAR",
                        "ARCHON",
                        "WIDOWMINE",
                        "WIDOWMINEBURROWED",
                        "BATTLECRUISER",
                        "CARRIER",
                        "TEMPEST",
                        "GHOST",
                    ]
                )
                high_value_targets = [
                    e for e in enemy_units if e.type_id in high_value_ids
                ]

                if high_value_targets:
                    # Use closer_than API for performance
                    if hasattr(enemy_units, "closer_than"):
                        nearby_targets = list(
                            enemy_units.closer_than(9.0, infestor.position)
                        )
                    else:
                        nearby_targets = [
                            e
                            for e in high_value_targets
                            if infestor.distance_to(e) < 9.0
                        ]

                    if nearby_targets:
                        target = nearby_targets[0]
                        if infestor.energy >= 100:  # Neural Parasite costs 100 energy
                            try:
                                b.do(
                                    infestor(
                                        AbilityId.NEURALPARASITE_NEURALPARASITE, target
                                    )
                                )
                                self.infestor_last_spell[infestor_tag] = current_time
                                continue
                            except Exception:
                                pass

            # Fungal Growth (area damage)
            if time_since_spell >= self.FUNGAL_GROWTH_COOLDOWN:
                # Find clumped enemy units
                if hasattr(enemy_units, "closer_than"):
                    nearby_enemies = list(
                        enemy_units.closer_than(10.0, infestor.position)
                    )
                else:
                    nearby_enemies = [
                        e for e in enemy_units if infestor.distance_to(e) < 10.0
                    ]

                if len(nearby_enemies) >= 3:  # At least 3 enemies for fungal
                    # Find best position to hit multiple enemies
                    best_target = self._find_best_fungal_target(
                        infestor, nearby_enemies
                    )
                    if best_target and infestor.energy >= 75:  # Fungal costs 75 energy
                        try:
                            b.do(
                                infestor(
                                    AbilityId.FUNGALGROWTH_FUNGALGROWTH, best_target
                                )
                            )
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

            consume_ability = getattr(AbilityId, "VIPERCONSUME_VIPERCONSUME", None)
            if consume_ability is None:
                consume_ability = getattr(AbilityId, "EFFECT_CONSUME", None)
            if consume_ability:
                last_consume_time = self.viper_last_consume.get(viper_tag, 0.0)
                time_since_consume = current_time - last_consume_time
                if (
                    viper.energy < self.consume_energy_threshold
                    and time_since_consume >= self.CONSUME_COOLDOWN
                ):
                    consume_target = self._find_consume_target(viper)
                    if consume_target:
                        try:
                            b.do(viper(consume_ability, consume_target))
                            self.viper_last_consume[viper_tag] = current_time
                            continue
                        except Exception:
                            pass

            # Abduct (pull high-value targets)
            if time_since_spell >= self.ABDUCT_COOLDOWN:
                # Find high-value targets
                high_value_targets = [
                    e
                    for e in enemy_units
                    if e.type_id
                    in [
                        UnitTypeId.SIEGETANKSIEGED,
                        UnitTypeId.COLOSSUS,
                        UnitTypeId.THOR,
                        UnitTypeId.BATTLECRUISER,
                    ]
                ]

                if high_value_targets:
                    # Use closer_than API for performance
                    if hasattr(enemy_units, "closer_than"):
                        nearby_targets = list(
                            enemy_units.closer_than(11.0, viper.position)
                        )
                    else:
                        nearby_targets = [
                            e for e in high_value_targets if viper.distance_to(e) < 11.0
                        ]

                    if nearby_targets:
                        target = nearby_targets[0]
                        if viper.energy >= 75:  # Abduct costs 75 energy
                            try:
                                b.do(viper(AbilityId.ABDUCT_ABDUCT, target))
                                self.viper_last_spell[viper_tag] = current_time
                                continue
                            except Exception:
                                pass

            # Parasitic Bomb (air units)
            if time_since_spell >= self.PARASITIC_BOMB_COOLDOWN:
                air_targets = [
                    e
                    for e in enemy_units
                    if getattr(e, "is_flying", False)
                    and e.type_id
                    in [
                        UnitTypeId.BANSHEE,
                        UnitTypeId.VIKING,
                        UnitTypeId.MEDIVAC,
                        UnitTypeId.VOIDRAY,
                        UnitTypeId.PHOENIX,
                        UnitTypeId.CARRIER,
                    ]
                ]

                if air_targets:
                    if hasattr(enemy_units, "closer_than"):
                        nearby_air = list(enemy_units.closer_than(14.0, viper.position))
                    else:
                        nearby_air = [
                            e for e in air_targets if viper.distance_to(e) < 14.0
                        ]

                    if nearby_air:
                        target = nearby_air[0]
                        if viper.energy >= 125:  # Parasitic Bomb costs 125 energy
                            try:
                                b.do(
                                    viper(AbilityId.PARASITICBOMB_PARASITICBOMB, target)
                                )
                                self.viper_last_spell[viper_tag] = current_time
                                continue
                            except Exception:
                                pass

            # Blinding Cloud (ground units)
            if time_since_spell >= self.BLINDING_CLOUD_COOLDOWN:
                ground_targets = [
                    e
                    for e in enemy_units
                    if not getattr(e, "is_flying", False)
                    and e.type_id
                    in [
                        UnitTypeId.SIEGETANKSIEGED,
                        UnitTypeId.MARINE,
                        UnitTypeId.MARAUDER,
                    ]
                ]

                if ground_targets:
                    if hasattr(enemy_units, "closer_than"):
                        nearby_ground = list(
                            enemy_units.closer_than(12.0, viper.position)
                        )
                    else:
                        nearby_ground = [
                            e for e in ground_targets if viper.distance_to(e) < 12.0
                        ]

                    if nearby_ground:
                        # Find clumped ground units
                        best_position = self._find_best_blinding_cloud_position(
                            viper, nearby_ground
                        )
                        if (
                            best_position and viper.energy >= 100
                        ):  # Blinding Cloud costs 100 energy
                            try:
                                b.do(
                                    viper(
                                        AbilityId.BLINDINGCLOUD_BLINDINGCLOUD,
                                        best_position,
                                    )
                                )
                                self.viper_last_spell[viper_tag] = current_time
                            except Exception:
                                pass

    def _find_best_fungal_target(
        self, infestor: Unit, enemies: List[Unit]
    ) -> Optional[Point2]:
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

    def _find_best_blinding_cloud_position(
        self, viper: Unit, enemies: List[Unit]
    ) -> Optional[Point2]:
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

    def _find_consume_target(self, viper: Unit) -> Optional[Unit]:
        """Find a safe structure to consume for Viper energy."""
        if not hasattr(self.bot, "structures"):
            return None

        if not UnitTypeId:
            return None

        candidate_ids = self._unit_type_ids(
            [
                "EXTRACTOR",
                "EVOLUTIONCHAMBER",
                "SPINECRAWLER",
                "SPORECRAWLER",
                "HATCHERY",
                "LAIR",
                "HIVE",
            ]
        )

        structures = [s for s in self.bot.structures if s.type_id in candidate_ids]
        if not structures:
            return None

        healthy = []
        for structure in structures:
            health = getattr(structure, "health", 0)
            health_ratio = getattr(structure, "health_percentage", 1.0)
            if health > 200 and health_ratio > 0.6:
                healthy.append(structure)

        candidates = healthy if healthy else structures

        try:
            return min(candidates, key=lambda s: viper.distance_to(s))
        except Exception:
            return candidates[0] if candidates else None

    async def _update_ravagers(self):
        """
        ★★★ UPDATE RAVAGERS - Corrosive Bile (부식성 담즙) ★★★

        Corrosive Bile 사용 우선순위:
        1. 적 건물 (특히 기지) - 건물 파괴
        2. 중갑 유닛 (시즈탱크, 콜로서스, 토르 등)
        3. 밀집된 적 병력 (3기 이상)

        특징:
        - 사거리 9 (안전 거리)
        - 에너지 비용 없음 (쿨다운만)
        - 2초 후 폭발 (예측 사격 필요)
        """
        b = self.bot

        if not hasattr(b, "units"):
            return

        ravagers = b.units(UnitTypeId.RAVAGER).ready
        if not ravagers.exists:
            return

        current_time = b.time

        # 적 구조물과 유닛 가져오기
        enemy_structures = getattr(b, "enemy_structures", [])
        enemy_units = getattr(b, "enemy_units", [])

        for ravager in ravagers:
            ravager_tag = ravager.tag

            # 쿨다운 확인
            last_bile_time = self.ravager_last_bile.get(ravager_tag, 0.0)
            time_since_bile = current_time - last_bile_time

            if time_since_bile < self.CORROSIVE_BILE_COOLDOWN:
                continue

            # ★ 우선순위 1: 적 건물 (특히 기지와 생산 건물)
            if enemy_structures and enemy_structures.exists:
                # 타운홀 우선
                townhall_types = {
                    UnitTypeId.NEXUS, UnitTypeId.COMMANDCENTER,
                    UnitTypeId.ORBITALCOMMAND, UnitTypeId.PLANETARYFORTRESS,
                    UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE
                }
                townhalls = [s for s in enemy_structures if s.type_id in townhall_types]

                if townhalls:
                    # 사거리 내 타운홀
                    nearby_townhalls = [t for t in townhalls if ravager.distance_to(t) <= 9.0]
                    if nearby_townhalls:
                        target = nearby_townhalls[0]
                        try:
                            b.do(ravager(AbilityId.EFFECT_CORROSIVEBILE, target.position))
                            self.ravager_last_bile[ravager_tag] = current_time
                            if b.iteration % 200 == 0:
                                print(f"[RAVAGER] [{int(current_time)}s] Bile targeting enemy base!")
                            continue
                        except Exception:
                            pass

                # 사거리 내 모든 건물
                nearby_structures = [s for s in enemy_structures if ravager.distance_to(s) <= 9.0]
                if nearby_structures:
                    # 가까운 건물 우선
                    target = min(nearby_structures, key=lambda s: ravager.distance_to(s))
                    try:
                        b.do(ravager(AbilityId.EFFECT_CORROSIVEBILE, target.position))
                        self.ravager_last_bile[ravager_tag] = current_time
                        continue
                    except Exception:
                        pass

            # ★ 우선순위 2: 중갑 고가치 유닛
            if enemy_units:
                high_value_types = {
                    UnitTypeId.SIEGETANKSIEGED, UnitTypeId.SIEGETANK,
                    UnitTypeId.COLOSSUS, UnitTypeId.IMMORTAL,
                    UnitTypeId.THOR, UnitTypeId.BATTLECRUISER,
                    UnitTypeId.ARCHON, UnitTypeId.CARRIER
                }
                high_value_units = [u for u in enemy_units if u.type_id in high_value_types]

                if high_value_units:
                    nearby_high_value = [u for u in high_value_units if ravager.distance_to(u) <= 9.0]
                    if nearby_high_value:
                        target = nearby_high_value[0]
                        try:
                            b.do(ravager(AbilityId.EFFECT_CORROSIVEBILE, target.position))
                            self.ravager_last_bile[ravager_tag] = current_time
                            continue
                        except Exception:
                            pass

                # ★ 우선순위 3: 밀집된 적 병력 (3기 이상)
                nearby_enemies = [e for e in enemy_units if ravager.distance_to(e) <= 9.0]
                if len(nearby_enemies) >= 3:
                    # 가장 밀집된 위치 찾기
                    best_position = self._find_best_bile_position(ravager, nearby_enemies)
                    if best_position:
                        try:
                            b.do(ravager(AbilityId.EFFECT_CORROSIVEBILE, best_position))
                            self.ravager_last_bile[ravager_tag] = current_time
                        except Exception:
                            pass

    def _find_best_bile_position(self, ravager: Unit, enemies: List[Unit]) -> Optional[Point2]:
        """
        가장 많은 적을 맞출 수 있는 Bile 위치 찾기

        Bile 범위: 2.0 (splash)
        """
        if not enemies:
            return None

        best_position = None
        max_hits = 0

        # 각 적 위치에서 몇 명을 맞출 수 있는지 계산
        for enemy in enemies[:10]:  # 최대 10개만 확인 (성능)
            hits = sum(1 for e in enemies if e.distance_to(enemy.position) <= 2.0)
            if hits > max_hits:
                max_hits = hits
                best_position = enemy.position

        return best_position if max_hits >= 3 else None

    async def _update_banelings(self):
        """
        ★ Baneling 자동 자폭 시스템 ★

        조건:
        - 적 5기 이상 밀집 시
        - 체력 50% 이하일 때 (어차피 죽을 것 같으면 자폭)
        """
        b = self.bot

        if not hasattr(b, "units"):
            return

        banelings = b.units(UnitTypeId.BANELING).ready
        if not banelings.exists:
            return

        enemy_units = getattr(b, "enemy_units", [])
        if not enemy_units:
            return

        for baneling in banelings:
            # 이미 자폭 명령 내림
            if baneling.tag in self.baneling_exploded:
                continue

            # 주변 적 확인
            nearby_enemies = [e for e in enemy_units if baneling.distance_to(e) <= 3.0]

            # 조건 1: 적 5기 이상 밀집
            if len(nearby_enemies) >= 5:
                try:
                    b.do(baneling(AbilityId.EFFECT_EXPLODE))
                    self.baneling_exploded.add(baneling.tag)
                    continue
                except Exception:
                    pass

            # 조건 2: 체력 50% 이하 + 적 2기 이상
            health_ratio = baneling.health / baneling.health_max if baneling.health_max > 0 else 1.0
            if health_ratio < 0.5 and len(nearby_enemies) >= 2:
                try:
                    b.do(baneling(AbilityId.EFFECT_EXPLODE))
                    self.baneling_exploded.add(baneling.tag)
                except Exception:
                    pass

    async def _update_overseers(self):
        """
        ★ Overseer Contaminate (오염) ★

        타겟: 적 생산 건물 (타운홀, 배럭, 게이트웨이 등)
        효과: 60초간 생산 불가
        """
        b = self.bot

        if not hasattr(b, "units"):
            return

        overseers = b.units(UnitTypeId.OVERSEER).ready
        if not overseers.exists:
            return

        enemy_structures = getattr(b, "enemy_structures", [])
        if not enemy_structures or not enemy_structures.exists:
            return

        current_time = b.time

        # 생산 건물 타입
        production_types = {
            UnitTypeId.NEXUS, UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND,
            UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE,
            UnitTypeId.BARRACKS, UnitTypeId.FACTORY, UnitTypeId.STARPORT,
            UnitTypeId.GATEWAY, UnitTypeId.ROBOTICSFACILITY, UnitTypeId.STARGATE,
            UnitTypeId.SPAWNINGPOOL, UnitTypeId.ROACHWARREN
        }

        for overseer in overseers:
            overseer_tag = overseer.tag

            # 쿨다운 확인
            last_contaminate = self.overseer_last_contaminate.get(overseer_tag, 0.0)
            if current_time - last_contaminate < self.CONTAMINATE_COOLDOWN:
                continue

            # 에너지 확인 (Contaminate는 125 에너지)
            if overseer.energy < 125:
                continue

            # 생산 건물 찾기
            production_buildings = [s for s in enemy_structures if s.type_id in production_types]
            if not production_buildings:
                continue

            # 사거리 내 건물 (Contaminate 사거리: 7)
            nearby_buildings = [b for b in production_buildings if overseer.distance_to(b) <= 7.0]
            if nearby_buildings:
                target = nearby_buildings[0]
                try:
                    b.do(overseer(AbilityId.CONTAMINATE_CONTAMINATE, target))
                    self.overseer_last_contaminate[overseer_tag] = current_time
                except Exception:
                    pass

    @staticmethod
    def _unit_type_ids(names: List[str]) -> List[object]:
        if not UnitTypeId:
            return []
        unit_ids = []
        for name in names:
            unit_type = getattr(UnitTypeId, name, None)
            if unit_type is not None:
                unit_ids.append(unit_type)
        return unit_ids
