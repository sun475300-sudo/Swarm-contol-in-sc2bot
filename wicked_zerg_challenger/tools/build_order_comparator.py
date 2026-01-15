# -*- coding: utf-8 -*-
"""
Build Order Comparator - Compare training builds with pro gamer replays

This module compares the build order used during training with pro gamer replay data
and analyzes the differences to improve future performance.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class BuildOrderComparison:
    """Result of comparing training build with pro gamer baseline"""
    parameter_name: str
    training_supply: Optional[float]
    pro_supply: Optional[float]
    difference: Optional[float]  # training - pro (positive = later, negative = earlier)
    improvement_needed: bool
    recommendation: str


@dataclass
class BuildOrderAnalysis:
    """Complete analysis of build order comparison"""
    game_id: str
    game_result: str  # "Victory" or "Defeat"
    training_build: Dict[str, Optional[float]]
    pro_baseline: Dict[str, Optional[float]]
    comparisons: List[BuildOrderComparison]
    overall_score: float  # 0.0 - 1.0
    recommendations: List[str]


class BuildOrderComparator:
    """
    Compare training build orders with pro gamer replay data
    
    Features:
    - Extract build order from current game
    - Load pro gamer baseline from learned_build_orders.json
    - Compare timings and identify gaps
    - Generate recommendations for improvement
    - Update learned parameters for next game
    """
    
    def __init__(self, learned_data_path: Optional[Path] = None):
        """
        Initialize BuildOrderComparator
        
        Args:
            learned_data_path: Path to learned_build_orders.json (default: auto-detect)
        """
        if learned_data_path is None:
            # Auto-detect learned_build_orders.json
            script_dir = Path(__file__).parent.parent
            possible_paths = [
                script_dir / "local_training" / "scripts" / "learned_build_orders.json",
                script_dir / "learned_build_orders.json",
                Path("local_training/scripts/learned_build_orders.json"),
            ]
            
            for path in possible_paths:
                if path.exists():
                    learned_data_path = path
                    break
        
        self.learned_data_path = learned_data_path
        self.pro_baseline: Dict[str, float] = {}
        self._load_pro_baseline()
        
        # Comparison history for trend analysis
        self.comparison_history: List[BuildOrderAnalysis] = []
        self.comparison_history_file = Path("local_training/scripts/build_order_comparison_history.json")
    
    def _load_pro_baseline(self) -> None:
        """Load pro gamer baseline from learned_build_orders.json"""
        if self.learned_data_path is None or not self.learned_data_path.exists():
            print(f"[WARNING] Learned data file not found: {self.learned_data_path}")
            return
        
        try:
            with open(self.learned_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                if "learned_parameters" in data:
                    self.pro_baseline = data["learned_parameters"]
                else:
                    self.pro_baseline = data
            
            print(f"[BUILD COMPARATOR] Loaded pro baseline: {len(self.pro_baseline)} parameters")
        except Exception as e:
            print(f"[WARNING] Failed to load pro baseline: {e}")
    
    def compare(
        self,
        training_build: Dict[str, Optional[float]],
        game_result: str,
        game_id: Optional[str] = None
    ) -> BuildOrderAnalysis:
        """
        Compare training build order with pro gamer baseline
        
        Args:
            training_build: Build order timing from current game (supply values)
            game_result: "Victory" or "Defeat"
            game_id: Unique game identifier
            
        Returns:
            BuildOrderAnalysis with comparisons and recommendations
        """
        if game_id is None:
            game_id = f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        comparisons: List[BuildOrderComparison] = []
        recommendations: List[str] = []
        
        # Compare each parameter
        for param_name in ["natural_expansion_supply", "gas_supply", "spawning_pool_supply", 
                          "third_hatchery_supply", "speed_upgrade_supply"]:
            training_value = training_build.get(param_name)
            pro_value = self.pro_baseline.get(param_name)
            
            if training_value is None and pro_value is None:
                continue
            
            comparison = self._compare_parameter(param_name, training_value, pro_value, game_result)
            comparisons.append(comparison)
            
            if comparison.improvement_needed:
                recommendations.append(comparison.recommendation)
        
        # Calculate overall score
        overall_score = self._calculate_score(comparisons, game_result)
        
        analysis = BuildOrderAnalysis(
            game_id=game_id,
            game_result=game_result,
            training_build=training_build,
            pro_baseline=self.pro_baseline,
            comparisons=comparisons,
            overall_score=overall_score,
            recommendations=recommendations
        )
        
        # Save to history
        self._save_comparison(analysis)
        
        return analysis
    
    def _compare_parameter(
        self,
        param_name: str,
        training_value: Optional[float],
        pro_value: Optional[float],
        game_result: str
    ) -> BuildOrderComparison:
        """Compare a single parameter"""
        if training_value is None:
            return BuildOrderComparison(
                parameter_name=param_name,
                training_supply=None,
                pro_supply=pro_value,
                difference=None,
                improvement_needed=True,
                recommendation=f"?? {param_name}: Not executed. Should execute at supply {pro_value}"
            )
        
        if pro_value is None:
            return BuildOrderComparison(
                parameter_name=param_name,
                training_supply=training_value,
                pro_supply=None,
                difference=None,
                improvement_needed=False,
                recommendation=f"? {param_name}: Executed at supply {training_value} (no baseline)"
            )
        
        difference = training_value - pro_value
        improvement_needed = False
        recommendation = ""
        
        # Tolerance window: within ¡¾2 supply is considered good
        tolerance = 2.0
        
        if abs(difference) <= tolerance:
            recommendation = f"? {param_name}: Excellent timing (Training: {training_value}, Pro: {pro_value})"
        elif difference > tolerance:
            # Training is later than pro (bad if defeat, okay if victory)
            if game_result == "Defeat":
                improvement_needed = True
                recommendation = f"?? {param_name}: Too late (Training: {training_value}, Pro: {pro_value}, Gap: +{difference:.1f})"
            else:
                recommendation = f"?? {param_name}: Later than pro but won (Training: {training_value}, Pro: {pro_value})"
        else:
            # Training is earlier than pro (generally good)
            if game_result == "Victory":
                recommendation = f"? {param_name}: Earlier than pro and won (Training: {training_value}, Pro: {pro_value}, Gap: {difference:.1f})"
            else:
                recommendation = f"?? {param_name}: Earlier than pro but lost (Training: {training_value}, Pro: {pro_value})"
        
        # Always flag if very late (>5 supply difference)
        if difference > 5:
            improvement_needed = True
        
        return BuildOrderComparison(
            parameter_name=param_name,
            training_supply=training_value,
            pro_supply=pro_value,
            difference=difference,
            improvement_needed=improvement_needed,
            recommendation=recommendation
        )
    
    def _calculate_score(
        self,
        comparisons: List[BuildOrderComparison],
        game_result: str
    ) -> float:
        """Calculate overall build order score (0.0 - 1.0)"""
        if not comparisons:
            return 0.5  # Neutral score if no comparisons
        
        score = 0.0
        weight_sum = 0.0
        
        # Weight each parameter by importance
        weights = {
            "natural_expansion_supply": 1.5,  # Very important
            "gas_supply": 1.2,  # Important
            "spawning_pool_supply": 1.5,  # Very important (defense)
            "third_hatchery_supply": 1.0,  # Medium importance
            "speed_upgrade_supply": 1.0,  # Medium importance
        }
        
        for comp in comparisons:
            weight = weights.get(comp.parameter_name, 1.0)
            
            if comp.difference is None:
                # Missing execution: penalty
                score += 0.2 * weight  # 20% score for missing
            elif abs(comp.difference) <= 2:
                # Excellent timing
                score += 1.0 * weight
            elif abs(comp.difference) <= 5:
                # Good timing
                score += 0.7 * weight
            elif abs(comp.difference) <= 10:
                # Acceptable timing
                score += 0.5 * weight
            else:
                # Poor timing
                score += 0.3 * weight
            
            weight_sum += weight
        
        overall_score = score / weight_sum if weight_sum > 0 else 0.5
        
        # Adjust based on game result
        if game_result == "Victory":
            overall_score = min(1.0, overall_score * 1.1)  # Boost for victories
        else:
            overall_score = overall_score * 0.9  # Reduce for defeats
        
        return overall_score
    
    def _save_comparison(self, analysis: BuildOrderAnalysis) -> None:
        """Save comparison to history file"""
        try:
            # Ensure directory exists
            self.comparison_history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing history
            if self.comparison_history_file.exists():
                with open(self.comparison_history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                    self.comparison_history = [
                        BuildOrderAnalysis(**item) for item in history_data.get("comparisons", [])
                    ]
            else:
                self.comparison_history = []
            
            # Add new analysis
            self.comparison_history.append(analysis)
            
            # Keep only last 100 comparisons
            if len(self.comparison_history) > 100:
                self.comparison_history = self.comparison_history[-100:]
            
            # Save to file
            history_data = {
                "last_updated": datetime.now().isoformat(),
                "total_comparisons": len(self.comparison_history),
                "comparisons": [
                    {
                        "game_id": comp.game_id,
                        "game_result": comp.game_result,
                        "training_build": comp.training_build,
                        "pro_baseline": comp.pro_baseline,
                        "overall_score": comp.overall_score,
                        "recommendations": comp.recommendations,
                        "comparisons": [
                            {
                                "parameter_name": c.parameter_name,
                                "training_supply": c.training_supply,
                                "pro_supply": c.pro_supply,
                                "difference": c.difference,
                                "improvement_needed": c.improvement_needed,
                                "recommendation": c.recommendation
                            }
                            for c in comp.comparisons
                        ]
                    }
                    for comp in self.comparison_history
                ]
            }
            
            with open(self.comparison_history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"[WARNING] Failed to save comparison history: {e}")
    
    def update_learned_parameters(
        self,
        analysis: BuildOrderAnalysis,
        learning_rate: float = 0.1
    ) -> Dict[str, float]:
        """
        Update learned parameters based on comparison analysis
        
        Args:
            analysis: BuildOrderAnalysis result
            learning_rate: How aggressively to update (0.0 - 1.0)
            
        Returns:
            Updated learned parameters
        """
        updated_params = self.pro_baseline.copy()
        
        # Only update if we won (victory builds are better)
        if analysis.game_result != "Victory":
            return updated_params
        
        # Update parameters that were executed and are different from baseline
        for comp in analysis.comparisons:
            if comp.training_supply is not None and comp.pro_supply is not None:
                # Move towards training value if it was successful
                current_value = updated_params.get(comp.parameter_name, comp.pro_supply)
                
                # If training was earlier and we won, move baseline earlier
                if comp.difference is not None and comp.difference < 0:
                    # Training was earlier - move baseline earlier slightly
                    new_value = current_value + (comp.difference * learning_rate * 0.5)
                    updated_params[comp.parameter_name] = max(6.0, new_value)  # Minimum supply 6
                elif comp.difference is not None and comp.difference > 2:
                    # Training was later - don't move (keep earlier baseline)
                    pass
        
        return updated_params
    
    def generate_report(self, analysis: BuildOrderAnalysis) -> str:
        """Generate human-readable comparison report"""
        report_parts = []
        
        report_parts.append("=" * 70)
        report_parts.append(f"BUILD ORDER COMPARISON REPORT")
        report_parts.append("=" * 70)
        report_parts.append(f"Game ID: {analysis.game_id}")
        report_parts.append(f"Game Result: {analysis.game_result}")
        report_parts.append(f"Overall Score: {analysis.overall_score:.2%}")
        report_parts.append("")
        
        report_parts.append("COMPARISON DETAILS:")
        report_parts.append("-" * 70)
        
        for comp in analysis.comparisons:
            report_parts.append(f"\n{comp.parameter_name}:")
            report_parts.append(f"  Training: {comp.training_supply or 'Not executed'}")
            report_parts.append(f"  Pro Baseline: {comp.pro_supply or 'N/A'}")
            if comp.difference is not None:
                report_parts.append(f"  Difference: {comp.difference:+.1f} supply")
            report_parts.append(f"  {comp.recommendation}")
        
        if analysis.recommendations:
            report_parts.append("")
            report_parts.append("RECOMMENDATIONS:")
            report_parts.append("-" * 70)
            for rec in analysis.recommendations:
                report_parts.append(f"  ? {rec}")
        
        report_parts.append("")
        report_parts.append("=" * 70)
        
        return "\n".join(report_parts)


def compare_with_pro_baseline(
    training_build: Dict[str, Optional[float]],
    game_result: str,
    game_id: Optional[str] = None
) -> BuildOrderAnalysis:
    """
    Convenience function to compare training build with pro baseline
    
    Args:
        training_build: Build order timing from current game
        game_result: "Victory" or "Defeat"
        game_id: Unique game identifier
        
    Returns:
        BuildOrderAnalysis result
    """
    comparator = BuildOrderComparator()
    return comparator.compare(training_build, game_result, game_id)
