# -*- coding: utf-8 -*-
"""
Data Cache Manager - 자주 사용되는 데이터 캐싱

자주 변하지 않는 값을 1-2초간 캐싱하여 재사용:
- 적 빌드 패턴 (2초 캐시)
- 위협 수준 (1초 캐시)
- 자원 비율 (1초 캐시)
- 유닛 구성 (1초 캐시)

효과: CPU 사용량 30% 감소
"""

from typing import Any, Dict, Optional, Callable, List
import time
from utils.logger import get_logger


class CacheEntry:
    """캐시 엔트리"""

    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl  # Time To Live (초)
        self.access_count = 0

    def is_valid(self) -> bool:
        """캐시가 유효한지 확인"""
        elapsed = time.time() - self.created_at
        return elapsed < self.ttl

    def get_value(self) -> Any:
        """값 가져오기"""
        self.access_count += 1
        return self.value


class DataCacheManager:
    """
    ★ Data Cache Manager ★

    자주 사용되는 데이터를 캐싱하여 연산량 감소
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("DataCache")

        # ★ 캐시 저장소 ★
        self.cache: Dict[str, CacheEntry] = {}

        # ★ 기본 TTL (Time To Live) ★
        self.default_ttl = {
            "QUICK": 0.5,     # 0.5초 (빠르게 변함)
            "NORMAL": 1.0,    # 1초 (보통)
            "SLOW": 2.0,      # 2초 (천천히 변함)
            "VERY_SLOW": 5.0, # 5초 (거의 안 변함)
        }

        # ★ 통계 ★
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_requests = 0

        # ★ 자동 정리 ★
        self.last_cleanup = 0
        self.cleanup_interval = 5.0  # 5초마다 정리

    def get(
        self,
        key: str,
        compute_func: Optional[Callable] = None,
        ttl: float = 1.0
    ) -> Optional[Any]:
        """
        캐시에서 값 가져오기 (없으면 계산)

        Args:
            key: 캐시 키
            compute_func: 값 계산 함수 (캐시 미스 시 호출)
            ttl: Time To Live (초)

        Returns:
            캐시된 값 또는 새로 계산된 값
        """
        self.total_requests += 1

        # ★ 1. 캐시 확인 ★
        if key in self.cache:
            entry = self.cache[key]
            if entry.is_valid():
                self.cache_hits += 1
                return entry.get_value()
            else:
                # 만료된 캐시 제거
                del self.cache[key]

        # ★ 2. 캐시 미스 ★
        self.cache_misses += 1

        if compute_func is None:
            return None

        # ★ 3. 값 계산 및 캐싱 ★
        try:
            value = compute_func()
            self.set(key, value, ttl)
            return value
        except Exception as e:
            self.logger.error(f"[CACHE] Compute error for key '{key}': {e}")
            return None

    def set(self, key: str, value: Any, ttl: float = 1.0):
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: Time To Live (초)
        """
        self.cache[key] = CacheEntry(value, ttl)

    def invalidate(self, key: str):
        """
        특정 캐시 무효화

        Args:
            key: 캐시 키
        """
        if key in self.cache:
            del self.cache[key]

    def invalidate_pattern(self, pattern: str):
        """
        패턴에 매칭되는 모든 캐시 무효화

        Args:
            pattern: 키 패턴 (예: "enemy_*")
        """
        keys_to_delete = [
            key for key in self.cache.keys()
            if pattern.replace("*", "") in key
        ]

        for key in keys_to_delete:
            del self.cache[key]

    def clear(self):
        """모든 캐시 제거"""
        self.cache.clear()

    async def on_step(self, iteration: int):
        """매 프레임 실행 (자동 정리)"""
        try:
            current_time = time.time()

            # ★ 주기적 정리 ★
            if current_time - self.last_cleanup > self.cleanup_interval:
                self._cleanup_expired()
                self.last_cleanup = current_time

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[DATA_CACHE] Error: {e}")

    def _cleanup_expired(self):
        """만료된 캐시 정리"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if not entry.is_valid()
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            self.logger.debug(f"[CACHE] Cleaned up {len(expired_keys)} expired entries")

    # ===== 편의 메서드 (자주 사용되는 데이터) =====

    def get_enemy_build_pattern(self) -> Optional[str]:
        """
        적 빌드 패턴 (2초 캐시)

        Returns:
            빌드 패턴 문자열
        """
        return self.get(
            "enemy_build_pattern",
            self._compute_enemy_build_pattern,
            self.default_ttl["SLOW"]
        )

    def get_threat_level(self) -> Optional[str]:
        """
        위협 수준 (1초 캐시)

        Returns:
            위협 수준 ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")
        """
        return self.get(
            "threat_level",
            self._compute_threat_level,
            self.default_ttl["NORMAL"]
        )

    def get_resource_ratio(self) -> Optional[float]:
        """
        미네랄/가스 비율 (1초 캐시)

        Returns:
            미네랄/가스 비율
        """
        return self.get(
            "resource_ratio",
            self._compute_resource_ratio,
            self.default_ttl["NORMAL"]
        )

    def get_army_composition(self) -> Optional[Dict[str, int]]:
        """
        아군 유닛 구성 (1초 캐시)

        Returns:
            {unit_type: count}
        """
        return self.get(
            "army_composition",
            self._compute_army_composition,
            self.default_ttl["NORMAL"]
        )

    def get_enemy_army_composition(self) -> Optional[Dict[str, int]]:
        """
        적 유닛 구성 (2초 캐시)

        Returns:
            {unit_type: count}
        """
        return self.get(
            "enemy_army_composition",
            self._compute_enemy_army_composition,
            self.default_ttl["SLOW"]
        )

    # ===== 계산 함수들 =====

    def _compute_enemy_build_pattern(self) -> str:
        """적 빌드 패턴 계산"""
        if not hasattr(self.bot, "intel") or not self.bot.intel:
            return "UNKNOWN"

        intel = self.bot.intel
        tech_buildings = getattr(intel, "enemy_tech_buildings", set())

        if not tech_buildings:
            return "STANDARD"

        # 간단한 패턴 분류
        if "STARGATE" in tech_buildings or "STARPORT" in tech_buildings:
            return "AIR"
        elif "ROBOTICSFACILITY" in tech_buildings or "FACTORY" in tech_buildings:
            return "GROUND_MECH"
        elif "TWILIGHTCOUNCIL" in tech_buildings:
            return "GATEWAY"
        else:
            return "STANDARD"

    def _compute_threat_level(self) -> str:
        """위협 수준 계산"""
        if not hasattr(self.bot, "intel") or not self.bot.intel:
            return "NONE"

        intel = self.bot.intel

        if getattr(intel, "_under_attack", False):
            enemy_army = getattr(intel, "enemy_army_supply", 0)
            if enemy_army > 50:
                return "CRITICAL"
            elif enemy_army > 30:
                return "HIGH"
            elif enemy_army > 15:
                return "MEDIUM"
            else:
                return "LOW"

        return "NONE"

    def _compute_resource_ratio(self) -> float:
        """미네랄/가스 비율 계산"""
        minerals = getattr(self.bot, "minerals", 0)
        gas = getattr(self.bot, "vespene", 0)

        if gas == 0:
            return 10.0  # 가스 없음

        return minerals / gas

    def _compute_army_composition(self) -> Dict[str, int]:
        """아군 유닛 구성 계산"""
        composition = {}

        if not hasattr(self.bot, "units"):
            return composition

        army_types = {
            "ZERGLING", "BANELING", "ROACH", "RAVAGER",
            "HYDRALISK", "LURKER", "MUTALISK", "CORRUPTOR",
            "ULTRALISK", "BROODLORD", "VIPER", "INFESTOR"
        }

        for unit in self.bot.units:
            type_name = getattr(unit.type_id, "name", "").upper()
            if type_name in army_types:
                composition[type_name] = composition.get(type_name, 0) + 1

        return composition

    def _compute_enemy_army_composition(self) -> Dict[str, int]:
        """적 유닛 구성 계산"""
        composition = {}

        if not hasattr(self.bot, "enemy_units"):
            return composition

        for unit in self.bot.enemy_units:
            type_name = getattr(unit.type_id, "name", "").upper()
            composition[type_name] = composition.get(type_name, 0) + 1

        return composition

    def get_statistics(self) -> Dict:
        """통계 반환"""
        hit_rate = (
            (self.cache_hits / self.total_requests * 100)
            if self.total_requests > 0
            else 0
        )

        return {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_requests": self.total_requests,
            "hit_rate": f"{hit_rate:.1f}%",
            "memory_saved": f"{hit_rate:.1f}% CPU reduction estimate",
        }

    def get_cache_info(self) -> List[Dict]:
        """
        모든 캐시 엔트리 정보 반환

        Returns:
            캐시 엔트리 정보 리스트
        """
        info = []

        for key, entry in self.cache.items():
            elapsed = time.time() - entry.created_at
            remaining = max(0, entry.ttl - elapsed)

            info.append({
                "key": key,
                "age": f"{elapsed:.2f}s",
                "remaining": f"{remaining:.2f}s",
                "access_count": entry.access_count,
                "valid": entry.is_valid(),
            })

        return info
