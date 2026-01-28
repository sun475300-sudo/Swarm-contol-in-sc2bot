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
    def __init__(self, bot, blackboard=None, config=None):
        """
        UnitFactory - Blackboard 통합 버전

        Args:
            bot: SC2 Bot 인스턴스
            blackboard: GameStateBlackboard 인스턴스 (Optional)
            config: GameConfig 인스턴스 (Optional)
        """
        self.bot = bot
        self.blackboard = blackboard
        self.config = config

        # Config 기반 설정 (fallback to defaults)
        if config:
            self.min_gas_reserve = config.MIN_GAS_RESERVE
            self.larva_pressure_threshold = config.LARVA_PRESSURE_THRESHOLD
        else:
            self.min_gas_reserve = 50
            self.larva_pressure_threshold = 6

        self.min_mineral_reserve_for_gas = 150
        self.gas_unit_ratio_target = 0.50  # ★ BALANCED: 0.60 → 0.50 (드론 우선) ★
        self.larva_gas_ratio = 0.45  # ★ BALANCED: 0.6 → 0.45 (미네랄 유닛 55%) ★
        self.max_larva_spend_per_step = 5

        # ★ COMBAT REINFORCEMENT SYSTEM ★
        # 전투 중 병력 충원을 위한 시스템
        self._combat_mode = False
        self._last_combat_check = 0
        self._combat_check_interval = 22  # ~1초마다 체크
        self._combat_larva_spend = 5  # 전투 중 더 많은 라바 소비 (3 -> 5)

        # 종족별 가스 유닛 비율 - ★ RE-BALANCED: 드론 생산 보장 ★
        self.race_gas_ratios = {
            "Terran": 0.50,    # ★ BALANCED: 0.65 → 0.50 (미네랄 여유 확보) ★
            "Protoss": 0.55,   # ★ BALANCED: 0.70 → 0.55 (드론 우선) ★
            "Zerg": 0.45,      # ★ BALANCED: 0.55 → 0.45 ★
            "Unknown": 0.50,   # ★ BALANCED: 0.60 → 0.50 ★
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
        if not (UnitTypeId and hasattr(self.bot, "larva") and self.bot.larva):
            # 라바가 없으면 할 게 없음
            return

        # ★ CRITICAL FIX: 앞마당/3멀티 확보를 위한 자원 보존 (확장 우선) ★
        # 유닛 생산이 확장을 방해하지 않도록 강제 제한
        townhalls = self.bot.townhalls
        base_count = townhalls.amount
        game_time = self.bot.time

        # 1. 앞마당 체크 (1분 지났는데 1베이스면 자원 세이브)
        # 단, 이미 해처리 건설 중이면(pending) 세이브 안 해도 됨
        pending_hatch = self.bot.already_pending(UnitTypeId.HATCHERY)

        # ★ FIX: 전투 중에는 확장 대기하지 않음 (생존 우선) ★
        strategy = getattr(self.bot, "strategy_manager", None)
        under_attack = False
        if strategy:
            under_attack = getattr(strategy, "emergency_active", False) or getattr(strategy, "defense_active", False)

        # ★ OPTIMIZATION: 2분 내 멀티 보장 (60초부터 자원 모으기 시작) ★
        # 기존 120초 -> 60초로 앞당김
        # ★ 단, 미네랄이 200-350 범위에 있을 때만 세이브 (너무 적으면 방어 유닛 필요)
        if base_count < 2 and game_time > 60 and pending_hatch == 0 and not under_attack:
            if 200 <= self.bot.minerals < 350: # 200 미만이면 유닛 생산 계속
                 if iteration % 100 == 0:
                     print(f"[UNIT_FACTORY] Saving minerals for Natural Expansion (Time: {int(game_time)}s), Minerals: {self.bot.minerals}")
                 return # 라바 소비 중단

        # 2. 3멀티 체크 (빠른 3멀티: 3분 30초 목표 -> 3분 10초부터 자원 보존)
        if base_count < 3 and game_time > 190 and pending_hatch == 0 and not under_attack:
             if 200 <= self.bot.minerals < 350:
                 if iteration % 100 == 0:
                     print(f"[UNIT_FACTORY] Saving minerals for 3rd Base (Time: {int(game_time)}s), Minerals: {self.bot.minerals}")
                 return

        # 3. 4멀티 체크 (빠른 4멀티: 5분 목표 -> 4분 40초부터 자원 보존)
        # ★ 4멀티는 선택사항이므로 미네랄 250+ 있을 때만 세이브
        if base_count < 4 and game_time > 280 and pending_hatch == 0 and not under_attack:
             if 250 <= self.bot.minerals < 350:
                 if iteration % 100 == 0:
                     print(f"[UNIT_FACTORY] Saving minerals for 4th Base (Time: {int(game_time)}s), Minerals: {self.bot.minerals}")
                 return

        larva = self.bot.larva
        if not larva:
            return

        if hasattr(self.bot, "supply_left") and self.bot.supply_left <= 0:
            return

        # ★★★ FIX: 사전 오버로드 생산 (supply_left < 4 시 강제) ★★★
        # 서플라이 블럭 방지: 미리 오버로드 생산
        if hasattr(self.bot, "supply_left") and self.bot.supply_left < 4:
            # 이미 생산 중인 오버로드 체크
            pending_overlords = self.bot.already_pending(UnitTypeId.OVERLORD)
            if pending_overlords == 0 and self.bot.can_afford(UnitTypeId.OVERLORD):
                # Blackboard 통합: 오버로드 긴급 요청
                if self.blackboard:
                    self.blackboard.request_production(
                        unit_type=UnitTypeId.OVERLORD,
                        count=1,
                        requester="UnitFactory",
                        priority=0  # URGENT
                    )
                    if iteration % 100 == 0:
                        print(f"[UNIT_FACTORY] ★ Preemptive Overlord (supply_left={self.bot.supply_left}) ★")
                else:
                    # Fallback: 직접 생산
                    try:
                        if larva:
                            if hasattr(self.bot, 'production') and self.bot.production:
                                await self.bot.production._safe_train(larva.first, UnitTypeId.OVERLORD)
                            else:
                                self.bot.do(larva.first.train(UnitTypeId.OVERLORD))
                            if iteration % 100 == 0:
                                print(f"[UNIT_FACTORY] ★ Preemptive Overlord (supply_left={self.bot.supply_left}) ★")
                    except Exception:
                        pass

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

        # === StrategyManager 실시간 비율 연동 (via Blackboard or Direct) ===
        # 매 스텝마다 전략 매니저의 가스 비율을 가져와서 적용
        strategy_mode = "NORMAL"
        emergency_active = False

        # 1. Try Blackboard first
        if self.blackboard:
            strategy_mode = self.blackboard.get("strategy_mode", "NORMAL")
            emergency_active = self.blackboard.get("is_rush_detected", False)
        
        # 2. Fallback to direct access if Blackboard missing (Backward Compat)
        elif hasattr(self.bot, "strategy_manager") and self.bot.strategy_manager:
            strategy = self.bot.strategy_manager
            strategy_mode = getattr(strategy, "current_mode", "NORMAL")
            # emergency_active handled below

        strategy = getattr(self.bot, "strategy_manager", None) # Still needed for get_unit_ratios until that is moved to Blackboard
        if strategy:
            # Emergency Mode에서는 저글링 위주 생산 (가스 비율 낮춤)
            if emergency_active or getattr(strategy, "emergency_active", False):
                self.gas_unit_ratio_target = 0.15  # 긴급 시 가스 유닛 최소화
            else:
                # ★★★ FIX: 프로토스 핵심 유닛 감지 시 가스 부스트 ★★★
                protoss_threat_boost = self._check_protoss_threat_boost()
                if protoss_threat_boost:
                    self.gas_unit_ratio_target = 0.55  # 히드라/커럽터 우선
                else:
                    # 종족별 유닛 비율에서 가스 유닛 비율 계산
                    ratios = strategy.get_unit_ratios()
                    if ratios:
                        # 가스 유닛: hydra, mutalisk, roach, ravager, corruptor 등
                        gas_ratio = (ratios.get("hydra", 0) + ratios.get("mutalisk", 0) +
                                    ratios.get("roach", 0) + ratios.get("ravager", 0) +
                                    ratios.get("corruptor", 0))
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
                if self.blackboard:
                    self.blackboard.request_production(
                        unit_type=UnitTypeId.OVERLORD,
                        count=1,
                        requester="UnitFactory",
                        priority=0  # URGENT
                    )
                else:
                    # Fallback: 직접 생산
                    try:
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

        # ★★★ Blackboard 통합: 우선순위 큐를 Blackboard에 요청으로 등록 ★★★
        if self.blackboard:
            to_request = min(self.max_larva_spend_per_step, len(larva))

            # 우선순위 큐에서 유닛 타입별로 그룹화
            unit_requests = {}
            for _ in range(to_request):
                unit_type = self._pick_unit(queue)
                if not unit_type:
                    break
                unit_requests[unit_type] = unit_requests.get(unit_type, 0) + 1

            # Blackboard에 생산 요청 등록
            for unit_type, count in unit_requests.items():
                # 전투 모드면 우선순위 높임 (MEDIUM → HIGH)
                priority = 1 if in_combat else 2
                self.blackboard.request_production(
                    unit_type=unit_type,
                    count=count,
                    requester="UnitFactory",
                    priority=priority
                )

            # 디버그 로그
            if iteration % 200 == 0 and unit_requests:
                print(f"[UNIT_FACTORY] Production requested: {unit_requests}")

        else:
            # Fallback: 직접 생산 (Blackboard 없을 때)
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
        # ★ OPTIMIZATION: Morph units (Ravager, Lurker) removed.
        # UnitFactory produces base units (Roach, Hydra) => UnitMorphManager updates them.
        return [
            {"unit": UnitTypeId.HYDRALISK, "min_gas": 50, "max_ratio": 0.5},    # Lurker material
            {"unit": UnitTypeId.CORRUPTOR, "min_gas": 100, "max_ratio": 0.3},
            {"unit": UnitTypeId.MUTALISK, "min_gas": 100, "max_ratio": 0.25},
            {"unit": UnitTypeId.ROACH, "min_gas": 25, "max_ratio": 0.6},        # Ravager material
            {"unit": UnitTypeId.ULTRALISK, "min_gas": 150, "max_ratio": 0.15},
            {"unit": UnitTypeId.INFESTOR, "min_gas": 150, "max_ratio": 0.1},
            {"unit": UnitTypeId.VIPER, "min_gas": 200, "max_ratio": 0.1},
        ]

    def _mineral_unit_table(self) -> List[dict]:
        # Banelings removed (Morphed from Zerglings)
        return [
            {"unit": UnitTypeId.ZERGLING, "max_ratio": 0.9}, # Baneling material included
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

    def _check_protoss_threat_boost(self) -> bool:
        """
        ★★★ 핵심 위협 유닛(공중 주력) 감지 ★★★
        """
        if not hasattr(self.bot, "enemy_units"):
            return False

        threat_units = {
            "IMMORTAL": 1, "VOIDRAY": 1, "COLOSSUS": 1,
            "CARRIER": 1, "ARCHON": 2, "DISRUPTOR": 1,
            "TEMPEST": 1, "BATTLECRUISER": 1, "LIBERATOR": 1
        }

        unit_counts = {}
        found_air_threat = False

        for enemy in self.bot.enemy_units:
            try:
                name = getattr(enemy.type_id, "name", "").upper()
                if name in threat_units:
                    unit_counts[name] = unit_counts.get(name, 0) + 1
                    if name in ["VOIDRAY", "CARRIER", "TEMPEST", "BATTLECRUISER", "LIBERATOR", "COLOSSUS"]:
                        found_air_threat = True
            except Exception:
                continue
                
        if found_air_threat:
             self.gas_unit_ratio_target = 0.60

        for unit_type, threshold in threat_units.items():
            if unit_counts.get(unit_type, 0) >= threshold:
                if self.bot.iteration % 200 == 0:
                    print(f"[UNIT_FACTORY] Threat: {unit_type} x{unit_counts[unit_type]} → Gas Boost!")
                return True

        return False
