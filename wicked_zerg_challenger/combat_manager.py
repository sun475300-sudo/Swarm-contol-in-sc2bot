# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from wicked_zerg_bot_pro import WickedZergBotPro

import json
import math
import os
import traceback

from sc2.data import Race  # type: ignore
from sc2.ids.ability_id import AbilityId  # type: ignore
from sc2.ids.unit_typeid import UnitTypeId  # type: ignore
from sc2.position import Point2  # type: ignore
from sc2.unit import Unit  # type: ignore

from config import TARGET_PRIORITY, Config, GamePhase

class CombatManager:
    def __init__(self, bot: "WickedZergBotPro"):
        self.bot = bot
        self.config = Config()

        self.rally_point: Optional[Point2] = None
        self.attack_target: Optional[Point2] = None
        self.current_win_rate: float = 50.0
        self.win_rate_threshold: float = 45.0
        self.retreat_threshold: float = 45.0
        self.advance_threshold: float = 50.0

        self.is_attacking: bool = False
        self.is_retreating: bool = False
        self.army_gathered: bool = False
        self.initial_army_count: int = 0
        self.current_army_count: int = 0
        self.previous_army_count: int = 0
        self.army_loss_threshold: float = 0.3
        self.regrouping_after_loss: bool = False
        self.regroup_start_time: float = 0.0
        self.harass_squad: List[Unit] = []
        self.harass_target: Optional[Point2] = None
        self.combat_mode: str = "CAUTIOUS"
        self.last_mode_update: int = 0
        self.personality: str = "NEUTRAL"
        self.last_personality_chat: int = 0
        self.personality_chat_interval: int = 450
        self.curriculum_level_idx = self._load_curriculum_level()

    def _load_curriculum_level(self) -> int:
        try:
            stats_file = os.path.join("data", "training_stats.json")
            if os.path.exists(stats_file):
                with open(stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    level_idx = data.get("curriculum_level_idx", 0)
                    if 0 <= level_idx <= 5:
                        return level_idx
        except Exception:
            pass
        return 0

    def _should_relax_retreat_conditions(self) -> bool:
        return self.curriculum_level_idx <= 1

    def initialize(self):
        b = self.bot
        try:
            if b.townhalls.exists:
                townhalls = [th for th in b.townhalls]
                if townhalls:
                    self.rally_point = townhalls[0].position.towards(b.game_info.map_center, 15)
                else:
                    self.rally_point = b.game_info.map_center
            else:
                try:
                    self.rally_point = b.game_info.map_center
                except:
                    self.rally_point = b.start_location if hasattr(b, "start_location") else None
        except Exception as e:
            try:
                self.rally_point = b.start_location if hasattr(b, "start_location") else b.game_info.map_center
            except:
                self.rally_point = None
            if self.rally_point is None:
                print(f"[WARNING] Failed to set rally point: {e}")

        try:
            if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                self.attack_target = b.enemy_start_locations[0]
            else:
                # Micro Ladder: Use map center as attack target
                try:
                    self.attack_target = b.game_info.map_center
                except:
                    self.attack_target = None
        except Exception as e:
            print(f"[WARNING] Failed to set attack target: {e}")
            self.attack_target = None

    async def update(self, game_phase: GamePhase, context: dict):
        b = self.bot
        intel = getattr(b, "intel", None)
        if intel and intel.cached_military is not None:
            self._cached_army_units = intel.cached_military
        else:
            self._cached_army_units = (
                b.units.filter(lambda u: u.type_id in b.combat_unit_types and u.is_ready)
                if hasattr(b, "combat_unit_types")
                else b.units
            )

        current_iteration = getattr(b, "iteration", 0)
        if current_iteration - self.last_mode_update >= 10:
            self._determine_combat_mode()
            self.last_mode_update = current_iteration

        self._update_army_status()
        self._update_win_rate()

        win_rate = getattr(b, "last_calculated_win_rate", self.current_win_rate)
        self.current_win_rate = win_rate
        can_attrit_enemy = self._can_attrit_enemy_units()

        if self.is_retreating:
            should_retreat = win_rate < self.advance_threshold and not can_attrit_enemy
        else:
            should_retreat = win_rate < self.retreat_threshold and not can_attrit_enemy

        if should_retreat:
            if not self.is_retreating:
                self.is_retreating = True
                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 448 == 0:
                    if hasattr(b, "personality_manager"):
                        from personality_manager import ChatPriority
                        await b.personality_manager.send_chat(
                            f"⚠️ 승률 {win_rate:.0f}%... 지금은 승산이 없습니다. 병력을 보존하기 위해 후퇴합니다.",
                            priority=ChatPriority.MEDIUM
                        )
            await self._execute_smart_retreat()
            await self._visualize_retreat_status(b, True)
            return
        else:
            if self.is_retreating:
                self.is_retreating = False
                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 448 == 0:
                    if hasattr(b, "personality_manager"):
                        if self.personality == "AGGRESSIVE":
                            await b.personality_manager.send_chat(
                                f"🔥 [공격적] 적의 방어선이 약해졌군요! 승률 {win_rate:.0f}%로 지금 바로 진격하겠습니다!",
                                priority=ChatPriority.MEDIUM
                            )
                        else:
                            await b.personality_manager.send_chat(
                                f"⚔️ 전열 재정비 완료! 승률 {win_rate:.0f}%로 반격을 시작합니다.",
                                priority=ChatPriority.MEDIUM
                            )
                await self._visualize_retreat_status(b, False)

        if await self._check_and_defend_with_workers():
            return

        self._check_army_gathered()

        if self.regrouping_after_loss:
            await self._rally_army()
            return

        if self._should_retreat():
            await self._execute_retreat()
            return

        if self._should_attack(game_phase, context):
            await self._execute_attack()
        else:
            await self._rally_army()

        await self._harass_enemy()
        await self._micro_units()

        # CRITICAL: Spell unit control is handled by SpellUnitManager (every 16 frames)
        # This reduces CPU load and allows proper spell cooldown management
        # Spell units are not controlled here to avoid duplicate control

    def _determine_combat_mode(self):
        b = self.bot

        try:
            workers = [w for w in b.workers] if b.workers.exists else []
            worker_count = len(workers)
            supply_cap = b.supply_cap

            eco_stability = min(1.0, worker_count / 30.0)

            # IMPROVED: Adjust aggression based on win rate
            # If win rate is low (below 30%), be more aggressive to improve performance
            win_rate = getattr(b, "last_calculated_win_rate", 50.0)
            low_win_rate_penalty = win_rate < 30.0  # Below 30% win rate

            if worker_count < 10:
                new_mode = "DEFENSIVE"
            elif worker_count >= 30 or supply_cap >= 100:
                new_mode = "AGGRESSIVE"
            elif low_win_rate_penalty and worker_count >= 16:
                # IMPROVED: Force AGGRESSIVE mode when win rate is low and we have enough workers
                new_mode = "AGGRESSIVE"
                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 100 == 0:
                    print(f"[COMBAT MODE] [{int(b.time)}s] Low win rate ({win_rate:.1f}%) - forcing AGGRESSIVE mode")
            else:
                new_mode = "CAUTIOUS"

            if new_mode != self.combat_mode:
                self.combat_mode = new_mode
                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 100 == 0:
                    print(
                        f"[COMBAT MODE] [{int(b.time)}s] Mode changed to {new_mode} (Workers: {worker_count}, Supply: {supply_cap}, Win Rate: {win_rate:.1f}%, Eco Stability: {eco_stability:.2f})"
                    )

        except Exception as e:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 100 == 0:
                print(f"[WARNING] Failed to determine combat mode: {e}")

    def _update_army_status(self):
        """Update army status (performance optimized + unit loss detection)"""
        b = self.bot

        self.current_army_count = b.supply_army

        if self.is_attacking and self.initial_army_count == 0:
            self.initial_army_count = self.current_army_count

        if not self.regrouping_after_loss and self.previous_army_count > 0:
            if self.current_army_count < self.previous_army_count:
                loss_amount = self.previous_army_count - self.current_army_count
                loss_ratio = (
                    loss_amount / self.previous_army_count if self.previous_army_count > 0 else 0.0
                )

                if loss_ratio >= self.army_loss_threshold:
                    self.regrouping_after_loss = True
                    self.regroup_start_time = b.time
                    self.is_attacking = False
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 50 == 0:
                        print(
                            f"[ARMY LOSS] [{int(b.time)}s] Significant army loss detected ({loss_amount} supply, {loss_ratio * 100:.1f}%) - Regrouping!"
                        )

        if self.regrouping_after_loss:
            time_since_regroup = b.time - self.regroup_start_time
            min_army_threshold = (
                max(40, int(self.previous_army_count * 0.7)) if self.previous_army_count > 0 else 40
            )

            if time_since_regroup >= 10:
                if self.army_gathered and self.current_army_count >= min_army_threshold:
                    self.regrouping_after_loss = False
                    self.initial_army_count = 0
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 50 == 0:
                        print(
                            f"[ARMY REGROUP] [{int(b.time)}s] Regrouping complete! Army: {self.current_army_count} supply (Threshold: {min_army_threshold})"
                        )
                elif (
                    time_since_regroup > 60
                ):  # Intelligent timeout: Assess situation after 60 seconds (prevent infinite waiting)
                    # Assess if regrouping is still beneficial or if we should resume operations
                    # Check if we have enough units to be effective, or if enemy is attacking
                    enemy_attacking = False
                    try:
                        if hasattr(b, "known_enemy_units"):
                            known_enemy = getattr(b, "known_enemy_units", None)
                            if (
                                known_enemy
                                and hasattr(known_enemy, "exists")
                                and known_enemy.exists
                            ):
                                threat_range_squared = 50 * 50  # 50^2 = 2500
                                enemy_nearby = [
                                    e
                                    for e in known_enemy
                                    if e.distance_to_squared(b.start_location)
                                    < threat_range_squared
                                ]
                                if enemy_nearby:
                                    enemy_attacking = True
                    except (AttributeError, TypeError):
                        pass

                    # Resume operations if enemy is attacking or if we have reasonable army size
                    should_resume = (
                        enemy_attacking or self.current_army_count >= min_army_threshold * 0.7
                    )

                    if (
                        should_resume or time_since_regroup > 90
                    ):  # Force resume after 90 seconds regardless
                        self.regrouping_after_loss = False
                        self.initial_army_count = 0
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 50 == 0:
                            reason = (
                                "Enemy attacking"
                                if enemy_attacking
                                else "Sufficient army"
                                if self.current_army_count >= min_army_threshold * 0.7
                                else "Timeout"
                            )
                            print(
                                f"[ARMY REGROUP] [{int(b.time)}s] Regrouping complete - Resuming operations ({reason}). Army: {self.current_army_count} supply"
                            )

        self.previous_army_count = self.current_army_count

    def _check_army_gathered(self):
        """
        병력 집결 상태 체크

        💡 집결 완료 조건:
            병력의 80% 이상이 집결지 반경 15 내에 있을 때
        """
        b = self.bot

        if not self.rally_point:
            self.army_gathered = False
            return

        army = self._get_army_units()
        if not army:
            self.army_gathered = False
            return

        rally_squared = 15 * 15  # 15^2 = 225
        near_rally = [u for u in army if u.distance_to_squared(self.rally_point) < rally_squared]
        gather_ratio = len(near_rally) / len(army) if army else 0

        self.army_gathered = gather_ratio >= max(0.65, self.config.RALLY_GATHER_PERCENT * 0.9)

    def _should_retreat(self) -> bool:
        """
        퇴각 여부 판단

        💡 퇴각 조건:
            공격 중 병력 손실율이 임계값을 넘으면 퇴각

        Curriculum Learning: 난이도가 낮을 때 퇴각 조건 완화
        - VeryEasy, Easy: 손실율 70% 이상에서만 퇴각 (적극적으로 싸우며 데이터 쌓기)
        - Medium 이상: 손실율 50% 이상에서 퇴각 (정상 동작)

        Returns:
            bool: 퇴각해야 하면 True
        """
        if not self.is_attacking:
            return False

        if self.initial_army_count == 0:
            return False

        loss_threshold = 0.5
        if self._should_relax_retreat_conditions():
            loss_threshold = 0.7

        loss_ratio = 1 - (self.current_army_count / self.initial_army_count)

        if loss_ratio >= loss_threshold:
            if not self._should_relax_retreat_conditions():
                print(f"⚠️ [{int(self.bot.time)}초] 손실율 {loss_ratio * 100:.0f}%! 퇴각 명령")
            return True

        return False

    async def _execute_retreat(self):
        b = self.bot

        self.is_retreating = True
        self.is_attacking = False
        self.initial_army_count = 0

        army = self._get_army_units()

        townhalls = [th for th in b.townhalls]
        if not townhalls:
            return

        sorted_army = sorted(army, key=lambda u: getattr(u, "health_percentage", 1.0))

        for unit in sorted_army:
            enemy_units = getattr(b, "enemy_units", [])
            if enemy_units:
                # IMPROVED: Use closer_than API for performance (O(n) instead of O(n²))
                if hasattr(enemy_units, 'closer_than'):
                    very_close_enemies = list(enemy_units.closer_than(3.0, unit.position))
                else:
                    very_close_enemies = [e for e in enemy_units if unit.distance_to(e) < 3.0]
                if very_close_enemies:
                    # IMPROVED: Use distance_to_squared if available, else distance_to ** 2
                    if hasattr(unit, 'distance_to_squared'):
                        closest_enemy = min(very_close_enemies, key=lambda e: unit.distance_to_squared(e))
                    else:
                        closest_enemy = min(very_close_enemies, key=lambda e: unit.distance_to(e) ** 2)
                    await b.do(unit.attack(closest_enemy))
                    continue

            if townhalls:
                closest_base = min(townhalls, key=lambda th: unit.distance_to(th) ** 2)
                await b.do(unit.move(closest_base.position))
        if townhalls and len(townhalls) > 0:
            self.rally_point = townhalls[0].position.towards(b.start_location, -5)

    async def _check_and_defend_with_workers(self) -> bool:
        b = self.bot

        try:
            my_army = b.units.filter(lambda u: u.type_id in b.combat_unit_types)
            if my_army.exists and my_army.amount > 0:
                return False

            if not b.townhalls.exists:
                return False

            main_base = b.townhalls.first
            if not main_base:
                return False

            base_radius_squared = 30 * 30
            enemies_near_base = []
            for e in b.enemy_units:
                # Use distance_to() ** 2 for API compatibility (works in all python-sc2 versions)
                if e.distance_to(main_base.position) ** 2 < base_radius_squared:
                    enemies_near_base.append(e)
            if not enemies_near_base:
                return False

            army_units = self._get_army_units()
            has_army = len(army_units) > 0

            if has_army:
                for unit in army_units:
                    if enemies_near_base:
                        closest_enemy = min(
                            enemies_near_base,
                            key=lambda e: unit.distance_to_squared(e)
                            if hasattr(unit, "distance_to_squared")
                            else unit.distance_to(e),
                        )
                        await b.do(unit.attack(closest_enemy))
                # CRITICAL: Return False to allow army production to continue
                # Army defense doesn't block production
                return False

            workers = b.workers.ready
            if workers.exists:
                worker_count = workers.amount
                if worker_count > 5:
                    defense_worker_count = min(max(3, worker_count // 3), 10)
                    defense_workers = list(workers)[:defense_worker_count]

                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 22 == 0:
                        print(
                            f"[DEFENSE] ⚠️ 병력 없음! 일꾼 {len(defense_workers)}기 동원하여 방어 중..."
                        )

                    # CRITICAL FIX: Workers NO LONGER ATTACK - Only retreat to safety
                    # Workers should gather resources, not fight. Army units should handle defense.
                    for worker in defense_workers:
                        try:
                            nearest_townhall = (
                                b.townhalls.closest_to(worker.position)
                                if b.townhalls.exists
                                else None
                            )
                            if nearest_townhall:
                                # Move behind townhall (safe position)
                                safe_pos = nearest_townhall.position.towards(b.start_location, 5)
                                await b.do(worker.move(safe_pos))
                            else:
                                # No townhall, gather nearest mineral
                                if b.mineral_field.exists:
                                    closest_mineral = b.mineral_field.closest_to(worker.position)
                                    if closest_mineral:
                                        await b.do(worker.gather(closest_mineral))
                        except Exception:
                            pass
                    return False
                else:
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 22 == 0:
                        print(f"[DEFENSE] 🚨 비상! 일꾼 {worker_count}기 모두 동원하여 방어 중...")

                    # CRITICAL FIX: Workers NO LONGER ATTACK - Only retreat to safety
                    # Workers should gather resources, not fight. Army units should handle defense.
                    for worker in workers:
                        try:
                            nearest_townhall = (
                                b.townhalls.closest_to(worker.position)
                                if b.townhalls.exists
                                else None
                            )
                            if nearest_townhall:
                                # Move behind townhall (safe position)
                                safe_pos = nearest_townhall.position.towards(b.start_location, 5)
                                await b.do(worker.move(safe_pos))
                            else:
                                # No townhall, gather nearest mineral
                                if b.mineral_field.exists:
                                    closest_mineral = b.mineral_field.closest_to(worker.position)
                                    if closest_mineral:
                                        await b.do(worker.gather(closest_mineral))
                        except Exception:
                            pass
                    return False

            return False

        except Exception as e:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[ERROR] _check_and_defend_with_workers 오류: {e}")
            return False

    def _should_attack(self, game_phase: GamePhase, context: dict) -> bool:
        """
        공격 여부 판단 (Economic-Driven + Serral 스타일)

        NOTE: No rush mode - Don't attack in early game (first 4 minutes)

        💡 공격 조건:
            1. Economic-Driven Combat Mode에 따른 제약
               - DEFENSIVE: 본진 수비만 (공격 불가)
               - CAUTIOUS: 조건부 공격 (집결 완료 + 최소 병력)
               - AGGRESSIVE: 적극적 공격
            2. IntelManager의 should_attack() 결과 (Serral 트리거)
            3. 병력이 집결 완료 (80% 이상)
            4. 저글링 20기 이상 또는 총 서플라이 60 이상
            5. 방어 모드가 아닐 때

        Args:
            game_phase: 현재 게임 단계
            context: 매니저 간 공유 데이터

        Returns:
            bool: 공격해야 하면 True
        """
        b = self.bot

        try:
            # Check if we need to defend (enemies near our bases)
            intel = getattr(b, "intel", None)  # type: ignore
            if intel:
                # Check if under attack
                if (
                    hasattr(intel, "combat")
                    and hasattr(intel.combat, "under_attack")
                    and intel.combat.under_attack
                ):
                    return False  # Defend first, don't attack

                # Check if enemy is attacking our bases
                if hasattr(intel, "signals") and isinstance(intel.signals, dict):
                    if intel.signals.get("enemy_attacking_our_bases", False):
                        return False  # Defend first when enemy is attacking our bases

            # Check game phase - if DEFENSE mode, don't attack
            if game_phase == GamePhase.DEFENSE:
                return False

            if self.regrouping_after_loss:
                return False

            # Safe access to mid_game_strong_build_active attribute
            mid_game_build_active = getattr(b, "mid_game_strong_build_active", False)
            if mid_game_build_active:
                intel = getattr(b, "intel", None)
                if intel and intel.cached_roaches is not None:
                    roaches = intel.cached_roaches
                else:
                    roaches = b.units(UnitTypeId.ROACH)

                if intel and intel.cached_hydralisks is not None:
                    hydralisks = intel.cached_hydralisks
                else:
                    hydralisks = b.units(UnitTypeId.HYDRALISK)

                # Ravagers, Lurkers, Banelings are not cached, use direct access
                ravagers = b.units(UnitTypeId.RAVAGER)
                lurkers = b.units(UnitTypeId.LURKER)
                banelings = b.units(UnitTypeId.BANELING)

                roach_count = roaches.amount if hasattr(roaches, "amount") else len(list(roaches))
                hydra_count = (
                    hydralisks.amount if hasattr(hydralisks, "amount") else len(list(hydralisks))
                )
                ravager_count = (
                    ravagers.amount if hasattr(ravagers, "amount") else len(list(ravagers))
                )
                lurker_count = lurkers.amount if hasattr(lurkers, "amount") else len(list(lurkers))
                baneling_count = (
                    banelings.amount if hasattr(banelings, "amount") else len(list(banelings))
                )

                total_strong_units = (
                    roach_count + hydra_count + ravager_count + lurker_count + baneling_count
                )

                if total_strong_units >= 8 or b.supply_army >= 50:
                    if self.army_gathered or b.supply_army >= 60:
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 50 == 0:
                            print(
                                f"[MID-GAME ATTACK] [{int(b.time)}s] Strong build active - Attacking! (Strong units: {total_strong_units}, Supply: {b.supply_army})"
                            )
                        return True
                    else:
                        return False

            # Get opponent race from bot or context
            opponent_race = None
            bot_opponent_race = getattr(b, "opponent_race", None)  # type: ignore
            if bot_opponent_race:
                opponent_race = bot_opponent_race
            elif "enemy_race" in context and context["enemy_race"]:
                opponent_race = context["enemy_race"]
            else:
                intel = getattr(b, "intel", None)  # type: ignore
                if (
                    intel
                    and hasattr(intel, "enemy")
                    and hasattr(intel.enemy, "race")
                    and intel.enemy.race
                ):
                    opponent_race = intel.enemy.race

            # Determine rush timing based on opponent race
            rush_timing = 240  # Default: 4 minutes
            if opponent_race == Race.Terran:
                rush_timing = self.config.RUSH_TIMING_TERRAN  # 5 minutes (300s)
            elif opponent_race == Race.Protoss:
                rush_timing = self.config.RUSH_TIMING_PROTOSS  # 4 minutes (240s)
            elif opponent_race == Race.Zerg:
                rush_timing = self.config.RUSH_TIMING_ZERG  # 3 minutes (180s)

            # Check if enough time has passed for this race matchup
            if hasattr(b, "time") and b.time < rush_timing:
                return False  # Don't attack before race-specific timing

            if self.combat_mode == "DEFENSIVE":
                return False

            intel = getattr(b, "intel", None)  # type: ignore
            if intel and hasattr(intel, "should_attack") and callable(intel.should_attack):
                if intel.should_attack():
                    if self.combat_mode == "CAUTIOUS":
                        if not self.army_gathered:
                            return False
                    return True

            # IMPROVED: Early game aggression - force attack when 12+ zerglings ready
            # This addresses low win rate against VeryEasy by being more aggressive
            intel = getattr(b, "intel", None)
            if intel and intel.cached_zerglings is not None:
                zerglings = list(intel.cached_zerglings)
            else:
                zerglings = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_ready]
            zergling_count = len(zerglings)

            spawning_pools = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure
                )
            )
            if spawning_pools and spawning_pools[0].is_ready:
                # IMPROVED: Attack trigger lowered - force attack when 24+ zerglings OR supply 80+
                # This addresses low win rate against VeryEasy by being more aggressive
                if zergling_count >= 24 or b.supply_army >= 80:
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 50 == 0:
                        print(f"[FORCE ATTACK] [{int(b.time)}s] Trigger: {zergling_count} zerglings OR {b.supply_army} supply - forcing attack!")
                    return True
                
                # IMPROVED: Attack when 12+ zerglings ready (reduced from 20)
                # This creates "offensive virtuous cycle" by converting resources to units
                if zergling_count >= 12 and b.time >= 180:  # At least 3 minutes passed
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 50 == 0:
                        print(f"[EARLY AGGRESSION] [{int(b.time)}s] {zergling_count} zerglings ready - forcing attack!")
                    return True

            if self.config.ALL_IN_12_POOL:
                if zergling_count >= self.config.ALL_IN_ZERGLING_ATTACK:
                    return True

            if self.is_retreating:
                if self.army_gathered:
                    self.is_retreating = False
                return False

            # Check for counter-attack opportunity (enemy attacked, now counter)
            counter_attack_opportunity = False
            intel = getattr(b, "intel", None)  # type: ignore
            if intel and hasattr(intel, "signals") and isinstance(intel.signals, dict):
                counter_attack_opportunity = intel.signals.get("counter_attack_opportunity", False)

                # Counter attack opportunity detected
                if counter_attack_opportunity:
                    # Army must be gathered and sufficient
                    if self.army_gathered and b.supply_army >= 50:
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 50 == 0:
                            print(
                                f"[COUNTER ATTACK] ✅ 역공 타이밍 감지! 병력 충분 ({b.supply_army} supply) - 공격!"
                            )
                        return True
                    else:
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 50 == 0:
                            print(
                                f"[COUNTER ATTACK] ⏳ 역공 타이밍 감지되었으나 병력 부족 (집결: {self.army_gathered}, 병력: {b.supply_army})"
                            )

            zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]
            zergling_count = len(zerglings)
            total_army = b.supply_army

            # IMPROVED: Check tech units for more aggressive attack
            roaches = [u for u in b.units(UnitTypeId.ROACH)]
            hydralisks = [u for u in b.units(UnitTypeId.HYDRALISK)]
            roach_count = len(roaches)
            hydra_count = len(hydralisks)
            tech_unit_count = roach_count + hydra_count

            lurkers = [u for u in b.units(UnitTypeId.LURKER) if u.is_ready]
            if len(lurkers) >= 8:
                return True

            if tech_unit_count >= 10:
                if self.army_gathered or total_army >= 50:
                    return True

            if total_army >= self.config.ALL_IN_ATTACK_SUPPLY:
                if self.combat_mode == "AGGRESSIVE":
                    return True
                elif self.combat_mode == "CAUTIOUS" and self.army_gathered:
                    return True

            if self.combat_mode == "AGGRESSIVE":
                if not self.army_gathered:
                    if total_army < self.config.TOTAL_ARMY_THRESHOLD - 10:
                        return False

                should_attack = (
                    zergling_count >= self.config.ZERGLING_ATTACK_THRESHOLD
                    or total_army >= self.config.TOTAL_ARMY_THRESHOLD
                    or tech_unit_count >= 8
                )
                return should_attack

            elif self.combat_mode == "CAUTIOUS":
                if not self.army_gathered and total_army < 50:
                    return False

                min_army_for_attack = self.config.TOTAL_ARMY_THRESHOLD + 5  # IMPROVED: +10 -> +5
                if total_army < min_army_for_attack:
                    return False

                should_attack = (
                    zergling_count >= self.config.ZERGLING_ATTACK_THRESHOLD + 2  # IMPROVED: +4 -> +2
                    or total_army >= min_army_for_attack
                    or tech_unit_count >= 6
                )
                return should_attack

            # Fallback (should not reach here)
            return False

        except Exception as e:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[ERROR] _should_attack 오류: {e}")
            return False

    async def _execute_attack(self):
        """
        공격 실행 - Economic-Driven Combat Mode에 따라 전략 변경

        💡 모드별 전략:
            - DEFENSIVE: 본진 수비만 (이 메서드는 호출되지 않음)
            - CAUTIOUS: 견제 위주 (소규모 교전, 일꾼 타겟팅)
            - AGGRESSIVE: 공격적 확장 (대규모 교전, 건물 파괴 우선)
        """
        b = self.bot

        try:
            if self.combat_mode == "DEFENSIVE":
                await self._rally_army()
                return
            pursue_targets: List = []
            intel = getattr(b, "intel", None)  # type: ignore
            if (
                intel
                and hasattr(intel, "get_pursue_targets")
                and callable(intel.get_pursue_targets)
            ):
                result = intel.get_pursue_targets()
                if result is not None and isinstance(result, list):
                    pursue_targets = result
            if pursue_targets:
                army = self._get_army_units()
                if army:
                    pursue_count = max(1, len(army) // 5)
                    pursue_units = army[:pursue_count]

                    # IMPROVED: Execute pursue commands with await b.do()
                    for i, unit in enumerate(pursue_units):
                        if i < len(pursue_targets):
                            target = pursue_targets[i]
                            if target is not None:
                                await b.do(unit.attack(target))

            if not self.is_attacking:
                self.is_attacking = True
                self.initial_army_count = self.current_army_count

            enemy_base_structures = []
            enemy_structures = getattr(b, "enemy_structures", [])
            base_types = {
                UnitTypeId.COMMANDCENTER,
                UnitTypeId.COMMANDCENTERFLYING,
                UnitTypeId.NEXUS,
                UnitTypeId.HATCHERY,
                UnitTypeId.LAIR,
                UnitTypeId.HIVE,
                UnitTypeId.ORBITALCOMMAND,
                UnitTypeId.PLANETARYFORTRESS,
            }

            for structure in enemy_structures:
                if structure.type_id in base_types:
                    enemy_base_structures.append(structure)

            target_structure = None
            if enemy_base_structures:
                my_start = b.start_location
                closest_base = min(
                    enemy_base_structures,
                    key=lambda s: my_start.distance_to(s.position) ** 2,
                )
                self.attack_target = closest_base.position
                target_structure = closest_base
                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 100 == 0:
                    print(
                        f"[ATTACK] 🎯 적 기지 건물 타겟팅: {closest_base.type_id.name} at {closest_base.position}"
                    )
            elif b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                self.attack_target = b.enemy_start_locations[0]
            else:
                self.attack_target = b.game_info.map_center

            army = self._get_army_units()
            army = [u for u in army if u.type_id != UnitTypeId.DRONE]
            total_army = b.supply_army

            if army and enemies:
                enemy_units = getattr(b, "enemy_units", [])
                if enemy_units:
                    # Find most threatening enemy (high priority, low health)
                    our_army_composition = {}
                    for unit_type in [UnitTypeId.ZERGLING, UnitTypeId.HYDRALISK, UnitTypeId.ROACH, UnitTypeId.RAVAGER]:
                        count = sum(1 for u in army if u.type_id == unit_type)
                        our_army_composition[unit_type] = count

                    # Select best shared target
                    best_shared_target = max(
                        enemy_units[:20],  # Limit to 20 enemies for performance
                        key=lambda e: self._calculate_dynamic_target_priority(e, our_army_composition)
                    )
                    setattr(b, "_shared_combat_target", best_shared_target)

            lurkers = [u for u in b.units(UnitTypeId.LURKER) if u.is_ready]
            if len(lurkers) >= 8:
                if target_structure:
                    target = target_structure.position
                    lurker_target = target_structure
                elif b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                    target = b.enemy_start_locations[0]
                    lurker_target = None
                else:
                    target = b.game_info.map_center
                    lurker_target = None

                for lurker in lurkers:
                    if not lurker.is_burrowed:
                        burrow_range_squared = 10 * 10  # 10^2 = 100
                        if lurker.distance_to(target) ** 2 < burrow_range_squared:
                            lurker(AbilityId.BURROWDOWN_LURKER)
                        else:
                            lurker.move(target)
                    else:
                        # Use ground_range instead of attack_range (python-sc2 API)
                        lurker_range = max(
                            getattr(lurker, "ground_range", 0),
                            getattr(lurker, "air_range", 0),
                        )
                        attack_range_squared = (
                            (lurker_range + lurker_target.radius) ** 2 if lurker_target else 0
                        )
                        if (
                            lurker_target
                            and lurker.distance_to(lurker_target) ** 2 <= attack_range_squared
                        ):
                            lurker.attack(lurker_target)
                        else:
                            enemy_units = getattr(b, "enemy_units", [])
                            nearby_range_squared = 10 * 10  # 10^2 = 100
                            nearby_enemies = [
                                e
                                for e in enemy_units
                                if lurker.distance_to(e) ** 2 <= nearby_range_squared
                            ]
                            if nearby_enemies:
                                lurker.attack(nearby_enemies[0])

                for unit in army:
                    if unit.type_id != UnitTypeId.LURKER:
                        # Use ground_range instead of attack_range (python-sc2 API)
                        unit_range = max(
                            getattr(unit, "ground_range", 0),
                            getattr(unit, "air_range", 0),
                        )
                        if (
                            target_structure
                            and unit.distance_to(target_structure)
                            <= unit_range + target_structure.radius
                        ):
                            await b.do(unit.attack(target_structure))
                        else:
                            await b.do(unit.attack(target))

                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 100 == 0:
                    target_name = target_structure.type_id.name if target_structure else "적 본진"
                    print(
                        f"[ATTACK] [{int(b.time)}s] Lurker Mass Attack! ({len(lurkers)} Lurkers) → {target_name}"
                    )
                return

            if total_army >= self.config.ALL_IN_ATTACK_SUPPLY:
                enemy_expansions = []

                enemy_structures = getattr(b, "enemy_structures", [])
                for structure in enemy_structures:
                    if structure.type_id in [
                        UnitTypeId.COMMANDCENTER,
                        UnitTypeId.COMMANDCENTERFLYING,
                        UnitTypeId.NEXUS,
                        UnitTypeId.HATCHERY,
                        UnitTypeId.LAIR,
                        UnitTypeId.HIVE,
                    ]:
                        enemy_expansions.append(structure.position)

                if not enemy_expansions:
                    expansion_locations_list = list(b.expansion_locations.keys())
                    expansion_check_range_squared = 15 * 15  # 15^2 = 225
                    for exp_pos in expansion_locations_list:
                        nearby_enemy = [
                            s
                            for s in enemy_structures
                            if s.distance_to(exp_pos) ** 2 < expansion_check_range_squared
                        ]
                        if nearby_enemy:
                            enemy_expansions.append(exp_pos)

                if not enemy_expansions:
                    if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                        target = b.enemy_start_locations[0]
                    else:
                        target = b.game_info.map_center
                else:
                    my_start = b.start_location
                    target = min(enemy_expansions, key=lambda pos: my_start.distance_to(pos))

                # Note: Dead units are automatically removed from the list in python-sc2
                # Safely filter by health (check if health attribute exists)
                all_army_units = [u for u in army if hasattr(u, "health") and u.health > 0]

                if target_structure:
                    target_pos = target_structure.position
                else:
                    target_pos = target

                formation_positions = self._calculate_concave_formation(all_army_units, target_pos)

                if target_structure:
                    for i, unit in enumerate(all_army_units):
                        if i < len(formation_positions):
                            formation_pos = formation_positions[i]
                            # Use ground_range instead of attack_range (python-sc2 API)
                            unit_range = max(
                                getattr(unit, "ground_range", 0),
                                getattr(unit, "air_range", 0),
                            )

                            if (
                                unit.distance_to(target_structure)
                                <= unit_range + target_structure.radius
                            ):
                                await b.do(unit.attack(target_structure))
                            elif unit.distance_to(formation_pos) > 2.0:
                                await b.do(unit.move(formation_pos))
                            else:
                                await b.do(unit.attack(target_structure))
                        else:
                            unit_range = max(
                                getattr(unit, "ground_range", 0),
                                getattr(unit, "air_range", 0),
                            )
                            if (
                                unit.distance_to(target_structure)
                                <= unit_range + target_structure.radius
                            ):
                                await b.do(unit.attack(target_structure))
                            else:
                                await b.do(unit.attack(target_structure.position))
                else:
                    for i, unit in enumerate(all_army_units):
                        if i < len(formation_positions):
                            formation_pos = formation_positions[i]
                            if unit.distance_to(formation_pos) > 2.0:
                                await b.do(unit.move(formation_pos))
                            else:
                                await b.do(unit.attack(target))
                        else:
                            await b.do(unit.attack(target))

                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 100 == 0:
                    target_name = (
                        target_structure.type_id.name if target_structure else f"위치 {target}"
                    )
                    print(f"[ELITE] 정예 AI급 공격! 인구수 {total_army}, 목표: {target_name}")
                return

            if self.config.ALL_IN_12_POOL and self.combat_mode == "AGGRESSIVE":
                intel = getattr(b, "intel", None)
                if intel and intel.cached_zerglings is not None:
                    zerglings = list(intel.cached_zerglings)
                else:
                    zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]
                if zerglings and self.attack_target:
                    enemy_units = getattr(b, "enemy_units", [])
                    worker_range_squared = 20 * 20  # 20^2 = 400
                    enemy_workers = [
                        u
                        for u in enemy_units
                        if u.type_id in [UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE]
                        and u.distance_to(self.attack_target) ** 2 < worker_range_squared
                    ]

                    # IMPROVED: Execute zergling commands with await b.do()
                    for zergling in zerglings:
                        if enemy_workers:
                            closest_worker = min(
                                enemy_workers,
                                key=lambda w: zergling.distance_to(w) ** 2,
                            )
                            await b.do(zergling.attack(closest_worker))
                        else:
                            await b.do(zergling.attack(self.attack_target))
                return

            if self.combat_mode == "CAUTIOUS":
                await self._execute_cautious_attack(target_structure)
                return

            if self.combat_mode == "AGGRESSIVE":
                await self._execute_aggressive_attack(target_structure)
                return

            intel = getattr(b, "intel", None)
            if intel and intel.cached_zerglings is not None:
                zerglings = intel.cached_zerglings.filter(lambda u: u.is_idle)
            else:
                zerglings = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_idle]

            # IMPROVED: Get nearby enemies for better targeting
            enemy_units = getattr(b, "enemy_units", [])
            if zerglings and self.attack_target:
                # IMPROVED: Execute zergling commands with await b.do() for proper command execution
                for zergling in zerglings:
                    # IMPROVED: Use priority target selection for better focus fire
                    # IMPROVED: Use closer_than API for performance
                    if hasattr(enemy_units, 'closer_than'):
                        nearby_enemies = list(enemy_units.closer_than(10.0, zergling.position))
                    else:
                        nearby_enemies = [e for e in enemy_units if zergling.distance_to(e) < 10] if enemy_units else []

                    if nearby_enemies:
                        # IMPROVED: Select priority target for focus fire
                        priority_target = self._select_priority_target(zergling, nearby_enemies)
                        if priority_target:
                            await b.do(zergling.attack(priority_target))
                            continue

                    # Fallback: Attack structure or move to attack target
                    zergling_range = max(
                        getattr(zergling, "ground_range", 0),
                        getattr(zergling, "air_range", 0),
                    )
                    attack_range_squared = (
                        (zergling_range + target_structure.radius) ** 2 if target_structure else 0
                    )
                    if (
                        target_structure
                        and zergling.distance_to(target_structure) ** 2 <= attack_range_squared
                    ):
                        await b.do(zergling.attack(target_structure))
                    else:
                        await b.do(zergling.attack(self.attack_target))

            other_army = [u for u in army if u.type_id != UnitTypeId.ZERGLING and u.is_idle]
            for unit in other_army:
                if self.attack_target:
                    # IMPROVED: Use priority target selection for better focus fire
                    # IMPROVED: Use closer_than API for performance (O(n) instead of O(n²))
                    if hasattr(enemy_units, 'closer_than'):
                        nearby_enemies = list(enemy_units.closer_than(12.0, unit.position))
                    else:
                        nearby_enemies = [e for e in enemy_units if unit.distance_to(e) < 12] if enemy_units else []

                    if nearby_enemies:
                        # IMPROVED: Select priority target for focus fire
                        priority_target = self._select_priority_target(unit, nearby_enemies)
                        if priority_target:
                            unit_range = max(
                                getattr(unit, "ground_range", 0), getattr(unit, "air_range", 0)
                            )
                            if unit.distance_to(priority_target) <= unit_range + priority_target.radius:
                                await b.do(unit.attack(priority_target))
                            else:
                                await b.do(unit.move(priority_target.position))
                            continue

                    # Fallback: Attack structure or move to attack target
                    unit_range = max(
                        getattr(unit, "ground_range", 0), getattr(unit, "air_range", 0)
                    )
                    attack_range_squared = (
                        (unit_range + target_structure.radius) ** 2 if target_structure else 0
                    )
                    if (
                        target_structure
                        and unit.distance_to(target_structure) ** 2 <= attack_range_squared
                    ):
                        await b.do(unit.attack(target_structure))
                    else:
                        await b.do(unit.attack(self.attack_target))
        except Exception as e:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[ERROR] _execute_attack 오류: {e}")

    async def _execute_cautious_attack(self, target_structure):
        """
        IMPROVED: CAUTIOUS 모드 공격 실행 - 견제 위주 전략

        💡 CAUTIOUS 전략:
            - 일꾼 타겟팅 우선 (경제 손상)
            - 소규모 교전
            - 건물 파괴는 부차적

        IMPROVED:
            - 더 많은 유닛을 견제에 투입 (8 -> 12)
            - 우선순위 타겟팅 사용
            - 테크 유닛도 견제에 활용
        """
        b = self.bot
        army = self._get_army_units()

        enemy_units = getattr(b, "enemy_units", [])

        enemy_workers = [
            u
            for u in enemy_units
            if u.type_id in [UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE]
        ]

        zerglings = [u for u in army if u.type_id == UnitTypeId.ZERGLING and u.is_idle]
        if zerglings and enemy_workers:
            for zergling in zerglings[: min(len(zerglings), 12)]:  # IMPROVED: 8 -> 12
                closest_worker = min(enemy_workers, key=lambda w: zergling.distance_to(w) ** 2)
                await b.do(zergling.attack(closest_worker))

        if self.attack_target:
            other_army = [u for u in army if u.type_id != UnitTypeId.ZERGLING and u.is_idle]
            for unit in other_army[: min(len(other_army), 10)]:  # IMPROVED: 6 -> 10
                # IMPROVED: Use closer_than API for performance
                if hasattr(enemy_units, 'closer_than'):
                    nearby_enemies = list(enemy_units.closer_than(10.0, unit.position))
                else:
                    nearby_enemies = [e for e in enemy_units if unit.distance_to(e) < 10] if enemy_units else []
                if nearby_enemies:
                    priority_target = self._select_priority_target(unit, nearby_enemies)
                    if priority_target:
                        await b.do(unit.attack(priority_target))
                    else:
                        await b.do(unit.move(self.attack_target))
                else:
                    await b.do(unit.move(self.attack_target))

    async def _execute_aggressive_attack(self, target_structure):
        """
        AGGRESSIVE 모드 공격 실행 - 공격적 확장 전략

        💡 AGGRESSIVE 전략:
            - 건물 파괴 우선 (게임 목적)
            - 대규모 교전
            - 소모전 강요
        """
        b = self.bot
        army = self._get_army_units()
        army = [u for u in army if u.type_id != UnitTypeId.DRONE]

        zerglings = [u for u in army if u.type_id == UnitTypeId.ZERGLING and u.is_idle]
        if zerglings and self.attack_target:
            for zergling in zerglings:
                # Use ground_range instead of attack_range (python-sc2 API)
                zergling_range = max(
                    getattr(zergling, "ground_range", 0),
                    getattr(zergling, "air_range", 0),
                )
                if (
                    target_structure
                    and zergling.distance_to(target_structure)
                    <= zergling_range + target_structure.radius
                ):
                    zergling.attack(target_structure)
                else:
                    zergling.attack(self.attack_target)

        other_army = [u for u in army if u.type_id != UnitTypeId.ZERGLING and u.is_idle]
        for unit in other_army:
            if self.attack_target:
                # Use ground_range instead of attack_range (python-sc2 API)
                unit_range = max(getattr(unit, "ground_range", 0), getattr(unit, "air_range", 0))
                if (
                    target_structure
                    and unit.distance_to(target_structure) <= unit_range + target_structure.radius
                ):
                    await b.do(unit.attack(target_structure))
                else:
                    await b.do(unit.attack(self.attack_target))

    async def _rally_army(self):
        """
        IMPROVED: 군대 집결 (재집결 중일 때는 더 적극적으로 병력 모으기)

        IMPROVED:
            - 더 빠른 집결 (거리 임계값 완화)
            - 유닛 타입별 집결 우선순위
            - 집결 중에도 적이 나타나면 즉시 대응
        """
        b = self.bot

        if not self.rally_point:
            if self.regrouping_after_loss and b.townhalls.exists:
                townhalls = [th for th in b.townhalls]
                if townhalls:
                    self.rally_point = townhalls[0].position.towards(b.game_info.map_center, 15)
                else:
                    return
            else:
                return

        army = self._get_army_units()

        # IMPROVED: Check for nearby enemies - if enemies are close, prioritize defense over rallying
        enemy_units = getattr(b, "enemy_units", [])
        if enemy_units:
            nearby_enemies = [e for e in enemy_units if any(u.distance_to(e) < 20 for u in army)]
            if nearby_enemies:
                # IMPROVED: Enemies nearby - attack instead of rallying (use await b.do())
                for unit in army:
                    closest_enemy = min(nearby_enemies, key=lambda e: unit.distance_to(e))
                    await b.do(unit.attack(closest_enemy))
                return

        if self.regrouping_after_loss:
            for unit in army:
                if unit.distance_to(self.rally_point) > 25:  # IMPROVED: 20 -> 25
                    await b.do(unit.move(self.rally_point))
                elif unit.is_idle:
                    import random

                    offset_x = random.uniform(-4, 4)  # IMPROVED: -3,3 -> -4,4
                    offset_y = random.uniform(-4, 4)  # IMPROVED: -3,3 -> -4,4
                    wait_position = self.rally_point + Point2((offset_x, offset_y))
                    await b.do(unit.move(wait_position))
        else:
            for unit in [u for u in army if u.is_idle]:
                distance_to_rally = unit.distance_to(self.rally_point)
                if distance_to_rally > 10:
                    await b.do(unit.move(self.rally_point))
                elif distance_to_rally > 5:
                    # Move towards rally point
                    move_pos = unit.position.towards(self.rally_point, 3.0)
                    await b.do(unit.move(move_pos))

    async def _harass_enemy(self):
        """
        저글링 견제 로직 - 상대 일꾼 공격 및 확장 방해

        💡 견제 전략:
            - 저글링 8마리 이상일 때 6마리를 견제 부대로 분리 (소수 정예)
            - 모든 유닛이 나가면 본진이 비어 위험하므로 일부만 보냄
            - 상대 앞마당(Natural)이나 본진 일꾼 공격
            - 히트앤런: 체력 낮으면 후퇴, 높으면 공격
            - 일꾼(SCV/Probe) 최우선 점사
        """
        b = self.bot

        # 🚀 OPTIMIZATION: Use IntelManager cached data or filter once
        intel = getattr(b, "intel", None)
        if intel and intel.cached_military is not None:
            # Filter zerglings from cached military units
            all_zerglings = [u for u in intel.cached_military if u.type_id == UnitTypeId.ZERGLING]
        else:
            # Fallback: direct access if cache not available
            all_zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]

        if len(all_zerglings) < 8:
            self.harass_squad = []
            return

        if len(self.harass_squad) < 6:
            non_harass_zerglings = [u for u in all_zerglings if u not in self.harass_squad]
            if non_harass_zerglings:
                non_harass_zerglings.sort(key=lambda u: u.health_percentage, reverse=True)
                needed = 6 - len(self.harass_squad)
                self.harass_squad.extend(non_harass_zerglings[:needed])

        # Modern python-sc2: Check if unit exists in bot's unit list instead of is_alive
        # 🚀 OPTIMIZATION: Use IntelManager cached data for faster lookup
        intel = getattr(b, "intel", None)
        if intel and intel.cached_military is not None:
            # Use cached military units for tag lookup (much faster)
            current_unit_tags = {u.tag for u in intel.cached_military if hasattr(u, "tag")}
        else:
            # Fallback: direct access if cache not available
            current_unit_tags = {u.tag for u in b.units if hasattr(u, "tag")}
        self.harass_squad = [
            u for u in self.harass_squad if hasattr(u, "tag") and u.tag in current_unit_tags
        ]

        if not self.harass_squad:
            return

        if not self.harass_target:
            if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                enemy_start = b.enemy_start_locations[0]
                self.harass_target = enemy_start.towards(b.game_info.map_center, 20)
            else:
                if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                    self.harass_target = b.enemy_start_locations[0]
                else:
                    self.harass_target = b.game_info.map_center

        # Note: Dead units are automatically removed from the list in python-sc2
        # Create set of current unit tags for fast lookup (once per frame)
        current_unit_tags = {u.tag for u in b.units if hasattr(u, "tag")}

        for zergling in self.harass_squad:
            # Modern python-sc2: Check if unit exists in bot's unit list
            # This is safer than checking is_alive attribute
            try:
                # Verify unit is still valid by checking if it exists in current units
                if not hasattr(zergling, "tag") or zergling.tag not in current_unit_tags:
                    continue

                # Also check health as additional safety measure
                if not hasattr(zergling, "health") or zergling.health <= 0:
                    continue
            except (AttributeError, TypeError):
                # Unit might be invalid, skip it
                continue

            if zergling.health_percentage < 0.3:
                townhalls = [th for th in b.townhalls]
                if townhalls:
                    if townhalls and len(townhalls) > 0:
                        retreat_pos = townhalls[0].position
                    else:
                        retreat_pos = b.start_location
                    await b.do(zergling.move(retreat_pos))
                continue

            enemy_units = getattr(b, "enemy_units", [])
            nearby_range_squared = 10 * 10  # 10^2 = 100
            nearby_enemies = [
                u for u in enemy_units if zergling.distance_to(u) ** 2 < nearby_range_squared
            ]

            if nearby_enemies:
                workers = [
                    u
                    for u in nearby_enemies
                    if u.type_id in [UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE]
                ]

                if workers:
                    target = min(workers, key=lambda w: zergling.distance_to(w) ** 2)
                    await b.do(zergling.attack(target))
                else:
                    target = min(nearby_enemies, key=lambda e: e.health)
                    await b.do(zergling.attack(target))
            else:
                if self.harass_target:
                    await b.do(zergling.attack(self.harass_target))

    async def _micro_units(self):
        """Individual unit micro control"""
        await self._micro_zerglings()
        await self._micro_banelings()
        await self._micro_roaches()
        await self._micro_hydralisks()

    async def _micro_zerglings(self):
        """
        저글링 카이팅 (Hit & Run)

        💡 카이팅 로직:
            weapon_cooldown > 0: 공격 쿨다운 중
            towards(target, -거리): 적 반대 방향으로 이동
        """
        b = self.bot

        intel = getattr(b, "intel", None)
        if intel and intel.cached_zerglings is not None:
            all_zerglings = list(intel.cached_zerglings)
        else:
            all_zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]

        zerglings = [u for u in all_zerglings if u not in self.harass_squad]
        for ling in zerglings:
            enemy_units = getattr(b, "enemy_units", [])
            engage_range_squared = self.config.ENGAGE_DISTANCE * self.config.ENGAGE_DISTANCE
            enemies = [u for u in enemy_units if u.distance_to(ling) ** 2 < engage_range_squared]

            if not enemies:
                continue

            target = self._select_priority_target(ling, enemies)
            if not target:
                continue

            if ling.health_percentage < self.config.RETREAT_HP_PERCENT:
                retreat_pos = self._get_retreat_position(ling)
                await b.do(ling.move(retreat_pos))
                continue

            # Check if we should kite (enemy can attack us)
            enemy_range = 0.0
            try:
                if hasattr(target, "ground_range"):
                    enemy_range = target.ground_range
                elif hasattr(target, "air_range"):
                    enemy_range = target.air_range
            except Exception:
                pass

            # IMPROVED: Smart kiting - only kite if enemy can attack us
            distance_to_target = ling.distance_to(target)
            should_kite = ling.weapon_cooldown > 0 and distance_to_target < enemy_range + 2.0

            if should_kite:
                # IMPROVED: Kite perpendicular to target (better than straight back)
                # Calculate perpendicular direction for better kiting
                to_target = target.position - ling.position
                perp = Point2((-to_target.y, to_target.x))  # Perpendicular vector
                perp_normalized = perp / (perp.length if perp.length > 0 else 1.0)
                kite_pos = ling.position + perp_normalized * self.config.KITING_DISTANCE
                await b.do(ling.move(kite_pos))
            elif ling.weapon_cooldown == 0:
                await b.do(ling.attack(target))
            else:
                if distance_to_target > 1.5:
                    await b.do(ling.move(target.position))

    async def _micro_banelings(self):
        """
        맹독충 마이크로 컨트롤

        💡 맹독충 전략:
            1. Terran 해병 상대: 클러스터 중심으로 이동하여 최대 피해
            2. Protoss/Zerg 저글링 상대: 적 저글링 그룹 중심으로 이동
            3. 산개: 다른 맹독충과 너무 가까이 있으면 산개하여 한 번에 다 잡히지 않게 함
            4. 최적 타겟: 다수의 적이 모인 곳을 우선 타겟팅
        """
        b = self.bot

        intel = getattr(b, "intel", None)
        if intel and hasattr(intel, "cached_banelings") and intel.cached_banelings is not None:
            all_banelings = list(intel.cached_banelings)
        else:
            all_banelings = [u for u in b.units(UnitTypeId.BANELING).ready]

        banelings = [u for u in all_banelings if u not in self.harass_squad]
        if not banelings:
            return

        enemy_units = getattr(b, "enemy_units", [])
        if not enemy_units:
            return

        # vs Terran Marines: Use MicroController's execute_baneling_vs_marines
        if b.opponent_race == Race.Terran:
            marines = [u for u in enemy_units if u.type_id == UnitTypeId.MARINE]
            if marines and b.micro:
                try:
                    await b.micro.execute_baneling_vs_marines(banelings, enemy_units)
                    return
                except Exception:
                    pass  # Fallback to general baneling control

        # General baneling control (vs Protoss/Zerg or Terran non-marines)
        engage_range_squared = self.config.ENGAGE_DISTANCE * self.config.ENGAGE_DISTANCE

        # Group enemy units by type to find clusters
        enemy_clusters = self._find_enemy_clusters(enemy_units, max_clusters=3)

        for baneling in banelings:
            if not baneling.is_ready:
                continue

            # Find nearby enemies
            nearby_enemies = [
                u for u in enemy_units
                if baneling.distance_to(u) ** 2 < engage_range_squared
            ]

            if not nearby_enemies:
                continue

            # Find closest cluster
            best_cluster = None
            min_distance = float('inf')

            for cluster_center, cluster_enemies in enemy_clusters:
                distance = baneling.distance_to(cluster_center)
                if distance < min_distance:
                    min_distance = distance
                    best_cluster = (cluster_center, cluster_enemies)

            # Spread out if too close to other banelings
            nearby_banelings = [
                b for b in banelings
                if b.tag != baneling.tag
                and baneling.distance_to(b) < 2.0  # BANELING_SPLIT_RADIUS
            ]

            if nearby_banelings and best_cluster:
                # Spread: Move away from average position of other banelings
                avg_pos = Point2((
                    sum(b.position.x for b in nearby_banelings) / len(nearby_banelings),
                    sum(b.position.y for b in nearby_banelings) / len(nearby_banelings),
                ))
                spread_dir_x = baneling.position.x - avg_pos.x
                spread_dir_y = baneling.position.y - avg_pos.y
                spread_length = math.sqrt(spread_dir_x ** 2 + spread_dir_y ** 2)

                if spread_length > 0.1:
                    # Spread 2.0 distance after normalization
                    spread_dir_x = (spread_dir_x / spread_length) * 2.0
                    spread_dir_y = (spread_dir_y / spread_length) * 2.0
                    spread_pos = Point2((
                        baneling.position.x + spread_dir_x,
                        baneling.position.y + spread_dir_y,
                    ))
                    await b.do(baneling.move(spread_pos))
                else:
                    # If no spread direction, move to cluster center
                    cluster_center, _ = best_cluster
                    await b.do(baneling.move(cluster_center))
            elif best_cluster:
                # Move to cluster center
                cluster_center, _ = best_cluster
                await b.do(baneling.move(cluster_center))
            else:
                # If no cluster, attack closest enemy
                closest_enemy = min(nearby_enemies, key=lambda e: baneling.distance_to(e))
                await b.do(baneling.attack(closest_enemy))

    def _find_enemy_clusters(
        self, enemy_units: List[Unit], max_clusters: int = 3
    ) -> List[tuple]:
        """
        적 유닛 클러스터 찾기 (간단한 거리 기반 클러스터링)

        Args:
            enemy_units: 적 유닛 리스트
            max_clusters: 최대 클러스터 수

        Returns:
            List of (cluster_center, cluster_enemies) tuples
        """
        if not enemy_units:
            return []

        if len(enemy_units) <= 3:
            center = Point2((
                sum(e.position.x for e in enemy_units) / len(enemy_units),
                sum(e.position.y for e in enemy_units) / len(enemy_units),
            ))
            return [(center, enemy_units)]

        # Simple distance-based clustering
        clusters = []
        used_units = set()
        cluster_radius = 5.0  # Cluster radius

        for enemy in enemy_units:
            if enemy.tag in used_units:
                continue

            cluster = [enemy]
            used_units.add(enemy.tag)

            for other in enemy_units:
                if other.tag in used_units:
                    continue
                if enemy.distance_to(other) < cluster_radius:
                    cluster.append(other)
                    used_units.add(other.tag)

            if cluster:
                center = Point2((
                    sum(e.position.x for e in cluster) / len(cluster),
                    sum(e.position.y for e in cluster) / len(cluster),
                ))
                clusters.append((center, cluster))

                if len(clusters) >= max_clusters:
                    break

        return clusters

    async def _micro_roaches(self):
        """Roach control"""
        b = self.bot

        intel = getattr(b, "intel", None)
        if intel and intel.cached_roaches is not None:
            roaches = list(intel.cached_roaches)
        else:
            roaches = [u for u in b.units(UnitTypeId.ROACH)]
        for roach in roaches:
            enemy_units = getattr(b, "enemy_units", [])
            engage_range_squared = self.config.ENGAGE_DISTANCE * self.config.ENGAGE_DISTANCE
            enemies = [u for u in enemy_units if u.distance_to(roach) ** 2 < engage_range_squared]

            if not enemies:
                continue

            if roach.health_percentage < 0.4:
                retreat_pos = self._get_retreat_position(roach)
                await b.do(roach.move(retreat_pos))
                continue

            target = self._select_priority_target(roach, enemies)
            if target:
                # IMPROVED: Roach kiting (roaches have regeneration, can kite better)
                roach_range = max(getattr(roach, "ground_range", 0), getattr(roach, "air_range", 0))
                distance_to_target = roach.distance_to(target)

                # IMPROVED: Kite if weapon cooldown > 0 and enemy can attack
                enemy_range = 0.0
                try:
                    if hasattr(target, "ground_range"):
                        enemy_range = target.ground_range
                    elif hasattr(target, "air_range"):
                        enemy_range = target.air_range
                except Exception:
                    pass

                if roach.weapon_cooldown > 0 and distance_to_target < enemy_range + 2.0:
                    kite_pos = roach.position.towards(target, -2.0)
                    await b.do(roach.move(kite_pos))
                elif roach.weapon_cooldown == 0:
                    await b.do(roach.attack(target))
                else:
                    if distance_to_target > roach_range + target.radius:
                        await b.do(roach.move(target.position))

    async def _micro_hydralisks(self):
        """Hydralisk control (ranged DPS)"""
        b = self.bot

        intel = getattr(b, "intel", None)
        if intel and intel.cached_hydralisks is not None:
            hydras = list(intel.cached_hydralisks)
        else:
            hydras = [u for u in b.units(UnitTypeId.HYDRALISK)]
        for hydra in hydras:
            enemy_units = getattr(b, "enemy_units", [])
            engage_range_squared = self.config.ENGAGE_DISTANCE * self.config.ENGAGE_DISTANCE
            enemies = [u for u in enemy_units if u.distance_to(hydra) ** 2 < engage_range_squared]

            if not enemies:
                continue

            if hydra.health_percentage < 0.5:
                retreat_pos = self._get_retreat_position(hydra)
                await b.do(hydra.move(retreat_pos))
                continue

            target = self._select_priority_target(hydra, enemies)
            if not target:
                continue

            hydra_range = max(getattr(hydra, "ground_range", 0), getattr(hydra, "air_range", 0))
            distance_to_target = hydra.distance_to(target)

            # IMPROVED: Maintain optimal range (6 for hydralisk with upgrade)
            optimal_range = 6.0 if hydra_range >= 6.0 else hydra_range

            if hydra.weapon_cooldown > 0:
                if distance_to_target < optimal_range - 1.0:
                    # Too close, kite back
                    kite_pos = hydra.position.towards(target, -(optimal_range - distance_to_target))
                    await b.do(hydra.move(kite_pos))
                elif distance_to_target > optimal_range + 1.0:
                    # Too far, move closer
                    await b.do(hydra.move(target.position))
                else:
                    # Optimal range, just move slightly back
                    kite_pos = hydra.position.towards(target, -2.0)
                    await b.do(hydra.move(kite_pos))
            else:
                if distance_to_target <= hydra_range + target.radius:
                    await b.do(hydra.attack(target))
                else:
                    await b.do(hydra.move(target.position))

    def _select_priority_target(self, unit: Unit, enemies: List[Unit]) -> Optional[Unit]:
        """
        IMPROVED: 우선순위 타겟 선택 (Focus Fire 강화)

        PERFORMANCE: Optimized using closer_than API to reduce O(n²) distance calculations
        - Uses closer_than() to filter enemies by range first (O(n) instead of O(n²))
        - Only calculates distance for enemies within range

        가중치 시스템:
            TARGET_PRIORITY 딕셔너리에서 유닛별 가중치를 가져와
            가장 높은 가중치의 적을 우선 공격

        IMPROVED: Focus Fire 강화
            - 여러 유닛이 같은 타겟을 공격하도록 공유 타겟 시스템 추가
            - 체력이 낮은 적 우선 공격 (빠른 제거)
            - 위험한 유닛(탱크, 거신 등) 우선 공격

        Args:
            unit: 공격할 아군 유닛
            enemies: 적 유닛들

        Returns:
            Unit: 선택된 타겟
        """
        # PERFORMANCE: Use closer_than API to filter enemies by range first
        # This reduces O(n²) distance calculations to O(n) filtering
        unit_range = max(getattr(unit, "ground_range", 0), getattr(unit, "air_range", 0))
        max_attack_range = unit_range + 3.0  # Add buffer for unit radius

        # PERFORMANCE: Filter enemies using closer_than if available (much faster than distance_to**2)
        in_range = []
        if hasattr(enemies, 'closer_than'):
            # enemies is already a Units object with closer_than method
            in_range_units = enemies.closer_than(max_attack_range, unit.position)
            if hasattr(in_range_units, '__iter__'):
                in_range = list(in_range_units)
        else:
            # Fallback: enemies is a list, use list comprehension with distance check
            # Still optimized: only check distance for enemies within reasonable range
            attack_range_squared = max_attack_range * max_attack_range
            in_range = [e for e in enemies if unit.distance_to(e) ** 2 <= attack_range_squared]

        # Fallback: if no enemies in range, use all enemies
        if not in_range:
            in_range = list(enemies) if not isinstance(enemies, list) else enemies

        if not in_range:
            # PERFORMANCE: Use closer_than with larger range for fallback if available
            if hasattr(enemies, 'closer_than'):
                nearby = enemies.closer_than(50.0, unit.position)
                if nearby and len(list(nearby)) > 0:
                    return nearby.closest_to(unit.position)
                if len(list(enemies)) > 0:
                    return enemies.closest_to(unit.position)
            elif enemies:
                # Fallback for list: use min with distance
                return min(enemies, key=lambda e: unit.distance_to(e) ** 2)
            return None

        b = self.bot
        shared_target = getattr(b, "_shared_combat_target", None)

        if shared_target and shared_target in in_range:
            try:
                if hasattr(shared_target, "health") and shared_target.health > 0:
                    return shared_target
            except Exception:
                pass

        # Calculate our army composition for dynamic priority
        our_army_composition = {}
        army = self._get_army_units()

        for unit_type in [
            UnitTypeId.ZERGLING,
            UnitTypeId.HYDRALISK,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
        ]:
            count = sum(1 for u in army if u.type_id == unit_type)
            our_army_composition[unit_type] = count

        # IMPROVED: Dynamic priority calculation with enhanced focus fire
        # Calculate priority for all enemies in range
        target_scores = []
        for enemy in in_range:
            priority_score = self._calculate_dynamic_target_priority(enemy, our_army_composition)
            # IMPROVED: Add distance penalty (closer = better for focus fire)
            distance = unit.distance_to(enemy)
            distance_bonus = max(0, (15.0 - distance) / 15.0) * 2.0  # Closer = up to +2.0 bonus
            # IMPROVED: Add health penalty (lower health = higher priority for focus fire)
            health_penalty = (1.0 - getattr(enemy, "health_percentage", 1.0)) * 3.0  # Lower health = up to +3.0 bonus
            total_score = priority_score + distance_bonus + health_penalty
            target_scores.append((enemy, total_score))

        # Select best target
        if target_scores:
            best_target = max(target_scores, key=lambda x: x[1])[0]

            # IMPROVED: Set shared target for focus fire (if target is high priority)
            if target_scores and max(target_scores, key=lambda x: x[1])[1] > 10.0:
                setattr(b, "_shared_combat_target", best_target)

            return best_target

        return None

    def _calculate_concave_formation(self, units: List[Unit], target: Point2) -> List[Point2]:
        """
        오목한 진형(Concave) 형성 계산 - 포위 전술

        적 위치를 중심으로 반원을 그리며 병력을 분산시킨 후 동시에 덮치는 전술
        저그 병력의 핵심은 '포위'입니다.

        Args:
            units: 아군 유닛 목록
            target: 적 위치 (목표 지점)

        Returns:
            List[Point2]: 각 유닛의 포위 위치 (formation positions)
        """
        if not units:
            return []

        formation_positions = []

        formation_radius = min(18.0, max(10.0, len(units) * 0.9))  # IMPROVED: 0.8 -> 0.9, 15 -> 18

        angle_step = 180.0 / len(units) if len(units) > 1 else 0

        for i, unit in enumerate(units):
            angle_deg = -90.0 + (i * angle_step)
            angle_rad = math.radians(angle_deg)

            unit_type = unit.type_id
            if unit_type == UnitTypeId.HYDRALISK:
                radius_multiplier = 1.2
            elif unit_type == UnitTypeId.ROACH:
                radius_multiplier = 1.0
            else:
                radius_multiplier = 0.9

            offset_x = formation_radius * radius_multiplier * math.cos(angle_rad)
            offset_y = formation_radius * radius_multiplier * math.sin(angle_rad)

            formation_pos = target + Point2((offset_x, offset_y))
            formation_positions.append(formation_pos)

        return formation_positions

    def _calculate_dynamic_target_priority(
        self, enemy_unit: Unit, our_army_composition: dict
    ) -> float:
        """
        동적 타겟 우선순위 계산 - 내 조합에 따른 상대 우선순위 재계산

        내 병력이 히드라 중심이라면 '탱크'를 1순위로,
        저글링 중심이라면 '기뢰나 맹독충'을 1순위로 피하거나 점사

        Args:
            enemy_unit: 적 유닛
            our_army_composition: 아군 조합 (유닛 타입별 수)

        Returns:
            float: 우선순위 점수 (높을수록 우선)
        """
        base_priority = TARGET_PRIORITY.get(enemy_unit.type_id, 1)

        hydra_count = our_army_composition.get(UnitTypeId.HYDRALISK, 0)
        zergling_count = our_army_composition.get(UnitTypeId.ZERGLING, 0)
        roach_count = our_army_composition.get(UnitTypeId.ROACH, 0)

        total_army = hydra_count + zergling_count + roach_count
        if total_army == 0:
            return base_priority

        hydra_ratio = hydra_count / total_army if total_army > 0 else 0
        zergling_ratio = zergling_count / total_army if total_army > 0 else 0

        if hydra_ratio > 0.4:
            if enemy_unit.type_id in [UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED]:
                return base_priority + 10.0
            if enemy_unit.type_id in [UnitTypeId.MEDIVAC, UnitTypeId.VIKINGFIGHTER]:
                return base_priority + 8.0

        if zergling_ratio > 0.6:
            if enemy_unit.type_id in [UnitTypeId.WIDOWMINE, UnitTypeId.BANELING]:
                return base_priority + 12.0
            if enemy_unit.type_id in [UnitTypeId.MARAUDER, UnitTypeId.MARINE]:
                return base_priority + 7.0

        roach_ratio = roach_count / total_army if total_army > 0 else 0
        if roach_ratio > 0.5:
            if enemy_unit.type_id in [UnitTypeId.COLOSSUS, UnitTypeId.IMMORTAL]:
                return base_priority + 10.0

        health_penalty = (1 - enemy_unit.health_percentage) * 5.0

        # IMPROVED: Add distance bonus (closer enemies are easier to focus fire)
        # This helps with focus fire coordination
        try:
            army = self._get_army_units()
            if army:
                # Calculate average distance from our army to this enemy
                avg_distance = sum(u.distance_to(enemy_unit) for u in army[:10]) / min(len(army), 10)
                distance_bonus = max(0, (20.0 - avg_distance) / 20.0) * 2.0  # Closer = up to +2.0 bonus
            else:
                distance_bonus = 0.0
        except Exception:
            distance_bonus = 0.0

        # IMPROVED: Add threat level bonus (high threat units get higher priority)
        threat_bonus = 0.0
        if enemy_unit.type_id in [
            UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED,
            UnitTypeId.COLOSSUS, UnitTypeId.HIGHTEMPLAR,
            UnitTypeId.DISRUPTOR, UnitTypeId.WIDOWMINE
        ]:
            threat_bonus = 5.0  # High threat units get +5.0 bonus

        return base_priority + health_penalty + distance_bonus + threat_bonus

    def _get_army_units(self) -> List[Unit]:
        """
        IMPROVED: 전투 유닛 목록 반환 (일꾼 제외)

        IMPROVED:
            - IntelManager 캐시 우선 사용 (성능 최적화)
            - 더 정확한 병력 추적 (ready 유닛만)
            - Queen 제외 (전투 유닛이 아님)

        Returns:
            List[Unit]: 전투 유닛 목록 (DRONE, QUEEN 제외)
        """
        b = self.bot

        # IMPROVED: Use IntelManager cache if available (performance optimization)
        intel = getattr(b, "intel", None)
        if intel and hasattr(intel, "cached_military") and intel.cached_military is not None:
            # Use cached military units (already filtered)
            if hasattr(intel.cached_military, "__iter__"):
                return [u for u in intel.cached_military if hasattr(u, "is_ready") and u.is_ready]
            else:
                # Fallback if cached_military is not iterable
                pass

        # IMPROVED: Filter army units (ready units only, exclude workers and queens)
        army_types = {
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKER,
            UnitTypeId.MUTALISK,
            UnitTypeId.CORRUPTOR,
            UnitTypeId.ULTRALISK,
            UnitTypeId.BROODLORD,
        }

        # IMPROVED: Get ready units only (exclude units that are still morphing/building)
        army_units = []
        try:
            for unit in b.units:
                if unit.type_id in army_types:
                    # IMPROVED: Only include ready units (exclude morphing units)
                    if hasattr(unit, "is_ready") and unit.is_ready:
                        army_units.append(unit)
                    elif not hasattr(unit, "is_ready"):
                        # If is_ready attribute doesn't exist, include the unit
                        army_units.append(unit)
        except Exception as e:
            # Fallback: simple filter if iteration fails
            army_units = [u for u in b.units if u.type_id in army_types]

        return army_units

    def _get_retreat_position(self, unit: Unit) -> Point2:
        """Calculate retreat position"""
        b = self.bot

        townhalls = [th for th in b.townhalls]
        if not townhalls:
            return b.start_location

        closest_th = min(townhalls, key=lambda th: unit.distance_to(th) ** 2)
        return closest_th.position

    def _calculate_army_centroid(self) -> Optional[Point2]:
        """
        군대 중심점(Centroid) 계산

        💡 클러스터링:
            병력의 평균 위치를 계산하여 집결 여부 판단

        Returns:
            Point2: 군대 중심점
        """
        army = self._get_army_units()

        if not army:
            return None

        x_sum = sum(u.position.x for u in army)
        y_sum = sum(u.position.y for u in army)

        return Point2((x_sum / len(army), y_sum / len(army)))

    def _calculate_army_spread(self) -> float:
        """
        군대 분산도 계산

        Returns:
            float: 중심점으로부터의 평균 거리
        """
        army = self._get_army_units()
        centroid = self._calculate_army_centroid()

        if not army or not centroid:
            return 0.0

        total_distance = sum(u.position.distance_to(centroid) for u in army)
        return total_distance / len(army)

    def get_combat_status(self) -> dict:
        """Return current combat status"""
        return {
            "is_attacking": self.is_attacking,
            "is_retreating": self.is_retreating,
            "army_gathered": self.army_gathered,
            "army_count": self.current_army_count,
            "rally_point": str(self.rally_point) if self.rally_point else None,
            "attack_target": str(self.attack_target) if self.attack_target else None,
        }

    def set_attack_target(self, target: Point2):
        """Set attack target"""
        self.attack_target = target

    def set_rally_point(self, point: Point2):
        """Set rally point"""
        self.rally_point = point

    def _can_attrit_enemy_units(self) -> bool:
        """
        소모전 판단 로직: 상대방의 병력을 갉아먹을 수 있는가?

        저그는 '소모전'에 능해야 함. 단순히 승률이 낮다고 빼는 것이 아니라,
        상대방의 병력을 지속적으로 감소시킬 수 있는지 판단.

        판단 기준:
        1. 히드라리스크: 사거리 우위로 안전하게 공격 가능
        2. 저글링: 감싸기(Surround)로 적 유닛 격파 가능
        3. 맹독충: 바이오닉 상대로 효과적
        4. 적 병력 대비 우리 병력의 효율성 (DPS/비용 비율)
        5. 지형 우위: 언덕 위에서 공격하면 유리
        6. 스플래시 데미지 유닛: 맹독충, 거신 등에 취약한 조합인지 확인

        Returns:
            bool: 소모전 가능 여부 (True = 계속 교전 가능, False = 퇴각 필요)
        """
        b = self.bot

        try:
            from config import Config
            _config = Config()
            hydralisks = b.units(UnitTypeId.HYDRALISK).ready
            zerglings = b.units(UnitTypeId.ZERGLING).ready
            banelings = b.units(UnitTypeId.BANELING).ready
            roaches = b.units(UnitTypeId.ROACH).ready

            hydra_count = (
                hydralisks.amount if hasattr(hydralisks, "amount") else len(list(hydralisks))
            )
            zergling_count = (
                zerglings.amount if hasattr(zerglings, "amount") else len(list(zerglings))
            )
            baneling_count = (
                banelings.amount if hasattr(banelings, "amount") else len(list(banelings))
            )
            roach_count = roaches.amount if hasattr(roaches, "amount") else len(list(roaches))

            enemy_units = b.known_enemy_units
            if not enemy_units or not enemy_units.exists:
                return False

            enemy_count = (
                enemy_units.amount if hasattr(enemy_units, "amount") else len(list(enemy_units))
            )

            terrain_advantage = 1.0
            try:
                army_centroid = self._calculate_army_centroid()
                if army_centroid:
                    terrain_advantage = _config.TERRAIN_ADVANTAGE_MULTIPLIER
            except Exception:
                pass

            if hydra_count >= 6:
                return True if terrain_advantage >= 1.0 else hydra_count >= 8

            if zergling_count >= 12 and baneling_count >= 2:
                return True

            if zergling_count >= 16:
                enemy_ranged_count = 0
                for enemy in enemy_units:
                    if hasattr(enemy, "is_ranged") and enemy.is_ranged:
                        enemy_ranged_count += 1

                if enemy_ranged_count < enemy_count * 0.3:
                    return True

            if roach_count >= 6 and hydra_count >= 3:
                return True

            our_total = hydra_count + zergling_count + roach_count
            if our_total > enemy_count * 1.5:
                return True

            if our_total < 8:
                return False

            return True

        except Exception as e:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 100 == 0:
                print(f"[WARNING] _can_attrit_enemy_units 오류: {e}")
            return False

    def _update_win_rate(self):
        """
        현재 승률을 계산하여 업데이트

        ProductionManager나 IntelManager에서 계산된 승률을 가져오거나,
        직접 계산하여 저장합니다.
        """
        b = self.bot

        try:
            production = getattr(b, "production", None)
            if production and hasattr(production, "last_calculated_win_rate"):
                calculated_rate = getattr(production, "last_calculated_win_rate", 50.0)
                self.current_win_rate = calculated_rate
                setattr(b, "current_win_rate", calculated_rate)
                return

            enemy_tech = getattr(b, "enemy_tech", "UNKNOWN")
            if enemy_tech == "UNKNOWN" or enemy_tech == "GROUND" or enemy_tech == "SCANNING":
                return

            hydra_count = (
                b.units(UnitTypeId.HYDRALISK).amount
                if hasattr(b.units(UnitTypeId.HYDRALISK), "amount")
                else len(list(b.units(UnitTypeId.HYDRALISK)))
            )
            ravager_count = (
                b.units(UnitTypeId.RAVAGER).amount
                if hasattr(b.units(UnitTypeId.RAVAGER), "amount")
                else len(list(b.units(UnitTypeId.RAVAGER)))
            )
            baneling_count = (
                b.units(UnitTypeId.BANELING).amount
                if hasattr(b.units(UnitTypeId.BANELING), "amount")
                else len(list(b.units(UnitTypeId.BANELING)))
            )
            zergling_count = (
                b.units(UnitTypeId.ZERGLING).amount
                if hasattr(b.units(UnitTypeId.ZERGLING), "amount")
                else len(list(b.units(UnitTypeId.ZERGLING)))
            )
            queen_count = (
                b.units(UnitTypeId.QUEEN).amount
                if hasattr(b.units(UnitTypeId.QUEEN), "amount")
                else len(list(b.units(UnitTypeId.QUEEN)))
            )

            win_rate = 50.0

            if enemy_tech == "AIR":
                base_rate = 30.0
                hydra_bonus = min(hydra_count * 5, 50)
                win_rate = base_rate + hydra_bonus
                queen_bonus = min(queen_count * 2, 10)
                win_rate += queen_bonus
            elif enemy_tech == "MECHANIC":
                base_rate = 40.0
                ravager_bonus = min(ravager_count * 7, 45)
                win_rate = base_rate + ravager_bonus
                roach_count = (
                    b.units(UnitTypeId.ROACH).amount
                    if hasattr(b.units(UnitTypeId.ROACH), "amount")
                    else len(list(b.units(UnitTypeId.ROACH)))
                )
                roach_bonus = min(roach_count * 1, 10)
                win_rate += roach_bonus
            elif enemy_tech == "BIO":
                base_rate = 35.0
                baneling_bonus = min(baneling_count * 4, 40)
                win_rate = base_rate + baneling_bonus
                win_rate += min(zergling_count * 0.5, 15)

                if hasattr(b, "state") and hasattr(b.state, "upgrades"):
                    upgrades = b.state.upgrades
                    from sc2.ids.upgrade_id import UpgradeId

                    centrifugal_upgrade_id = getattr(UpgradeId, "CENTRIFUGALHOOKS", None)
                    if not centrifugal_upgrade_id:
                        centrifugal_upgrade_id = getattr(UpgradeId, "CENTRIFUGAL_HOOKS", None)
                    if centrifugal_upgrade_id and centrifugal_upgrade_id in upgrades:
                        win_rate += 15

            self.current_win_rate = max(10.0, min(95.0, win_rate))
            setattr(b, "current_win_rate", self.current_win_rate)

        except Exception as e:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 500 == 0:
                print(f"[WARNING] Failed to update win rate: {e}")

    async def _execute_smart_retreat(self):
        """
        승률 기반 스마트 후퇴 실행

        승률이 낮을 때 모든 전투 유닛을 본진으로 후퇴시킵니다.
        """
        b = self.bot

        try:
            if not b.townhalls.exists:
                return

            home_base = b.townhalls.first.position

            army_types = {
                UnitTypeId.ZERGLING,
                UnitTypeId.ROACH,
                UnitTypeId.RAVAGER,
                UnitTypeId.HYDRALISK,
                UnitTypeId.BANELING,
                UnitTypeId.LURKER,
            }

            for unit in b.units:
                if unit.type_id in army_types and not unit.is_structure:
                    enemy_nearby = False
                    if hasattr(b, "enemy_units") and b.enemy_units:
                        enemy_threat_range_squared = 15.0 * 15.0  # 15^2 = 225
                        for enemy in b.enemy_units:
                            if unit.distance_to(enemy) ** 2 < enemy_threat_range_squared:
                                enemy_nearby = True
                                break

                    home_base_range_squared = 30.0 * 30.0  # 30^2 = 900
                    if enemy_nearby or unit.distance_to(home_base) ** 2 > home_base_range_squared:
                        await b.do(unit.move(home_base))

        except Exception as e:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 100 == 0:
                print(f"[WARNING] Failed to execute smart retreat: {e}")

    async def _visualize_retreat_status(self, bot, is_retreating: bool):
        try:
            show_window = os.environ.get("SHOW_WINDOW", "false").lower() == "true"
            if not show_window:
                return

            current_iteration = getattr(bot, "iteration", 0)
            if current_iteration % 4 != 0:
                return

            win_rate = self.current_win_rate
            if hasattr(bot, "client") and bot.client:
                if is_retreating:
                    status_text = f"RETREATING - Win Rate {win_rate:.0f}% < {self.advance_threshold:.0f}%"
                    color = (255, 0, 0)
                else:
                    status_text = f"ENGAGING - Win Rate {win_rate:.0f}% >= {self.retreat_threshold:.0f}%"
                    color = (0, 255, 0)

                try:
                    bot.client.debug_text_screen(status_text, pos=(0.4, 0.1), size=15, color=color)
                except Exception:
                    pass

            visualizer = getattr(bot, "visualizer", None)
            if visualizer and hasattr(visualizer, "update_dashboard"):
                try:
                    visualizer.update_dashboard(bot)
                except Exception:
                    pass
        except Exception:
            pass
