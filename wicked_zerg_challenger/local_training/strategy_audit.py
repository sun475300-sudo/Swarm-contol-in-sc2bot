#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build-Order Gap Analyzer (빌드오더 오차 분석기)

프로게이머의 리플레이 데이터와 봇이 실제로 수행한 데이터를 프레임 단위로 대조하여
'성능 저하의 구간'을 찾아내는 시스템

핵심 기능:
1. Time Gap (시간 오차) 분석
2. Sequence Error (순서 오류) 분석
3. Resource Efficiency (자원 효율) 분석
4. 자동 보완 로직 (CurriculumManager 연동)
5. Gemini Self-Healing 연동
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class BuildEvent:
    """건물 건설 이벤트"""
    building_name: str
    completion_time: float  # 게임 시간 (초)
    supply_at_completion: int
    minerals_at_completion: int
    vespene_at_completion: int
    event_type: str = "building_completed"  # building_completed, building_started, upgrade_completed


@dataclass
class TimeGap:
    """시간 오차 분석 결과"""
    building_name: str
    pro_time: float  # 프로게이머 시간
    bot_time: float  # 봇 시간
    gap_seconds: float  # 오차 (초)
    gap_percentage: float  # 오차 비율 (%)
    severity: str  # "critical", "major", "minor", "ok"


@dataclass
class SequenceError:
    """순서 오류 분석 결과"""
    expected_building: str
    actual_building: str
    expected_time: float
    actual_time: float
    error_type: str  # "order_mismatch", "missing_building", "extra_building"


@dataclass
class ResourceEfficiency:
    """자원 효율 분석 결과"""
    supply: int
    pro_minerals: int
    bot_minerals: int
    pro_vespene: int
    bot_vespene: int
    mineral_waste: int  # 봇이 프로보다 더 많이 남긴 미네랄
    vespene_waste: int  # 봇이 프로보다 더 많이 남긴 가스
    efficiency_score: float  # 0.0 ~ 1.0 (1.0이 최고)


@dataclass
class GapAnalysisResult:
    """전체 분석 결과"""
    game_id: str
    analysis_time: str
    time_gaps: List[TimeGap]
    sequence_errors: List[SequenceError]
    resource_efficiency: List[ResourceEfficiency]
    critical_issues: List[str]  # 가장 심각한 문제 3개
    recommendations: List[str]  # 개선 권장사항


