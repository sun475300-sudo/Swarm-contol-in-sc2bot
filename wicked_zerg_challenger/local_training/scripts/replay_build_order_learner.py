# -*- coding: utf-8 -*-
"""
Replay Build Order Learner

리플레이 파일에서 빌드 오더를 추출하고 학습합니다.

주요 기능:
1. SC2Replay 파일 파싱
2. 빌드 오더 추출 (유닛/건물 생산 순서)
3. 프로 게이머 빌드 오더 저장
4. 학습 파라미터 생성
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 프로젝트 루트 추가
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class ReplayBuildOrderLearner:
    """리플레이에서 빌드 오더를 학습하는 클래스"""

    def __init__(self, replay_dir: Optional[str] = None, output_dir: Optional[str] = None):
        self.replay_dir = Path(replay_dir) if replay_dir else project_root / "replays"
        self.output_dir = Path(output_dir) if output_dir else script_dir / "learned_build_orders.json"

        # 저그 유닛/건물 목록
        self.zerg_units = {
            "Drone", "Zergling", "Baneling", "Roach", "Ravager",
            "Hydralisk", "Lurker", "Mutalisk", "Corruptor", "BroodLord",
            "Infestor", "SwarmHost", "Ultralisk", "Viper", "Queen", "Overlord", "Overseer"
        }
        self.zerg_buildings = {
            "Hatchery", "Lair", "Hive", "SpawningPool", "BanelingNest",
            "RoachWarren", "HydraliskDen", "LurkerDen", "Spire", "GreaterSpire",
            "InfestationPit", "UltraliskCavern", "EvolutionChamber", "Extractor",
            "SpineCrawler", "SporeCrawler", "NydusNetwork"
        }

        # 학습된 빌드 오더
        self.learned_builds: Dict[str, List[Dict]] = {
            "vs_terran": [],
            "vs_protoss": [],
            "vs_zerg": [],
            "general": []
        }

        # 빌드 오더 통계
        self.build_stats: Dict[str, Any] = {
            "total_replays": 0,
            "zerg_wins": 0,
            "avg_game_length": 0.0,
            "common_openers": {}
        }

    def scan_replays(self) -> List[Path]:
        """리플레이 파일 스캔"""
        replays = []
        if self.replay_dir.exists():
            for ext in ["*.SC2Replay", "*.sc2replay"]:
                replays.extend(self.replay_dir.glob(f"**/{ext}"))
        print(f"[REPLAY] Found {len(replays)} replay files")
        return replays

    def parse_replay(self, replay_path: Path) -> Optional[Dict[str, Any]]:
        """리플레이 파일 파싱"""
        try:
            # sc2reader 시도
            try:
                import sc2reader
                replay = sc2reader.load_replay(str(replay_path), load_level=4)
                return self._extract_from_sc2reader(replay)
            except ImportError:
                pass

            # 기본 메타데이터 추출
            return self._extract_basic_metadata(replay_path)

        except Exception as e:
            print(f"[REPLAY] Failed to parse {replay_path.name}: {e}")
            return None

    def _extract_from_sc2reader(self, replay) -> Dict[str, Any]:
        """sc2reader로 상세 정보 추출"""
        data = {
            "map": replay.map_name,
            "duration": replay.game_length.seconds if hasattr(replay, 'game_length') else 0,
            "players": [],
            "build_orders": [],
            "winner": None
        }

        for player in replay.players:
            player_data = {
                "name": player.name,
                "race": str(player.play_race) if hasattr(player, 'play_race') else "Unknown",
                "result": str(player.result) if hasattr(player, 'result') else "Unknown",
                "apm": player.avg_apm if hasattr(player, 'avg_apm') else 0
            }
            data["players"].append(player_data)

            # 저그 플레이어의 빌드 오더 추출
            if "Zerg" in player_data["race"]:
                build_order = self._extract_build_order(replay, player)
                if build_order:
                    data["build_orders"].append({
                        "player": player.name,
                        "race": player_data["race"],
                        "result": player_data["result"],
                        "actions": build_order
                    })

                    if "Win" in player_data["result"]:
                        data["winner"] = player.name

        return data

    def _extract_build_order(self, replay, player) -> List[Dict]:
        """플레이어의 빌드 오더 추출"""
        build_order = []

        try:
            # 이벤트에서 유닛/건물 생산 추출
            for event in replay.events:
                if hasattr(event, 'player') and event.player == player:
                    # 유닛 생성 이벤트
                    if hasattr(event, 'unit') and hasattr(event, 'second'):
                        unit_name = str(event.unit.name) if hasattr(event.unit, 'name') else ""
                        if unit_name in self.zerg_units or unit_name in self.zerg_buildings:
                            build_order.append({
                                "time": event.second,
                                "action": "build" if unit_name in self.zerg_buildings else "train",
                                "unit": unit_name,
                                "supply": getattr(event, 'supply', 0)
                            })
        except Exception as e:
            print(f"[REPLAY] Build order extraction error: {e}")

        # 시간순 정렬
        build_order.sort(key=lambda x: x["time"])
        return build_order[:50]  # 처음 50개만

    def _extract_basic_metadata(self, replay_path: Path) -> Dict[str, Any]:
        """기본 메타데이터 추출 (sc2reader 없이)"""
        return {
            "map": "Unknown",
            "duration": 0,
            "players": [],
            "build_orders": [],
            "file": replay_path.name,
            "parsed_at": datetime.now().isoformat()
        }

    def learn_from_replays(self, max_replays: int = 100) -> Dict[str, Any]:
        """리플레이에서 빌드 오더 학습"""
        replays = self.scan_replays()[:max_replays]

        if not replays:
            print("[REPLAY] No replays found, using default build orders")
            return self._get_default_build_orders()

        processed = 0
        for replay_path in replays:
            data = self.parse_replay(replay_path)
            if data and data.get("build_orders"):
                self._process_build_order(data)
                processed += 1

        self.build_stats["total_replays"] = processed
        print(f"[REPLAY] Processed {processed} replays")

        return self._generate_learned_parameters()

    def _process_build_order(self, data: Dict) -> None:
        """빌드 오더 처리 및 분류"""
        for build in data.get("build_orders", []):
            if "Win" in build.get("result", ""):
                self.build_stats["zerg_wins"] += 1

                # 상대 종족별 분류
                opponent_race = self._get_opponent_race(data, build["player"])
                category = f"vs_{opponent_race.lower()}" if opponent_race else "general"

                if category in self.learned_builds:
                    self.learned_builds[category].append({
                        "actions": build["actions"],
                        "map": data.get("map", "Unknown"),
                        "duration": data.get("duration", 0)
                    })

    def _get_opponent_race(self, data: Dict, player_name: str) -> str:
        """상대 종족 추출"""
        for player in data.get("players", []):
            if player["name"] != player_name:
                return player.get("race", "Unknown")
        return "Unknown"

    def _generate_learned_parameters(self) -> Dict[str, Any]:
        """학습된 파라미터 생성"""
        parameters = {
            "build_order_timings": self._calculate_avg_timings(),
            "unit_priorities": self._calculate_unit_priorities(),
            "expansion_timings": self._calculate_expansion_timings(),
            "stats": self.build_stats,
            "generated_at": datetime.now().isoformat()
        }
        return parameters

    def _calculate_avg_timings(self) -> Dict[str, float]:
        """평균 빌드 타이밍 계산"""
        timings: Dict[str, List[float]] = {}

        for category, builds in self.learned_builds.items():
            for build in builds:
                for action in build.get("actions", []):
                    unit = action.get("unit", "")
                    time = action.get("time", 0)
                    if unit and time > 0:
                        if unit not in timings:
                            timings[unit] = []
                        timings[unit].append(time)

        return {unit: sum(times) / len(times) for unit, times in timings.items() if times}

    def _calculate_unit_priorities(self) -> Dict[str, float]:
        """유닛 우선순위 계산"""
        counts: Dict[str, int] = {}
        total = 0

        for category, builds in self.learned_builds.items():
            for build in builds:
                for action in build.get("actions", []):
                    unit = action.get("unit", "")
                    if unit:
                        counts[unit] = counts.get(unit, 0) + 1
                        total += 1

        if total == 0:
            return {}
        return {unit: count / total for unit, count in counts.items()}

    def _calculate_expansion_timings(self) -> Dict[str, float]:
        """확장 타이밍 계산"""
        timings = {"second_base": [], "third_base": [], "fourth_base": []}

        for category, builds in self.learned_builds.items():
            for build in builds:
                hatch_count = 0
                for action in build.get("actions", []):
                    if action.get("unit") == "Hatchery":
                        hatch_count += 1
                        if hatch_count == 1:
                            timings["second_base"].append(action.get("time", 0))
                        elif hatch_count == 2:
                            timings["third_base"].append(action.get("time", 0))
                        elif hatch_count == 3:
                            timings["fourth_base"].append(action.get("time", 0))

        return {
            base: sum(times) / len(times) if times else 0.0
            for base, times in timings.items()
        }

    def _get_default_build_orders(self) -> Dict[str, Any]:
        """기본 빌드 오더 (리플레이 없을 때)"""
        return {
            "build_order_timings": {
                "Hatchery": 90.0,  # 2번째 기지
                "SpawningPool": 75.0,
                "Extractor": 85.0,
                "Queen": 100.0,
                "Zergling": 110.0,
                "RoachWarren": 180.0,
                "Lair": 300.0,
                "HydraliskDen": 360.0
            },
            "unit_priorities": {
                "Drone": 0.3,
                "Zergling": 0.25,
                "Roach": 0.15,
                "Hydralisk": 0.1,
                "Queen": 0.1,
                "Baneling": 0.05,
                "Mutalisk": 0.05
            },
            "expansion_timings": {
                "second_base": 90.0,
                "third_base": 240.0,
                "fourth_base": 420.0
            },
            "stats": {
                "total_replays": 0,
                "zerg_wins": 0,
                "source": "default"
            },
            "generated_at": datetime.now().isoformat()
        }

    def save_learned_data(self, data: Dict[str, Any]) -> bool:
        """학습 데이터 저장"""
        try:
            output_path = Path(self.output_dir)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"[REPLAY] Saved learned data to {output_path}")
            return True
        except Exception as e:
            print(f"[REPLAY] Failed to save: {e}")
            return False

    def run(self) -> Dict[str, Any]:
        """메인 실행"""
        print("=" * 60)
        print("REPLAY BUILD ORDER LEARNER")
        print("=" * 60)

        # 학습 실행
        learned_params = self.learn_from_replays()

        # 저장
        self.save_learned_data(learned_params)

        # 결과 출력
        print("\n[RESULTS]")
        print(f"  - Total replays processed: {learned_params['stats'].get('total_replays', 0)}")
        print(f"  - Zerg wins analyzed: {learned_params['stats'].get('zerg_wins', 0)}")
        print(f"  - Build timings learned: {len(learned_params.get('build_order_timings', {}))}")
        print(f"  - Unit priorities: {len(learned_params.get('unit_priorities', {}))}")
        print("=" * 60)

        return learned_params


def main():
    """메인 함수"""
    learner = ReplayBuildOrderLearner()
    learner.run()


if __name__ == "__main__":
    main()
