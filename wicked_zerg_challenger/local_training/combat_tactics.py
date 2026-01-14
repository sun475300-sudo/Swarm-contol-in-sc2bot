# -*- coding: utf-8 -*-
from typing import Any, List

from sc2.data import Race  # type: ignore
from sc2.ids.ability_id import AbilityId  # type: ignore
from sc2.ids.unit_typeid import UnitTypeId  # type: ignore

class CombatTactics:
    def __init__(self, bot: Any) -> None:
        self.bot = bot

    async def execute_combat(self) -> None:
        b = self.bot
        try:
            if b.opponent_race == Race.Terran:
                banelings = list(b.units(UnitTypeId.BANELING).ready)
                if banelings:
                    enemy_units = getattr(b, "enemy_units", [])
                    if enemy_units:
                        enemy_list = list(enemy_units) if hasattr(enemy_units, "__iter__") else []
                        if b.micro:
                            await b.micro.execute_baneling_vs_marines(banelings, enemy_list)
        except Exception:
            pass

        if not hasattr(b, "unit_micro"):
            try:
                if b.micro is not None:
                    b.unit_micro = b.micro
                else:

                    class DummyMicroController:
                        async def execute_spread_attack(self, *args):
                            pass

                        async def execute_stutter_step(self, *args):
                            pass

                        async def execute_unit_micro(self, *args):
                            pass

                    b.unit_micro = DummyMicroController()  # type: ignore[assignment]
            except Exception:
                b.unit_micro = None

        intel = getattr(b, "intel", None)
        if (
            intel
            and hasattr(intel, "should_attack")
            and callable(intel.should_attack)
            and intel.should_attack()
        ):
            target = (
                b.enemy_start_locations[0]
                if b.enemy_start_locations and len(b.enemy_start_locations) > 0
                else b.game_info.map_center
            )

            cached_units = getattr(b, "_cached_units", None)
            if cached_units is None or isinstance(cached_units, List):
                cached_units = b.units
            cached_enemy_units = getattr(b, "_cached_enemy_units", None) or getattr(
                b, "enemy_units", None
            )

            army_types = {
                UnitTypeId.ZERGLING,
                UnitTypeId.ROACH,
                UnitTypeId.HYDRALISK,
                UnitTypeId.QUEEN,
            }
            all_army = (
                cached_units.filter(lambda u: u.type_id in army_types)
                if hasattr(cached_units, "filter")
                else b.units.filter(lambda u: u.type_id in army_types)
            )
            if b.unit_micro and all_army.exists:
                await b.unit_micro.execute_unit_micro(all_army)

            zerglings = (
                cached_units(UnitTypeId.ZERGLING)
                if hasattr(cached_units, "__call__")
                else b.units(UnitTypeId.ZERGLING)
            )
            zerglings_list = [u for u in zerglings] if hasattr(zerglings, "__iter__") else []
            if len(zerglings_list) >= 10:
                if cached_enemy_units and b.micro:
                    if b.opponent_race == Race.Zerg:
                        enemy_zerglings = [
                            u for u in cached_enemy_units if u.type_id == UnitTypeId.ZERGLING
                        ]
                        if enemy_zerglings and hasattr(b.micro, "execute_zvz_zergling_micro"):
                            await b.micro.execute_zvz_zergling_micro(
                                zerglings_list, enemy_zerglings
                            )
                    else:
                        if hasattr(b.micro, "execute_spread_attack"):
                            b.micro.execute_spread_attack(zerglings, target, cached_enemy_units)

            hydras = (
                cached_units(UnitTypeId.HYDRALISK)
                if hasattr(cached_units, "__call__")
                else b.units(UnitTypeId.HYDRALISK)
            )
            hydras_list = [u for u in hydras] if hasattr(hydras, "__iter__") else []
            if hydras_list and b.micro:
                if hasattr(b.micro, "execute_overlord_hunter"):
                    await b.micro.execute_overlord_hunter(hydras_list)
                if hasattr(b.micro, "execute_stutter_step"):
                    try:
                        b.micro.execute_stutter_step(hydras, target)
                    except TypeError:
                        pass

            roaches = (
                cached_units(UnitTypeId.ROACH)
                if hasattr(cached_units, "__call__")
                else b.units(UnitTypeId.ROACH)
            )
            roaches_list = [u for u in roaches] if hasattr(roaches, "__iter__") else []
            if roaches_list and cached_enemy_units and b.micro:
                if hasattr(b.micro, "execute_spread_attack"):
                    try:
                        b.micro.execute_spread_attack(roaches, target, cached_enemy_units)
                    except TypeError:
                        pass

            ravagers_raw = (
                cached_units(UnitTypeId.RAVAGER)
                if hasattr(cached_units, "__call__")
                else b.units(UnitTypeId.RAVAGER)
            )
            ravagers = (
                [u for u in ravagers_raw if hasattr(u, "is_ready") and u.is_ready]
                if hasattr(ravagers_raw, "__iter__")
                else []
            )
            if ravagers and cached_enemy_units and b.micro:
                await b.micro.execute_serral_bile_sniping(ravagers, cached_enemy_units)

            lurkers_raw = (
                cached_units(UnitTypeId.LURKER)
                if hasattr(cached_units, "__call__")
                else b.units(UnitTypeId.LURKER)
            )
            lurkers = (
                [u for u in lurkers_raw if hasattr(u, "is_ready") and u.is_ready]
                if hasattr(lurkers_raw, "__iter__")
                else []
            )
            if lurkers and cached_enemy_units and b.micro:
                await b.micro.execute_lurker_area_denial(lurkers, cached_enemy_units)

        elif (
            intel
            and hasattr(intel, "should_defend")
            and callable(intel.should_defend)
            and intel.should_defend()
        ):
            cached_units = getattr(b, "_cached_units", None)
            if cached_units is None or isinstance(cached_units, List):
                cached_units = b.units
            cached_enemy_units = (
                getattr(b, "_cached_enemy_units", None)
                or getattr(b, "known_enemy_units", None)
                or getattr(b, "enemy_units", None)
            )

            army_types = {
                UnitTypeId.ZERGLING,
                UnitTypeId.ROACH,
                UnitTypeId.HYDRALISK,
                UnitTypeId.LURKER,
                UnitTypeId.QUEEN,
            }
            all_army = (
                cached_units.filter(lambda u: u.type_id in army_types)
                if hasattr(cached_units, "filter")
                else b.units.filter(lambda u: u.type_id in army_types)
            )
            if b.unit_micro and all_army.exists:
                await b.unit_micro.execute_unit_micro(all_army)

            if all_army.exists and b.micro and hasattr(b.micro, "execute_defensive_spread"):
                b.micro.execute_defensive_spread(all_army, b.start_location, radius=15.0)

            if b.opponent_race == Race.Zerg and b.micro:
                zerglings = cached_units(UnitTypeId.ZERGLING)
                zerglings_list = [u for u in zerglings]
                if zerglings_list and cached_enemy_units:
                    enemy_zerglings = [
                        u for u in cached_enemy_units if u.type_id == UnitTypeId.ZERGLING
                    ]
                    if enemy_zerglings and hasattr(b.micro, "execute_zvz_zergling_micro"):
                        await b.micro.execute_zvz_zergling_micro(zerglings_list, enemy_zerglings)

            if b.micro:
                hydras = cached_units(UnitTypeId.HYDRALISK)
                hydras_list = [u for u in hydras]
                if hydras_list and hasattr(b.micro, "execute_overlord_hunter"):
                    await b.micro.execute_overlord_hunter(hydras_list)

            lurkers = [u for u in cached_units(UnitTypeId.LURKER) if u.is_ready]
            enemy_ground = []
            if cached_enemy_units:
                enemy_ground = [
                    u
                    for u in cached_enemy_units
                    if hasattr(u, "health")
                    and u.health > 0
                    and hasattr(u, "is_flying")
                    and not u.is_flying
                ]

            enemies_near_base_cached = None
            if enemy_ground:
                enemies_near_base_cached = [
                    e for e in enemy_ground if e.distance_to(b.start_location) < 25
                ]

            for lurker in lurkers:
                try:
                    lurker_pos = lurker.position
                    lurker_to_start_dist = lurker_pos.distance_to(b.start_location)
                    if lurker.is_burrowed:
                        if enemies_near_base_cached:
                            enemies_in_range = [
                                e
                                for e in enemies_near_base_cached
                                if lurker_pos.distance_to(e.position) <= 10
                            ]
                            if enemies_in_range:
                                lurker.attack(enemies_in_range[0])
                        else:
                            lurker(AbilityId.BURROWUP_LURKER)
                    else:
                        if lurker_to_start_dist < 20:
                            if enemy_ground:
                                lurker(AbilityId.BURROWDOWN_LURKER)
                            else:
                                lurker.move(b.start_location)
                except Exception:
                    pass

    async def maintain_defensive_army(self) -> None:
        b = self.bot
        try:
            army = b.units.filter(lambda u: u.type_id in b.combat_unit_types)
            army_count = army.amount if hasattr(army, "amount") else len(list(army))
            min_army_count = 20 if b.time < 300 else 50
            if army_count < min_army_count:
                larvae = b.units(UnitTypeId.LARVA).ready
                if not larvae.exists:
                    return
                if b.vespene >= 25:
                    if (
                        b.can_afford(UnitTypeId.ROACH)
                        and b.units(UnitTypeId.ROACHWARREN).ready.exists
                    ):
                        if b.supply_left >= 2:
                            try:
                                larvae.random.train(UnitTypeId.ROACH)
                                if b.iteration % 100 == 0:
                                    print(
                                        f"[DEFENSIVE ARMY] [{int(b.time)}s] Building Roach for defense (Army: {army_count}/{min_army_count})"
                                    )
                                return
                            except Exception:
                                pass
                    if (
                        b.can_afford(UnitTypeId.HYDRALISK)
                        and b.units(UnitTypeId.HYDRALISKDEN).ready.exists
                    ):
                        if b.supply_left >= 2:
                            try:
                                larvae.random.train(UnitTypeId.HYDRALISK)
                                if b.iteration % 100 == 0:
                                    print(
                                        f"[DEFENSIVE ARMY] [{int(b.time)}s] Building Hydralisk for defense (Army: {army_count}/{min_army_count})"
                                    )
                                return
                            except Exception:
                                pass
                if (
                    b.can_afford(UnitTypeId.ZERGLING)
                    and b.units(UnitTypeId.SPAWNINGPOOL).ready.exists
                ):
                    if b.supply_left >= 2:
                        try:
                            larvae.random.train(UnitTypeId.ZERGLING)
                            if b.iteration % 100 == 0:
                                print(
                                    f"[DEFENSIVE ARMY] [{int(b.time)}s] Building Zergling for defense (Army: {army_count}/{min_army_count})"
                                )
                            return
                        except Exception:
                            pass
        except Exception as e:
            if b.iteration % 100 == 0:
                print(f"[WARNING] _maintain_defensive_army error: {e}")

    async def defensive_rally(self) -> None:
        b = self.bot
        try:
            army = b.units.filter(lambda u: u.type_id in b.combat_unit_types and u.is_ready)
            if not army.exists:
                return
            enemy_units_obj = getattr(b, "known_enemy_units", None) or getattr(
                b, "enemy_units", None
            )
            enemy_near_base = None
            if enemy_units_obj and hasattr(enemy_units_obj, "exists") and enemy_units_obj.exists:
                townhall_positions = [th.position for th in b.townhalls]
                if townhall_positions:
                    enemy_near_base = enemy_units_obj.filter(
                        lambda u: any(u.distance_to(base) < 30 for base in townhall_positions)
                    )
            if enemy_near_base and enemy_near_base.exists:
                if b.townhalls.exists:
                    main_base = b.townhalls.first
                    closest_enemy = enemy_near_base.closest_to(main_base.position)
                    if closest_enemy:
                        target = closest_enemy.position
                        for unit in army:
                            try:
                                unit.attack(target)
                            except Exception:
                                pass
                        if b.iteration % 100 == 0:
                            print(
                                f"[DEFENSIVE RALLY] [{int(b.time)}s] Enemy detected! Attacking {enemy_near_base.amount} enemies near base"
                            )
            else:
                if b.townhalls.amount > 1:
                    natural_base = None
                    townhalls_list = list(b.townhalls.ready)
                    if len(townhalls_list) >= 2:
                        natural_base = townhalls_list[1]
                    elif len(townhalls_list) >= 1:
                        natural_base = townhalls_list[0]
                    if natural_base:
                        rally_point = natural_base.position.towards(b.game_info.map_center, 8)
                        idle_army = army.filter(lambda u: u.is_idle)
                        for unit in idle_army:
                            try:
                                if unit.distance_to(rally_point) > 5:
                                    unit.move(rally_point)
                            except Exception:
                                pass
                else:
                    if b.townhalls.exists:
                        main_base = b.townhalls.first
                        rally_point = main_base.position.towards(b.game_info.map_center, 8)
                        idle_army = army.filter(lambda u: u.is_idle)
                        for unit in idle_army:
                            try:
                                if unit.distance_to(rally_point) > 5:
                                    unit.move(rally_point)
                            except Exception:
                                pass
        except Exception as e:
            if b.iteration % 100 == 0:
                print(f"[WARNING] _defensive_rally error: {e}")

    async def worker_defense_emergency(self) -> None:
        b = self.bot
        try:
            enemy_units_obj = getattr(b, "known_enemy_units", None) or getattr(
                b, "enemy_units", None
            )
            if not enemy_units_obj:
                return
            townhall_positions = [th.position for th in b.townhalls]
            if not townhall_positions:
                return
            near_enemies = enemy_units_obj.filter(
                lambda u: any(u.distance_to(base) < 15 for base in townhall_positions)
            )
            if not near_enemies.exists:
                intel = getattr(b, "intel", None)
                workers = (
                    intel.cached_workers
                    if (intel and intel.cached_workers is not None)
                    else b.workers
                )
                for drone in workers.filter(lambda w: w.is_attacking):
                    try:
                        closest_mineral = b.mineral_field.closest_to(drone)
                        if closest_mineral:
                            drone.gather(closest_mineral)
                    except Exception:
                        pass
                return
            if near_enemies.exists:
                workers_at_risk = b.workers.filter(
                    lambda w: any(w.distance_to(e) < 12 for e in near_enemies)
                )
                if workers_at_risk.exists:
                    for worker in workers_at_risk:
                        try:
                            nearest_townhall = (
                                b.townhalls.closest_to(worker.position)
                                if b.townhalls.exists
                                else None
                            )
                            if nearest_townhall:
                                if worker.distance_to(nearest_townhall) < 15:
                                    safe_minerals = b.mineral_field.closer_than(
                                        10, nearest_townhall.position
                                    )
                                    if safe_minerals.exists:
                                        await b.do(worker.gather(safe_minerals.closest_to(worker.position)))
                                    else:
                                        retreat_pos = nearest_townhall.position.towards(
                                            worker.position, -3
                                        )
                                        await b.do(worker.move(retreat_pos))
                                else:
                                    await b.do(worker.move(nearest_townhall.position))
                            else:
                                # No townhall found, move to start location
                                if b.start_location:
                                    await b.do(worker.move(b.start_location))
                        except Exception:
                            pass
            my_army = b.units.filter(lambda u: u.type_id in b.combat_unit_types)
            is_outnumbered = my_army.amount < near_enemies.amount if my_army.exists else True
            is_defenseless = not my_army.exists
            
            # CRITICAL: If we have ANY army, workers should NOT be used for defense
            # Workers should gather resources, not fight. Army units should handle defense.
            if my_army.exists and my_army.amount > 0:
                # We have army - workers should gather resources, not fight
                return
            
            # CRITICAL FIX: Minimum drone preservation (prevents economy collapse)
            # Always maintain at least MIN_DRONES_FOR_DEFENSE drones for resource gathering
            worker_count = (
                b.workers.amount if hasattr(b.workers, "amount") else len(list(b.workers))
            )
            from config import Config
            _config = Config()
            MIN_DRONES_FOR_DEFENSE = _config.MIN_DRONES_FOR_DEFENSE
            
            if worker_count < MIN_DRONES_FOR_DEFENSE:
                # ÃÖ¼Ò ÀÏ²Û À¯Áö - µ¿¿øÇÏÁö ¾ÊÀ½ (°æÁ¦ ºØ±« ¹æÁö)
                return
            
            # Calculate maximum workers that can be pulled (preserve minimum)
            max_pullable_workers = max(0, worker_count - MIN_DRONES_FOR_DEFENSE)
            if max_pullable_workers <= 0:
                # Cannot pull any workers without violating minimum
                return
            retreat_threshold = _config.WORKER_DEFENSE_RETREAT_THRESHOLD
            if is_defenseless:
                nearby_workers = b.workers.filter(
                    lambda w: any(w.distance_to(e) < 12 for e in near_enemies)
                )
                if nearby_workers.exists:
                    workers_list = sorted(
                        [w for w in nearby_workers],
                        key=lambda w: w.health_percentage
                        if hasattr(w, "health_percentage")
                        else 1.0,
                        reverse=True,
                    )
                    # CRITICAL FIX: Respect minimum drone preservation
                    # ÃÖ´ë µ¿¿ø °¡´É ¼ö = ÀüÃ¼ ÀÏ²Û - ÃÖ¼Ò À¯Áö ÀÏ²Û ¼ö
                    max_workers_to_pull = min(
                        max_pullable_workers,  # ÃÖ´ë µ¿¿ø °¡´É ¼ö (ÃÖ¼Ò À¯Áö ¼ö º¸Àå)
                        max(int(worker_count * retreat_threshold), 1),  # ÃÖ¼Ò 1±â
                        min(10, len(workers_list)),  # ÃÖ´ë 10±â
                    )
                    
                    # ÀýÃ¼Àý¸í »óÈ²¿¡¼­µµ ÃÖ¼Ò ÀÏ²ÛÀº º¸Á¸
                    if max_workers_to_pull <= 0:
                        # ÃÖ¼Ò ÀÏ²Û ¼ö¸¦ º¸Á¸ÇÒ ¼ö ¾øÀ¸¸é µ¿¿øÇÏÁö ¾ÊÀ½
                        return
                    # CRITICAL FIX: Workers NO LONGER ATTACK - Only retreat to safety
                    # Workers should gather resources, not fight. Army units should handle defense.
                    defense_workers = workers_list[:max_workers_to_pull]
                    for drone in defense_workers:
                        try:
                            # Workers retreat to nearest townhall instead of attacking
                            nearest_townhall = (
                                b.townhalls.closest_to(drone.position)
                                if b.townhalls.exists
                                else None
                            )
                            if nearest_townhall:
                                # Move behind townhall (safe position)
                                safe_pos = nearest_townhall.position.towards(b.start_location, 5)
                                await b.do(drone.move(safe_pos))
                            else:
                                # No townhall, gather nearest mineral
                                if b.mineral_field.exists:
                                    closest_mineral = b.mineral_field.closest_to(drone.position)
                                    if closest_mineral:
                                        await b.do(drone.gather(closest_mineral))
                        except Exception:
                            pass
                critical_structures = b.townhalls
                if critical_structures.exists:
                    for th in critical_structures:
                        enemies_near_th = near_enemies.filter(lambda e: e.distance_to(th) < 10)
                        if enemies_near_th.exists and th.health_percentage < 0.3:
                            if worker_count < 5 and not my_army.exists:
                                if not hasattr(b, "game_ended") or not b.game_ended:
                                    try:
                                        await b.chat_send("GG")
                                        b.game_ended = True
                                        if hasattr(b, "client") and b.client:
                                            await b.client.leave_game()  # type: ignore
                                    except Exception:
                                        pass
                                return
        except Exception as e:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration - getattr(b, "last_error_log_frame", 0) >= 100:
                print(f"[WARNING] Worker defense error: {e}")
                b.last_error_log_frame = current_iteration