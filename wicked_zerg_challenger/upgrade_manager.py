# -*- coding: utf-8 -*-
"""
Evolution Chamber upgrade manager.

Chooses upgrades based on unit composition and opponent race.
"""

from typing import Dict, List, Optional

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
except ImportError:  # Fallbacks for tooling environments
    UnitTypeId = None
    UpgradeId = None


class EvolutionUpgradeManager:
    """
    Manages all Zerg upgrades with dynamic priorities.

    0순위 (생명줄):
    - 대사 촉진 (Metabolic Boost / 발업): 저글링 속도
    - 기낭 갑피 (Pneumatized Carapace): 대군주 속도

    1순위: Evolution Chamber 공방 업그레이드
    """

    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0
        self.update_interval = 22  # 더 자주 체크 (1초마다)
        self.gas_reserve_threshold = 200

        # 0순위 업그레이드 상태 추적
        self._zergling_speed_started = False
        self._overlord_speed_started = False

    async def on_step(self, iteration: int) -> None:
        if not UnitTypeId or not UpgradeId:
            return
        if iteration - self.last_update < self.update_interval:
            return

        self.last_update = iteration
        if not hasattr(self.bot, "structures"):
            return

        game_time = getattr(self.bot, "time", 0)

        # === 0순위: 핵심 업그레이드 (생명줄) ===
        await self._research_critical_upgrades(iteration)

        # === ★★★ 테크 변이: 해처리 → 레어 → 군락 ★★★ ===
        await self._upgrade_tech_buildings(iteration)

        # === 1순위: Evolution Chamber 업그레이드 (4분 이후) ===
        if game_time >= 240:
            # Build Evolution Chamber if missing
            await self._build_evolution_chamber()

            evo_chambers = self.bot.structures(UnitTypeId.EVOLUTIONCHAMBER).ready
            if not evo_chambers:
                return

        upgrade_order = self._get_upgrade_priority()
        vespene = getattr(self.bot, "vespene", 0)
        gas_constrained = vespene < self.gas_reserve_threshold
        for evo in evo_chambers:
            if hasattr(evo, "is_idle") and not evo.is_idle:
                continue

            for upgrade_id in upgrade_order:
                if gas_constrained and upgrade_id != upgrade_order[0]:
                    continue
                if not self._can_research(upgrade_id):
                    continue
                if not self.bot.can_afford(upgrade_id):
                    continue

                try:
                    self.bot.do(evo.research(upgrade_id))
                    upgrade_name = getattr(upgrade_id, "name", str(upgrade_id))
                    print(f"[UPGRADE] Researching {upgrade_name}")
                except Exception:
                    continue
                return

    def _get_upgrade_priority(self) -> List[object]:
        """
        Get upgrade priority - 명확한 순서

        기본 순서 (저글링/맹독충 체제):
        3. 공격 +1 (Melee +1)
        5. 방어 +1 (Armor +1)
        6. 공격 +2 (Melee +2)

        바퀴/히드라 체제:
        3. 원거리 +1 (Missile +1)
        5. 방어 +1 (Armor +1)
        6. 원거리 +2 (Missile +2)
        """
        composition = self._get_unit_composition()
        enemy_race = self._normalize_enemy_race(getattr(self.bot, "enemy_race", ""))

        # 유닛 수 확인
        zergling_count = composition.get("zergling", 0)
        baneling_count = composition.get("baneling", 0)
        roach_count = composition.get("roach", 0)
        hydra_count = composition.get("hydralisk", 0)
        mutalisk_count = composition.get("mutalisk", 0)

        total_melee = zergling_count + baneling_count
        total_ranged = roach_count + hydra_count

        # === 체제 판단 ===
        # 바퀴/히드라가 메인이면 원거리 우선
        is_ranged_main = total_ranged > total_melee and total_ranged >= 5

        priorities = []

        if is_ranged_main:
            # 바퀴/히드라 체제: 원거리 → 방어 → 원거리
            priorities = ["missile", "armor", "missile", "armor", "missile"]
        else:
            # 저글링/맹독충 체제 (기본): 근접 → 방어 → 근접
            priorities = ["melee", "armor", "melee", "armor", "melee"]

        # 뮤탈이 있으면 공중 공격도 추가
        if mutalisk_count >= 5:
            priorities.append("air_attack")

        # === 업그레이드 순서 생성 (중복 제거) ===
        upgrade_order: List[object] = []
        seen_upgrades = set()

        for lane in priorities:
            next_upgrade = self._next_upgrade(lane)
            if next_upgrade and next_upgrade not in seen_upgrades:
                upgrade_order.append(next_upgrade)
                seen_upgrades.add(next_upgrade)

        return upgrade_order

    def _get_unit_composition(self) -> Dict[str, int]:
        counts = {
            "melee": 0,
            "ranged": 0,
            "zergling": 0,
            "baneling": 0,
            "hydralisk": 0,
            "roach": 0,
            "mutalisk": 0,
            "corruptor": 0,
        }
        if not hasattr(self.bot, "units"):
            return counts

        units = self.bot.units
        for unit in units:
            if unit.type_id in self._melee_unit_types():
                counts["melee"] += 1
                if unit.type_id == UnitTypeId.ZERGLING:
                    counts["zergling"] += 1
                if unit.type_id == UnitTypeId.BANELING:
                    counts["baneling"] += 1
            elif unit.type_id in self._ranged_unit_types():
                counts["ranged"] += 1
                if unit.type_id == UnitTypeId.HYDRALISK:
                    counts["hydralisk"] += 1
                if unit.type_id == UnitTypeId.ROACH:
                    counts["roach"] += 1
            elif unit.type_id in self._air_unit_types():
                if unit.type_id == UnitTypeId.MUTALISK:
                    counts["mutalisk"] += 1
                if unit.type_id == UnitTypeId.CORRUPTOR:
                    counts["corruptor"] += 1

        return counts

    @staticmethod
    def _has_unit(enemy_units, names: List[str]) -> bool:
        if not UnitTypeId or not enemy_units:
            return False
        for name in names:
            unit_id = getattr(UnitTypeId, name, None)
            if unit_id and any(e.type_id == unit_id for e in enemy_units):
                return True
        return False

    @staticmethod
    def _normalize_enemy_race(value) -> str:
        if value is None:
            return ""
        if hasattr(value, "name"):
            return str(value.name).lower()
        text = str(value).lower()
        if text.startswith("race."):
            return text.split(".", 1)[1]
        return text

    @staticmethod
    def _melee_unit_types() -> List[object]:
        if not UnitTypeId:
            return []
        return [
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ULTRALISK,
        ]

    @staticmethod
    def _ranged_unit_types() -> List[object]:
        if not UnitTypeId:
            return []
        return [
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKER,
        ]

    @staticmethod
    def _air_unit_types() -> List[object]:
        if not UnitTypeId:
            return []
        return [
            UnitTypeId.MUTALISK,
            UnitTypeId.CORRUPTOR,
            UnitTypeId.BROODLORD,
            UnitTypeId.VIPER,
        ]

    def _next_upgrade(self, lane: str) -> Optional[object]:
        upgrade_paths = {
            "melee": [
                getattr(UpgradeId, "ZERGMELEEWEAPONSLEVEL1", None),
                getattr(UpgradeId, "ZERGMELEEWEAPONSLEVEL2", None),
                getattr(UpgradeId, "ZERGMELEEWEAPONSLEVEL3", None),
            ],
            "missile": [
                getattr(UpgradeId, "ZERGMISSILEWEAPONSLEVEL1", None),
                getattr(UpgradeId, "ZERGMISSILEWEAPONSLEVEL2", None),
                getattr(UpgradeId, "ZERGMISSILEWEAPONSLEVEL3", None),
            ],
            "armor": [
                getattr(UpgradeId, "ZERGGROUNDARMORSLEVEL1", None),
                getattr(UpgradeId, "ZERGGROUNDARMORSLEVEL2", None),
                getattr(UpgradeId, "ZERGGROUNDARMORSLEVEL3", None),
            ],
            "air_attack": [
                getattr(UpgradeId, "ZERGFLYERWEAPONSLEVEL1", None),
                getattr(UpgradeId, "ZERGFLYERWEAPONSLEVEL2", None),
                getattr(UpgradeId, "ZERGFLYERWEAPONSLEVEL3", None),
            ],
            "air_armor": [
                getattr(UpgradeId, "ZERGFLYERARMORSLEVEL1", None),
                getattr(UpgradeId, "ZERGFLYERARMORSLEVEL2", None),
                getattr(UpgradeId, "ZERGFLYERARMORSLEVEL3", None),
            ],
        }

        upgrades = [u for u in upgrade_paths.get(lane, []) if u]
        for upgrade in upgrades:
            if self._is_upgrade_done(upgrade):
                continue
            if self.bot.already_pending_upgrade(upgrade) > 0:
                continue
            if not self._tech_requirement_met(upgrade):
                continue
            return upgrade
        return None

    def _is_upgrade_done(self, upgrade_id) -> bool:
        upgrades = getattr(self.bot, "state", None)
        if upgrades and hasattr(self.bot.state, "upgrades"):
            return upgrade_id in self.bot.state.upgrades
        return False

    def _tech_requirement_met(self, upgrade_id) -> bool:
        if not UnitTypeId:
            return True

        name = getattr(upgrade_id, "name", "")
        if "LEVEL2" in name:
            return self._has_lair()
        if "LEVEL3" in name:
            return self._has_hive()
        return True

    def _has_lair(self) -> bool:
        if not hasattr(self.bot, "structures"):
            return False
        lair = self.bot.structures(UnitTypeId.LAIR)
        hive = self.bot.structures(UnitTypeId.HIVE)
        return bool((lair and lair.ready) or (hive and hive.ready))

    def _has_hive(self) -> bool:
        if not hasattr(self.bot, "structures"):
            return False
        hive = self.bot.structures(UnitTypeId.HIVE)
        return bool(hive and hive.ready)

    def _can_research(self, upgrade_id) -> bool:
        """Check if upgrade can be researched (not already done or pending)."""
        if self._is_upgrade_done(upgrade_id):
            return False
        if self.bot.already_pending_upgrade(upgrade_id) > 0:
            return False
        if not self._tech_requirement_met(upgrade_id):
            return False
        return True

    async def _research_critical_upgrades(self, iteration: int) -> None:
        """
        핵심 업그레이드 연구 (명확한 우선순위)

        순서:
        1. 저글링 발업 (Metabolic Boost)
        2. 대군주 속업 (Pneumatized Carapace)
        3. 공격 +1 (Evolution Chamber에서)
        4. 맹독충 발업 (Centrifugal Hooks) - Lair 필요
        5. 방어 +1 (Evolution Chamber에서)
        6. 공격 +2 (Evolution Chamber에서)
        7. 아드레날린 (Adrenal Glands) - Hive 필요
        """
        game_time = getattr(self.bot, "time", 0)

        # === 1순위: 저글링 발업 (Metabolic Boost) ===
        # 스포닝 풀 완료 후 즉시!
        if not self._zergling_speed_started:
            await self._research_zergling_speed(iteration)
            return  # 발업 연구 시작할 때까지 다른 것 하지 않음

        # === 2순위: 대군주 속업 (Pneumatized Carapace) ===
        # 저글링 발업 시작 후, 3:00~3:30 사이에 연구
        if not self._overlord_speed_started and game_time >= 180:
            await self._research_overlord_speed(iteration)

        # === 4순위: 맹독충 발업 (Centrifugal Hooks) - Lair 필요 ===
        # 공격 +1 이후 연구 (Evolution Chamber에서 공1업 먼저)
        if self._has_lair():
            melee_1 = getattr(UpgradeId, "ZERGMELEEWEAPONSLEVEL1", None)
            if melee_1 and self._is_upgrade_done(melee_1):
                await self._research_baneling_speed(iteration)

            # 바퀴 발업 (바퀴가 있을 때만)
            roaches = self.bot.units(UnitTypeId.ROACH)
            if roaches.amount >= 3:
                await self._research_roach_speed(iteration)

            # 히드라 발업 (히드라가 있을 때만)
            hydras = self.bot.units(UnitTypeId.HYDRALISK)
            if hydras.amount >= 3:
                await self._research_hydra_speed(iteration)

            # 잠복 (맹독충 4기 이상일 때)
            banelings = self.bot.units(UnitTypeId.BANELING)
            if banelings.amount >= 4:
                await self._research_burrow(iteration)

        # === 7순위: 아드레날린 (Adrenal Glands) - Hive 필요 ===
        # 공2업 이후 연구
        if self._has_hive():
            melee_2 = getattr(UpgradeId, "ZERGMELEEWEAPONSLEVEL2", None)
            if melee_2 and self._is_upgrade_done(melee_2):
                await self._research_adrenal_glands(iteration)

    async def _research_zergling_speed(self, iteration: int) -> None:
        """대사 촉진 (Metabolic Boost) 연구 - 저글링 속도"""
        # 이미 연구 중이거나 완료되었으면 스킵
        zergling_speed = getattr(UpgradeId, "ZERGLINGMOVEMENTSPEED", None)
        if not zergling_speed:
            return

        if self._is_upgrade_done(zergling_speed):
            self._zergling_speed_started = True
            return

        if self.bot.already_pending_upgrade(zergling_speed) > 0:
            self._zergling_speed_started = True
            return

        # 스포닝 풀 확인
        spawning_pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not spawning_pools.exists:
            return

        # 가스 100 필요
        if not self.bot.can_afford(zergling_speed):
            return

        # 연구 시작
        pool = spawning_pools.first
        if hasattr(pool, "is_idle") and pool.is_idle:
            try:
                self.bot.do(pool.research(zergling_speed))
                self._zergling_speed_started = True
                game_time = getattr(self.bot, "time", 0)
                print(f"[UPGRADE] [{int(game_time)}s] ★★★ 대사 촉진 (저글링 발업) 연구 시작! ★★★")
            except Exception as e:
                if iteration % 200 == 0:
                    print(f"[WARNING] Zergling speed research error: {e}")

    async def _research_overlord_speed(self, iteration: int) -> None:
        """기낭 갑피 (Pneumatized Carapace) 연구 - 대군주 속도"""
        overlord_speed = getattr(UpgradeId, "OVERLORDSPEED", None)
        if not overlord_speed:
            return

        if self._is_upgrade_done(overlord_speed):
            self._overlord_speed_started = True
            return

        if self.bot.already_pending_upgrade(overlord_speed) > 0:
            self._overlord_speed_started = True
            return

        # 해처리/레어/하이브 확인
        townhalls = self.bot.townhalls.ready
        if not townhalls.exists:
            return

        # 가스 100 필요
        if not self.bot.can_afford(overlord_speed):
            return

        # 연구 시작 (여유 있는 해처리에서)
        for th in townhalls:
            if hasattr(th, "is_idle") and th.is_idle:
                try:
                    self.bot.do(th.research(overlord_speed))
                    self._overlord_speed_started = True
                    game_time = getattr(self.bot, "time", 0)
                    print(f"[UPGRADE] [{int(game_time)}s] ★★★ 기낭 갑피 (대군주 속업) 연구 시작! ★★★")
                    return
                except Exception:
                    continue

    async def _research_baneling_speed(self, iteration: int) -> None:
        """원심 고리 (Centrifugal Hooks) 연구 - 맹독충 속도"""
        baneling_speed = getattr(UpgradeId, "CENTRIFICALHOOKS", None)
        if not baneling_speed:
            return

        if self._is_upgrade_done(baneling_speed):
            return

        if self.bot.already_pending_upgrade(baneling_speed) > 0:
            return

        # 맹독충 둥지 확인
        baneling_nests = self.bot.structures(UnitTypeId.BANELINGNEST).ready
        if not baneling_nests.exists:
            return

        # 가스 150 필요
        if not self.bot.can_afford(baneling_speed):
            return

        # 연구 시작
        nest = baneling_nests.first
        if hasattr(nest, "is_idle") and nest.is_idle:
            try:
                self.bot.do(nest.research(baneling_speed))
                game_time = getattr(self.bot, "time", 0)
                print(f"[UPGRADE] [{int(game_time)}s] ★★ 원심 고리 (맹독충 발업) 연구 시작! ★★")
            except Exception:
                pass

    async def _research_roach_speed(self, iteration: int) -> None:
        """신경 재구성 (Glial Reconstitution) 연구 - 바퀴 속도"""
        roach_speed = getattr(UpgradeId, "GLIALRECONSTITUTION", None)
        if not roach_speed:
            return

        if self._is_upgrade_done(roach_speed):
            return

        if self.bot.already_pending_upgrade(roach_speed) > 0:
            return

        # 바퀴 굴 확인
        roach_warrens = self.bot.structures(UnitTypeId.ROACHWARREN).ready
        if not roach_warrens.exists:
            return

        # 바퀴가 3기 이상 있을 때만 연구 (자원 효율)
        roaches = self.bot.units(UnitTypeId.ROACH)
        if roaches.amount < 3:
            return

        # 가스 100 필요
        if not self.bot.can_afford(roach_speed):
            return

        # 연구 시작
        warren = roach_warrens.first
        if hasattr(warren, "is_idle") and warren.is_idle:
            try:
                self.bot.do(warren.research(roach_speed))
                game_time = getattr(self.bot, "time", 0)
                print(f"[UPGRADE] [{int(game_time)}s] ★★ 신경 재구성 (바퀴 발업) 연구 시작! ★★")
            except Exception:
                pass

    async def _research_hydra_speed(self, iteration: int) -> None:
        """근육 보강 (Muscular Augments) 연구 - 히드라 속도"""
        hydra_speed = getattr(UpgradeId, "EVOLVEMUSCULARAUGMENTS", None)
        if not hydra_speed:
            return

        if self._is_upgrade_done(hydra_speed):
            return

        if self.bot.already_pending_upgrade(hydra_speed) > 0:
            return

        # 히드라 굴 확인
        hydra_dens = self.bot.structures(UnitTypeId.HYDRALISKDEN).ready
        if not hydra_dens.exists:
            return

        # 가스 100 필요
        if not self.bot.can_afford(hydra_speed):
            return

        # 연구 시작 (사거리 업그레이드보다 속도 우선!)
        den = hydra_dens.first
        if hasattr(den, "is_idle") and den.is_idle:
            try:
                self.bot.do(den.research(hydra_speed))
                game_time = getattr(self.bot, "time", 0)
                print(f"[UPGRADE] [{int(game_time)}s] ★★ 근육 보강 (히드라 발업) 연구 시작! ★★")
            except Exception:
                pass

    async def _research_burrow(self, iteration: int) -> None:
        """잠복 (Burrow) 연구 - 맹독충 지뢰, 바퀴 회복 등"""
        burrow = getattr(UpgradeId, "BURROW", None)
        if not burrow:
            return

        if self._is_upgrade_done(burrow):
            return

        if self.bot.already_pending_upgrade(burrow) > 0:
            return

        # 해처리/레어/하이브 확인
        townhalls = self.bot.townhalls.ready
        if not townhalls.exists:
            return

        # 맹독충이 2기 이상 있을 때 잠복 연구 (맹독충 지뢰용)
        banelings = self.bot.units(UnitTypeId.BANELING)
        if banelings.amount < 2:
            return

        # 가스 100 필요
        if not self.bot.can_afford(burrow):
            return

        # 연구 시작
        for th in townhalls:
            if hasattr(th, "is_idle") and th.is_idle:
                try:
                    self.bot.do(th.research(burrow))
                    game_time = getattr(self.bot, "time", 0)
                    print(f"[UPGRADE] [{int(game_time)}s] ★★ 잠복 (Burrow) 연구 시작! ★★")
                    return
                except Exception:
                    continue

    async def _research_adrenal_glands(self, iteration: int) -> None:
        """아드레날린 분비선 (Adrenal Glands) 연구 - 저글링 공속업 (Crackling)"""
        adrenal = getattr(UpgradeId, "ZERGLINGATTACKSPEED", None)
        if not adrenal:
            return

        if self._is_upgrade_done(adrenal):
            return

        if self.bot.already_pending_upgrade(adrenal) > 0:
            return

        # 스포닝 풀 확인
        spawning_pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not spawning_pools.exists:
            return

        # 저글링 발업이 먼저 완료되어야 함
        zergling_speed = getattr(UpgradeId, "ZERGLINGMOVEMENTSPEED", None)
        if zergling_speed and not self._is_upgrade_done(zergling_speed):
            return

        # 가스 200 필요
        if not self.bot.can_afford(adrenal):
            return

        # 연구 시작
        pool = spawning_pools.first
        if hasattr(pool, "is_idle") and pool.is_idle:
            try:
                self.bot.do(pool.research(adrenal))
                game_time = getattr(self.bot, "time", 0)
                print(f"[UPGRADE] [{int(game_time)}s] ★★★ 아드레날린 분비선 (Crackling) 연구 시작! ★★★")
            except Exception:
                pass

    async def _build_evolution_chamber(self) -> bool:
        """Build Evolution Chamber for upgrades."""
        # Check time (after 4 minutes)
        if getattr(self.bot, "time", 0) < 240:
            return False

        # Check if already exists or pending
        evo_chambers = self.bot.structures(UnitTypeId.EVOLUTIONCHAMBER)
        if evo_chambers.exists or self.bot.already_pending(UnitTypeId.EVOLUTIONCHAMBER) > 0:
            return False

        # Check resources
        if not self.bot.can_afford(UnitTypeId.EVOLUTIONCHAMBER):
            return False

        # Need Spawning Pool first
        if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            return False

        # Build near townhall
        if self.bot.townhalls.exists:
            try:
                await self.bot.build(
                    UnitTypeId.EVOLUTIONCHAMBER,
                    near=self.bot.townhalls.first.position
                )
                print(f"[UPGRADE] [{int(self.bot.time)}s] Building Evolution Chamber")
                return True
            except Exception:
                pass
        return False

    # ============================================================
    # ★★★ TECH BUILDING UPGRADES: Hatchery → Lair → Hive ★★★
    # ============================================================

    async def _upgrade_tech_buildings(self, iteration: int) -> None:
        """
        테크 건물 변이: 해처리 → 레어 → 군락

        타이밍:
        - 레어 (Lair): 4분 (240초) 이후, 스포닝 풀 있을 때
        - 군락 (Hive): 8분 (480초) 이후, 인페스테이션 핏 있을 때

        조건:
        - 자원 충분 (미네랄 150 + 가스 100)
        - 해처리/레어가 idle 상태일 때
        - 이미 변이 중이 아닐 때
        """
        game_time = getattr(self.bot, "time", 0)

        # === 레어 (Lair) 변이: 4분 이후 ===
        if game_time >= 240:
            await self._upgrade_to_lair(iteration)

        # === 군락 (Hive) 변이: 8분 이후 ===
        if game_time >= 480:
            await self._upgrade_to_hive(iteration)

    async def _upgrade_to_lair(self, iteration: int) -> None:
        """
        해처리 → 레어 변이

        조건:
        - 스포닝 풀이 완료되어야 함
        - 레어/군락이 없어야 함
        - 변이 중이 아니어야 함
        """
        # 이미 레어나 군락이 있으면 스킵
        lairs = self.bot.structures(UnitTypeId.LAIR)
        hives = self.bot.structures(UnitTypeId.HIVE)

        if lairs.exists or hives.exists:
            return

        # 레어 변이 중인지 확인 (any hatchery is upgrading)
        if self.bot.already_pending(UnitTypeId.LAIR) > 0:
            return

        # 스포닝 풀 필요
        spawning_pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not spawning_pools.exists:
            return

        # 해처리가 있어야 함
        hatcheries = self.bot.structures(UnitTypeId.HATCHERY).ready.idle
        if not hatcheries.exists:
            return

        # 자원 확인 (미네랄 150 + 가스 100)
        if self.bot.minerals < 150 or self.bot.vespene < 100:
            return

        # 변이 시작 (가장 안전한 해처리 = 본진)
        try:
            # 본진 해처리 선택 (start_location에 가장 가까운)
            if hasattr(self.bot, "start_location"):
                main_hatch = hatcheries.closest_to(self.bot.start_location)
            else:
                main_hatch = hatcheries.first

            self.bot.do(main_hatch(UnitTypeId.LAIR))
            game_time = getattr(self.bot, "time", 0)
            print(f"[TECH] [{int(game_time)}s] ★★★ 레어 (Lair) 변이 시작! ★★★")
        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Lair upgrade error: {e}")

    async def _upgrade_to_hive(self, iteration: int) -> None:
        """
        레어 → 군락 (Hive) 변이

        조건:
        - 인페스테이션 핏 (Infestation Pit)이 완료되어야 함
        - 군락이 없어야 함
        - 변이 중이 아니어야 함

        군락 테크 필요 유닛:
        - 울트라리스크 (Ultralisk Cavern)
        - 아드레날린 분비선 (Adrenal Glands)
        - 공격/방어 +3 업그레이드
        """
        # 이미 군락이 있으면 스킵
        hives = self.bot.structures(UnitTypeId.HIVE)
        if hives.exists:
            return

        # 군락 변이 중인지 확인
        if self.bot.already_pending(UnitTypeId.HIVE) > 0:
            return

        # 레어가 있어야 함
        lairs = self.bot.structures(UnitTypeId.LAIR).ready.idle
        if not lairs.exists:
            return

        # 인페스테이션 핏 필요 (군락 변이 조건)
        infestation_pits = self.bot.structures(UnitTypeId.INFESTATIONPIT).ready
        if not infestation_pits.exists:
            # 인페스테이션 핏 건설 시도
            await self._build_infestation_pit(iteration)
            return

        # 자원 확인 (미네랄 200 + 가스 150)
        if self.bot.minerals < 200 or self.bot.vespene < 150:
            return

        # 변이 시작
        try:
            lair = lairs.first
            self.bot.do(lair(UnitTypeId.HIVE))
            game_time = getattr(self.bot, "time", 0)
            print(f"[TECH] [{int(game_time)}s] ★★★ 군락 (Hive) 변이 시작! ★★★")
        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Hive upgrade error: {e}")

    async def _build_infestation_pit(self, iteration: int) -> None:
        """
        인페스테이션 핏 건설 (군락 변이 조건)

        조건:
        - 레어가 있어야 함
        - 7분 (420초) 이후
        """
        game_time = getattr(self.bot, "time", 0)

        # 7분 이후에만 건설
        if game_time < 420:
            return

        # 이미 있거나 건설 중이면 스킵
        infestation_pits = self.bot.structures(UnitTypeId.INFESTATIONPIT)
        if infestation_pits.exists or self.bot.already_pending(UnitTypeId.INFESTATIONPIT) > 0:
            return

        # 레어 필요
        if not self._has_lair():
            return

        # 자원 확인 (미네랄 100 + 가스 100)
        if self.bot.minerals < 100 or self.bot.vespene < 100:
            return

        # 건설 시도
        if self.bot.townhalls.exists:
            try:
                await self.bot.build(
                    UnitTypeId.INFESTATIONPIT,
                    near=self.bot.townhalls.first.position
                )
                print(f"[TECH] [{int(game_time)}s] ★★ 인페스테이션 핏 건설 시작 (군락 준비) ★★")
            except Exception:
                pass
