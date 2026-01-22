"""
Patch Validator - syntax validation and regression checks.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class PatchValidationResult:
    ok: bool
    syntax_ok: bool
    tests_ok: bool
    errors: List[str] = field(default_factory=list)
    test_output: str = ""


class PatchValidator:
    """Validates generated patches before applying them."""

    def __init__(
        self,
        repo_root: Optional[str] = None,
        test_command: Optional[List[str]] = None,
        timeout_sec: int = 180,
    ) -> None:
        self.name = "patch_validator"
        self.repo_root = Path(repo_root) if repo_root else self._find_repo_root()
        self.test_command = test_command
        self.timeout_sec = timeout_sec

    def validate_patch(
        self, proposed_changes: Dict[str, str], run_tests: bool = True
    ) -> PatchValidationResult:
        errors: List[str] = []

        syntax_ok = True
        for path_str, content in proposed_changes.items():
            if not path_str.endswith(".py"):
                continue
            file_path = self.repo_root / path_str
            ok, err = self._validate_python_syntax(content, file_path)
            if not ok:
                syntax_ok = False
                errors.append(err)

        tests_ok = True
        test_output = ""
        if run_tests and syntax_ok:
            tests_ok, test_output = self._run_regression_tests()
            if not tests_ok:
                errors.append("Regression tests failed")

        ok = syntax_ok and tests_ok
        return PatchValidationResult(
            ok=ok,
            syntax_ok=syntax_ok,
            tests_ok=tests_ok,
            errors=errors,
            test_output=test_output,
        )

    @staticmethod
    def _validate_python_syntax(content: str, file_path: Path) -> Tuple[bool, str]:
        try:
            ast.parse(content, filename=str(file_path))
        except SyntaxError as exc:
            return False, f"{file_path}: {exc.msg} (line {exc.lineno})"
        return True, ""

    def _run_regression_tests(self) -> Tuple[bool, str]:
        command = self._resolve_test_command()
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, str(exc)

        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()

    def _resolve_test_command(self) -> List[str]:
        if self.test_command:
            return self.test_command

        tests_dir = self.repo_root / "tests"
        pytest_available = importlib.util.find_spec("pytest") is not None
        if pytest_available and tests_dir.exists():
            return [sys.executable, "-m", "pytest", "-q"]

        if tests_dir.exists():
            return [sys.executable, "-m", "unittest", "discover", "-s", "tests"]

        return [sys.executable, "-m", "compileall", "-q", "."]

    def _find_repo_root(self) -> Path:
        current = Path(__file__).resolve()
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists():
                return parent
        return Path.cwd()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(repo_root='{self.repo_root}')"
