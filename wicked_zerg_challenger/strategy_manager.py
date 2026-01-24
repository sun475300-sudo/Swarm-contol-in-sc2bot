# -*- coding: utf-8 -*-
"""
Strategy Manager - Race-specific and Emergency Mode Controller

Features:
1. Race-specific unit composition adjustments
2. Rush/Cheese detection and Emergency Mode
3. Dynamic strategy switching
4. Rogue Tactics integration

프로게이머 참고:
- 대 테란: 뮤탈리스크 + 바퀴 + 맹독충
- 대 프로토스: 히드라리스크 + 바퀴 + 점막 확장
- 대 저그: 저글링 + 맹독충 + 뮤탈리스크
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from utils.logger import get_logger


class GamePhase(Enum):
    """게임 페이즈"""
    EARLY = "early"      # 0-4분
    MID = "mid"          # 4-10분
    LATE = "late"        # 10분+


class StrategyMode(Enum):
    """전략 모드"""
    NORMAL = "normal"
    EMERGENCY = "emergency"
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    ALL_IN = "all_in"


class EnemyRace(Enum):
    """상대 종족"""
    TERRAN = "Terran"
    PROTOSS = "Protoss"
    ZERG = "Zerg"
    RANDOM = "Random"
    UNKNOWN = "Unknown"


class StrategyManager:
    """
    종족별 전략 및 Emergency Mode 관리자

    Features:
    - 상대 종족에 따른 유닛 비율 조정
    - 러시/치즈 감지 및 긴급 대응
    - Rogue Tactics 연동
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("StrategyManager")

        # 전략 상태
        self.current_mode = StrategyMode.NORMAL
        self.detected_enemy_race = EnemyRace.UNKNOWN
        self.game_phase = GamePhase.EARLY

        # Emergency Mode 설정
        self.emergency_active = False
        self.emergency_start_time = 0.0
        self.emergency_duration = 120.0  # 2분 지속

        # 러시 감지 설정
        self.rush_detection_threshold = 150.0  # 2:30 이전 공격 = 러시
        self.cheese_detection_threshold = 120.0  # 2분 이전 공격 = 치즈

        # ★★★ 로그 스팸 방지 ★★★
        self.last_air_threat_log = 0
        self.last_major_attack_log = 0
        self.last_high_templar_log = 0  # 하이템플러/아콘 로그 쿨다운
        self.last_disruptor_log = 0  # 디스럽터 로그 쿨다운
        self.log_cooldown = 5.0  # 5초마다만 로그

        # ★★★ 4분 이전 견제 시스템 ★★★
        self.early_harassment_active = False
        self.last_harassment_time = 0
        self.harassment_interval = 30.0  # 30초마다 견제

        # 종족별 유닛 비율 (ZERGLING, ROACH, HYDRA, MUTALISK, BANELING, RAVAGER, CORRUPTOR)
        self.race_unit_ratios = {
            EnemyRace.TERRAN: {
                GamePhase.EARLY: {"zergling": 0.3, "roach": 0.4, "baneling": 0.3},
                GamePhase.MID: {"zergling": 0.2, "roach": 0.3, "hydra": 0.2, "mutalisk": 0.3},
                GamePhase.LATE: {"zergling": 0.1, "roach": 0.2, "hydra": 0.3, "mutalisk": 0.4},
            },
            # ★★★ 프로토스 상대 전략 강화 ★★★
            # 불멸자 → 레이바저 담즙, 저글링 포위
            # 콜로서스 → 커럽터, 레이바저 담즙
            # 차원분광기 → 퀸, 히드라
            # 보호막 배터리 → 레이바저 담즙
            EnemyRace.PROTOSS: {
                # 초반: 저글링 압박 + 레이바저 담즙으로 포스필드/배터리 견제
                GamePhase.EARLY: {"zergling": 0.3, "roach": 0.3, "ravager": 0.3, "queen": 0.1},
                # 중반: 히드라 중심 + 레이바저 담즙 + 커럽터 (콜로서스/공허)
                GamePhase.MID: {"roach": 0.15, "ravager": 0.2, "hydra": 0.4, "corruptor": 0.25},
                # 후반: 히드라 + 커럽터/감염충 (강화장막/둥지벌레)
                GamePhase.LATE: {"hydra": 0.35, "corruptor": 0.3, "ravager": 0.15, "infestor": 0.2},
            },
            EnemyRace.ZERG: {
                GamePhase.EARLY: {"zergling": 0.5, "baneling": 0.5},
                GamePhase.MID: {"zergling": 0.3, "roach": 0.2, "baneling": 0.3, "mutalisk": 0.2},
                GamePhase.LATE: {"zergling": 0.2, "roach": 0.2, "hydra": 0.2, "mutalisk": 0.4},
            },
            EnemyRace.UNKNOWN: {
                GamePhase.EARLY: {"zergling": 0.5, "roach": 0.3, "baneling": 0.2},
                GamePhase.MID: {"zergling": 0.2, "roach": 0.3, "hydra": 0.3, "mutalisk": 0.2},
                GamePhase.LATE: {"zergling": 0.1, "roach": 0.2, "hydra": 0.3, "mutalisk": 0.4},
            },
        }

        # Emergency Mode 비율 (방어 우선)
        self.emergency_ratios = {
            "zergling": 0.5,
            "roach": 0.25,
            "baneling": 0.15,  # 맹독충 추가 (러쉬 방어용)
            "queen": 0.1,  # 퀸 추가 생산 (트랜스퓨전 + 방어)
        }

        # 방어 건물 긴급 건설 플래그
        self.emergency_spine_requested = False
        self.emergency_spore_requested = False

        # Rogue Tactics 연동
        self.rogue_tactics_active = False
        self.larva_saving_mode = False

    def update(self) -> None:
        """매 스텝마다 호출하여 전략 업데이트"""
        self._detect_enemy_race()
        self._update_game_phase()
        self._check_rush_detection()
        self._check_early_harassment()  # ★ 1-4분 견제 시스템 ★
        self._check_rogue_tactics()
        self._update_strategy_mode()
        self._update_counter_build()  # 적 빌드에 따른 대응
        self._detect_direct_air_threat()  # ★ 직접 공중 유닛 감지 ★
        self._counter_protoss_units()  # ★ 프로토스 유닛 카운터 ★

    def _detect_enemy_race(self) -> None:
        """상대 종족 감지"""
        if self.detected_enemy_race != EnemyRace.UNKNOWN:
            return

        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race is None:
            return

        race_name = str(enemy_race)
        if "Terran" in race_name:
            self.detected_enemy_race = EnemyRace.TERRAN
        elif "Protoss" in race_name:
            self.detected_enemy_race = EnemyRace.PROTOSS
        elif "Zerg" in race_name:
            self.detected_enemy_race = EnemyRace.ZERG
        elif "Random" in race_name:
            self.detected_enemy_race = EnemyRace.RANDOM

    def _update_game_phase(self) -> None:
        """게임 페이즈 업데이트"""
        game_time = getattr(self.bot, "time", 0.0)

        if game_time < 240:  # 4분
            self.game_phase = GamePhase.EARLY
        elif game_time < 600:  # 10분
            self.game_phase = GamePhase.MID
        else:
            self.game_phase = GamePhase.LATE

    def _check_rush_detection(self) -> None:
        """러시/치즈 감지 (초반 + 중후반)"""
        game_time = getattr(self.bot, "time", 0.0)

        # 이미 Emergency Mode면 스킵
        if self.emergency_active:
            # Emergency 종료 체크
            if game_time - self.emergency_start_time > self.emergency_duration:
                self._end_emergency_mode()
            return

        # 초반 러시 감지 (3분 이전)
        if game_time < self.rush_detection_threshold:
            is_rush = self._detect_early_aggression(game_time)
            if is_rush:
                self._activate_emergency_mode(game_time)
                return

        # 중후반 대규모 공격 감지 (4분 이후)
        if game_time >= 240:
            is_major_attack = self._detect_major_attack(game_time)
            if is_major_attack:
                self._activate_defense_mode(game_time)

    def _detect_early_aggression(self, game_time: float) -> bool:
        """초반 공격 감지"""
        # 게임 초반이 아니면 러시가 아님
        if game_time > self.rush_detection_threshold:
            return False

        # Intel Manager 활용
        intel = getattr(self.bot, "intel", None)
        if intel:
            if hasattr(intel, "is_under_attack") and intel.is_under_attack():
                return True
            if hasattr(intel, "detected_rush") and intel.detected_rush:
                return True

        # 직접 적 유닛 체크
        if hasattr(self.bot, "enemy_units") and self.bot.enemy_units:
            if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
                main_base = self.bot.townhalls.first
                # ★ CRITICAL: 비상 모드 조건 완화 (30 → 15) - 확장 차단 방지 ★
                nearby_enemies = [e for e in self.bot.enemy_units
                                 if e.can_attack and e.distance_to(main_base) < 15]
                # 적 3마리 이상일 때만 러시로 판정 (정찰 유닛 무시)
                if len(nearby_enemies) >= 3:
                    return True

        return False

    def _check_early_harassment(self) -> None:
        """
        1-4분 견제 시스템

        1분부터 시작하여 30초마다 적 본진을 견제
        저글링, 뮤탈리스크 등 빠른 유닛으로 적 일꾼 견제 및 정보 수집
        """
        game_time = getattr(self.bot, "time", 0.0)

        # 1분부터 4분까지만 활성화
        if game_time < 60 or game_time >= 240:
            self.early_harassment_active = False
            return

        # 30초마다 견제
        # 30초마다 견제
        if game_time - self.last_harassment_time < self.harassment_interval:
            return

        self.last_harassment_time = game_time
        self.early_harassment_active = True
        
        # Log only - Control is delegated to CombatManager
        self.logger.info(f"[{int(game_time)}s] EARLY HARASSMENT: Signal sent to CombatManager")

    def _detect_major_attack(self, game_time: float) -> bool:
        """
        중후반 대규모 공격 감지

        조건:
        1. 적 군대가 우리 기지 근처에 있음
        2. 적 군대 규모가 일정 수준 이상
        3. 고위협 유닛 (시즈탱크, 콜로서스 등) 포함
        """
        if not hasattr(self.bot, "enemy_units") or not hasattr(self.bot, "townhalls"):
            return False

        if not self.bot.townhalls.exists:
            return False

        enemy_units = self.bot.enemy_units
        if not enemy_units:
            return False

        # 고위협 유닛 목록 (중후반 푸쉬의 핵심)
        high_threat_units = {
            # 테란
            "SIEGETANK", "SIEGETANKSIEGED", "THOR", "BATTLECRUISER",
            "LIBERATOR", "LIBERATORAG", "CYCLONE", "WIDOWMINE",
            # 프로토스
            "COLOSSUS", "DISRUPTOR", "IMMORTAL", "ARCHON",
            "CARRIER", "TEMPEST", "VOIDRAY", "HIGHTEMPLAR",
            # 저그
            "ULTRALISK", "BROODLORD", "RAVAGER", "LURKER", "LURKERMP"
        }

        total_threat_score = 0
        high_threat_count = 0
        enemies_near_base = []

        for th in self.bot.townhalls:
            for enemy in enemy_units:
                try:
                    if enemy.distance_to(th.position) < 40:  # 기지 40 거리 내
                        enemies_near_base.append(enemy)

                        # 위협 점수 계산
                        enemy_type = getattr(enemy.type_id, "name", "").upper()

                        if enemy_type in high_threat_units:
                            high_threat_count += 1
                            total_threat_score += 10  # 고위협 유닛
                        elif enemy.can_attack:
                            total_threat_score += 2  # 일반 전투 유닛
                except Exception:
                    continue

        # 대규모 공격 판정
        # 조건: 위협 점수 20 이상 또는 고위협 유닛 2개 이상
        if total_threat_score >= 20 or high_threat_count >= 2:
            # ★★★ 로그 스팸 방지: 5초마다만 출력 ★★★
            if game_time - self.last_major_attack_log > self.log_cooldown:
                self.logger.warning(f"[{int(game_time)}s] MAJOR ATTACK DETECTED! "
                                    f"Threat score: {total_threat_score}, High-threat units: {high_threat_count}")
                self.last_major_attack_log = game_time
            return True

        return False

    def _activate_defense_mode(self, game_time: float) -> None:
        """
        중후반 방어 모드 활성화

        Emergency Mode와 다르게:
        1. 드론 생산은 계속 (경제 유지)
        2. 군대 집결 우선
        3. 방어 건물 추가 건설
        """
        # 이미 방어 모드면 스킵
        if self.current_mode == StrategyMode.DEFENSIVE:
            return

        self.current_mode = StrategyMode.DEFENSIVE

        # ★★★ 로그 스팸 방지: 모드 전환 시에만 출력 ★★★
        self.logger.warning(f"[{int(game_time)}s] DEFENSE MODE ACTIVATED - Major attack incoming!")

        # 군대 집결 신호
        self._request_army_rally()

        # 확장 기지 방어 건물 추가 요청
        self.emergency_spine_requested = True

        # 적 공중 유닛 체크
        if hasattr(self.bot, "enemy_units"):
            air_threats = ["MUTALISK", "VOIDRAY", "ORACLE", "PHOENIX",
                         "BATTLECRUISER", "CARRIER", "LIBERATOR", "BROODLORD"]
            for enemy in self.bot.enemy_units:
                enemy_type = getattr(enemy.type_id, "name", "").upper()
                if enemy_type in air_threats:
                    self.emergency_spore_requested = True
                    break

    def _request_army_rally(self) -> None:
        """군대 집결 요청"""
        # Combat Manager에 집결 신호 전송
        combat = getattr(self.bot, "combat_manager", None)
        if combat:
            # 집결 포인트를 위협받는 기지 근처로 설정
            if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
                rally_pos = self.bot.townhalls.first.position
                combat._rally_point = rally_pos
                combat._rally_point = rally_pos
                combat._min_army_for_attack = 999  # 공격 중지, 방어 우선
                self.logger.info("Army rallying to defend base!")

    def _update_counter_build(self) -> None:
        """
        적 빌드에 따른 대응 빌드 업데이트

        Intel Manager에서 감지한 적 빌드 패턴에 따라
        아군 유닛 비율을 조정합니다.
        """
        intel = getattr(self.bot, "intel", None)
        if not intel:
            return

        enemy_pattern = ""
        if hasattr(intel, "get_enemy_build_pattern"):
            enemy_pattern = intel.get_enemy_build_pattern()

        if enemy_pattern == "unknown":
            return

        game_time = getattr(self.bot, "time", 0)

        # === 적 빌드별 대응 유닛 비율 설정 ===

        # 테란 바이오 (해병/의무관)
        if enemy_pattern == "terran_bio":
            self.race_unit_ratios[self.detected_enemy_race] = {
                GamePhase.EARLY: {"zergling": 0.3, "baneling": 0.5, "roach": 0.2},
                GamePhase.MID: {"zergling": 0.2, "baneling": 0.4, "mutalisk": 0.3, "ultralisk": 0.1},
                GamePhase.LATE: {"zergling": 0.2, "baneling": 0.3, "ultralisk": 0.3, "mutalisk": 0.2},
            }

        # 테란 메카닉 (탱크/토르)
        elif enemy_pattern == "terran_mech":
            self.race_unit_ratios[self.detected_enemy_race] = {
                GamePhase.EARLY: {"zergling": 0.4, "roach": 0.4, "ravager": 0.2},
                GamePhase.MID: {"roach": 0.2, "hydra": 0.4, "mutalisk": 0.3, "corruptor": 0.1},
                GamePhase.LATE: {"hydra": 0.3, "corruptor": 0.3, "broodlord": 0.2, "viper": 0.2},
            }

        # 프로토스 스타게이트 (공중 유닛)
        elif enemy_pattern == "protoss_stargate":
            self._handle_air_threat()
            self.race_unit_ratios[self.detected_enemy_race] = {
                GamePhase.EARLY: {"zergling": 0.3, "queen": 0.2, "hydra": 0.5},
                GamePhase.MID: {"hydra": 0.5, "corruptor": 0.3, "queen": 0.2},
                GamePhase.LATE: {"hydra": 0.4, "corruptor": 0.4, "viper": 0.2},
            }

        # 프로토스 로보 (불멸자/거신)
        elif enemy_pattern == "protoss_robo":
            self.race_unit_ratios[self.detected_enemy_race] = {
                GamePhase.EARLY: {"zergling": 0.3, "roach": 0.5, "ravager": 0.2},
                GamePhase.MID: {"roach": 0.3, "hydra": 0.4, "corruptor": 0.3},
                GamePhase.LATE: {"hydra": 0.3, "corruptor": 0.3, "broodlord": 0.2, "viper": 0.2},
            }

        # 저그 뮤탈 (공중)
        elif enemy_pattern == "zerg_muta":
            self._handle_air_threat()
            self.race_unit_ratios[self.detected_enemy_race] = {
                GamePhase.EARLY: {"zergling": 0.3, "queen": 0.3, "hydra": 0.4},
                GamePhase.MID: {"hydra": 0.5, "queen": 0.2, "mutalisk": 0.3},
                GamePhase.LATE: {"hydra": 0.4, "corruptor": 0.3, "infestor": 0.3},
            }

        # 러쉬 대응 (공통)
        elif "rush" in enemy_pattern or "proxy" in enemy_pattern or "12pool" in enemy_pattern:
            self.emergency_ratios = {
                "zergling": 0.5,
                "roach": 0.3,
                "queen": 0.2,
            }
            self.emergency_spine_requested = True

        # 로그 출력 (30초마다)
        if int(game_time) % 30 == 0 and self.bot.iteration % 22 == 0:
            self.logger.info(f"[{int(game_time)}s] Counter build for {enemy_pattern}")

    def _handle_air_threat(self) -> None:
        """
        ★★★ 공중 위협 대응 강화 ★★★

        적 공중 유닛 감지 시:
        1. 스포어 크롤러 긴급 건설 (모든 기지에)
        2. 히드라리스크 굴 최우선 건설
        3. 퀸 추가 생산 (대공 + 트랜스퓨전)
        4. 커럽터/히드라 우선 생산
        """
        game_time = getattr(self.bot, "time", 0)

        # ★ 스포어 크롤러 긴급 건설 ★
        self.emergency_spore_requested = True

        # ★ 기지 수만큼 스포어 필요 ★
        if not hasattr(self, "_spore_count_needed"):
            self._spore_count_needed = 0
        if hasattr(self.bot, "townhalls"):
            self._spore_count_needed = max(2, self.bot.townhalls.amount)

        # ★ 히드라 굴 긴급 건설 ★
        if hasattr(self.bot, "structures"):
            try:
                from sc2.ids.unit_typeid import UnitTypeId

                # 히드라 굴 체크
                hydra_dens = self.bot.structures(UnitTypeId.HYDRALISKDEN)
                if not hydra_dens.exists and self.bot.already_pending(UnitTypeId.HYDRALISKDEN) == 0:
                    # 레어가 있으면 히드라 굴 건설
                    lairs = self.bot.structures(UnitTypeId.LAIR)
                    hives = self.bot.structures(UnitTypeId.HIVE)
                    if lairs.exists or hives.exists:
                        # ★★★ 로그 스팸 방지: 5초마다만 출력 ★★★
                        if game_time - self.last_air_threat_log > self.log_cooldown:
                            print(f"[STRATEGY] [{int(game_time)}s] ★★★ AIR THREAT - BUILDING HYDRA DEN NOW ★★★")
                            self.last_air_threat_log = game_time
                        # 직접 건설 시도
                        if self.bot.can_afford(UnitTypeId.HYDRALISKDEN):
                            if self.bot.townhalls.exists:
                                pos = self.bot.townhalls.first.position.towards(
                                    self.bot.game_info.map_center, 5
                                )
                                try:
                                    self.bot.train_or_build_sync(UnitTypeId.HYDRALISKDEN, near=pos)
                                except Exception as e:
                                    self.logger.warning(f"Failed to build emergency Hydra Den: {e}")

                # ★ 스파이어 체크 (커럽터 생산용) ★
                spires = self.bot.structures(UnitTypeId.SPIRE)
                greater_spires = self.bot.structures(UnitTypeId.GREATERSPIRE)
                if not spires.exists and not greater_spires.exists:
                    if self.bot.already_pending(UnitTypeId.SPIRE) == 0:
                        lairs = self.bot.structures(UnitTypeId.LAIR)
                        hives = self.bot.structures(UnitTypeId.HIVE)
                        if (lairs.exists or hives.exists) and self.bot.can_afford(UnitTypeId.SPIRE):
                            print(f"[STRATEGY] [{int(game_time)}s] ★ Building Spire for Corruptors ★")

            except Exception as e:
                if self.bot.iteration % 200 == 0:
                    self.logger.warning(f"Air threat handling error: {e}")

        # ★ 대공 유닛 비율 강제 조정 ★
        self._force_anti_air_ratios()

        # 로그 쿨다운 (10초마다만 출력)
        if not hasattr(self, "_last_air_log_time"):
            self._last_air_log_time = 0
        if game_time - self._last_air_log_time >= 10:
            self.logger.warning(f"[{int(game_time)}s] ★★ AIR THREAT ACTIVE - Anti-air priority ★★")
            self._last_air_log_time = game_time

    def _force_anti_air_ratios(self) -> None:
        """★ 대공 유닛 비율 강제 조정 ★"""
        # 모든 페이즈에 대공 유닛 비율 높이기
        anti_air_ratios = {
            GamePhase.EARLY: {"zergling": 0.2, "queen": 0.3, "hydra": 0.5},
            GamePhase.MID: {"hydra": 0.5, "corruptor": 0.3, "queen": 0.2},
            GamePhase.LATE: {"hydra": 0.4, "corruptor": 0.4, "viper": 0.2},
        }

        # 현재 적 종족의 비율 덮어쓰기
        self.race_unit_ratios[self.detected_enemy_race] = anti_air_ratios

    def get_spore_count_needed(self) -> int:
        """필요한 스포어 크롤러 수 반환"""
        return getattr(self, "_spore_count_needed", 2)

    def _detect_direct_air_threat(self) -> None:
        """
        ★ 직접 공중 유닛 감지 및 대응 ★

        빌드 패턴이 아닌 실제 공중 유닛이 보이면 즉시 대응
        """
        if not hasattr(self.bot, "enemy_units"):
            return

        game_time = getattr(self.bot, "time", 0)

        # 공중 위협 유닛 목록
        air_threat_units = {
            # 테란
            "BANSHEE", "BATTLECRUISER", "LIBERATOR", "LIBERATORAG",
            "VIKINGFIGHTER", "RAVEN", "MEDIVAC",
            # 프로토스
            "VOIDRAY", "ORACLE", "PHOENIX", "CARRIER", "TEMPEST",
            "MOTHERSHIP", "INTERCEPTOR",
            # 저그
            "MUTALISK", "CORRUPTOR", "BROODLORD", "VIPER"
        }

        # 공중 유닛 카운트
        air_unit_count = 0
        detected_air_types = set()

        for enemy in self.bot.enemy_units:
            try:
                enemy_type = getattr(enemy.type_id, "name", "").upper()
                if enemy_type in air_threat_units or getattr(enemy, "is_flying", False):
                    air_unit_count += 1
                    detected_air_types.add(enemy_type)
            except Exception:
                continue

        # 공중 유닛 2기 이상 감지시 대응 활성화
        if air_unit_count >= 2:
            self._air_threat_active = True
            self.emergency_spore_requested = True

            # 30초마다 로그
            if int(game_time) % 30 == 0 and self.bot.iteration % 22 == 0:
                self.logger.warning(f"[{int(game_time)}s] ★★★ AIR THREAT ACTIVE: {air_unit_count} air units detected! ★★★")
                self.logger.info(f"Air types: {detected_air_types}")

            # 히드라 우선 생산 설정
            self._force_hydra_production = True

            # 현재 페이즈에 히드라 비율 증가
            current_ratios = self.get_unit_ratios()
            if "hydra" in current_ratios:
                current_ratios["hydra"] = max(current_ratios.get("hydra", 0), 0.4)
            else:
                current_ratios["hydra"] = 0.4

            # 공중 위협 대응 호출
            self._handle_air_threat()

        elif air_unit_count == 0:
            # 공중 위협 해제 (일정 시간 유지)
            if hasattr(self, "_air_threat_active") and self._air_threat_active:
                if not hasattr(self, "_air_threat_clear_time"):
                    self._air_threat_clear_time = game_time
                elif game_time - self._air_threat_clear_time > 60:  # 60초 후 해제
                    self._air_threat_active = False
                    self._force_hydra_production = False
                    self.logger.info(f"[{int(game_time)}s] Air threat cleared")

    def is_air_threat_detected(self) -> bool:
        """공중 위협 감지 여부"""
        # ★ 직접 감지 우선 체크 ★
        if getattr(self, "_air_threat_active", False):
            return True

        intel = getattr(self.bot, "intel", None)
        if not intel:
            return False

        enemy_pattern = ""
        if hasattr(intel, "get_enemy_build_pattern"):
            enemy_pattern = intel.get_enemy_build_pattern()

        return enemy_pattern in ["protoss_stargate", "zerg_muta", "terran_mech"]

    def _counter_protoss_units(self) -> None:
        """
        ★★★ 프로토스 유닛별 카운터 로직 ★★★

        감지된 프로토스 유닛에 따라 유닛 비율 동적 조정:
        - 불멸자(Immortal): 레이바저 담즙, 저글링 포위
        - 콜로서스(Colossus): 커럽터 필수, 레이바저 담즙
        - 공허 포격기(VoidRay): 히드라, 퀸
        - 아둔의 창(Adept): 바퀴, 저글링 수비
        - 고위 기사(HighTemplar): 분산, 링/바퀴 돌진
        - 추적자(Stalker): 저글링 포위, 바퀴
        """
        if self.detected_enemy_race != EnemyRace.PROTOSS:
            return

        if not hasattr(self.bot, "enemy_units"):
            return

        game_time = getattr(self.bot, "time", 0)

        # 프로토스 핵심 유닛 카운트
        immortal_count = 0
        colossus_count = 0
        voidray_count = 0
        disruptor_count = 0
        high_templar_count = 0
        archon_count = 0
        carrier_count = 0
        stalker_count = 0

        for enemy in self.bot.enemy_units:
            try:
                enemy_type = getattr(enemy.type_id, "name", "").upper()

                if enemy_type == "IMMORTAL":
                    immortal_count += 1
                elif enemy_type == "COLOSSUS":
                    colossus_count += 1
                elif enemy_type == "VOIDRAY":
                    voidray_count += 1
                elif enemy_type == "DISRUPTOR":
                    disruptor_count += 1
                elif enemy_type == "HIGHTEMPLAR":
                    high_templar_count += 1
                elif enemy_type == "ARCHON":
                    archon_count += 1
                elif enemy_type == "CARRIER":
                    carrier_count += 1
                elif enemy_type == "STALKER":
                    stalker_count += 1
            except Exception:
                continue

        # ★ 유닛별 대응 전략 ★

        # 불멸자 2기 이상 → 레이바저 담즙 강화
        if immortal_count >= 2:
            if not hasattr(self, "_immortal_counter_active"):
                self._immortal_counter_active = False

            if not self._immortal_counter_active:
                self._immortal_counter_active = True
                self.logger.info(f"[{int(game_time)}s] ★ IMMORTAL DETECTED ({immortal_count}) - Ravager bile priority ★")

            # 레이바저 비율 증가
            self._adjust_unit_ratio("ravager", 0.35)
            self._adjust_unit_ratio("zergling", 0.35)  # 포위용
            self._adjust_unit_ratio("roach", 0.1)  # 바퀴 감소 (불멸자 약점)

        # 콜로서스 1기 이상 → 커럽터 필수
        if colossus_count >= 1:
            if not hasattr(self, "_colossus_counter_active"):
                self._colossus_counter_active = False

            if not self._colossus_counter_active:
                self._colossus_counter_active = True
                self.logger.info(f"[{int(game_time)}s] ★★★ COLOSSUS DETECTED ({colossus_count}) - Corruptor PRIORITY ★★★")

            # 커럽터 + 레이바저 담즙
            self._adjust_unit_ratio("corruptor", 0.4)
            self._adjust_unit_ratio("ravager", 0.2)
            self._adjust_unit_ratio("hydra", 0.3)

            # 스파이어 긴급 건설
            self._request_spire_build()

        # 공허 포격기/캐리어 → 대공 강화
        if voidray_count >= 2 or carrier_count >= 1:
            self.logger.warning(f"[{int(game_time)}s] ★ AIR THREAT - VoidRay/Carrier detected ★")
            self._handle_air_threat()
            self._adjust_unit_ratio("hydra", 0.5)
            self._adjust_unit_ratio("corruptor", 0.3)

        # 디스럽터 → 분산 필요, 빠른 공격
        if disruptor_count >= 1:
            # 로그 스팸 방지
            if game_time - self.last_disruptor_log > self.log_cooldown:
                self.logger.warning(f"[{int(game_time)}s] DISRUPTOR DETECTED - Split micro needed")
                self.last_disruptor_log = game_time
            # 빠른 유닛으로 우회 공격
            self._adjust_unit_ratio("zergling", 0.3)
            self._adjust_unit_ratio("mutalisk", 0.3)

        # 고위 기사/아콘 → 분산, 빠른 돌진
        if high_templar_count >= 1 or archon_count >= 2:
            # 로그 스팸 방지
            if game_time - self.last_high_templar_log > self.log_cooldown:
                self.logger.warning(f"[{int(game_time)}s] HIGH TEMPLAR/ARCHON - Rush them!")
                self.last_high_templar_log = game_time
            self._adjust_unit_ratio("zergling", 0.4)
            self._adjust_unit_ratio("ravager", 0.3)  # 담즙으로 폭풍 지역 회피

    def _adjust_unit_ratio(self, unit_type: str, target_ratio: float) -> None:
        """유닛 비율 동적 조정"""
        current_ratios = self.race_unit_ratios[self.detected_enemy_race].get(
            self.game_phase, {}
        )

        if unit_type in current_ratios:
            # 기존 비율보다 높으면 업데이트
            if target_ratio > current_ratios[unit_type]:
                current_ratios[unit_type] = target_ratio
        else:
            current_ratios[unit_type] = target_ratio

    def _request_spire_build(self) -> None:
        """스파이어 긴급 건설 요청"""
        if not hasattr(self.bot, "structures"):
            return

        try:
            from sc2.ids.unit_typeid import UnitTypeId

            spires = self.bot.structures(UnitTypeId.SPIRE)
            greater_spires = self.bot.structures(UnitTypeId.GREATERSPIRE)

            if not spires.exists and not greater_spires.exists:
                if self.bot.already_pending(UnitTypeId.SPIRE) == 0:
                    # 레어 체크
                    lairs = self.bot.structures(UnitTypeId.LAIR)
                    hives = self.bot.structures(UnitTypeId.HIVE)

                    if (lairs.exists or hives.exists) and self.bot.can_afford(UnitTypeId.SPIRE):
                        game_time = getattr(self.bot, "time", 0)
                        print(f"[STRATEGY] [{int(game_time)}s] ★★★ BUILDING SPIRE FOR CORRUPTORS (Auto) ★★★")
                        
                        # 건설 위치: 메인 기지 근처
                        if self.bot.townhalls.exists:
                            main_base = self.bot.townhalls.first
                            # 맵 중앙 방향으로 약간 이동 (건물 겹침 방지)
                            pos = main_base.position.towards(self.bot.game_info.map_center, 6)
                            
                            # 비동기 빌드 명령 (Worker Manager가 처리하도록 build 사용)
                            # self.bot.build는 적절한 일꾼을 찾아 건설함
                            try:
                                # await self.bot.build(...)는 코루틴이므로 await 필요하지만
                                # on_step이 async이므로 가능? 아니면 create_task?
                                # StrategyManager.update는 동기 함수일 수 있음.
                                # self.bot.do(self.bot.workers.closest_to(pos).build(UnitTypeId.SPIRE, pos)) 사용이 안전.
                                
                                # 하지만 build 함수는 최적 위치를 찾아주므로 build 사용이 좋음.
                                # 여기서 bot은 BotAI 인스턴스.
                                # 비동기 함수 호출이 어려우면 동기식으로 처리해야 함.
                                # 여기서는 안전하게 bot.build (async) 대신 일꾼 직접 명령 사용
                                
                                worker = self.bot.workers.closest_to(pos)
                                if worker:
                                    # 위치 찾기 (sc2 메서드)
                                    # find_placement는 async 메서드임. 동기 컨텍스트라면 문제.
                                    # StrategyManager.update가 sync인지 async인지 확인 필요.
                                    # bot_step_integration.py에서 `await self._safe_manager_step(...)`으로 호출됨.
                                    # `_safe_manager_step`을 보면 `method_name="update"`를 호출함.
                                    # execute_game_logic -> StrategyManager.update (sync defined).
                                    
                                    # Sync method cannot await.
                                    # So we use self.bot.do(worker.build(UnitTypeId.SPIRE, pos)) and hope placement is valid.
                                    # Better: Use `client.query_building_placement`? Too slow for sync.
                                    # Let's just issue the command. The bot class usually has `train_or_build_sync` helper if defined?
                                    # I saw `self.bot.train_or_build_sync` in `_handle_air_threat` earlier!
                                    # Let's use that if available, or just print warning if not.
                                    
                                    if hasattr(self.bot, "train_or_build_sync"):
                                        self.bot.train_or_build_sync(UnitTypeId.SPIRE, near=pos)
                                    else:
                                        # Fallback logic
                                        self.bot.do(worker.build(UnitTypeId.SPIRE, pos))
                                        
                            except Exception as e:
                                self.logger.warning(f"Spire construction failed: {e}")

        except Exception as e:
            self.logger.warning(f"Spire build request failed: {e}")

    def should_force_hydra(self) -> bool:
        """히드라 강제 생산 여부"""
        return getattr(self, "_force_hydra_production", False)

    def _activate_emergency_mode(self, game_time: float) -> None:
        """Emergency Mode 활성화"""
        self.emergency_active = True
        self.emergency_start_time = game_time
        self.current_mode = StrategyMode.EMERGENCY

        self.logger.warning(f"EMERGENCY MODE ACTIVATED at {int(game_time)}s - Rush detected!")

        # Economy Manager에 알림
        if hasattr(self.bot, "economy") and self.bot.economy:
            self.bot.economy.set_emergency_mode(True)

        # 긴급 방어 건물 건설 요청
        self.emergency_spine_requested = True
        self.emergency_spore_requested = False  # 지상 러쉬면 스파인 우선

        # 적 공중 유닛이 있으면 스포어도 요청
        if hasattr(self.bot, "enemy_units"):
            for enemy in self.bot.enemy_units:
                if hasattr(enemy, "is_flying") and enemy.is_flying:
                    self.emergency_spore_requested = True
                    break

        self.logger.info(f"Emergency defense requested: Spine={self.emergency_spine_requested}, Spore={self.emergency_spore_requested}")

    def _end_emergency_mode(self) -> None:
        """Emergency Mode 종료"""
        self.emergency_active = False
        self.current_mode = StrategyMode.NORMAL

        self.logger.info("Emergency mode ended - Returning to normal operations")

        # Economy Manager 복구
        if hasattr(self.bot, "economy") and self.bot.economy:
            self.bot.economy.set_emergency_mode(False)

    def _check_rogue_tactics(self) -> None:
        """Rogue Tactics 상태 확인"""
        rogue = getattr(self.bot, "rogue_tactics", None)
        if rogue:
            self.rogue_tactics_active = True
            self.larva_saving_mode = getattr(rogue, "larva_saving_active", False)
        else:
            self.rogue_tactics_active = False
            self.larva_saving_mode = False

    def _update_strategy_mode(self) -> None:
        """전략 모드 업데이트"""
        if self.emergency_active:
            return  # Emergency 유지

        # 군대 우위 계산
        our_army = 0
        enemy_army = 0

        if hasattr(self.bot, "units"):
            for unit in self.bot.units:
                if unit.can_attack and unit.type_id.name != "DRONE":
                    our_army += 1

        if hasattr(self.bot, "enemy_units"):
            for unit in self.bot.enemy_units:
                if unit.can_attack:
                    enemy_army += 1

        # 공급량 기반 공격 (적 정보가 없어도 공격)
        army_supply = getattr(self.bot, "supply_army", 0)
        
        # 전략 결정
        if self.current_mode != StrategyMode.EMERGENCY:
            # 1. 압도적 물량이면 공격 (적 유닛 수와 무관하게)
            if army_supply >= 100:
                self.current_mode = StrategyMode.ALL_IN
            # 2. 적당한 물량이면 공격적 운영
            elif army_supply >= 40:
                self.current_mode = StrategyMode.AGGRESSIVE
            # 3. 상대적 우위 계산 (기존 로직)
            elif our_army > enemy_army * 1.5 and our_army >= 10:
                self.current_mode = StrategyMode.AGGRESSIVE
            elif our_army < enemy_army * 0.5 and enemy_army > 5:
                self.current_mode = StrategyMode.DEFENSIVE
            else:
                self.current_mode = StrategyMode.NORMAL

    def get_unit_ratios(self) -> Dict[str, float]:
        """
        현재 상황에 맞는 유닛 비율 반환

        Returns:
            유닛 종류별 비율 딕셔너리
        """
        if self.emergency_active:
            return self.emergency_ratios

        race = self.detected_enemy_race
        if race == EnemyRace.RANDOM or race == EnemyRace.UNKNOWN:
            race = EnemyRace.UNKNOWN

        phase_ratios = self.race_unit_ratios.get(race, self.race_unit_ratios[EnemyRace.UNKNOWN])
        return phase_ratios.get(self.game_phase, phase_ratios[GamePhase.EARLY])

    def should_produce_drone(self) -> bool:
        """
        드론 생산 여부 결정

        Returns:
            드론을 생산해야 하면 True
        """
        # Emergency Mode에서는 드론 생산 최소화
        if self.emergency_active:
            drone_count = 0
            if hasattr(self.bot, "units"):
                drones = self.bot.units.filter(lambda u: u.type_id.name == "DRONE")
                drone_count = drones.amount if hasattr(drones, "amount") else len(drones)
            return drone_count < 12  # 최소 12기만 유지

        return True

    def should_save_larva(self) -> bool:
        """
        Rogue Tactics의 라바 세이빙 모드 확인

        Returns:
            라바를 아껴야 하면 True
        """
        return self.larva_saving_mode

    def get_priority_unit(self) -> Optional[str]:
        """
        현재 우선 생산해야 할 유닛 반환

        Returns:
            우선 유닛 이름 또는 None
        """
        if self.emergency_active:
            return "zergling"  # 긴급 시 저글링 우선

        ratios = self.get_unit_ratios()
        if ratios:
            # 가장 비율이 높은 유닛 반환
            return max(ratios.keys(), key=lambda k: ratios[k])
        return None

    def get_status_report(self) -> Dict[str, Any]:
        """
        전략 상태 리포트 반환

        Returns:
            상태 정보 딕셔너리
        """
        return {
            "mode": self.current_mode.value,
            "enemy_race": self.detected_enemy_race.value,
            "game_phase": self.game_phase.value,
            "emergency_active": self.emergency_active,
            "rogue_tactics_active": self.rogue_tactics_active,
            "larva_saving": self.larva_saving_mode,
            "unit_ratios": self.get_unit_ratios(),
        }
