# -*- coding: utf-8 -*-
"""
ÀÌº´·Ä(Rogue) ¼±¼ö Àü¼ú ±¸Çö ¸Å´ÏÀú

ÇÙ½É Àü¼ú:
1. ¸Íµ¶Ãæ µå¶ø (Baneling Drop): Àû º´·ÂÀÌ ÀüÁøÇÏ´Â Å¸ÀÌ¹Ö¿¡ µå¶ø
2. ½Ã¾ß ¹Û ¿ìÈ¸ ±âµ¿: ÀûÀÇ ½Ã¾ß ¹üÀ§¸¦ ÇÇÇØ µå¶ø ÁöÁ¡±îÁö ÀÌµ¿
3. ¶ó¹Ù ¼¼ÀÌºù: ±³Àü Á÷Àü ¶ó¹Ù¸¦ ¸ð¾ÆµÎ¾ú´Ù°¡ µå¶ø ÈÄ Æø¹ßÀû »ý»ê
4. ÈÄ¹Ý ¿î¿µ: Á¡¸· °¨Áö ±â¹Ý ÀÇ»ç°áÁ¤
"""

from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from wicked_zerg_bot_pro import WickedZergBotPro

from sc2.ids.ability_id import AbilityId  # type: ignore
from sc2.ids.unit_typeid import UnitTypeId  # type: ignore
from sc2.ids.upgrade_id import UpgradeId  # type: ignore
from sc2.position import Point2  # type: ignore
from sc2.unit import Unit  # type: ignore