class StrategyAudit:
    """빌드오더 오차 분석기"""
    
    def __init__(
        self,
        learned_build_orders_path: Optional[Path] = None,
        telemetry_data_path: Optional[Path] = None
    ):
        """
        Args:
            learned_build_orders_path: 프로게이머 데이터 경로
            telemetry_data_path: 봇 텔레메트리 데이터 경로
        """
        # 프로게이머 데이터 경로
        if learned_build_orders_path is None:
            # 여러 경로 시도
            possible_paths = [
                Path("local_training/scripts/learned_build_orders.json"),
                Path("D:/replays/archive"),
            ]
            for path in possible_paths:
                if path.is_dir():
                    training_dirs = sorted(path.glob("training_*"), reverse=True)
                    if training_dirs:
                        learned_build_orders_path = training_dirs[0] / "learned_build_orders.json"
                        break
                elif path.exists():
                    learned_build_orders_path = path
                    break
        
        self.learned_build_orders_path = learned_build_orders_path
        self.pro_data: Dict[str, Any] = {}
        self.load_pro_data()
        
        # 텔레메트리 데이터는 게임 중에 실시간으로 전달받음
        self.telemetry_data_path = telemetry_data_path
        
        # 분석 결과 저장 경로
        self.analysis_output_dir = Path("local_training/data/strategy_audit")
        self.analysis_output_dir.mkdir(parents=True, exist_ok=True)
        
    def load_pro_data(self) -> None:
        """프로게이머 데이터 로드"""
        if not self.learned_build_orders_path or not self.learned_build_orders_path.exists():
            logger.warning(f"Pro gamer data not found: {self.learned_build_orders_path}")
            return
        
        try:
            with open(self.learned_build_orders_path, 'r', encoding='utf-8') as f:
                self.pro_data = json.load(f)
            logger.info(f"Loaded pro gamer data from {self.learned_build_orders_path}")
        except Exception as e:
            logger.error(f"Failed to load pro gamer data: {e}")
            self.pro_data = {}
    
    def extract_bot_build_events(
        self,
        build_order_timing: Dict[str, float],
        telemetry_data: List[Dict[str, Any]]
    ) -> List[BuildEvent]:
        """
        봇의 빌드 이벤트 추출
        
        Args:
            build_order_timing: production_manager의 build_order_timing 딕셔너리
            telemetry_data: 텔레메트리 로그 데이터
        
        Returns:
            빌드 이벤트 리스트
        """
        events = []
        
        # build_order_timing에서 건물 완성 시간 추출
        building_mapping = {
            "spawning_pool": "SpawningPool",
            "spawning_pool_time": "SpawningPool",
            "gas": "Extractor",
            "gas_time": "Extractor",
            "natural_expansion": "Hatchery",
            "natural_expansion_time": "Hatchery",
            "roach_warren": "RoachWarren",
            "roach_warren_time": "RoachWarren",
            "hydralisk_den": "HydraliskDen",
            "hydralisk_den_time": "HydraliskDen",
            "lair": "Lair",
            "lair_time": "Lair",
            "hive": "Hive",
            "hive_time": "Hive",
        }
        
        for key, time in build_order_timing.items():
            building_name = building_mapping.get(key, key)
            
            # 해당 시간의 텔레메트리 데이터 찾기
            telemetry_at_time = None
            for tel in telemetry_data:
                if abs(tel.get("time", 0) - time) < 1.0:  # 1초 이내
                    telemetry_at_time = tel
                    break
            
            if telemetry_at_time:
                event = BuildEvent(
                    building_name=building_name,
                    completion_time=time,
                    supply_at_completion=int(telemetry_at_time.get("supply_used", 0)),
                    minerals_at_completion=int(telemetry_at_time.get("minerals", 0)),
                    vespene_at_completion=int(telemetry_at_time.get("vespene", 0)),
                )
                events.append(event)
        
        return sorted(events, key=lambda x: x.completion_time)
    
    def extract_pro_build_events(self) -> List[BuildEvent]:
        """프로게이머의 빌드 이벤트 추출"""
        events = []
        
        if not self.pro_data:
            return events
        
        learned_params = self.pro_data.get("learned_parameters", {})
        build_orders = self.pro_data.get("build_orders", [])
        
        # learned_parameters에서 타이밍 추출
        supply_to_time_mapping = {}  # supply -> time 매핑 (평균값)
        
        for bo in build_orders[:10]:  # 처음 10개 샘플 사용
            timings = bo.get("timings", {})
            for key, supply in timings.items():
                if key not in supply_to_time_mapping:
                    supply_to_time_mapping[key] = []
                supply_to_time_mapping[key].append(supply)
        
        # Supply를 시간으로 변환 (대략적인 변환: supply 1 = 약 1.5초)
        # 실제로는 더 정교한 변환이 필요하지만, 여기서는 단순화
        for key, supply_list in supply_to_time_mapping.items():
            avg_supply = sum(supply_list) / len(supply_list)
            estimated_time = avg_supply * 1.5  # 대략적인 변환
            
            building_name = key.replace("_supply", "").replace("_", "").title()
            
            event = BuildEvent(
                building_name=building_name,
                completion_time=estimated_time,
                supply_at_completion=int(avg_supply),
                minerals_at_completion=0,  # 프로 데이터에는 없음
                vespene_at_completion=0,   # 프로 데이터에는 없음
            )
            events.append(event)
        
        return sorted(events, key=lambda x: x.completion_time)
    
    def analyze_time_gaps(
        self,
        pro_events: List[BuildEvent],
        bot_events: List[BuildEvent]
    ) -> List[TimeGap]:
        """시간 오차 분석"""
        gaps = []
        
        # 건물 이름으로 매칭
        pro_by_name = {e.building_name: e for e in pro_events}
        bot_by_name = {e.building_name: e for e in bot_events}
        
        for building_name in set(pro_by_name.keys()) & set(bot_by_name.keys()):
            pro_event = pro_by_name[building_name]
            bot_event = bot_by_name[building_name]
            
            gap_seconds = bot_event.completion_time - pro_event.completion_time
            gap_percentage = (gap_seconds / pro_event.completion_time * 100) if pro_event.completion_time > 0 else 0
            
            # 심각도 판정
            if gap_seconds > 30 or gap_percentage > 50:
                severity = "critical"
            elif gap_seconds > 15 or gap_percentage > 25:
                severity = "major"
            elif gap_seconds > 5 or gap_percentage > 10:
                severity = "minor"
            else:
                severity = "ok"
            
            gap = TimeGap(
                building_name=building_name,
                pro_time=pro_event.completion_time,
                bot_time=bot_event.completion_time,
                gap_seconds=gap_seconds,
                gap_percentage=gap_percentage,
                severity=severity
            )
            gaps.append(gap)
        
        return sorted(gaps, key=lambda x: abs(x.gap_seconds), reverse=True)
    
    def analyze_sequence_errors(
        self,
        pro_events: List[BuildEvent],
        bot_events: List[BuildEvent]
    ) -> List[SequenceError]:
        """순서 오류 분석"""
        errors = []
        
        # 순서 비교 (처음 10개 건물만)
        pro_order = [e.building_name for e in pro_events[:10]]
        bot_order = [e.building_name for e in bot_events[:10]]
        
        # 순서가 다른 경우 찾기
        for i, (pro_building, bot_building) in enumerate(zip(pro_order, bot_order)):
            if pro_building != bot_building:
                pro_time = pro_events[i].completion_time if i < len(pro_events) else 0
                bot_time = bot_events[i].completion_time if i < len(bot_events) else 0
                
                error = SequenceError(
                    expected_building=pro_building,
                    actual_building=bot_building,
                    expected_time=pro_time,
                    actual_time=bot_time,
                    error_type="order_mismatch"
                )
                errors.append(error)
        
        # 누락된 건물 찾기
        pro_buildings = {e.building_name for e in pro_events}
        bot_buildings = {e.building_name for e in bot_events}
        missing = pro_buildings - bot_buildings
        
        for building_name in missing:
            pro_event = next((e for e in pro_events if e.building_name == building_name), None)
            if pro_event:
                error = SequenceError(
                    expected_building=building_name,
                    actual_building="MISSING",
                    expected_time=pro_event.completion_time,
                    actual_time=0,
                    error_type="missing_building"
                )
                errors.append(error)
        
        return errors
    
    def analyze_resource_efficiency(
        self,
        pro_events: List[BuildEvent],
        bot_events: List[BuildEvent],
        telemetry_data: List[Dict[str, Any]]
    ) -> List[ResourceEfficiency]:
        """자원 효율 분석"""
        efficiency_data = []
        
        # Supply 구간별로 비교 (10, 20, 30, 40, 50)
        supply_checkpoints = [10, 20, 30, 40, 50]
        
        for supply in supply_checkpoints:
            # 봇의 해당 supply 시점 찾기
            bot_tel = None
            for tel in telemetry_data:
                if tel.get("supply_used", 0) >= supply:
                    bot_tel = tel
                    break
            
            if not bot_tel:
                continue
            
            # 프로는 평균적으로 해당 supply에서 자원이 거의 0에 수렴한다고 가정
            # (실제로는 더 정교한 분석 필요)
            pro_minerals = 50  # 프로는 평균 50 미네랄 유지
            pro_vespene = 25   # 프로는 평균 25 가스 유지
            
            bot_minerals = bot_tel.get("minerals", 0)
            bot_vespene = bot_tel.get("vespene", 0)
            
            mineral_waste = max(0, bot_minerals - pro_minerals)
            vespene_waste = max(0, bot_vespene - pro_vespene)
            
            # 효율 점수 계산 (0.0 ~ 1.0)
            total_waste = mineral_waste + vespene_waste * 2  # 가스는 2배 가중치
            max_waste = 500  # 최대 낭비 기준
            efficiency_score = max(0.0, 1.0 - (total_waste / max_waste))
            
            efficiency = ResourceEfficiency(
                supply=supply,
                pro_minerals=pro_minerals,
                bot_minerals=bot_minerals,
                pro_vespene=pro_vespene,
                bot_vespene=bot_vespene,
                mineral_waste=mineral_waste,
                vespene_waste=vespene_waste,
                efficiency_score=efficiency_score
            )
            efficiency_data.append(efficiency)
        
        return efficiency_data
    
    def analyze(
        self,
        build_order_timing: Dict[str, float],
        telemetry_data: List[Dict[str, Any]],
        game_id: Optional[str] = None
    ) -> GapAnalysisResult:
        """
        전체 분석 수행
        
        Args:
            build_order_timing: 봇의 빌드 오더 타이밍
            telemetry_data: 봇의 텔레메트리 데이터
            game_id: 게임 ID (선택사항)
        
        Returns:
            분석 결과
        """
        if game_id is None:
            game_id = f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 이벤트 추출
        pro_events = self.extract_pro_build_events()
        bot_events = self.extract_bot_build_events(build_order_timing, telemetry_data)
        
        if not pro_events or not bot_events:
            logger.warning("Insufficient data for analysis")
            return GapAnalysisResult(
                game_id=game_id,
                analysis_time=datetime.now().isoformat(),
                time_gaps=[],
                sequence_errors=[],
                resource_efficiency=[],
                critical_issues=[],
                recommendations=[]
            )
        
        # 분석 수행
        time_gaps = self.analyze_time_gaps(pro_events, bot_events)
        sequence_errors = self.analyze_sequence_errors(pro_events, bot_events)
        resource_efficiency = self.analyze_resource_efficiency(pro_events, bot_events, telemetry_data)
        
        # 심각한 문제 추출 (상위 3개)
        critical_issues = []
        for gap in sorted(time_gaps, key=lambda x: abs(x.gap_seconds), reverse=True)[:3]:
            if gap.severity in ["critical", "major"]:
                critical_issues.append(
                    f"{gap.building_name}: {gap.gap_seconds:.1f}초 늦음 "
                    f"(프로: {gap.pro_time:.1f}초, 봇: {gap.bot_time:.1f}초)"
                )
        
        # 권장사항 생성
        recommendations = []
        for gap in time_gaps[:3]:
            if gap.severity == "critical":
                recommendations.append(
                    f"{gap.building_name} 건설을 {gap.gap_seconds:.1f}초 더 빠르게 시작하도록 "
                    f"economy_manager.py의 드론 생산 로직을 최적화하세요."
                )
        
        # 자원 효율이 낮은 경우
        low_efficiency = [e for e in resource_efficiency if e.efficiency_score < 0.5]
        if low_efficiency:
            recommendations.append(
                f"Supply {low_efficiency[0].supply} 구간에서 자원 효율이 낮습니다. "
                f"production_manager.py의 Emergency Flush 로직을 강화하세요."
            )
        
        result = GapAnalysisResult(
            game_id=game_id,
            analysis_time=datetime.now().isoformat(),
            time_gaps=time_gaps,
            sequence_errors=sequence_errors,
            resource_efficiency=resource_efficiency,
            critical_issues=critical_issues,
            recommendations=recommendations
        )
        
        # 결과 저장
        self.save_analysis_result(result)
        
        return result
    
    def save_analysis_result(self, result: GapAnalysisResult) -> None:
        """분석 결과 저장"""
        output_file = self.analysis_output_dir / f"gap_analysis_{result.game_id}.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(result), f, indent=2, ensure_ascii=False)
            logger.info(f"Analysis result saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save analysis result: {e}")
    
    def generate_gemini_feedback(self, result: GapAnalysisResult) -> str:
        """
        Gemini Self-Healing을 위한 피드백 생성
        
        Returns:
            Gemini에게 전달할 피드백 문자열
        """
        feedback_parts = []
        
        feedback_parts.append("=== Build-Order Gap Analysis ===")
        feedback_parts.append(f"Game ID: {result.game_id}")
        feedback_parts.append("")
        
        if result.critical_issues:
            feedback_parts.append("Critical Issues (프로 대비 가장 늦은 건물 3개):")
            for i, issue in enumerate(result.critical_issues, 1):
                feedback_parts.append(f"  {i}. {issue}")
            feedback_parts.append("")
        
        if result.time_gaps:
            feedback_parts.append("Time Gaps (시간 오차):")
            for gap in result.time_gaps[:5]:
                feedback_parts.append(
                    f"  - {gap.building_name}: {gap.gap_seconds:.1f}초 늦음 "
                    f"({gap.severity})"
                )
            feedback_parts.append("")
        
        if result.sequence_errors:
            feedback_parts.append("Sequence Errors (순서 오류):")
            for error in result.sequence_errors[:3]:
                feedback_parts.append(
                    f"  - 예상: {error.expected_building}, 실제: {error.actual_building}"
                )
            feedback_parts.append("")
        
        if result.resource_efficiency:
            low_efficiency = [e for e in result.resource_efficiency if e.efficiency_score < 0.5]
            if low_efficiency:
                feedback_parts.append("Resource Efficiency Issues (자원 효율 문제):")
                for eff in low_efficiency:
                    feedback_parts.append(
                        f"  - Supply {eff.supply}: 효율 {eff.efficiency_score:.2f} "
                        f"(미네랄 낭비: {eff.mineral_waste}, 가스 낭비: {eff.vespene_waste})"
                    )
                feedback_parts.append("")
        
        if result.recommendations:
            feedback_parts.append("Recommendations (권장사항):")
            for i, rec in enumerate(result.recommendations, 1):
                feedback_parts.append(f"  {i}. {rec}")
        
        return "\n".join(feedback_parts)


