#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
완전한 실행 스크립트 - 전체 시스템을 처음부터 끝까지 실행
Complete Execution Script - Run entire system from start to finish

이 스크립트는 프로젝트의 전체 실행 흐름을 한 곳에 모아서 실행합니다.
This script consolidates the entire execution flow of the project.
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Optional, Any

# ============================================================================
# 1. 시스템 초기화 (System Initialization)
# ============================================================================

def initialize_system() -> Path:
    """시스템 초기화"""
    print("=" * 70)
    print("1. 시스템 초기화 (System Initialization)")
    print("=" * 70)

    # 1.1 SC2 경로 설정
    print("\n[1.1] SC2 경로 설정...")
    sc2_path = setup_sc2_path()
    if sc2_path:
        print(f"  ? SC2 경로: {sc2_path}")
    else:
        print("  ? SC2 경로를 찾을 수 없습니다. SC2PATH 환경 변수를 설정하세요.")

    # 1.2 Python 경로 설정
    print("\n[1.2] Python 경로 설정...")
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    print(f"  ? 프로젝트 경로: {project_dir}")

    # 1.3 로깅 시스템 초기화
    print("\n[1.3] 로깅 시스템 초기화...")
    try:
        from loguru import logger
        logger.remove()
        logger.add(sys.stderr, colorize=True, enqueue=True, catch=True, level="INFO")
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        logger.add(
            str(log_dir / "complete_run.log"),
            rotation="10 MB",
            enqueue=True,
            catch=True,
            level="DEBUG",
            encoding="utf-8",
        )
        print("  ? 로깅 시스템 초기화 완료")
    except ImportError:
        print("  ? loguru가 설치되지 않았습니다. 기본 로깅을 사용합니다.")
        import logging
        logging.basicConfig(level=logging.INFO)

    # 1.4 PyTorch 설정
    print("\n[1.4] PyTorch 설정...")
    try:
        import torch
        num_threads = int(os.environ.get("TORCH_NUM_THREADS", "12"))
        torch.set_num_threads(num_threads)
        os.environ["OMP_NUM_THREADS"] = str(num_threads)
        os.environ["MKL_NUM_THREADS"] = str(num_threads)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            print(f"  ? GPU: {gpu_name} ({num_threads} CPU 스레드)")
        else:
            print(f"  ? CPU 모드 ({num_threads} 스레드)")
    except ImportError:
        print("  ? PyTorch가 설치되지 않았습니다. Neural Network 기능이 비활성화됩니다.")

    # 1.5 이벤트 루프 설정
    print("\n[1.5] 이벤트 루프 설정...")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if sys.platform == "win32":
        try:
            # WindowsSelectorEventLoopPolicy is deprecated in Python 3.12+
            # Using default event loop policy
            pass
        except:
            pass
    print("  ? 이벤트 루프 설정 완료")

    print("\n" + "=" * 70)
    print("시스템 초기화 완료!")
    print("=" * 70 + "\n")

    return project_dir


def setup_sc2_path() -> Optional[str]:
    """SC2 경로 설정"""
    if "SC2PATH" in os.environ:
        sc2_path = os.environ["SC2PATH"]
        if os.path.exists(sc2_path):
            return sc2_path

    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SOFTWARE\Blizzard Entertainment\StarCraft II")
            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            if os.path.exists(install_path):
                os.environ["SC2PATH"] = install_path
                return install_path
        except:
            pass

    common_paths = [
        "C:\\Program Files (x86)\\StarCraft II",
        "C:\\Program Files\\StarCraft II",
        "D:\\StarCraft II",
    ]
    for path in common_paths:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            return path

    return None

# ============================================================================
# 2. 봇 초기화 (Bot Initialization)
# ============================================================================

def initialize_bot(project_dir: Path) -> Optional[Any]:
    """봇 초기화"""
    print("=" * 70)
    print("2. 봇 초기화 (Bot Initialization)")
    print("=" * 70)

    print("\n[2.1] 봇 클래스 임포트...")
    try:
        # Ensure project directory is in sys.path for import resolution
        if str(project_dir) not in sys.path:
            sys.path.insert(0, str(project_dir))
        from wicked_zerg_bot_pro import WickedZergBotPro  # type: ignore
        print("  ? WickedZergBotPro 클래스 로드 완료")
    except ImportError as e:
        print(f"  ? 봇 클래스 임포트 실패: {e}")
        return None

    print("\n[2.2] 봇 인스턴스 생성...")
    try:
        bot_instance = WickedZergBotPro(  # type: ignore
            train_mode=True,
            instance_id=0,
            personality="serral",
            opponent_race=None,
            game_count=0
        )
        print("  ? 봇 인스턴스 생성 완료")
        print(f"     - Personality: {getattr(bot_instance, 'personality', 'unknown')}")
        print(f"     - Instance ID: {getattr(bot_instance, 'instance_id', 0)}")
        print(f"     - Train Mode: {getattr(bot_instance, 'train_mode', False)}")
    except Exception as e:
        print(f"  ? 봇 인스턴스 생성 실패: {e}")
        return None

    print("\n[2.3] 매니저 초기화 확인...")
    managers = [
        ("Intel Manager", "intel"),
        ("Economy Manager", "economy"),
        ("Production Manager", "production"),
        ("Combat Manager", "combat"),
        ("Scouting System", "scout"),
        ("Micro Controller", "micro"),
        ("Queen Manager", "queen_manager"),
 ]

    for name, attr in managers:
        manager = getattr(bot_instance, attr, None)
        if manager is None:
            print(f"  ? {name}: 나중에 초기화됨 (on_start에서)")
        else:
            print(f"  ? {name}: 초기화됨")

    print("\n[2.4] Telemetry Logger 확인...")
    if hasattr(bot_instance, 'telemetry_logger'):
        print("  ? Telemetry Logger: 초기화됨")
    else:
        print("  ? Telemetry Logger: 초기화되지 않음")

    print("\n" + "=" * 70)
    print("봇 초기화 완료!")
    print("=" * 70 + "\n")

    return bot_instance

