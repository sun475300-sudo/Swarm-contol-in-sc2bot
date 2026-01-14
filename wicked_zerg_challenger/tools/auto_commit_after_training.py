#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Commit After Training - 자동 커밋 스크립트

훈련 종료 후 자동으로 변경사항을 커밋하고 GitHub에 푸시합니다.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_command(cmd: list, cwd: Path = None) -> tuple:
    """명령어 실행"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def check_git_repo() -> bool:
    """Git 저장소인지 확인"""
    success, _ = run_command(["git", "rev-parse", "--git-dir"])
    return success


def check_remote() -> bool:
    """원격 저장소 설정 확인"""
    success, output = run_command(["git", "remote", "-v"])
    if not success:
        return False

    # 원하는 원격 저장소 URL 확인 (부분 매칭으로 유연하게)
    target_urls = [
        "github.com/sun475300-sudo/Swarm-Control-in-sc2bot",
        "Swarm-Control-in-sc2bot.git"
    ]
    return any(url in output for url in target_urls)


def setup_remote() -> bool:
    """원격 저장소 설정"""
    print("[INFO] Setting up remote repository...")

    # 기존 origin 제거 (있다면)
    run_command(["git", "remote", "remove", "origin"])

    # 새로운 origin 추가
    success, output = run_command([
        "git", "remote", "add", "origin",
        "https://github.com/sun475300-sudo/Swarm-Control-in-sc2bot.git"
    ])

    if success:
        print(f"[OK] Remote repository configured: origin")
        return True
    else:
        print(f"[ERROR] Failed to setup remote: {output}")
        return False


def get_changed_files() -> list[str]:
    """변경된 파일 목록 가져오기"""
    success, output = run_command(["git", "status", "--porcelain"])
    if not success:
        return []

    files = []
    for line in output.strip().split('\n'):
        if line.strip():
            # 상태 코드 제거 (예: " M", "A ", "??")
            file_path = line[3:].strip()
            if file_path:
                files.append(file_path)

    return files


def create_commit_message() -> str:
    """커밋 메시지 생성"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 변경된 파일 목록
    changed_files = get_changed_files()

    # 주요 변경사항 분류
    model_files = [f for f in changed_files if 'models/' in f or '.pt' in f]
    code_files = [f for f in changed_files if f.endswith('.py')]
    config_files = [f for f in changed_files if f.endswith('.json') or f.endswith('.md')]

    message = f"""Training completed - Auto commit

Timestamp: {timestamp}

Changes:
- Model files: {len(model_files)}
- Code files: {len(code_files)}
- Config/Doc files: {len(config_files)}
- Total files: {len(changed_files)}

Training session completed successfully.
"""

    return message


def commit_and_push() -> bool:
    """변경사항 커밋 및 푸시"""
    print("\n" + "="*70)
    print("AUTO COMMIT AFTER TRAINING")
    print("="*70)

    # Git 저장소 확인
    if not check_git_repo():
        print("[ERROR] Not a git repository!")
        return False

    # 원격 저장소 확인 및 설정
    if not check_remote():
        print("[WARNING] Remote repository not configured. Setting up...")
        if not setup_remote():
            return False

    # 변경된 파일 확인
    changed_files = get_changed_files()
    if not changed_files:
        print("[INFO] No changes to commit.")
        return True

    print(f"\n[INFO] Found {len(changed_files)} changed files:")
    for f in changed_files[:10]:  # 처음 10개만 표시
        print(f"  - {f}")
    if len(changed_files) > 10:
        print(f"  ... and {len(changed_files) - 10} more files")

    # 모든 변경사항 스테이징
    print("\n[STEP 1] Staging all changes...")
    success, output = run_command(["git", "add", "-A"])
    if not success:
        print(f"[ERROR] Failed to stage changes: {output}")
        return False
    print("[OK] All changes staged")

    # 커밋 메시지 생성
    commit_message = create_commit_message()

    # 커밋
    print("\n[STEP 2] Creating commit...")
    success, output = run_command([
        "git", "commit", "-m", commit_message
    ])
    if not success:
        if "nothing to commit" in output.lower():
            print("[INFO] Nothing to commit (working tree clean)")
            return True
        print(f"[ERROR] Failed to commit: {output}")
        return False
    print("[OK] Commit created")

    # 현재 브랜치 확인
    success, branch_output = run_command(["git", "branch", "--show-current"])
    branch = branch_output.strip() if success else "main"

    # 푸시
    print(f"\n[STEP 3] Pushing to origin/{branch}...")
    success, output = run_command([
        "git", "push", "-u", "origin", branch
    ])
    if not success:
        print(f"[ERROR] Failed to push: {output}")
        print("[INFO] You may need to push manually:")
        print(f"  git push -u origin {branch}")
        return False
    print("[OK] Pushed to remote repository")

    print("\n" + "="*70)
    print("AUTO COMMIT COMPLETE")
    print("="*70)
    print(f"Repository: https://github.com/sun475300-sudo/Swarm-Control-in-sc2bot.git")
    print(f"Branch: {branch}")
    print("="*70 + "\n")

    return True


def main():
    """메인 함수"""
    try:
        success = commit_and_push()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
