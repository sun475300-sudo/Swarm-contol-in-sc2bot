# -*- coding: utf-8 -*-
"""
Compare Pro Gamer Replays vs Training Replays

프로게이머 리플레이 학습데이터와 훈련한 리플레이 학습데이터를 비교 분석하는 스크립트입니다.
- 프로게이머 리플레이 데이터 로드 (D:\replays\replays)
- 훈련 리플레이 데이터 로드 (training_stats.json, build_order_comparison_history.json)
- 두 데이터 소스 비교 분석
- 상세 리포트 생성
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import statistics

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
 sys.path.insert(0, str(script_dir))

try:
    from local_training.scripts.replay_build_order_learner import ReplayBuildOrderExtractor
    from tools.build_order_comparator import BuildOrderComparator
except ImportError as e:
    print(f"[WARNING] Failed to import required modules: {e}")
    ReplayBuildOrderExtractor = None
    BuildOrderComparator = None


class ProVsTrainingComparator:
    """프로게이머 리플레이 vs 훈련 리플레이 비교 분석 클래스"""

    def __init__(
        self,
        pro_replay_dir: Optional[Path] = None,
        training_data_dir: Optional[Path] = None
    ):
        """
        Initialize ProVsTrainingComparator

        Args:
            pro_replay_dir: Directory containing pro gamer replays (default: D:\replays\replays)
            training_data_dir: Directory containing training data (default: auto-detect)
        """
        # Pro replay directory
        if pro_replay_dir is None:
            pro_replay_dir = Path("D:/replays/replays")
        if not pro_replay_dir.exists():
            # Try alternative paths
            alt_paths = [
                Path(__file__).parent.parent / "replays_archive",
                Path.home() / "replays" / "replays",
            ]
            for path in alt_paths:
                if path.exists():
                    pro_replay_dir = path
                    break

        self.pro_replay_dir = pro_replay_dir

        # Training data directory
        if training_data_dir is None:
            training_data_dir = Path(__file__).parent.parent

        self.training_data_dir = training_data_dir
 
        # Training data paths
        self.training_stats_path = training_data_dir / "data" / "training_stats.json"
        if not self.training_stats_path.exists():
            self.training_stats_path = training_data_dir / "training_stats.json"

        self.comparison_history_path = training_data_dir / "local_training" / "scripts" / "build_order_comparison_history.json"
        self.learned_build_orders_path = training_data_dir / "local_training" / "scripts" / "learned_build_orders.json"

        # Pro replay learned data paths
        self.pro_archive_dir = Path("D:/replays/archive")
        if not self.pro_archive_dir.exists():
            self.pro_archive_dir = Path("D:/replays/archive")

        # Output directory
        self.output_dir = training_data_dir / "local_training" / "comparison_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
 
        print(f"[COMPARATOR] Initialized")
        print(f"[COMPARATOR] Pro replay directory: {self.pro_replay_dir}")
        print(f"[COMPARATOR] Training data directory: {self.training_data_dir}")
        print(f"[COMPARATOR] Output directory: {self.output_dir}")
 
 def load_pro_replay_data(self) -> Dict[str, Any]:
        """Load pro gamer replay data"""
 pro_data = {
            "build_orders": [],
            "timings": defaultdict(list),
            "replay_count": 0,
            "source": "pro_replays"
 }
 
 # Try to load from learned_build_orders.json (pro baseline)
 if self.learned_build_orders_path.exists():
 try:
                with open(self.learned_build_orders_path, 'r', encoding='utf-8') as f:
 pro_baseline = json.load(f)
                    pro_data["baseline"] = pro_baseline
                    print(f"[PRO DATA] Loaded pro baseline from {self.learned_build_orders_path}")
 except Exception as e:
                print(f"[WARNING] Failed to load pro baseline: {e}")
 
 # Try to load from archive directory
 if self.pro_archive_dir.exists():
            archive_files = list(self.pro_archive_dir.glob("training_*/learned_build_orders.json"))
 if archive_files:
 # Load most recent archive
 latest_archive = max(archive_files, key=lambda p: p.stat().st_mtime)
 try:
                    with open(latest_archive, 'r', encoding='utf-8') as f:
 archive_data = json.load(f)
                        if "learned_parameters" in archive_data:
                            pro_data["baseline"] = archive_data["learned_parameters"]
 elif isinstance(archive_data, dict):
                            pro_data["baseline"] = archive_data
                        print(f"[PRO DATA] Loaded pro data from archive: {latest_archive}")
 except Exception as e:
                    print(f"[WARNING] Failed to load archive data: {e}")
 
 # Try to extract from replay files if sc2reader is available
 if ReplayBuildOrderExtractor and self.pro_replay_dir.exists():
 try:
 extractor = ReplayBuildOrderExtractor(str(self.pro_replay_dir))
 replay_files = extractor.scan_replays()
 
 if replay_files:
                    print(f"[PRO DATA] Found {len(replay_files)} pro replay files")
 # Extract build orders from a sample of replays (limit to 50 for performance)
 sample_size = min(50, len(replay_files))
 for replay_path in replay_files[:sample_size]:
 try:
 build_order = extractor.extract_build_order(replay_path)
 if build_order:
                                pro_data["build_orders"].append(build_order)
 
 # Extract timings
                                for param_name in ["natural_expansion_supply", "gas_supply", 
                                                  "spawning_pool_supply", "third_hatchery_supply", 
                                                  "speed_upgrade_supply"]:
 if param_name in build_order:
 value = build_order[param_name]
 if value is not None:
                                            pro_data["timings"][param_name].append(value)
 except Exception as e:
                            print(f"[WARNING] Failed to extract from {replay_path.name}: {e}")
 continue
 
                    pro_data["replay_count"] = len(pro_data["build_orders"])
                    print(f"[PRO DATA] Extracted {pro_data['replay_count']} build orders from replays")
 except Exception as e:
                print(f"[WARNING] Failed to extract from replay files: {e}")
 
 return pro_data
 
 def load_training_data(self) -> Dict[str, Any]:
        """Load training replay data"""
 training_data = {
            "build_orders": [],
            "timings": defaultdict(list),
            "game_count": 0,
            "comparisons": [],
            "source": "training"
 }
 
 # Load comparison history
 if self.comparison_history_path.exists():
 try:
                with open(self.comparison_history_path, 'r', encoding='utf-8') as f:
 history_data = json.load(f)
                    comparisons = history_data.get("comparisons", [])
                    training_data["comparisons"] = comparisons
                    training_data["game_count"] = len(comparisons)
 
 # Extract build orders from comparisons
 for comp in comparisons:
                        training_build = comp.get("training_build", {})
 if training_build:
                            training_data["build_orders"].append(training_build)
 
 # Extract timings
 for param_name, value in training_build.items():
 if value is not None:
                                    training_data["timings"][param_name].append(value)
 
                    print(f"[TRAINING DATA] Loaded {len(comparisons)} comparisons")
 except Exception as e:
                print(f"[WARNING] Failed to load comparison history: {e}")
 
 # Load training stats
 if self.training_stats_path.exists():
 try:
                with open(self.training_stats_path, 'r', encoding='utf-8', errors='ignore') as f:
 stats_count = 0
 for line in f:
 line = line.strip()
 if not line:
 continue
 try:
 obj = json.loads(line)
 stats_count += 1
 except json.JSONDecodeError:
 continue
                    training_data["stats_count"] = stats_count
                    print(f"[TRAINING DATA] Loaded {stats_count} training stats records")
 except Exception as e:
                print(f"[WARNING] Failed to load training stats: {e}")
 
 return training_data
 
 def compare_timings(
 self,
 pro_data: Dict[str, Any],
 training_data: Dict[str, Any]
 ) -> Dict[str, Dict[str, Any]]:
        """Compare build order timings between pro and training"""
 comparison_results = {}
 
 # Get baseline from pro data
        pro_baseline = pro_data.get("baseline", {})
        pro_timings = pro_data.get("timings", {})
        training_timings = training_data.get("timings", {})
 
 # Parameters to compare
 parameters = [
            "natural_expansion_supply",
            "gas_supply",
            "spawning_pool_supply",
            "third_hatchery_supply",
            "speed_upgrade_supply"
 ]
 
 for param_name in parameters:
 pro_baseline_value = pro_baseline.get(param_name)
 pro_timing_list = pro_timings.get(param_name, [])
 training_timing_list = training_timings.get(param_name, [])
 
 comparison = {
                "parameter": param_name,
                "pro_baseline": pro_baseline_value,
                "pro_mean": statistics.mean(pro_timing_list) if pro_timing_list else None,
                "pro_median": statistics.median(pro_timing_list) if pro_timing_list else None,
                "pro_std": statistics.stdev(pro_timing_list) if len(pro_timing_list) > 1 else None,
                "pro_count": len(pro_timing_list),
                "training_mean": statistics.mean(training_timing_list) if training_timing_list else None,
                "training_median": statistics.median(training_timing_list) if training_timing_list else None,
                "training_std": statistics.stdev(training_timing_list) if len(training_timing_list) > 1 else None,
                "training_count": len(training_timing_list),
 }
 
 # Calculate differences
            if comparison["pro_mean"] is not None and comparison["training_mean"] is not None:
                comparison["mean_difference"] = comparison["training_mean"] - comparison["pro_mean"]
                comparison["median_difference"] = (
                    comparison["training_median"] - comparison["pro_median"]
                    if comparison["training_median"] is not None and comparison["pro_median"] is not None
 else None
 )
 else:
                comparison["mean_difference"] = None
                comparison["median_difference"] = None
 
 comparison_results[param_name] = comparison
 
 return comparison_results
 
 def analyze_performance(
 self,
 pro_data: Dict[str, Any],
 training_data: Dict[str, Any]
 ) -> Dict[str, Any]:
        """Analyze overall performance comparison"""
 analysis = {
            "pro_replay_count": pro_data.get("replay_count", 0),
            "training_game_count": training_data.get("game_count", 0),
            "pro_baseline_available": "baseline" in pro_data,
            "training_comparisons_available": len(training_data.get("comparisons", [])) > 0,
 }
 
 # Analyze build order scores from training
        comparisons = training_data.get("comparisons", [])
 if comparisons:
 scores = []
 victories = 0
 defeats = 0
 
 for comp in comparisons:
                score = comp.get("overall_score")
 if score is not None:
 scores.append(score)
 
                result = comp.get("game_result", "").lower()
                if "victory" in result:
 victories += 1
 else:
 defeats += 1
 
 if scores:
                analysis["avg_build_order_score"] = statistics.mean(scores)
                analysis["median_build_order_score"] = statistics.median(scores)
                analysis["min_build_order_score"] = min(scores)
                analysis["max_build_order_score"] = max(scores)
 
            analysis["victories"] = victories
            analysis["defeats"] = defeats
            analysis["win_rate"] = (victories / len(comparisons) * 100) if comparisons else 0.0
 
 return analysis
 
 def generate_comparison_report(
 self,
 pro_data: Dict[str, Any],
 training_data: Dict[str, Any],
 timing_comparisons: Dict[str, Dict[str, Any]],
 performance_analysis: Dict[str, Any]
 ) -> str:
        """Generate detailed comparison report"""
 report_parts = []
 
        report_parts.append("=" * 70)
        report_parts.append("PRO GAMER REPLAYS vs TRAINING REPLAYS COMPARISON REPORT")
        report_parts.append("=" * 70)
        report_parts.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_parts.append("")
 
 # Data sources
        report_parts.append("DATA SOURCES:")
        report_parts.append("-" * 70)
        report_parts.append(f"Pro Replay Directory: {self.pro_replay_dir}")
        report_parts.append(f"Pro Replays Analyzed: {pro_data.get('replay_count', 0)}")
        report_parts.append(f"Training Data Directory: {self.training_data_dir}")
        report_parts.append(f"Training Games Analyzed: {training_data.get('game_count', 0)}")
        report_parts.append("")
 
 # Performance summary
        report_parts.append("PERFORMANCE SUMMARY:")
        report_parts.append("-" * 70)
        if performance_analysis.get("win_rate") is not None:
            report_parts.append(f"Training Win Rate: {performance_analysis.get('win_rate', 0.0):.2f}%")
            report_parts.append(f"Training Victories: {performance_analysis.get('victories', 0)}")
            report_parts.append(f"Training Defeats: {performance_analysis.get('defeats', 0)}")
 
        if performance_analysis.get("avg_build_order_score") is not None:
            report_parts.append(f"Average Build Order Score: {performance_analysis.get('avg_build_order_score', 0.0):.2%}")
            report_parts.append(f"Median Build Order Score: {performance_analysis.get('median_build_order_score', 0.0):.2%}")
            report_parts.append(f"Score Range: {performance_analysis.get('min_build_order_score', 0.0):.2%} - {performance_analysis.get('max_build_order_score', 0.0):.2%}")
        report_parts.append("")
 
 # Timing comparisons
        report_parts.append("BUILD ORDER TIMING COMPARISONS:")
        report_parts.append("-" * 70)
 
 for param_name, comp in timing_comparisons.items():
            report_parts.append(f"\n{param_name}:")
 
            if comp["pro_baseline"] is not None:
                report_parts.append(f"  Pro Baseline: {comp['pro_baseline']:.1f} supply")
 
            if comp["pro_mean"] is not None:
                report_parts.append(f"  Pro Mean: {comp['pro_mean']:.1f} supply (n={comp['pro_count']})")
                if comp["pro_std"] is not None:
                    report_parts.append(f"  Pro Std Dev: {comp['pro_std']:.2f} supply")
 
            if comp["training_mean"] is not None:
                report_parts.append(f"  Training Mean: {comp['training_mean']:.1f} supply (n={comp['training_count']})")
                if comp["training_std"] is not None:
                    report_parts.append(f"  Training Std Dev: {comp['training_std']:.2f} supply")
 
            if comp["mean_difference"] is not None:
                diff = comp["mean_difference"]
 if abs(diff) <= 2:
                    status = "? EXCELLENT"
 elif abs(diff) <= 5:
                    status = "?? GOOD"
 else:
                    status = "? NEEDS IMPROVEMENT"
 
                report_parts.append(f"  Difference: {diff:+.1f} supply {status}")
 if diff > 0:
                    report_parts.append(f"    → Training is {diff:.1f} supply LATER than pro")
 elif diff < 0:
                    report_parts.append(f"    → Training is {abs(diff):.1f} supply EARLIER than pro")
 else:
                    report_parts.append(f"    → Training matches pro timing")
 
        report_parts.append("")
 
 # Recommendations
        report_parts.append("RECOMMENDATIONS:")
        report_parts.append("-" * 70)
 
 improvements_needed = []
 for param_name, comp in timing_comparisons.items():
            if comp["mean_difference"] is not None:
                diff = comp["mean_difference"]
 if diff > 5:
 improvements_needed.append(
                        f"  - {param_name}: Execute {diff:.1f} supply earlier (currently {comp['training_mean']:.1f}, should be {comp['pro_mean']:.1f})"
 )
 
 if improvements_needed:
 for rec in improvements_needed:
 report_parts.append(rec)
 else:
            report_parts.append("  ? All timings are within acceptable range!")
 
        report_parts.append("")
        report_parts.append("=" * 70)
 
        return "\n".join(report_parts)
 
 def save_comparison_data(
 self,
 pro_data: Dict[str, Any],
 training_data: Dict[str, Any],
 timing_comparisons: Dict[str, Dict[str, Any]],
 performance_analysis: Dict[str, Any],
 report: str
 ) -> None:
        """Save comparison data and report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
 
 # Save comparison data
 comparison_data = {
            "timestamp": timestamp,
            "pro_data": {
                "replay_count": pro_data.get("replay_count", 0),
                "baseline": pro_data.get("baseline", {}),
                "timings": {k: list(v) for k, v in pro_data.get("timings", {}).items()}
 },
            "training_data": {
                "game_count": training_data.get("game_count", 0),
                "timings": {k: list(v) for k, v in training_data.get("timings", {}).items()}
 },
            "timing_comparisons": timing_comparisons,
            "performance_analysis": performance_analysis
 }
 
        comparison_file = self.output_dir / f"comparison_{timestamp}.json"
        with open(comparison_file, 'w', encoding='utf-8') as f:
 json.dump(comparison_data, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] Comparison data: {comparison_file}")
 
 # Save report
        report_file = self.output_dir / f"report_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
 f.write(report)
        print(f"[SAVED] Report: {report_file}")


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("PRO GAMER REPLAYS vs TRAINING REPLAYS COMPARISON")
    print("=" * 70)
 print()
 
 comparator = ProVsTrainingComparator()
 
 # Load data
    print("[STEP 1] Loading pro gamer replay data...")
 pro_data = comparator.load_pro_replay_data()
 
    print("\n[STEP 2] Loading training replay data...")
 training_data = comparator.load_training_data()
 
    if not pro_data.get("baseline") and not pro_data.get("build_orders"):
        print("[WARNING] No pro replay data found. Please ensure pro replays are available.")
 
    if not training_data.get("comparisons") and not training_data.get("build_orders"):
        print("[WARNING] No training data found. Please run training first.")
 return
 
 # Compare timings
    print("\n[STEP 3] Comparing build order timings...")
 timing_comparisons = comparator.compare_timings(pro_data, training_data)
 
 # Analyze performance
    print("\n[STEP 4] Analyzing performance...")
 performance_analysis = comparator.analyze_performance(pro_data, training_data)
 
 # Generate report
    print("\n[STEP 5] Generating comparison report...")
 report = comparator.generate_comparison_report(
 pro_data,
 training_data,
 timing_comparisons,
 performance_analysis
 )
 
 # Print report
    print("\n" + report)
 
 # Save data
    print("\n[STEP 6] Saving comparison data...")
 comparator.save_comparison_data(
 pro_data,
 training_data,
 timing_comparisons,
 performance_analysis,
 report
 )
 
    print("\n" + "=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
 main()