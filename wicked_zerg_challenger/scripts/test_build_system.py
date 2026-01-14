#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Order System Test Script

Tests the build order collection and validation system.
This script verifies:
1. Build order data files exist and are valid JSON
2. Build order collector can be imported and initialized
3. Data directory structure is correct
4. Sample build orders have required fields
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text:^60}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}[OK]{RESET} {text}")


def print_error(text: str):
    """Print error message"""
    print(f"{RED}[X]{RESET} {text}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{YELLOW}[!]{RESET} {text}")


def print_info(text: str):
    """Print info message"""
    print(f"{BLUE}[i]{RESET} {text}")


def test_data_directory() -> bool:
    """Test if data/build_orders directory exists"""
    print_header("TEST 1: Data Directory Structure")

    data_dir = Path("data/build_orders")

    if not data_dir.exists():
        print_error(f"Data directory not found: {data_dir}")
        print_info("Creating directory...")
        data_dir.mkdir(parents=True, exist_ok=True)
        print_success(f"Created directory: {data_dir}")
        return False

    print_success(f"Data directory exists: {data_dir}")
    return True


def test_build_order_files() -> tuple[bool, List[Path]]:
    """Test if build order JSON files exist"""
    print_header("TEST 2: Build Order Files")

    data_dir = Path("data/build_orders")
    json_files = list(data_dir.glob("*.json"))

    if not json_files:
        print_warning("No build order JSON files found")
        print_info("Run: python tools/build_order_collector.py --source spawningtool --race zerg --limit 10")
        return False, []

    print_success(f"Found {len(json_files)} build order file(s)")

    # Filter out summary files
    build_files = [f for f in json_files if not f.name.startswith("collection_summary")]
    print_info(f"Build order files: {len(build_files)}")
    print_info(f"Summary files: {len(json_files) - len(build_files)}")

    return True, build_files


def test_json_validity(files: List[Path]) -> tuple[bool, List[Dict]]:
    """Test if JSON files are valid and have required structure"""
    print_header("TEST 3: JSON File Validity")

    valid_builds = []
    invalid_count = 0

    for file_path in files:
        if file_path.name.startswith("collection_summary"):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if it's a list of builds or a single build
            if isinstance(data, list):
                builds = data
            elif isinstance(data, dict):
                builds = [data]
            else:
                print_error(f"Invalid structure in {file_path.name}: expected dict or list")
                invalid_count += 1
                continue

            # Validate each build
            for build in builds:
                if validate_build_structure(build, file_path.name):
                    valid_builds.append(build)
                else:
                    invalid_count += 1

        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON in {file_path.name}: {e}")
            invalid_count += 1
        except Exception as e:
            print_error(f"Error reading {file_path.name}: {e}")
            invalid_count += 1

    if valid_builds:
        print_success(f"Valid builds found: {len(valid_builds)}")

    if invalid_count > 0:
        print_warning(f"Invalid or problematic builds: {invalid_count}")

    return len(valid_builds) > 0, valid_builds


def validate_build_structure(build: Dict, filename: str) -> bool:
    """Validate that a build order has required fields"""
    required_fields = ["name", "race", "vs_race", "steps"]

    missing_fields = [field for field in required_fields if field not in build]

    if missing_fields:
        print_warning(f"{filename}: Missing fields: {', '.join(missing_fields)}")
        return False

    # Validate steps
    if not isinstance(build["steps"], list):
        print_warning(f"{filename}: 'steps' must be a list")
        return False

    if len(build["steps"]) == 0:
        print_warning(f"{filename}: 'steps' list is empty")
        return False

    # Validate step structure
    step_fields = ["supply", "time_seconds", "action"]
    for i, step in enumerate(build["steps"]):
        if not isinstance(step, dict):
            print_warning(f"{filename}: Step {i} is not a dict")
            return False

        missing_step_fields = [field for field in step_fields if field not in step]
        if missing_step_fields:
            print_warning(f"{filename}: Step {i} missing fields: {', '.join(missing_step_fields)}")
            return False

    return True


def test_build_order_collector() -> bool:
    """Test if build order collector can be imported"""
    print_header("TEST 4: Build Order Collector Module")

    try:
        sys.path.insert(0, str(Path("tools").absolute()))
        from build_order_collector import (
            SpawningToolCollector,
            SC2SenseiCollector,
            BuildOrderStep,
            BuildOrder
        )
        print_success("SpawningToolCollector imported successfully")
        print_success("SC2SenseiCollector imported successfully")
        print_success("BuildOrderStep imported successfully")
        print_success("BuildOrder imported successfully")
        return True
    except ImportError as e:
        print_error(f"Failed to import collector classes: {e}")
        print_info("Make sure dependencies are installed:")
        print_info("  pip install requests beautifulsoup4 selenium webdriver-manager")
        return False
    except Exception as e:
        print_error(f"Unexpected error importing collector: {e}")
        return False


