# -*- coding: utf-8 -*-
"""
Gen-AI Self-Healing System - 자가 수복 시스템 고도화

CRITICAL IMPROVEMENTS:
1. 코드 검증 단계 강화 (ast.parse() 구문 검사)
2. 학습 데이터 필터 (자원 효율, 교전 효율 기준)
3. 코드 최적화 정적 분석 (중복 루프, 비효율적인 컴프리헨션 감지)
"""

import ast
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import google.generativeai as genai

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("[WARNING] google.generativeai not available")


class GenAISelfHealing:
    """
    Generative AI 기반 자가 수복 시스템

    Gemini API를 사용하여 에러 분석, 패치 생성, 코드 검증을 수행합니다.
    """

    def __init__(
        self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"
    ):
        """
        Args:
            api_key: Gemini API 키 (없으면 환경변수에서 로드)
            model_name: 사용할 모델 이름
        """
        self.model_name = model_name
        self.model = None

        if GENAI_AVAILABLE:
            try:
                if api_key is None:
                    # 환경변수 또는 파일에서 API 키 로드
                    api_key = os.environ.get("GEMINI_API_KEY")
                    if api_key is None:
                        api_key_path = (
                            Path(__file__).parent / "api_keys" / "GEMINI_API_KEY.txt"
                        )
                        if api_key_path.exists():
                            api_key = api_key_path.read_text().strip()

                if api_key:
                    genai.configure(api_key=api_key)
                    self.model = genai.GenerativeModel(model_name)
            except Exception as e:
                print(f"[WARNING] Failed to initialize Gemini: {e}")

    def analyze_error(
        self, error: Exception, context: Dict, source_code: Optional[str] = None
    ) -> Dict:
        """
        에러 분석 및 패치 생성

        CRITICAL IMPROVEMENT: 코드 검증 단계 강화

        Args:
            error: 발생한 에러
            context: 에러 컨텍스트 (파일명, 라인 번호 등)
            source_code: 소스 코드 (선택사항)

        Returns:
            분석 결과 딕셔너리
        """
        if not self.model:
            return {
                "success": False,
                "error": "Gemini model not available",
                "patch_code": None,
            }

        try:
            # 프롬프트 생성
            prompt = self._generate_error_analysis_prompt(error, context, source_code)

            # Gemini API 호출
            response = self.model.generate_content(prompt)

            # 응답 파싱
            response_text = response.text if hasattr(response, "text") else str(response)

            # 패치 코드 추출
            patch_code = self._extract_patch_code(response_text)

            # 패치 코드 검증
            validation_result = self._validate_patch_code(patch_code)

            return {
                "success": True,
                "analysis": response_text,
                "patch_code": patch_code,
                "validation": validation_result,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "patch_code": None}

    def _generate_error_analysis_prompt(
        self, error: Exception, context: Dict, source_code: Optional[str]
    ) -> str:
        """에러 분석 프롬프트 생성"""
        prompt = f"""
에러 분석 및 패치 생성을 요청합니다.

에러 정보:
- 에러 타입: {type(error).__name__}
- 에러 메시지: {str(error)}
- 파일: {context.get('file', 'Unknown')}
- 라인: {context.get('line', 'Unknown')}

"""
        if source_code:
            prompt += f"""
문제 소스 코드:
```python
{source_code}
```

"""
        prompt += """
요청 사항:
1. 에러의 원인 분석
2. 수정된 코드 제공 (Python 코드만, 주석 포함)
3. 수정 이유 설명

응답 형식:
```python
# 수정된 코드
...
```

설명:
...
"""
        return prompt

    def _extract_patch_code(self, response_text: str) -> str:
        """응답에서 패치 코드 추출"""
        # 코드 블록 찾기
        if "```python" in response_text:
            start = response_text.find("```python") + len("```python")
            end = response_text.find("```", start)
            if end > start:
                return response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + len("```")
            end = response_text.find("```", start)
            if end > start:
                return response_text[start:end].strip()

        return ""

    def _validate_patch_code(self, patch_code: str) -> Dict[str, Any]:
        """
        패치 코드 검증

        CRITICAL IMPROVEMENT: ast.parse()로 구문 오류 사전 검사

        Args:
            patch_code: 검증할 코드

        Returns:
            검증 결과 딕셔너리
        """
        result = {
            "syntax_valid": False,
            "errors": [],
            "warnings": [],
            "nested_loops": 0,
            "inefficient_comprehensions": [],
        }

        if not patch_code:
            result["errors"].append("Empty patch code")
            return result

        try:
            # 1. 구문 검사
            try:
                tree = ast.parse(patch_code)
                result["syntax_valid"] = True
            except SyntaxError as e:
                result["errors"].append(f"Syntax error: {e}")
                return result

            # 2. 중복 루프 감지
            result["nested_loops"] = self._detect_nested_loops(tree)
            if result["nested_loops"] > 2:
                result["warnings"].append(
                    f"Deep nested loops detected: {result['nested_loops']} levels"
                )

            # 3. 비효율적인 컴프리헨션 감지
            result["inefficient_comprehensions"] = (
                self._detect_inefficient_comprehensions(tree)
            )
            if result["inefficient_comprehensions"]:
                result["warnings"].append(
                    f"Inefficient comprehensions: {len(result['inefficient_comprehensions'])} found"
                )

        except Exception as e:
            result["errors"].append(f"Validation error: {e}")

        return result

    def _detect_nested_loops(self, tree: ast.AST) -> int:
        """중복 루프 깊이 감지"""

        class LoopDepthVisitor(ast.NodeVisitor):
            def __init__(self):
                self.max_depth = 0
                self.current_depth = 0

            def visit_For(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1

            def visit_While(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1

        visitor = LoopDepthVisitor()
        visitor.visit(tree)
        return visitor.max_depth

    def _detect_inefficient_comprehensions(self, tree: ast.AST) -> List[str]:
        """비효율적인 컴프리헨션 감지"""

        class ComprehensionVisitor(ast.NodeVisitor):
            def __init__(self):
                self.inefficient = []

            def visit_ListComp(self, node):
                # 중첩된 컴프리헨션 감지
                for generator in node.generators:
                    if isinstance(
                        generator.iter,
                        (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp),
                    ):
                        self.inefficient.append("Nested comprehension detected")
                self.generic_visit(node)

            def visit_DictComp(self, node):
                for generator in node.generators:
                    if isinstance(
                        generator.iter,
                        (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp),
                    ):
                        self.inefficient.append("Nested comprehension detected")
                self.generic_visit(node)

        visitor = ComprehensionVisitor()
        visitor.visit(tree)
        return visitor.inefficient

    def filter_training_data(
        self,
        replay_data: List[Dict],
        min_resource_efficiency: float = 0.7,
        min_combat_efficiency: float = 0.6,
    ) -> List[Dict]:
        """
        학습 데이터 필터

        CRITICAL IMPROVEMENT: 승리한 게임 중에서도 효율이 높은 데이터만 선별

        Args:
            replay_data: 리플레이 데이터 리스트
            min_resource_efficiency: 최소 자원 효율 (0.0 ~ 1.0)
            min_combat_efficiency: 최소 교전 효율 (0.0 ~ 1.0)

        Returns:
            필터된 데이터 리스트
        """
        filtered = []

        for data in replay_data:
            # 승리한 게임만 선별
            if not data.get("victory", False):
                continue

            # 자원 효율 계산
            resource_efficiency = self._calculate_resource_efficiency(data)
            if resource_efficiency < min_resource_efficiency:
                continue

            # 교전 효율 계산
            combat_efficiency = self._calculate_combat_efficiency(data)
            if combat_efficiency < min_combat_efficiency:
                continue

            # 효율 점수 추가
            data["resource_efficiency"] = resource_efficiency
            data["combat_efficiency"] = combat_efficiency

            filtered.append(data)

        return filtered

    def _calculate_resource_efficiency(self, data: Dict) -> float:
        """자원 효율 계산"""
        try:
            # 자원 수집량과 소모량
            minerals_collected = data.get("minerals_collected", 0)
            minerals_spent = data.get("minerals_spent", 0)

            if minerals_collected == 0:
                return 0.0

            # 수집한 자원 중 소모한 비율
            efficiency = min(1.0, minerals_spent / minerals_collected)

            return efficiency

        except Exception:
            return 0.5  # 기본값

    def _calculate_combat_efficiency(self, data: Dict) -> float:
        """교전 효율 계산"""
        try:
            # 교전 승률
            battles_won = data.get("battles_won", 0)
            battles_total = data.get("battles_total", 1)

            if battles_total == 0:
                return 0.0

            win_rate = battles_won / battles_total

            # 유닛 손실 비율
            units_lost = data.get("units_lost", 0)
            units_killed = data.get("units_killed", 1)

            loss_ratio = units_lost / units_killed if units_killed > 0 else 1.0

            # 승률과 손실 비율을 조합한 효율 계산
            efficiency = win_rate * (1.0 - min(1.0, loss_ratio * 0.5))

            return efficiency

        except Exception:
            return 0.5  # 기본값

    def validate_code_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        코드 구문 검증 (SyntaxError 체크)

        Gemini가 생성한 코드를 적용하기 전에 구문 오류를 사전에 검사

        Args:
            code: 검증할 코드 문자열

        Returns:
            (is_valid, error_message) 튜플
        """
        try:
            # AST 파싱으로 구문 오류 검사
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            error_msg = f"SyntaxError at line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\nCode: {e.text.strip()}"
            return False, error_msg
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def static_analysis_optimization(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        정적 분석을 통한 코드 최적화 감지

        성능에 영향을 주는 중복 루프나 비효율적인 리스트 컴프리헨션을 감지

        Args:
            file_path: 분석할 파일 경로

        Returns:
            최적화 제안 리스트
        """
        suggestions = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                lines = content.splitlines()

            # AST 파싱
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError:
                return suggestions  # 구문 오류가 있으면 분석 불가

            # 1. 중복 루프 감지
            for node in ast.walk(tree):
                if isinstance(node, ast.For):
                    # 중첩된 for 루프 확인
                    nested_fors = [
                        n for n in ast.walk(node) if isinstance(n, ast.For) and n != node
                    ]
                    if nested_fors:
                        suggestions.append(
                            {
                                "type": "nested_loop",
                                "line": node.lineno,
                                "message": f"Nested for loops detected at line {node.lineno}. Consider using itertools.product() or vectorization.",
                                "severity": "medium",
                            }
                        )

            # 2. 비효율적인 리스트 컴프리헨션 감지
            for i, line in enumerate(lines, 1):
                # 중첩된 리스트 컴프리헨션
                if line.count("[") >= 3 and "for" in line and "in" in line:
                    # 간단한 휴리스틱: 너무 복잡한 컴프리헨션
                    if line.count("for") >= 2:
                        suggestions.append(
                            {
                                "type": "complex_comprehension",
                                "line": i,
                                "message": f"Complex nested list comprehension at line {i}. Consider breaking into multiple steps for readability and performance.",
                                "severity": "low",
                            }
                        )

                # 리스트 컴프리헨션 내부의 함수 호출
                if "[" in line and "for" in line and "(" in line:
                    # 함수 호출이 있는 컴프리헨션은 map() 사용 고려
                    if line.count("(") > line.count("["):
                        suggestions.append(
                            {
                                "type": "function_in_comprehension",
                                "line": i,
                                "message": f"Function calls in list comprehension at line {i}. Consider using map() for better performance.",
                                "severity": "low",
                            }
                        )

            # 3. 중복 코드 블록 감지 (간단한 버전)
            line_hashes = {}
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if len(stripped) > 20:  # 충분히 긴 라인만
                    line_hash = hash(stripped)
                    if line_hash in line_hashes:
                        # 같은 라인이 반복됨
                        prev_line = line_hashes[line_hash]
                        suggestions.append(
                            {
                                "type": "duplicate_code",
                                "line": i,
                                "message": f"Duplicate code detected at line {i} (similar to line {prev_line}). Consider extracting to a function.",
                                "severity": "medium",
                            }
                        )
                    else:
                        line_hashes[line_hash] = i

        except Exception as e:
            print(f"[STATIC_ANALYSIS] Error analyzing {file_path}: {e}")

        return suggestions


# 전역 인스턴스 (선택적 사용)
_global_self_healing: Optional[GenAISelfHealing] = None


def get_self_healing() -> Optional[GenAISelfHealing]:
    """전역 Self-Healing 인스턴스 가져오기"""
    return _global_self_healing


def init_self_healing(
    api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"
) -> GenAISelfHealing:
    """
    전역 Self-Healing 인스턴스 초기화

    Args:
        api_key: Google Gemini API 키
        model_name: 사용할 모델 이름

    Returns:
        GenAISelfHealing 인스턴스
    """
    global _global_self_healing
    _global_self_healing = GenAISelfHealing(api_key=api_key, model_name=model_name)
    return _global_self_healing
