# -*- coding: utf-8 -*-
"""
Economy Manager - deterministic worker production with macro hatcheries.
"""

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # Fallbacks for tooling environments

    class UnitTypeId:
        DRONE = "DRONE"
        OVERLORD = "OVERLORD"
        HATCHERY = "HATCHERY"


from local_training.economy_combat_balancer import EconomyCombatBalancer


class EconomyManager:
    """
    Manages economy and larva production.

    Features:
    - Dynamic drone production based on base count
    - Auto supply management
    - Macro hatchery construction when resources stockpile
    - Prevents resource banking by expanding production capacity
    - Gold base prioritization for expansion
    """

    # Gold mineral patch threshold (normal patches have ~900, gold have ~1500+)
    GOLD_MINERAL_THRESHOLD = 1200

    def __init__(self, bot):
        self.bot = bot
        self.balancer = EconomyCombatBalancer(bot)
        # Resource thresholds for macro hatchery
        self.macro_hatchery_mineral_threshold = 1500  # Build macro hatch if minerals > 1500
        self.macro_hatchery_larva_threshold = 3  # and average larva per base < 3
        self.last_macro_hatch_check = 0
        self.macro_hatch_check_interval = 50  # Check every 50 frames
        # Gold base tracking
        self._gold_bases_cache = []
        self._gold_cache_time = 0

    async def on_step(self, iteration: int) -> None:
        if not hasattr(self.bot, "larva"):
            return

        # 게임 시작 초반 일꾼 분할 (첫 10초)
        if iteration < 50:
            await self._optimize_early_worker_split()

        await self._train_overlord_if_needed()
        await self._train_drone_if_needed()

        # Distribute workers to gas (every 11 frames = ~0.5 seconds) - IMPROVED: 더 자주 재분배
        if iteration % 11 == 0:
            await self._distribute_workers_to_gas()

        # Redistribute mineral workers between bases (every 22 frames = ~1 second) - IMPROVED: 더 자주 재분배
        if iteration % 22 == 0:
            await self._redistribute_mineral_workers()

        # PROACTIVE expansion check (every 33 frames = ~1.5 seconds)
        # 10분(600초) 안에 3베이스 확보를 위한 사전 예방적 확장
        if iteration % 33 == 0:
            await self._check_proactive_expansion()

        # Check for expansion needs when resources depleting (every 66 frames = ~3 seconds)
        if iteration % 66 == 0:
            await self._check_expansion_on_depletion()

        # Check for macro hatchery needs periodically
        if iteration - self.last_macro_hatch_check >= self.macro_hatch_check_interval:
            self.last_macro_hatch_check = iteration
            await self._build_macro_hatchery_if_needed()

    async def _optimize_early_worker_split(self) -> None:
        """
        초반 일꾼 분할 최적화.

        게임 시작 시 12기의 일꾼을 8개의 미네랄 패치에 분배:
        - 4개 패치에 2명씩 (8명)
        - 4개 패치에 1명씩 (4명)

        이렇게 하면 멀리 있는 미네랄에도 일꾼이 배치됨.
        """
        if not hasattr(self.bot, "workers") or not hasattr(self.bot, "mineral_field"):
            return

        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return

        workers = self.bot.workers
        if not workers or workers.amount < 12:
            return

        # 이미 분배된 일꾼이 있으면 건너뜀
        if hasattr(self, "_early_split_done") and self._early_split_done:
            return

        main_base = self.bot.townhalls.first
        nearby_minerals = self.bot.mineral_field.closer_than(10, main_base)

        if not nearby_minerals or nearby_minerals.amount < 6:
            return

        # 미네랄을 거리순으로 정렬 (가까운 것부터)
        sorted_minerals = sorted(nearby_minerals, key=lambda m: m.distance_to(main_base))

        # 일꾼 목록 생성
        worker_list = list(workers)

        try:
            assigned_count = 0
            mineral_assignments = {m.tag: 0 for m in sorted_minerals}

            # 1단계: 각 미네랄에 1명씩 배치
            for mineral in sorted_minerals[:8]:  # 최대 8개 패치
                if assigned_count >= len(worker_list):
                    break
                worker = worker_list[assigned_count]
                self.bot.do(worker.gather(mineral))
                mineral_assignments[mineral.tag] = 1
                assigned_count += 1

            # 2단계: 남은 일꾼을 가까운 미네랄에 2번째로 배치
            for mineral in sorted_minerals[:4]:  # 가까운 4개 패치에 추가
                if assigned_count >= len(worker_list):
                    break
                if mineral_assignments[mineral.tag] < 2:
                    worker = worker_list[assigned_count]
                    self.bot.do(worker.gather(mineral))
                    mineral_assignments[mineral.tag] = 2
                    assigned_count += 1

            self._early_split_done = True
            print(f"[ECONOMY] Early worker split completed: {assigned_count} workers distributed")

        except Exception as e:
            pass

    async def _train_overlord_if_needed(self) -> None:
        if not hasattr(self.bot, "supply_left"):
            return

        # 더 공격적인 오버로드 생산: supply_left < 6 으로 조정 (기존 2)
        # 가스가 높으면 더 많은 서플라이 여유분 확보
        gas = getattr(self.bot, "vespene", 0)
        supply_threshold = 6 if gas < 1000 else 10  # 가스 높으면 더 여유롭게

        if self.bot.supply_left >= supply_threshold:
            return

        if not self.bot.can_afford(UnitTypeId.OVERLORD):
            return

        larva_unit = self._get_first_larva()
        if not larva_unit:
            return

        try:
            # Use ProductionResilience._safe_train if available
            if hasattr(self.bot, 'production') and self.bot.production:
                await self.bot.production._safe_train(larva_unit, UnitTypeId.OVERLORD)
            else:
                # Fallback: bot.do() is not async
                self.bot.do(larva_unit.train(UnitTypeId.OVERLORD))
        except Exception:
            return

    async def _train_drone_if_needed(self) -> None:
        # === Emergency Mode Check ===
        # 비상 모드에서는 최소 드론만 유지 (12기)
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy and getattr(strategy, "emergency_active", False):
            worker_count = 0
            if hasattr(self.bot, "workers"):
                workers = self.bot.workers
                worker_count = workers.amount if hasattr(workers, "amount") else len(list(workers))

            if worker_count >= 12:
                # 비상 모드 + 최소 드론 확보 → 드론 생산 중단
                return

        if not self.balancer.should_train_drone():
            return

        if hasattr(self.bot, "supply_left") and self.bot.supply_left <= 0:
            return

        if not self.bot.can_afford(UnitTypeId.DRONE):
            return

        larva_unit = self._get_first_larva()
        if not larva_unit:
            return

        try:
            # Use ProductionResilience._safe_train if available
            if hasattr(self.bot, 'production') and self.bot.production:
                await self.bot.production._safe_train(larva_unit, UnitTypeId.DRONE)
            else:
                # Fallback: use bot.do() without await (it's not async)
                self.bot.do(larva_unit.train(UnitTypeId.DRONE))
        except Exception as e:
            game_time = getattr(self.bot, "time", 0.0)
            print(f"[ECONOMY_WARN] [{int(game_time)}s] Drone train failed: {e}")
            return

    async def _distribute_workers_to_gas(self) -> None:
        """
        Distribute workers to extractors.

        Ensures each extractor has 3 workers for optimal gas mining.
        """
        if not hasattr(self.bot, "gas_buildings"):
            return

        extractors = self.bot.gas_buildings.ready
        if not extractors:
            return

        if not hasattr(self.bot, "workers") or not self.bot.workers:
            return

        for extractor in extractors:
            # Check how many workers are assigned
            assigned_workers = extractor.assigned_harvesters
            ideal_workers = extractor.ideal_harvesters  # Usually 3

            if assigned_workers < ideal_workers:
                # Find idle or mineral-mining workers nearby
                workers_needed = ideal_workers - assigned_workers

                try:
                    # Get workers that are gathering minerals (not gas)
                    available_workers = self.bot.workers.filter(
                        lambda w: (
                            w.is_gathering and
                            not w.is_carrying_vespene and
                            w.distance_to(extractor) < 20
                        )
                    )

                    if not available_workers:
                        # Try idle workers
                        available_workers = self.bot.workers.filter(
                            lambda w: w.is_idle and w.distance_to(extractor) < 20
                        )

                    if available_workers:
                        # Assign closest workers to extractor
                        for _ in range(min(workers_needed, len(available_workers))):
                            worker = available_workers.closest_to(extractor)
                            if worker:
                                self.bot.do(worker.gather(extractor))
                                available_workers = available_workers.filter(
                                    lambda w: w.tag != worker.tag
                                )
                except Exception:
                    continue

    async def _build_macro_hatchery_if_needed(self) -> None:
        """
        Build macro hatchery when resources are stockpiling.

        IMPROVED: 전투 중이면 더 공격적으로 매크로 해처리 건설

        Conditions:
        - Minerals > threshold (전투 중에는 더 낮은 임계값)
        - Average larva per base < threshold
        - Have at least 2 bases
        - Not already building a hatchery
        """
        if not hasattr(self.bot, "minerals") or not hasattr(self.bot, "townhalls"):
            return

        # ★ 전투 모드 체크 - 가스 과잉 시 더 공격적으로 매크로 해처리 건설 ★
        in_combat = False
        gas_overflow = False

        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy and getattr(strategy, "emergency_active", False):
            in_combat = True

        # 가스 과잉 체크 (가스 > 1500이고 라바 < 5)
        gas = getattr(self.bot, "vespene", 0)
        total_larva = len(self.bot.larva) if hasattr(self.bot, "larva") else 0
        if gas > 1500 and total_larva < 5:
            gas_overflow = True

        # Check resource conditions (전투/가스 과잉 시 낮은 임계값)
        minerals = self.bot.minerals
        mineral_threshold = 800 if (in_combat or gas_overflow) else self.macro_hatchery_mineral_threshold

        if minerals < mineral_threshold:
            return

        # Check base count
        townhalls = self.bot.townhalls.ready
        if not townhalls or townhalls.amount < 2:
            return

        # Check larva availability
        avg_larva_per_base = total_larva / max(1, townhalls.amount)

        # 전투/가스 과잉 시 더 높은 라바 임계값 (더 많이 필요)
        larva_threshold = 5 if (in_combat or gas_overflow) else self.macro_hatchery_larva_threshold

        if avg_larva_per_base >= larva_threshold:
            return  # Have enough larva production

        # Check if already building hatchery
        if hasattr(self.bot, "already_pending"):
            pending = self.bot.already_pending(UnitTypeId.HATCHERY)
            # 전투/가스 과잉 시 여러 개 동시 건설 허용
            max_pending = 2 if (in_combat or gas_overflow) else 1
            if pending >= max_pending:
                return

        # Don't build if can't afford
        if not self.bot.can_afford(UnitTypeId.HATCHERY):
            return

        # Find safe build location near main base
        if not hasattr(self.bot, "start_location"):
            return

        main_base = townhalls.first
        build_location = await self._find_macro_hatch_location(main_base)

        if build_location:
            try:
                # Build macro hatchery
                worker = None
                if hasattr(self.bot, "workers") and self.bot.workers:
                    worker = self.bot.workers.closest_to(build_location)

                if worker:
                    self.bot.do(
                        worker.build(UnitTypeId.HATCHERY, build_location)
                    )
                    game_time = getattr(self.bot, "time", 0)
                    reason = "COMBAT/GAS_OVERFLOW" if (in_combat or gas_overflow) else "normal"
                    print(f"[ECONOMY] [{int(game_time)}s] Building MACRO HATCHERY ({reason}, gas: {gas}, larva: {total_larva})")
            except Exception:
                pass

    async def _find_macro_hatch_location(self, main_base):
        """Find safe location for macro hatchery near main base."""
        if not hasattr(self.bot, "can_place"):
            return None

        try:
            # Try positions around main base at distance 8-12
            import math

            for angle in range(0, 360, 45):
                for distance in [8, 10, 12]:
                    rad = math.radians(angle)
                    x_offset = distance * math.cos(rad)
                    y_offset = distance * math.sin(rad)

                    try:
                        # Create Point2 if available
                        if hasattr(main_base.position, "__add__"):
                            test_pos = main_base.position.offset(
                                (x_offset, y_offset)
                            )
                        else:
                            continue

                        # Check if we can place hatchery there
                        if await self.bot.can_place(UnitTypeId.HATCHERY, test_pos):
                            return test_pos
                    except Exception:
                        continue

        except Exception:
            pass

        return None

    async def _redistribute_mineral_workers(self) -> None:
        """
        Redistribute mineral workers between bases.

        - Move workers from over-saturated bases to under-saturated ones
        - Move workers from DEPLETED bases to other bases
        - Detect bases with low/no mineral patches
        - Keep only gas workers at depleted bases with extractors
        - Optimal: 16 workers per base for minerals (2 per patch)

        IMPROVED: 쿨다운 추가, 이동 중인 일꾼 제외, 고갈 조건 완화
        """
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "workers"):
            return

        townhalls = self.bot.townhalls.ready
        if not townhalls or townhalls.amount < 2:
            return  # Need at least 2 bases

        workers = self.bot.workers
        if not workers:
            return

        # 쿨다운 체크 (5초마다만 실행)
        current_time = getattr(self.bot, "time", 0)
        if not hasattr(self, "_last_redistribute_time"):
            self._last_redistribute_time = 0
        if current_time - self._last_redistribute_time < 5.0:
            return
        self._last_redistribute_time = current_time

        try:
            # First: Check for DEPLETED bases (완화: 미네랄 < 2개 또는 총량 < 300)
            depleted_bases = []
            active_bases = []

            for th in townhalls:
                # Count mineral patches near this base
                nearby_minerals = self.bot.mineral_field.closer_than(10, th)
                mineral_count = nearby_minerals.amount if hasattr(nearby_minerals, 'amount') else len(list(nearby_minerals))

                # Count total minerals remaining
                total_minerals = sum(m.mineral_contents for m in nearby_minerals) if nearby_minerals else 0

                # 완화된 조건: 미네랄 < 2개 또는 총량 < 300
                if mineral_count < 2 or total_minerals < 300:
                    # Base is depleted - move workers out
                    depleted_bases.append(th)
                else:
                    active_bases.append(th)

            # Move workers from depleted bases to active bases
            for depleted_th in depleted_bases:
                if not active_bases:
                    break

                # Get IDLE mineral workers at this depleted base (not moving, not carrying)
                # 개선: is_idle 또는 is_gathering하고 있고 가까이 있는 일꾼만
                nearby_workers = workers.filter(
                    lambda w: (w.distance_to(depleted_th) < 8 and  # 거리 줄임 (15 -> 8)
                              (w.is_idle or (w.is_gathering and not w.is_moving)) and
                              not w.is_carrying_vespene and
                              not any(e.distance_to(w) < 3 for e in self.bot.gas_buildings))
                )

                if not nearby_workers or nearby_workers.amount < 2:  # 최소 2명 이상만
                    continue

                # Find best target base (closest active base with capacity)
                best_target = None
                best_deficit = 0
                for active_th in active_bases:
                    assigned = active_th.assigned_harvesters
                    ideal = active_th.ideal_harvesters
                    deficit = ideal - assigned
                    if deficit > best_deficit:
                        best_deficit = deficit
                        best_target = active_th

                if not best_target:
                    # All bases full - use closest
                    best_target = min(active_bases, key=lambda th: th.distance_to(depleted_th))

                # Move workers to target base (최대 3명으로 줄임)
                workers_moved = 0
                for worker in nearby_workers:
                    if workers_moved >= 3:  # Max 3 at a time (5 -> 3)
                        break

                    minerals = self.bot.mineral_field.closer_than(10, best_target)
                    if minerals:
                        try:
                            self.bot.do(worker.gather(minerals.closest_to(best_target)))
                            workers_moved += 1
                        except Exception:
                            continue

                if workers_moved > 0:
                    print(f"[ECONOMY] [{int(current_time)}s] Moved {workers_moved} workers from depleted base")

            # Second: Normal redistribution for over/under-saturated bases
            over_saturated = []
            under_saturated = []

            for th in active_bases:  # Only check active bases
                assigned = th.assigned_harvesters
                ideal = th.ideal_harvesters  # Usually 16 for minerals

                if assigned > ideal + 2:  # Over by more than 2
                    over_saturated.append((th, assigned - ideal))
                elif assigned < ideal - 2:  # Under by more than 2
                    under_saturated.append((th, ideal - assigned))

            # Move workers from over-saturated to under-saturated
            for over_th, excess in over_saturated:
                if not under_saturated:
                    break

                # Get workers near this townhall
                nearby_workers = workers.filter(
                    lambda w: w.distance_to(over_th) < 15 and w.is_gathering
                )

                for under_th, deficit in under_saturated[:]:
                    if excess <= 0 or deficit <= 0:
                        continue

                    # Move workers
                    workers_to_move = min(excess, deficit, 3)  # Max 3 at a time
                    for _ in range(workers_to_move):
                        if not nearby_workers:
                            break

                        worker = nearby_workers.furthest_to(over_th)
                        if worker:
                            # Find mineral field near target base
                            minerals = self.bot.mineral_field.closer_than(10, under_th)
                            if minerals:
                                self.bot.do(worker.gather(minerals.closest_to(under_th)))
                                nearby_workers = nearby_workers.filter(
                                    lambda w: w.tag != worker.tag
                                )
                                excess -= 1
                                deficit -= 1

                    # Update under-saturated list
                    if deficit <= 0:
                        under_saturated.remove((under_th, deficit))

        except Exception:
            pass

    def _get_first_larva(self):
        larva = getattr(self.bot, "larva", None)
        if not larva:
            return None
        if hasattr(larva, "first"):
            return larva.first
        try:
            return next(iter(larva))
        except Exception:
            return None

    async def _check_proactive_expansion(self) -> None:
        """
        Proactive expansion based on timing - 10분 안에 3베이스 확보.

        Timing targets:
        - Natural (2nd base): 30-60초 (드론 13-14마리 때)
        - 3rd base: 240-300초 (4-5분)
        - 4th base: 360-420초 (6-7분)

        Pro Zerg players expand PROACTIVELY, not reactively.
        """
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "time"):
            return

        townhalls = self.bot.townhalls
        game_time = self.bot.time  # 게임 시간 (초)
        base_count = townhalls.amount if hasattr(townhalls, "amount") else len(list(townhalls))

        # 확장 타이밍 체크
        should_expand = False
        expand_reason = ""

        # 1베이스 → 2베이스 (내츄럴): 30초 이후, 드론 13마리 이상
        if base_count == 1:
            worker_count = self.bot.workers.amount if hasattr(self.bot, "workers") else 0
            if game_time >= 30 and worker_count >= 13:
                should_expand = True
                expand_reason = f"Natural expansion (time: {int(game_time)}s, workers: {worker_count})"

        # 2베이스 → 3베이스: 240초(4분) 이후
        elif base_count == 2:
            if game_time >= 240:  # 4분
                should_expand = True
                expand_reason = f"3rd base timing (time: {int(game_time)}s)"

        # 3베이스 → 4베이스: 360초(6분) 이후
        elif base_count == 3:
            if game_time >= 360:  # 6분
                should_expand = True
                expand_reason = f"4th base timing (time: {int(game_time)}s)"

        # 4베이스 이상: 480초(8분) 이후, 또는 미네랄 > 800
        elif base_count >= 4:
            minerals = self.bot.minerals if hasattr(self.bot, "minerals") else 0
            if game_time >= 480 or minerals > 800:
                should_expand = True
                expand_reason = f"5th+ base (time: {int(game_time)}s, minerals: {minerals})"

        if not should_expand:
            return

        # 이미 확장 중인지 확인
        if hasattr(self.bot, "already_pending"):
            pending = self.bot.already_pending(UnitTypeId.HATCHERY)
            if pending > 0:
                return

        # 비용 확인
        if not self.bot.can_afford(UnitTypeId.HATCHERY):
            return

        # 공격 받고 있는지 확인 (2베이스 이후에만)
        if base_count >= 2:
            strategy = getattr(self.bot, "strategy_manager", None)
            if strategy and getattr(strategy, "emergency_active", False):
                return  # 비상 모드에서는 확장 중단

        # 확장 실행 (황금 기지 우선)
        try:
            # 황금 기지 우선 확장 시도
            gold_pos = await self._get_best_expansion_with_gold_priority()
            if gold_pos:
                if hasattr(self.bot, "workers") and self.bot.workers:
                    worker = self.bot.workers.closest_to(gold_pos)
                    if worker:
                        self.bot.do(worker.build(UnitTypeId.HATCHERY, gold_pos))
                        is_gold = self._is_gold_expansion(gold_pos)
                        gold_tag = " [GOLD!]" if is_gold else ""
                        print(f"[PROACTIVE EXPAND] [{int(game_time)}s] {expand_reason}{gold_tag}")
                        return
            # 폴백: expand_now 사용
            if hasattr(self.bot, "expand_now"):
                await self.bot.expand_now()
                print(f"[PROACTIVE EXPAND] [{int(game_time)}s] {expand_reason}")
        except Exception as e:
            pass  # Silently fail

    async def _check_expansion_on_depletion(self) -> None:
        """
        Check if we need to expand due to resource depletion.

        ★ IMPROVED: 자원 고갈 사전 감지 및 조기 확장 ★

        Triggers expansion if:
        - Total remaining minerals across bases < threshold
        - Worker saturation is high but income is dropping
        - No expansion currently pending
        - ★ NEW: 특정 기지의 미네랄이 50% 미만일 때 미리 확장
        """
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "mineral_field"):
            return

        townhalls = self.bot.townhalls.ready
        if not townhalls:
            return

        try:
            # Calculate total remaining minerals across all bases
            total_remaining_minerals = 0
            depleted_base_count = 0
            low_mineral_base_count = 0  # ★ 미네랄 50% 미만 기지 ★

            for th in townhalls:
                nearby_minerals = self.bot.mineral_field.closer_than(10, th)
                base_minerals = sum(m.mineral_contents for m in nearby_minerals) if nearby_minerals else 0
                total_remaining_minerals += base_minerals

                if base_minerals < 500:  # Less than 500 minerals = depleted
                    depleted_base_count += 1
                elif base_minerals < 3000:  # ★ 3000 미만 = 50% 고갈 (full은 ~6000) ★
                    low_mineral_base_count += 1

            # Calculate threshold based on worker count
            worker_count = self.bot.workers.amount if hasattr(self.bot, "workers") else 0
            # Need ~1500 minerals per 16 workers for decent income
            mineral_threshold_per_worker = 100
            expansion_threshold = worker_count * mineral_threshold_per_worker

            # Check if we need to expand
            should_expand = False
            expand_reason = ""

            # ★ NEW: Reason 0: 미네랄 50% 미만 기지가 있으면 사전 확장 ★
            if low_mineral_base_count >= 1 and townhalls.amount >= 2:
                should_expand = True
                expand_reason = f"PREEMPTIVE: {low_mineral_base_count} bases below 50% minerals"

            # Reason 1: Total minerals running low
            if total_remaining_minerals < expansion_threshold and total_remaining_minerals < 5000:
                should_expand = True
                expand_reason = f"low minerals ({int(total_remaining_minerals)} remaining)"

            # Reason 2: Multiple depleted bases
            if depleted_base_count >= townhalls.amount // 2 and townhalls.amount > 1:
                should_expand = True
                expand_reason = f"{depleted_base_count}/{townhalls.amount} bases depleted"

            # Reason 3: High worker count but low base count
            # Optimal: ~16 workers per base
            optimal_bases = max(1, worker_count // 16)
            if townhalls.amount < optimal_bases:
                should_expand = True
                expand_reason = f"need more bases for {worker_count} workers"

            # ★ NEW: Reason 4: 일꾼이 포화인데 기지가 부족 ★
            if hasattr(self.bot, "townhalls"):
                total_ideal = sum(th.ideal_harvesters for th in townhalls)
                if worker_count >= total_ideal * 0.9 and townhalls.amount < 5:
                    should_expand = True
                    expand_reason = f"workers saturated ({worker_count}/{total_ideal}), need more bases"

            if not should_expand:
                return

            # Check if already expanding
            if self.bot.already_pending(UnitTypeId.HATCHERY) > 0:
                return

            # Check if we can afford expansion
            if not self.bot.can_afford(UnitTypeId.HATCHERY):
                return

            # ★ 공격 받고 있으면 확장 지연 (단, 심각한 고갈은 예외) ★
            strategy = getattr(self.bot, "strategy_manager", None)
            if strategy and getattr(strategy, "emergency_active", False):
                if depleted_base_count < townhalls.amount // 2:
                    return  # 비상 모드에서는 확장 중단 (심각한 고갈 제외)

            # Try to expand
            if hasattr(self.bot, "expand_now"):
                try:
                    await self.bot.expand_now()
                    game_time = getattr(self.bot, "time", 0)
                    print(f"[ECONOMY] [{int(game_time)}s] ★ Expanding: {expand_reason} ★")
                except Exception:
                    pass
            elif hasattr(self.bot, "get_next_expansion"):
                try:
                    next_pos = await self.bot.get_next_expansion()
                    if next_pos:
                        await self.bot.build(UnitTypeId.HATCHERY, near=next_pos)
                        game_time = getattr(self.bot, "time", 0)
                        print(f"[ECONOMY] [{int(game_time)}s] ★ Expanding: {expand_reason} ★")
                except Exception:
                    pass

        except Exception:
            pass

    def _is_gold_expansion(self, position) -> bool:
        """
        Check if an expansion location has gold minerals.

        Gold patches have ~1500 minerals vs normal ~900.
        """
        if not hasattr(self.bot, "mineral_field"):
            return False

        try:
            nearby_minerals = self.bot.mineral_field.closer_than(10, position)
            if not nearby_minerals:
                return False

            # Check if any mineral patch is gold (>1200 minerals)
            for mineral in nearby_minerals:
                if mineral.mineral_contents > self.GOLD_MINERAL_THRESHOLD:
                    return True
            return False
        except Exception:
            return False

    def _get_gold_expansion_locations(self) -> list:
        """
        Get all expansion locations with gold minerals.

        Returns list of (position, gold_mineral_count) tuples sorted by priority.
        """
        if not hasattr(self.bot, "expansion_locations_list"):
            return []

        current_time = getattr(self.bot, "time", 0)

        # 캐시 사용 (30초마다 갱신)
        if current_time - self._gold_cache_time < 30 and self._gold_bases_cache:
            return self._gold_bases_cache

        gold_expansions = []

        try:
            # Get already taken expansion positions
            taken_positions = set()
            if hasattr(self.bot, "townhalls"):
                for th in self.bot.townhalls:
                    taken_positions.add(th.position)

            # Check enemy bases
            enemy_expansions = set()
            if hasattr(self.bot, "enemy_structures"):
                for struct in self.bot.enemy_structures:
                    if hasattr(struct, "is_structure") and struct.is_structure:
                        enemy_expansions.add(struct.position)

            for exp_pos in self.bot.expansion_locations_list:
                # Skip already taken positions
                if any(exp_pos.distance_to(taken) < 5 for taken in taken_positions):
                    continue

                # Skip enemy positions
                if any(exp_pos.distance_to(enemy) < 10 for enemy in enemy_expansions):
                    continue

                # Check for gold minerals
                nearby_minerals = self.bot.mineral_field.closer_than(10, exp_pos)
                if not nearby_minerals:
                    continue

                gold_count = 0
                total_minerals = 0
                for mineral in nearby_minerals:
                    if mineral.mineral_contents > self.GOLD_MINERAL_THRESHOLD:
                        gold_count += 1
                    total_minerals += mineral.mineral_contents

                if gold_count > 0:
                    # Priority: gold count * 1000 + total minerals
                    priority = gold_count * 1000 + total_minerals
                    gold_expansions.append((exp_pos, gold_count, total_minerals, priority))

            # Sort by priority (highest first)
            gold_expansions.sort(key=lambda x: x[3], reverse=True)

            # Cache results
            self._gold_bases_cache = gold_expansions
            self._gold_cache_time = current_time

            return gold_expansions

        except Exception:
            return []

    async def _get_best_expansion_with_gold_priority(self):
        """
        Get the best expansion location, prioritizing gold bases.

        Priority order:
        1. Gold base closest to our main base (safe gold)
        2. Normal expansion from get_next_expansion()
        """
        if not hasattr(self.bot, "start_location"):
            return None

        try:
            our_base = self.bot.start_location
            enemy_base = None
            if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
                enemy_base = self.bot.enemy_start_locations[0]

            # Get gold expansion locations
            gold_expansions = self._get_gold_expansion_locations()

            if gold_expansions:
                # Calculate safety score for each gold base
                best_gold = None
                best_score = float('-inf')

                for exp_pos, gold_count, total_minerals, _ in gold_expansions:
                    # Safety score: closer to our base is safer
                    dist_to_us = exp_pos.distance_to(our_base)
                    dist_to_enemy = exp_pos.distance_to(enemy_base) if enemy_base else 100

                    # Score: prefer closer to us, farther from enemy
                    # Gold count bonus: +50 per gold patch
                    safety_score = (dist_to_enemy - dist_to_us) + (gold_count * 50)

                    # Early game (< 5 minutes): prioritize safety more
                    game_time = getattr(self.bot, "time", 0)
                    if game_time < 300:  # 5분 이전
                        # Only consider if closer to us than enemy
                        if dist_to_us < dist_to_enemy:
                            if safety_score > best_score:
                                best_score = safety_score
                                best_gold = exp_pos
                    else:
                        # After 5 minutes: can take riskier gold bases
                        if safety_score > best_score:
                            best_score = safety_score
                            best_gold = exp_pos

                if best_gold:
                    # Verify we can place hatchery there
                    if hasattr(self.bot, "can_place"):
                        if await self.bot.can_place(UnitTypeId.HATCHERY, best_gold):
                            return best_gold

            # Fallback: use standard expansion
            if hasattr(self.bot, "get_next_expansion"):
                return await self.bot.get_next_expansion()

            return None

        except Exception:
            # Fallback on error
            if hasattr(self.bot, "get_next_expansion"):
                return await self.bot.get_next_expansion()
            return None