def update_curriculum_priority(
    curriculum_manager,
    gap_analysis: GapAnalysisResult
) -> None:
    """
    CurriculumManager의 우선순위 업데이트
    
    Args:
        curriculum_manager: CurriculumManager 인스턴스
        gap_analysis: 분석 결과
    """
    if not gap_analysis.time_gaps:
        return
    
    # 가장 심각한 시간 오차를 가진 건물 찾기
    critical_gap = max(
        gap_analysis.time_gaps,
        key=lambda x: abs(x.gap_seconds) if x.severity in ["critical", "major"] else 0
    )
    
    if critical_gap.severity in ["critical", "major"]:
        building_name = critical_gap.building_name
        logger.info(
            f"[CURRICULUM] Updating priority for {building_name} "
            f"(gap: {critical_gap.gap_seconds:.1f}초)"
        )
        
        # CurriculumManager에 우선순위 업데이트 요청
        # (실제 구현은 CurriculumManager의 메서드에 따라 다름)
        if hasattr(curriculum_manager, 'update_priority'):
            curriculum_manager.update_priority(building_name, "Urgent")


# 사용 예시 함수
def analyze_bot_performance(
    bot,
    game_result: str = "defeat"
) -> Optional[GapAnalysisResult]:
    """
    게임 종료 후 봇 성능 분석
    
    Args:
        bot: WickedZergBotPro 인스턴스
        game_result: 게임 결과 ("victory" or "defeat")
    
    Returns:
        분석 결과 (패배한 경우에만)
    """
    # 패배한 경우에만 분석
    if game_result.lower() != "defeat":
        return None
    
    try:
        # StrategyAudit 초기화
        auditor = StrategyAudit()
        
        # 봇의 빌드 오더 타이밍 추출
        build_order_timing = {}
        if hasattr(bot, 'production') and bot.production:
            build_order_timing = getattr(bot.production, 'build_order_timing', {})
        
        # 텔레메트리 데이터 추출
        telemetry_data = []
        if hasattr(bot, 'telemetry_logger') and bot.telemetry_logger:
            telemetry_data = bot.telemetry_logger.telemetry_data
        
        # 분석 수행
        instance_id = getattr(bot, 'instance_id', 0)
        result = auditor.analyze(
            build_order_timing=build_order_timing,
            telemetry_data=telemetry_data,
            game_id=f"game_{instance_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze bot performance: {e}")
        import traceback
        traceback.print_exc()
        return None