def test_build_order_statistics(builds: List[Dict]) -> None:
    """Print statistics about collected build orders"""
    print_header("TEST 5: Build Order Statistics")

    if not builds:
        print_warning("No valid builds to analyze")
        return

    # Count by matchup
    matchups = {}
    for build in builds:
        matchup = f"{build.get('race', '?')}v{build.get('vs_race', '?')}"
        matchups[matchup] = matchups.get(matchup, 0) + 1

    print_info("Build orders by matchup:")
    for matchup, count in sorted(matchups.items()):
        print(f"  {matchup}: {count}")

    # Count by player (if available)
    players = {}
    for build in builds:
        player = build.get("player_name", "Unknown")
        players[player] = players.get(player, 0) + 1

    if len(players) > 1:
        print_info(f"\nBuild orders by player: {len(players)} unique players")
        top_players = sorted(players.items(), key=lambda x: x[1], reverse=True)[:5]
        for player, count in top_players:
            print(f"  {player}: {count}")

    # Average steps per build
    total_steps = sum(len(build.get("steps", [])) for build in builds)
    avg_steps = total_steps / len(builds) if builds else 0
    print_info(f"\nAverage steps per build: {avg_steps:.1f}")
    print_info(f"Total build steps: {total_steps}")


def test_build_order_learner_module() -> bool:
    """Test if build_order_learner module exists (optional)"""
    print_header("TEST 6: Build Order Learner Module (Optional)")

    learner_file = Path("build_order_learner.py")

    if learner_file.exists():
        print_success(f"Found {learner_file}")
        try:
            # Try to import
            import build_order_learner
            print_success("build_order_learner imported successfully")

            # Check for required classes
            if hasattr(build_order_learner, "BuildOrderLearner"):
                print_success("BuildOrderLearner class found")
            else:
                print_warning("BuildOrderLearner class not found")

            if hasattr(build_order_learner, "BuildOrderExecutor"):
                print_success("BuildOrderExecutor class found")
            else:
                print_warning("BuildOrderExecutor class not found")

            return True
        except Exception as e:
            print_error(f"Error importing build_order_learner: {e}")
            return False
    else:
        print_warning(f"{learner_file} not found")
        print_info("This is optional - the learner module may not be implemented yet")
        print_info("You can still use build_order_collector.py to collect data")
        return False


def main():
    """Run all tests"""
    print_header("BUILD ORDER SYSTEM TEST SUITE")
    print_info("Testing build order collection and validation system...\n")

    results = {
        "data_directory": False,
        "build_files": False,
        "json_validity": False,
        "collector_module": False,
        "learner_module": False
    }

    # Test 1: Data directory
    results["data_directory"] = test_data_directory()

    # Test 2: Build order files
    files_exist, build_files = test_build_order_files()
    results["build_files"] = files_exist

    # Test 3: JSON validity
    if build_files:
        json_valid, valid_builds = test_json_validity(build_files)
        results["json_validity"] = json_valid

        # Test 5: Statistics (only if we have valid builds)
        if valid_builds:
            test_build_order_statistics(valid_builds)
    else:
        print_warning("Skipping JSON validity test (no files found)")
        valid_builds = []

    # Test 4: Collector module
    results["collector_module"] = test_build_order_collector()

    # Test 6: Learner module (optional)
    results["learner_module"] = test_build_order_learner_module()

    # Final summary
    print_header("TEST SUMMARY")

    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)

    print_info(f"Tests passed: {passed_tests}/{total_tests}")
    print()

    for test_name, passed in results.items():
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {test_name:.<30} {status}")

    print()

    if not results["build_files"]:
        print_warning("No build order files found!")
        print_info("To collect build orders, run:")
        print_info("  python tools/build_order_collector.py --source spawningtool --race zerg --limit 10")
        print()

    if not results["collector_module"]:
        print_warning("Build order collector module not available!")
        print_info("Install dependencies:")
        print_info("  pip install requests beautifulsoup4 selenium webdriver-manager")
        print()

    if results["json_validity"] and results["collector_module"]:
        print_success("Build order system is ready to use!")
        print_info("Next steps:")
        print_info("  1. Collect more build orders if needed")
        print_info("  2. Integrate BuildOrderLearner into your bot (if implemented)")
        print_info("  3. Run training: python main_integrated.py")
    else:
        print_warning("Some tests failed. Please fix issues above before proceeding.")

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