# ============================================================================
# 3. 게임 실행 (Game Execution)
# ============================================================================

def run_game(bot_instance: Any) -> bool:
    """게임 실행"""
    print("=" * 70)
    print("3. 게임 실행 (Game Execution)")
    print("=" * 70)

    print("\n[3.1] SC2 라이브러리 임포트...")
    try:
        from sc2.main import run_game as sc2_run_game  # type: ignore
        from sc2.player import Bot, Computer  # type: ignore
        from sc2.data import Race, Difficulty  # type: ignore
        from sc2 import maps  # type: ignore
        print("  ? SC2 라이브러리 로드 완료")
    except ImportError as e:
        print(f"  ? SC2 라이브러리 임포트 실패: {e}")
        print("     sc2 패키지를 설치하세요: pip install sc2")
        return False

    print("\n[3.2] 게임 설정...")
    map_name = "AbyssalReefLE"
    bot = Bot(Race.Zerg, bot_instance)  # type: ignore
    opponent = Computer(Race.Terran, Difficulty.VeryHard)  # type: ignore
    print(f"  ? 맵: {map_name}")
    print(f"  ? 상대: Terran (VeryHard)")

    print("\n[3.3] 게임 시작...")
    print("  → 게임이 시작됩니다. 종료하려면 Ctrl+C를 누르세요.")
    print("  → 게임 진행 중에는 on_step()이 매 프레임마다 실행됩니다.")
    print("  → 게임 종료 시 on_end()가 실행됩니다.")
    print()

    try:
        sc2_run_game(  # type: ignore
            maps.get(map_name),  # type: ignore
            [bot, opponent],
            realtime=False
        )
        print("\n  ? 게임 완료!")
        return True
    except KeyboardInterrupt:
        print("\n  ? 사용자에 의해 중단됨")
        return False
    except Exception as e:
        print(f"\n  ? 게임 실행 오류: {e}")
        return False

# ============================================================================
# 4. 대시보드 서버 (Dashboard Server) - 선택적
# ============================================================================

def start_dashboard_server(background: bool = False) -> Optional[Any]:
    """대시보드 서버 시작"""
    print("=" * 70)
    print("4. 대시보드 서버 시작 (Dashboard Server)")
    print("=" * 70)

    print("\n[4.1] 대시보드 서버 확인...")
    dashboard_api_path = Path("monitoring/dashboard_api.py")
    if not dashboard_api_path.exists():
        print("  ? dashboard_api.py를 찾을 수 없습니다.")
        return None

    print("\n[4.2] FastAPI 서버 시작...")
    if background:
        print("  → 백그라운드에서 실행됩니다.")
        import subprocess
        import sys
        process = subprocess.Popen(
            [sys.executable, str(dashboard_api_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"  ? 서버 프로세스 시작됨 (PID: {process.pid})")
        print(f"     → http://localhost:8000 에서 접속 가능")
        return process
    else:
        print("  → 서버를 시작하려면 별도 터미널에서 다음 명령을 실행하세요:")
        print(f"     python {dashboard_api_path}")
        return None

# ============================================================================
# 5. 메인 실행 함수
# ============================================================================

def main():
    """메인 실행 함수"""
    print("\n" + "=" * 70)
    print("완전한 실행 스크립트 - 전체 시스템 실행")
    print("Complete Execution Script - Full System Run")
    print("=" * 70 + "\n")

    # 1. 시스템 초기화
    project_dir = initialize_system()

    # 2. 봇 초기화
    bot_instance = initialize_bot(project_dir)
    if bot_instance is None:
        print("봇 초기화 실패. 종료합니다.")
        return 1

    # 3. 대시보드 서버 시작 (선택적)
    dashboard_process = None
    start_dashboard = input("\n대시보드 서버를 시작하시겠습니까? (y/n): ").lower().strip()
    if start_dashboard == 'y':
        dashboard_process = start_dashboard_server(background=True)

    # 4. 게임 실행
    try:
        success = run_game(bot_instance)
        if success:
            print("\n" + "=" * 70)
            print("전체 실행 완료!")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("게임 실행 중 오류 발생")
            print("=" * 70)
    finally:
        # 5. 정리
        if dashboard_process:
            print("\n[5] 대시보드 서버 종료...")
            dashboard_process.terminate()
            dashboard_process.wait()
            print("  ? 대시보드 서버 종료됨")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