class RogueTacticsManager:
    """
    ÀÌº´·Ä(Rogue) ¼±¼ö Àü¼ú ±¸Çö ¸Å´ÏÀú
    
    ÁÖ¿ä ±â´É:
    - ¸Íµ¶Ãæ µå¶ø Å¸ÀÌ¹Ö °¨Áö ¹× ½ÇÇà
    - ½Ã¾ß ¹Û ¿ìÈ¸ ±âµ¿ °æ·Î Å½»ö
    - ¶ó¹Ù ¼¼ÀÌºù ÆÐÅÏ °ü¸®
    - Á¡¸· ±â¹Ý Àû º´·Â °¨Áö
    """

    def __init__(self, bot: "WickedZergBotPro"):
        self.bot = bot
        
        # µå¶ø »óÅÂ
        self.drop_squad: List[Unit] = []  # µå¶ø¿ë ´ë±ºÁÖ + ¸Íµ¶Ãæ
        self.drop_target: Optional[Point2] = None
        self.drop_in_progress: bool = False
        self.last_drop_time: float = 0.0
        self.drop_cooldown: float = 30.0  # µå¶ø Äð´Ù¿î (30ÃÊ)
        
        # ¶ó¹Ù ¼¼ÀÌºù »óÅÂ
        self.larva_saving_mode: bool = False
        self.saved_larva_count: int = 0
        self.larva_save_start_time: float = 0.0
        self.larva_save_duration: float = 10.0  # ¶ó¹Ù ¼¼ÀÌºù Áö¼Ó ½Ã°£ (10ÃÊ)
        
        # Àû º´·Â °¨Áö (Á¡¸· ±â¹Ý)
        self.enemy_on_creep: bool = False
        self.enemy_advancing: bool = False
        self.last_enemy_on_creep_time: float = 0.0
        
        # ´ë±ºÁÖ ¼Ó¾÷ »óÅÂ
        self.overlord_speed_researched: bool = False
        self.overlord_speed_research_time: float = 0.0
        
        # ½Ã¾ß ¹üÀ§ °è»ê¿ë
        self.vision_range: float = 11.0  # ´ë±ºÁÖ ½Ã¾ß ¹üÀ§
        self.enemy_vision_range: float = 9.0  # Àû À¯´Ö Æò±Õ ½Ã¾ß ¹üÀ§

    async def update(self):
        """¸Å ÇÁ·¹ÀÓ ¾÷µ¥ÀÌÆ®"""
        b = self.bot
        
        # ´ë±ºÁÖ ¼Ó¾÷ »óÅÂ È®ÀÎ
        self._check_overlord_speed_upgrade()
        
        # Àû º´·ÂÀÌ Á¡¸·¿¡ ´ê¾Ò´ÂÁö °¨Áö
        self._detect_enemy_on_creep()
        
        # µå¶ø ½ÇÇà
        await self._execute_baneling_drop()
        
        # ¶ó¹Ù ¼¼ÀÌºù °ü¸®
        await self._manage_larva_saving()
        
        # µå¶ø À¯´Ö °ü¸®
        await self._manage_drop_units()

    def _check_overlord_speed_upgrade(self):
        """´ë±ºÁÖ ¼Ó¾÷ »óÅÂ È®ÀÎ"""
        b = self.bot
        
        if UpgradeId.OVERLORDSPEED in b.state.upgrades:
            if not self.overlord_speed_researched:
                self.overlord_speed_researched = True
                self.overlord_speed_research_time = b.time
                print(f"[ROGUE TACTICS] [{int(b.time)}s] Overlord Speed researched - Drop tactics enabled")
        else:
            self.overlord_speed_researched = False

    def _detect_enemy_on_creep(self):
        """
        Àû º´·ÂÀÌ Á¡¸·¿¡ ´ê¾Ò´ÂÁö °¨Áö
        
        Rogue Àü¼ú: Àû º´·ÂÀÌ ³» ±âÁö ¾Õ¸¶´ç Á¡¸· ³¡¿¡ µµ´ÞÇßÀ» ¶§ µå¶ø À¯´Ö Ãâ¹ß
        """
        b = self.bot
        
        # Á¡¸·ÀÌ ÀÖ´Â Áö¿ª È®ÀÎ
        if not b.townhalls.exists:
            self.enemy_on_creep = False
            self.enemy_advancing = False
            return
        
        main_hatch = b.townhalls.first
        if not main_hatch:
            return
        
        # Á¡¸· ¹Ý°æ ³» Àû À¯´Ö È®ÀÎ (Á¡¸·Àº ´ë·« 15-20 À¯´Ö ¹Ý°æ)
        creep_radius = 20.0
        enemy_units = b.enemy_units.closer_than(creep_radius, main_hatch.position)
        
        if enemy_units.exists:
            self.enemy_on_creep = True
            self.last_enemy_on_creep_time = b.time
            
            # ÀûÀÌ ÀüÁø ÁßÀÎÁö È®ÀÎ (ÀÌÀü ÇÁ·¹ÀÓ ´ëºñ À§Ä¡ º¯È­)
            if hasattr(self, "_last_enemy_positions"):
                advancing_count = 0
                for enemy in enemy_units:
                    if enemy.tag in self._last_enemy_positions:
                        last_pos = self._last_enemy_positions[enemy.tag]
                        current_pos = enemy.position
                        # ÀûÀÌ ¿ì¸® ±âÁö ¹æÇâÀ¸·Î ÀÌµ¿ ÁßÀÎÁö È®ÀÎ
                        to_base = main_hatch.position - last_pos
                        movement = current_pos - last_pos
                        if to_base.dot(movement) > 0:  # ³»ÀûÀÌ ¾ç¼ö¸é °°Àº ¹æÇâ
                            advancing_count += 1
                
                self.enemy_advancing = advancing_count >= 3  # 3±â ÀÌ»ó ÀüÁø Áß
            else:
                self.enemy_advancing = True
            
            # Àû À§Ä¡ ÀúÀå
            self._last_enemy_positions = {enemy.tag: enemy.position for enemy in enemy_units}
        else:
            self.enemy_on_creep = False
            # 5ÃÊ ÀÌ»ó ÀûÀÌ Á¡¸·¿¡ ¾øÀ¸¸é ÀüÁø »óÅÂ ÇØÁ¦
            if b.time - self.last_enemy_on_creep_time > 5.0:
                self.enemy_advancing = False

    async def _execute_baneling_drop(self):
        """
        ¸Íµ¶Ãæ µå¶ø ½ÇÇà
        
        Rogue Àü¼ú:
        1. Àû º´·ÂÀÌ ÀüÁøÇÏ´Â Å¸ÀÌ¹Ö °¨Áö
        2. ´ë±ºÁÖ ¼Ó¾÷ ¿Ï·á È®ÀÎ
        3. ¸Íµ¶Ãæ ÁØºñ È®ÀÎ
        4. ½Ã¾ß ¹Û ¿ìÈ¸ ±âµ¿À¸·Î µå¶ø ÁöÁ¡ ÀÌµ¿
        5. Àû º»Áø/È®Àå ±âÁö¿¡ µå¶ø
        
        ÁÖÀÇ: µå¶ø ÁøÇà ÁßÀÌ¸é °è¼Ó ½ÇÇà, ¾Æ´Ï¸é »õ µå¶ø ½ÃÀÛ
        """
        b = self.bot
        
        # µå¶ø ÁøÇà ÁßÀÌ¸é °è¼Ó ½ÇÇà
        if self.drop_in_progress:
            # µå¶ø À¯´Ö »óÅÂ È®ÀÎ
            overlords = b.units(UnitTypeId.OVERLORD)
            drop_overlord = None
            for overlord in overlords:
                if overlord.passengers:  # À¯´ÖÀ» ÅÂ¿î ´ë±ºÁÖ
                    drop_overlord = overlord
                    break
            
            if drop_overlord and self.drop_target:
                # µå¶ø ½ÃÄö½º °è¼Ó ½ÇÇà
                banelings = list(b.units(UnitTypeId.BANELING).ready)
                path = self._calculate_stealth_path(drop_overlord.position, self.drop_target) or [self.drop_target]
                await self._execute_drop_sequence(drop_overlord, banelings, path, self.drop_target)
            else:
                # µå¶ø À¯´ÖÀÌ ¾øÀ¸¸é µå¶ø Áß´Ü
                self.drop_in_progress = False
            return
        
        # »õ µå¶ø ½ÃÀÛ Á¶°Ç È®ÀÎ
        if not self._can_execute_drop():
            return
        
        # µå¶ø À¯´Ö ÁØºñ
        drop_overlord, banelings = await self._prepare_drop_units()
        if not drop_overlord or not banelings:
            return
        
        # µå¶ø Å¸°Ù °áÁ¤
        drop_target = self._find_drop_target()
        if not drop_target:
            return
        
        # ½Ã¾ß ¹Û ¿ìÈ¸ °æ·Î °è»ê
        path = self._calculate_stealth_path(drop_overlord.position, drop_target)
        if not path:
            # ¿ìÈ¸ °æ·Î°¡ ¾øÀ¸¸é Á÷Á¢ ÀÌµ¿ (À§ÇèÇÏÁö¸¸ ½Ãµµ)
            path = [drop_target]
        
        # µå¶ø ½ÇÇà ½ÃÀÛ
        await self._execute_drop_sequence(drop_overlord, banelings, path, drop_target)

    def _can_execute_drop(self) -> bool:
        """µå¶ø ½ÇÇà °¡´É ¿©ºÎ È®ÀÎ"""
        b = self.bot
        
        # 1. ´ë±ºÁÖ ¼Ó¾÷ ¿Ï·á È®ÀÎ
        if not self.overlord_speed_researched:
            return False
        
        # 2. Äð´Ù¿î È®ÀÎ
        if b.time - self.last_drop_time < self.drop_cooldown:
            return False
        
        # 3. ÀÌ¹Ì µå¶ø ÁøÇà ÁßÀÌ¸é ½ºÅµ
        if self.drop_in_progress:
            return False
        
        # 4. ÀûÀÌ Á¡¸·¿¡ ÀÖ°í ÀüÁø ÁßÀÎÁö È®ÀÎ (Rogue Àü¼ú ÇÙ½É)
        if not (self.enemy_on_creep and self.enemy_advancing):
            return False
        
        # 5. ¸Íµ¶ÃæÀÌ ÁØºñµÇ¾î ÀÖ´ÂÁö È®ÀÎ
        banelings = b.units(UnitTypeId.BANELING).ready
        if not banelings.exists or banelings.amount < 4:  # ÃÖ¼Ò 4±â ÇÊ¿ä
            return False
        
        # 6. µå¶ø¿ë ´ë±ºÁÖ È®ÀÎ
        overlords = b.units(UnitTypeId.OVERLORD).ready
        if not overlords.exists:
            return False
        
        return True

    async def _prepare_drop_units(self) -> Tuple[Optional[Unit], List[Unit]]:
        """µå¶ø À¯´Ö ÁØºñ"""
        b = self.bot
        
        # ¸Íµ¶Ãæ ¼±ÅÃ (ÃÖ´ë 8±â)
        banelings = list(b.units(UnitTypeId.BANELING).ready)[:8]
        if len(banelings) < 4:
            return None, []
        
        # µå¶ø¿ë ´ë±ºÁÖ ¼±ÅÃ (°¡Àå °¡±î¿î ´ë±ºÁÖ)
        overlords = b.units(UnitTypeId.OVERLORD).ready
        if not overlords.exists:
            return None, []
        
        # ÀÌ¹Ì À¯´ÖÀ» ÅÂ¿î ´ë±ºÁÖ°¡ ÀÖÀ¸¸é ¿ì¼± »ç¿ë
        for overlord in overlords:
            if overlord.passengers:
                return overlord, banelings
        
        # ºó ´ë±ºÁÖ ¼±ÅÃ
        drop_overlord = overlords.closest_to(b.townhalls.first.position)
        return drop_overlord, banelings

    def _find_drop_target(self) -> Optional[Point2]:
        """
        µå¶ø Å¸°Ù °áÁ¤
        
        ¿ì¼±¼øÀ§:
        1. Àû º»Áø ÀÏ²Û ÁýÁß Áö¿ª
        2. Àû È®Àå ±âÁö ÀÏ²Û
        3. Àû ÁÖ¿ä °Ç¹° (°ø¼º ÀüÂ÷ ¶óÀÎ µî)
        """
        b = self.bot
        
        # Àû º»Áø À§Ä¡ È®ÀÎ
        if b.enemy_start_locations:
            enemy_main = b.enemy_start_locations[0]
            
            # Àû ÀÏ²Û À§Ä¡ È®ÀÎ
            enemy_workers = b.enemy_units.filter(
                lambda u: u.type_id in [UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE]
            )
            
            if enemy_workers.exists:
                # ÀÏ²ÛÀÌ °¡Àå ¸¹Àº Áö¿ª Ã£±â
                worker_positions = [w.position for w in enemy_workers]
                if worker_positions:
                    # ÀÏ²ÛµéÀÇ Áß½ÉÁ¡ °è»ê
                    center_x = sum(p.x for p in worker_positions) / len(worker_positions)
                    center_y = sum(p.y for p in worker_positions) / len(worker_positions)
                    return Point2((center_x, center_y))
            
            # ÀÏ²ÛÀÌ º¸ÀÌÁö ¾ÊÀ¸¸é º»Áø Áß½É
            return enemy_main
        
        # Àû º»ÁøÀ» ¸ð¸£¸é ¸Ê Áß½É
        return b.game_info.map_center

    def _calculate_stealth_path(
        self, start: Point2, target: Point2
    ) -> Optional[List[Point2]]:
        """
        ½Ã¾ß ¹Û ¿ìÈ¸ ±âµ¿ °æ·Î °è»ê
        
        Rogue Àü¼ú: ÀûÀÇ ½Ã¾ß ¹üÀ§¸¦ ÇÇÇØ ¸Ê °¡ÀåÀÚ¸®¸¦ ÀÌ¿ëÇÏ¿© ÀÌµ¿
        
        ¾Ë°í¸®Áò:
        1. Àû À¯´ÖÀÇ ½Ã¾ß ¹üÀ§ È®ÀÎ
        2. Á÷Á¢ °æ·Î»ó¿¡ Àû ½Ã¾ß°¡ ÀÖÀ¸¸é ¿ìÈ¸ °æ·Î °è»ê
        3. ¸Ê °¡ÀåÀÚ¸®¸¦ µû¶ó ÀÌµ¿ÇÏ¿© Àû ½Ã¾ß È¸ÇÇ
        """
        b = self.bot
        
        # 1. ¸Ê °æ°è È®ÀÎ
        map_width = b.game_info.map_size.width
        map_height = b.game_info.map_size.height
        
        # 2. Àû À¯´ÖÀÇ ½Ã¾ß ¹üÀ§ È®ÀÎ
        enemy_units = b.enemy_units
        if not enemy_units.exists:
            # ÀûÀÌ º¸ÀÌÁö ¾ÊÀ¸¸é Á÷Á¢ °æ·Î
            return [target]
        
        # 3. Á÷Á¢ °æ·Î»ó¿¡ Àû ½Ã¾ß°¡ ÀÖ´ÂÁö È®ÀÎ
        direct_path_blocked = False
        for enemy in enemy_units:
            # Àû°ú Á÷Á¢ °æ·ÎÀÇ ÃÖ´Ü °Å¸® °è»ê
            enemy_pos = enemy.position
            # °£´ÜÇÑ °Å¸® Ã¼Å©: Àû ½Ã¾ß ¹üÀ§ ³»¿¡ °æ·Î°¡ ÀÖ´ÂÁö
            to_target = target - start
            to_enemy = enemy_pos - start
            
            # ³»ÀûÀ» »ç¿ëÇÏ¿© °æ·Î°¡ Àû ½Ã¾ß ¹üÀ§ ³»¿¡ ÀÖ´ÂÁö È®ÀÎ
            if to_target.length > 0:
                projection = (to_enemy.dot(to_target) / to_target.length) / to_target.length
                if 0 < projection < 1:  # °æ·Î»ó¿¡ ÀÖÀ½
                    closest_point = start + to_target * projection
                    if closest_point.distance_to(enemy_pos) < self.enemy_vision_range:
                        direct_path_blocked = True
                        break
        
        # Á÷Á¢ °æ·Î°¡ ¸·ÇôÀÖÁö ¾ÊÀ¸¸é Á÷Á¢ °æ·Î »ç¿ë
        if not direct_path_blocked:
            return [target]
        
        # 4. ¿ìÈ¸ °æ·Î °è»ê: ¸Ê °¡ÀåÀÚ¸®¸¦ µû¶ó ÀÌµ¿
        waypoints = []
        
        # ½ÃÀÛÁ¡¿¡¼­ ¸Ê °¡ÀåÀÚ¸®·Î
        # ¿ÞÂÊ/¿À¸¥ÂÊ °¡ÀåÀÚ¸® Áß Å¸°Ù¿¡ ´õ °¡±î¿î ÂÊ ¼±ÅÃ
        left_edge = Point2((0, start.y))
        right_edge = Point2((map_width, start.y))
        
        # Å¸°Ù ¹æÇâÀÇ °¡ÀåÀÚ¸® ¼±ÅÃ
        if abs(start.x - left_edge.x) < abs(start.x - right_edge.x):
            waypoints.append(left_edge)
        else:
            waypoints.append(right_edge)
        
        # Å¸°Ù ¹æÇâÀÇ °¡ÀåÀÚ¸®¸¦ µû¶ó ÀÌµ¿
        waypoints.append(Point2((waypoints[0].x, target.y)))
        waypoints.append(target)
        
        return waypoints

    async def _execute_drop_sequence(
        self,
        overlord: Unit,
        banelings: List[Unit],
        path: List[Point2],
        target: Point2,
    ):
        """
        µå¶ø ½ÃÄö½º ½ÇÇà
        
        Rogue Àü¼ú: ¸Íµ¶ÃæÀ» ´ë±ºÁÖ¿¡ ÅÂ¿ö Àû º»Áø/È®Àå ±âÁö¿¡ µå¶ø
        
        ÁÖÀÇ: ÀÌ ¸Þ¼­µå´Â ¸Å ÇÁ·¹ÀÓ È£ÃâµÇ¸ç, µå¶ø »óÅÂ¿¡ µû¶ó ´Ü°èº°·Î ½ÇÇàµË´Ï´Ù.
        """
        b = self.bot
        
        # µå¶ø »óÅÂ ÃÊ±âÈ­ (Ã¹ ½ÇÇà ½Ã)
        if not self.drop_in_progress:
            self.drop_in_progress = True
            self.drop_target = target
            self.drop_squad = [overlord] + banelings[:8]
            print(f"[ROGUE DROP] [{int(b.time)}s] Drop sequence started - Target: {target}")
        
        try:
            # 1. ¸Íµ¶ÃæÀ» ´ë±ºÁÖ¿¡ ÅÂ¿ì±â (¾ÆÁ÷ ÅÂ¿ìÁö ¾Ê¾ÒÀ¸¸é)
            if not overlord.passengers or len(overlord.passengers) < len(banelings):
                for baneling in banelings[:8]:  # ÃÖ´ë 8±â
                    if baneling.is_ready and overlord.cargo_space_left > 0:
                        # python-sc2: load ¸í·É »ç¿ë
                        try:
                            # LOAD ability´Â À¯´Ö Å¸ÀÔ¿¡ µû¶ó ÀÚµ¿ ¼±ÅÃµÊ
                            await b.do(overlord(AbilityId.LOAD, baneling))
                        except Exception:
                            # ´ëÃ¼ ¹æ¹ý ½Ãµµ
                            try:
                                if hasattr(overlord, "load"):
                                    overlord.load(baneling)
                            except Exception:
                                pass
                return  # ´ÙÀ½ ÇÁ·¹ÀÓ¿¡ °è¼Ó
            
            # 2. °æ·Î¸¦ µû¶ó ÀÌµ¿
            if path and len(path) > 0:
                # ÇöÀç waypoint È®ÀÎ
                current_waypoint_idx = getattr(self, "_current_waypoint_idx", 0)
                if current_waypoint_idx < len(path):
                    next_waypoint = path[current_waypoint_idx]
                    
                    # waypoint¿¡ µµ´ÞÇß´ÂÁö È®ÀÎ
                    if overlord.distance_to(next_waypoint) < 3.0:
                        # ´ÙÀ½ waypoint·Î ÀÌµ¿
                        current_waypoint_idx += 1
                        self._current_waypoint_idx = current_waypoint_idx
                    
                    # ´ÙÀ½ waypoint·Î ÀÌµ¿ ¸í·É
                    if current_waypoint_idx < len(path):
                        overlord.move(path[current_waypoint_idx])
                    else:
                        # ¸ðµç waypoint¸¦ Áö³ªÃÆÀ¸¸é Å¸°ÙÀ¸·Î Á÷Á¢ ÀÌµ¿
                        overlord.move(target)
                else:
                    # °æ·Î°¡ ¾øÀ¸¸é Å¸°ÙÀ¸·Î Á÷Á¢ ÀÌµ¿
                    overlord.move(target)
            
            # 3. Å¸°Ù ÁöÁ¡¿¡ µµ´ÞÇß´ÂÁö È®ÀÎÇÏ°í µå¶ø
            if overlord.distance_to(target) < 8.0:  # 8 À¯´Ö ÀÌ³»¸é µå¶ø °¡´É
                # µå¶ø ½ÇÇà
                try:
                    # python-sc2: unload_all ¸í·É »ç¿ë (À§Ä¡ ÁöÁ¤)
                    # UNLOADALL_AT ¶Ç´Â UNLOADALL »ç¿ë
                    try:
                        await b.do(overlord(AbilityId.UNLOADALL_AT, target))
                    except (AttributeError, KeyError):
                        # ´ëÃ¼ ¹æ¹ý: UNLOADALL »ç¿ë
                        try:
                            await b.do(overlord(AbilityId.UNLOADALL, target))
                        except (AttributeError, KeyError):
                            # ÃÖÁ¾ ´ëÃ¼: Á÷Á¢ ¸Þ¼­µå È£Ãâ
                            if hasattr(overlord, "unload_all"):
                                overlord.unload_all(target)
                except Exception as unload_error:
                    # µå¶ø ½ÇÆÐ ½Ã ·Î±×¸¸ Ãâ·Â (´ÙÀ½ ÇÁ·¹ÀÓ¿¡ Àç½Ãµµ)
                    if b.iteration % 50 == 0:
                        print(f"[ROGUE DROP] Unload attempt failed: {unload_error}")
                
                print(f"[ROGUE DROP] [{int(b.time)}s] Baneling drop executed at {target}")
                self.last_drop_time = b.time
                
                # ¶ó¹Ù ¼¼ÀÌºù ÇØÁ¦ (µå¶ø ÈÄ Æø¹ßÀû »ý»ê)
                self.larva_saving_mode = False
                
                # µå¶ø ¿Ï·á
                self.drop_in_progress = False
                self._current_waypoint_idx = 0  # waypoint ÀÎµ¦½º ÃÊ±âÈ­
                
        except Exception as e:
            print(f"[ROGUE DROP ERROR] Drop execution failed: {e}")
            import traceback
            traceback.print_exc()
            # ¿¡·¯ ¹ß»ý ½Ã µå¶ø Áß´Ü
            self.drop_in_progress = False

    async def _manage_larva_saving(self):
        """
        ¶ó¹Ù ¼¼ÀÌºù °ü¸®
        
        Rogue Àü¼ú: ±³Àü Á÷Àü ¶ó¹Ù¸¦ ¼Ò¸ðÇÏÁö ¾Ê°í ¸ð¾ÆµÎ¾ú´Ù°¡,
        µå¶øÀ¸·Î Àû ÀÏ²ÛÀÌ³ª ÁÖ¿ä º´·ÂÀ» ¼Ô¾Æ³½ Á÷ÈÄ ÇÑ²¨¹ø¿¡ Æø¹ßÀûÀ¸·Î º´·ÂÀ» Âï¾î³¿
        """
        b = self.bot
        
        # ÀûÀÌ Á¡¸·¿¡ ÀÖ°í ÀüÁø ÁßÀÌ¸é ¶ó¹Ù ¼¼ÀÌºù ½ÃÀÛ
        if self.enemy_on_creep and self.enemy_advancing and not self.larva_saving_mode:
            self.larva_saving_mode = True
            self.larva_save_start_time = b.time
            larvae = b.units(UnitTypeId.LARVA)
            self.saved_larva_count = larvae.amount if larvae.exists else 0
            print(f"[ROGUE LARVA SAVE] [{int(b.time)}s] Larva saving started ({self.saved_larva_count} larvae)")
        
        # ¶ó¹Ù ¼¼ÀÌºù ¸ðµå ÇØÁ¦ Á¶°Ç
        if self.larva_saving_mode:
            # 1. µå¶ø ¿Ï·á ÈÄ
            if b.time - self.last_drop_time < 2.0 and self.last_drop_time > 0:
                self.larva_saving_mode = False
                print(f"[ROGUE LARVA SAVE] [{int(b.time)}s] Larva saving ended - Drop completed, explosive production enabled")
            
            # 2. ½Ã°£ ÃÊ°ú (10ÃÊ)
            elif b.time - self.larva_save_start_time > self.larva_save_duration:
                self.larva_saving_mode = False
                print(f"[ROGUE LARVA SAVE] [{int(b.time)}s] Larva saving ended - Timeout")
            
            # 3. ÀûÀÌ Á¡¸·¿¡¼­ ¹þ¾î³²
            elif not self.enemy_on_creep and b.time - self.last_enemy_on_creep_time > 3.0:
                self.larva_saving_mode = False
                print(f"[ROGUE LARVA SAVE] [{int(b.time)}s] Larva saving ended - Enemy retreated")

    async def _manage_drop_units(self):
        """
        µå¶ø À¯´Ö °ü¸® (´ë±ºÁÖ + ¸Íµ¶Ãæ)
        
        µå¶ø ÁøÇà ÁßÀÎ ´ë±ºÁÖÀÇ »óÅÂ¸¦ È®ÀÎÇÏ°í °ü¸®
        (ÇöÀç´Â _execute_drop_sequence¿¡¼­ Ã³¸®ÇÏ¹Ç·Î ¿©±â¼­´Â Ãß°¡ °ü¸®¸¸ ¼öÇà)
        """
        b = self.bot
        
        # µå¶ø ÁøÇà ÁßÀÌ ¾Æ´Ï¸é ½ºÅµ
        if not self.drop_in_progress:
            return
        
        # µå¶ø À¯´Ö »óÅÂ È®ÀÎ (Ãß°¡ ·ÎÁ÷ ÇÊ¿ä ½Ã ±¸Çö)
        # ÇöÀç´Â _execute_drop_sequence¿¡¼­ ¸ðµç µå¶ø ·ÎÁ÷À» Ã³¸®

    def should_save_larva(self) -> bool:
        """¶ó¹Ù ¼¼ÀÌºù ¸ðµå ¿©ºÎ ¹ÝÈ¯"""
        return self.larva_saving_mode

    def get_enemy_on_creep_status(self) -> Tuple[bool, bool]:
        """ÀûÀÌ Á¡¸·¿¡ ÀÖ´ÂÁö, ÀüÁø ÁßÀÎÁö ¹ÝÈ¯"""
        return self.enemy_on_creep, self.enemy_advancing

    def get_drop_readiness(self) -> bool:
        """µå¶ø ÁØºñ »óÅÂ ¹ÝÈ¯"""
        return (
            self.overlord_speed_researched
            and not self.drop_in_progress
            and (self.bot.time - self.last_drop_time) >= self.drop_cooldown
        )
