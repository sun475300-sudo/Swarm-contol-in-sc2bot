#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit factory - larva production with gas reservation logic.

Keeps gas-heavy units from being starved by mineral-only spam.
"""

from typing import Iterable, List, Optional

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # Fallbacks for tooling environments
    UnitTypeId = None


class UnitFactory:
    def __init__(self, bot):
        self.bot = bot
        self.min_gas_reserve = 100
        self.min_mineral_reserve_for_gas = 150
        self.gas_unit_ratio_target = 0.35  # 기본값, 동적으로 조정됨
        self.larva_gas_ratio = 0.4
        self.larva_pressure_threshold = 6
        self.max_larva_spend_per_step = 3

        # ★ COMBAT REINFORCEMENT SYSTEM ★
        # 전투 중 병력 충원을 위한 시스템
        self._combat_mode = False
        self._last_combat_check = 0
        self._combat_check_interval = 22  # ~1초마다 체크
        self._combat_larva_spend = 5  # 전투 중 더 많은 라바 소비 (3 -> 5)

        # 종족별 가스 유닛 비율 (Strategy Manager와 연동)
        self.race_gas_ratios = {
            "Terran": 0.40,    # 대 테란: 뮤탈/히드라 비중 높음
            "Protoss": 0.45,   # 대 프로토스: 히드라 비중 매우 높음
            "Zerg": 0.30,      # 대 저그: 저글링/맹독충 비중 높음
            "Unknown": 0.35,
        }

    def _should_save_larva(self) -> bool:
        """
        Rogue Tactics의 라바 세이빙 모드 확인.

        맹독충 드랍 등 전술을 위해 라바를 아껴야 하는지 체크합니다.

        Returns:
            라바를 아껴야 하면 True
        """
        # Strategy Manager 체크
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy and hasattr(strategy, "should_save_larva"):
            if strategy.should_save_larva():
                return True

        # Rogue Tactics Manager 직접 체크
        rogue = getattr(self.bot, "rogue_tactics", None)
        if rogue:
            if getattr(rogue, "larva_saving_active", False):
                return True
            if getattr(rogue, "preparing_baneling_drop", False):
                return True

        return False

    def _update_gas_ratio_target(self) -> None:
        """
        상대 종족에 따라 가스 유닛 비율 동적 조정.
        """
        # Strategy Manager에서 종족 정보 가져오기
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy:
            race = getattr(strategy, "detected_enemy_race", None)
            if race:
                race_name = race.value if hasattr(race, "value") else str(race)
                self.gas_unit_ratio_target = self.race_gas_ratios.get(
                    race_name, self.race_gas_ratios["Unknown"]
                )
                return

        # 직접 종족 확인
        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race:
            race_str = str(enemy_race)
            for race_name in self.race_gas_ratios:
                if race_name in race_str:
                    self.gas_unit_ratio_target = self.race_gas_ratios[race_name]
                    return

    def _is_emergency_mode(self) -> bool:
        """Emergency Mode 확인 - 드론 대신 군대 우선"""
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy:
            return getattr(strategy, "emergency_active", False)
        return False

    def _check_combat_mode(self, iteration: int) -> bool:
        """
        전투 모드 확인 - 전투 중이면 병력 충원 모드 활성화

        Returns:
            True if in combat mode (need reinforcement)
        """
        if iteration - self._last_combat_check < self._combat_check_interval:
            return self._combat_mode

        self._last_combat_check = iteration

        # 전투 감지 조건들
        in_combat = False

        # 1. Strategy Manager의 emergency_active 체크
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy and getattr(strategy, "emergency_active", False):
            in_combat = True

        # 2. 적 유닛이 기지 근처에 있는지 체크
        if not in_combat and hasattr(self.bot, "enemy_units") and hasattr(self.bot, "townhalls"):
            enemy_units = self.bot.enemy_units
            for th in self.bot.townhalls:
                nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < 35]
                if len(nearby_enemies) >= 3:  # 3기 이상의 적이 근처에
                    in_combat = True
                    break

        # 3. 아군 병력 손실 체크 (서플라이 급감)
        if not in_combat and hasattr(self.bot, "supply_army"):
            supply_army = self.bot.supply_army
            if not hasattr(self, "_last_supply_army"):
                self._last_supply_army = supply_army
            else:
                supply_loss = self._last_supply_army - supply_army
                if supply_loss > 10:  # 10 서플라이 이상 손실
                    in_combat = True
                self._last_supply_army = supply_army

        self._combat_mode = in_combat
        return in_combat

    async def on_step(self, iteration: int) -> None:
        if not UnitTypeId or not hasattr(self.bot, "larva"):
            return

        larva = self.bot.larva
        if not larva:
            return

        if hasattr(self.bot, "supply_left") and self.bot.supply_left <= 0:
            return

        # ★ COMBAT REINFORCEMENT: 전투 모드 체크 ★
        in_combat = self._check_combat_mode(iteration)

        # 전투 중이면 더 많은 라바 소비
        if in_combat:
            self.max_larva_spend_per_step = self._combat_larva_spend
            if iteration % 200 == 0:
                game_time = getattr(self.bot, "time", 0)
                print(f"[UNIT_FACTORY] [{int(game_time)}s] COMBAT MODE: Increased production rate")
        else:
            self.max_larva_spend_per_step = 3  # 기본값

        # === StrategyManager 실시간 비율 연동 ===
        # 매 스텝마다 전략 매니저의 가스 비율을 가져와서 적용
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy:
            # Emergency Mode에서는 저글링 위주 생산 (가스 비율 낮춤)
            if getattr(strategy, "emergency_active", False):
                self.gas_unit_ratio_target = 0.15  # 긴급 시 가스 유닛 최소화
            else:
                # 종족별 유닛 비율에서 가스 유닛 비율 계산
                ratios = strategy.get_unit_ratios()
                if ratios:
                    # 가스 유닛: hydra, mutalisk, roach 등
                    gas_ratio = ratios.get("hydra", 0) + ratios.get("mutalisk", 0) + ratios.get("roach", 0)
                    if gas_ratio > 0:
                        self.gas_unit_ratio_target = gas_ratio

                        # 디버그 로그 (100 프레임마다)
                        if iteration % 100 == 0:
                            race = getattr(strategy, "detected_enemy_race", None)
                            race_name = race.value if hasattr(race, "value") else str(race)
                            print(f"[UNIT_FACTORY] vs {race_name}: gas_ratio_target = {self.gas_unit_ratio_target:.2f}")

        # Rogue Tactics 라바 세이빙 체크
        if self._should_save_larva():
            # 라바 세이빙 모드: 최소 라바만 사용 (오버로드 등 필수 유닛만)
            if iteration % 100 == 0:
                print("[UNIT_FACTORY] Larva saving mode - minimal production")
            # 오버로드가 필요하면 생산, 아니면 스킵
            if self.bot.supply_left < 2 and self.bot.can_afford(UnitTypeId.OVERLORD):
                try:
                    # ProductionResilience의 _safe_train 사용 (있을 경우)
                    if hasattr(self.bot, 'production') and self.bot.production:
                        await self.bot.production._safe_train(larva.first, UnitTypeId.OVERLORD)
                    else:
                        self.bot.do(larva.first.train(UnitTypeId.OVERLORD))
                except Exception:
                    pass
            return

        # 종족별 가스 비율 업데이트 (StrategyManager 없을 때 fallback)
        if not strategy:
            self._update_gas_ratio_target()

        minerals = getattr(self.bot, "minerals", 0)
        vespene = getattr(self.bot, "vespene", 0)
        gas_units = self._count_gas_units()
        total_units = max(1, self._count_combat_units())
        gas_ratio = gas_units / total_units
        can_spend_gas = vespene >= self.min_gas_reserve
        queue = self._build_priority_queue(
            minerals=minerals,
            vespene=vespene,
            gas_ratio=gas_ratio,
            gas_units=gas_units,
            larva_count=len(larva),
            can_spend_gas=can_spend_gas,
        )

        to_spend = 0
        for larva_unit in larva:
            if to_spend >= self.max_larva_spend_per_step:
                break

            unit_type = self._pick_unit(queue)
            if not unit_type:
                break

            try:
                # ProductionResilience의 _safe_train 사용 (있을 경우)
                if hasattr(self.bot, 'production') and self.bot.production:
                    await self.bot.production._safe_train(larva_unit, unit_type)
                else:
                    # Fallback: 직접 train 호출
                    self.bot.do(larva_unit.train(unit_type))
                to_spend += 1
            except Exception:
                continue

    def _pick_unit(self, queue: List[object]) -> Optional[object]:
        for unit_type in queue:
            if self._can_train(unit_type):
                return unit_type
        return None

    def _can_train(self, unit_type) -> bool:
        if not self.bot.can_afford(unit_type):
            return False
        if not self._requirements_met(unit_type):
            return False
        return True

    def _requirements_met(self, unit_type) -> bool:
        if not hasattr(self.bot, "structures"):
            return True

        requirements = {
            UnitTypeId.ZERGLING: UnitTypeId.SPAWNINGPOOL,
            UnitTypeId.BANELING: UnitTypeId.BANELINGNEST,
            UnitTypeId.ROACH: UnitTypeId.ROACHWARREN,
            UnitTypeId.RAVAGER: UnitTypeId.ROACHWARREN,
            UnitTypeId.HYDRALISK: UnitTypeId.HYDRALISKDEN,
            UnitTypeId.LURKER: UnitTypeId.LURKERDENMP,
        }
        required = requirements.get(unit_type)
        if not required:
            return True

        structures = self.bot.structures(required)
        return bool(structures and structures.ready)

    def _build_priority_queue(
        self,
        minerals: int,
        vespene: int,
        gas_ratio: float,
        gas_units: int,
        larva_count: int,
        can_spend_gas: bool,
    ) -> List[object]:
        # ★ 공중 위협 시 히드라 강제 생산 ★
        force_hydra = getattr(self, "_force_hydra", False)
        if force_hydra:
            # 히드라 굴 있고 가스 충분하면 히드라 최우선
            if self._requirements_met(UnitTypeId.HYDRALISK) and vespene >= 50:
                hydra_count = self._count_unit_type(UnitTypeId.HYDRALISK)
                # 히드라 비율 50%까지 올리기
                if hydra_count < 15:  # 또는 비율 체크
                    return [UnitTypeId.HYDRALISK, UnitTypeId.ROACH, UnitTypeId.ZERGLING]

        gas_priority = can_spend_gas and gas_ratio < self.gas_unit_ratio_target
        larva_gas_target = max(1, int(larva_count * self.larva_gas_ratio))
        gas_shortfall = gas_units < larva_gas_target
        mineral_guard = minerals < self.min_mineral_reserve_for_gas

        allow_mineral_mix = not (gas_priority and (gas_shortfall or mineral_guard))
        if gas_priority and larva_count >= self.larva_pressure_threshold:
            allow_mineral_mix = allow_mineral_mix or minerals >= self.min_mineral_reserve_for_gas * 2

        queue: List[object] = []

        # ★ Strategy Manager에서 공중 위협 감지시 히드라 우선 ★
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy and hasattr(strategy, "should_force_hydra") and strategy.should_force_hydra():
            # 히드라 우선 순위로 배치
            if self._requirements_met(UnitTypeId.HYDRALISK) and vespene >= 50:
                queue.append(UnitTypeId.HYDRALISK)

        if gas_priority:
            queue.extend(self._filter_units(self._gas_unit_table(), vespene))
            if allow_mineral_mix:
                queue.extend(self._filter_units(self._mineral_unit_table(), vespene))
        else:
            if allow_mineral_mix:
                queue.extend(self._filter_units(self._mineral_unit_table(), vespene))
            queue.extend(self._filter_units(self._gas_unit_table(), vespene))

        if not queue:
            queue = [entry["unit"] for entry in self._gas_unit_table() + self._mineral_unit_table()]
        return queue

    def _filter_units(self, table: List[dict], vespene: int) -> List[object]:
        queue: List[object] = []
        for entry in table:
            unit_type = entry["unit"]
            max_ratio = entry.get("max_ratio")
            min_gas = entry.get("min_gas", 0)
            if max_ratio is not None and self._unit_ratio(unit_type) >= max_ratio:
                continue
            if vespene < min_gas:
                continue
            queue.append(unit_type)
        return queue

    def _gas_unit_table(self) -> List[dict]:
        return [
            {"unit": UnitTypeId.HYDRALISK, "min_gas": 50, "max_ratio": 0.45},
            {"unit": UnitTypeId.ROACH, "min_gas": 25, "max_ratio": 0.5},
            {"unit": UnitTypeId.RAVAGER, "min_gas": 25, "max_ratio": 0.35},
            {"unit": UnitTypeId.LURKER, "min_gas": 75, "max_ratio": 0.2},
            {"unit": UnitTypeId.ULTRALISK, "min_gas": 150, "max_ratio": 0.15},
        ]

    def _mineral_unit_table(self) -> List[dict]:
        return [
            {"unit": UnitTypeId.ZERGLING, "max_ratio": 0.7},
            {"unit": UnitTypeId.BANELING, "max_ratio": 0.35},
        ]

    def _count_combat_units(self) -> int:
        if not hasattr(self.bot, "units"):
            return 0
        units = self.bot.units
        combat_types = {
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKER,
            UnitTypeId.ULTRALISK,
        }
        return sum(1 for unit in units if unit.type_id in combat_types)

    def _count_gas_units(self) -> int:
        if not hasattr(self.bot, "units"):
            return 0
        units = self.bot.units
        gas_types = {
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKER,
            UnitTypeId.ULTRALISK,
        }
        return sum(1 for unit in units if unit.type_id in gas_types)

    def _count_unit_type(self, unit_type) -> int:
        if not hasattr(self.bot, "units"):
            return 0
        units = self.bot.units
        return sum(1 for unit in units if unit.type_id == unit_type)

    def _unit_ratio(self, unit_type) -> float:
        total = max(1, self._count_combat_units())
        return self._count_unit_type(unit_type) / total
