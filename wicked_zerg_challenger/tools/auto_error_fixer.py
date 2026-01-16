# -*- coding: utf-8 -*-
"""
자동 에러 수정 도구

일반적인 에러 패턴을 자동으로 감지하고 수정
"""

import os
import re
import time
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional

PROJECT_ROOT = Path(__file__).parent.parent


class AutoErrorFixer:
    """자동 에러 수정기"""

    def __init__(self):
        self.fixes_applied: List[Dict[str, Any]] = []

    def fix_common_errors(self, file_path: Path) -> Tuple[bool, List[str]]:
        """일반적인 에러 수정"""
        fixes: List[str] = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                lines = content.splitlines()

            original_content = content
            modified = False
            # lines 변수는 사용하지 않지만 향후 확장성을 위해 유지
            _ = lines  # noqa: F841

            # 1. loguru_logger 미정의 에러 수정
            if 'loguru_logger' in content and 'from loguru import logger' not in content:
                # loguru_logger를 logger로 변경
                content = re.sub(r'\bloguru_logger\.', 'logger.', content)
                content = re.sub(r'\bloguru_logger\s*=', 'logger =', content)
                if content != original_content:
                    fixes.append("loguru_logger -> logger 변경")
                    modified = True

            # 2. vespene -> vespene 변경
            if 'vespene' in content:
                content = content.replace('vespene', 'vespene')
                if content != original_content:
                    fixes.append("vespene -> vespene 변경")
                    modified = True

            # 3. await bool 에러 수정 (간단한 패턴)
            # await unit.train() -> await self._safe_train(unit, ...)
            if 'await' in content and '.train(' in content:
                # 이미 _safe_train을 사용하는지 확인
                if '_safe_train' not in content:
                    # 이건 수동 수정이 필요하므로 경고만
                    pass

            # 4. None 체크 추가 (간단한 패턴)
            # self.manager.method() -> if self.manager: self.manager.method()
            if 'self.' in content and '.method()' in content:
                # 이미 체크가 있는지 확인
                pass

            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True, fixes

            return False, []

        except Exception as e:
            return False, [f"Error: {str(e)}"]

    def scan_and_fix(self, target_files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """스캔 및 수정"""
        if target_files is None:
            # 모든 Python 파일 찾기
            target_files = []
            for root, dirs, files in os.walk(PROJECT_ROOT):
                dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv'}]
                for file in files:
                    if file.endswith('.py'):
                        target_files.append(Path(root) / file)

        results = {
            "scanned": len(target_files),
            "fixed": 0,
            "fixes": []
        }

        for file_path in target_files:
            success, fixes = self.fix_common_errors(file_path)
            if success and fixes:
                if isinstance(results["fixed"], int):
                    results["fixed"] += 1
                if isinstance(results["fixes"], list):
                    results["fixes"].append({
                        "file": str(file_path.relative_to(PROJECT_ROOT)),
                        "fixes": fixes
                    })
                self.fixes_applied.append({
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "fixes": fixes,
                    "timestamp": time.time()
                })

        return results


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="자동 에러 수정 도구")
    parser.add_argument("--file", help="특정 파일만 수정")
    parser.add_argument("--all", action="store_true", help="모든 파일 수정")

    args = parser.parse_args()

    print("=" * 70)
    print("자동 에러 수정 도구")
    print("=" * 70)
    print()

    fixer = AutoErrorFixer()

    if args.file:
        file_path = PROJECT_ROOT / args.file
        if file_path.exists():
            success, fixes = fixer.fix_common_errors(file_path)
            if success:
                print(f"[FIXED] {args.file}")
                for fix in fixes:
                    print(f"  - {fix}")
            else:
                print(f"[NO FIXES] {args.file}")
        else:
            print(f"[ERROR] File not found: {args.file}")
    elif args.all:
        print("모든 파일 스캔 및 수정 중...")
        results = fixer.scan_and_fix()
        print(f"\n스캔 완료: {results['scanned']}개 파일")
        print(f"수정 완료: {results['fixed']}개 파일")
        if results["fixes"]:
            print("\n수정된 파일:")
            for fix_info in results["fixes"][:10]:  # 상위 10개만
                print(f"  - {fix_info['file']}")
                for fix in fix_info["fixes"]:
                    print(f"    - {fix}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
