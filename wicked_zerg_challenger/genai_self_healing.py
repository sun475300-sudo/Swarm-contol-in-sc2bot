#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

Gen-AI Self-Healing System

Google Vertex AI (Gemini)¸¦ È°¿ëÇÑ ÀÚµ¿ ¿¡·¯ ºÐ¼® ¹× ÆÐÄ¡ Á¦¾È ½Ã½ºÅÛ



±â´É:

1. ·±Å¸ÀÓ ¿¡·¯ ¹ß»ý ½Ã Traceback ¹× ¼Ò½º ÄÚµå¸¦ Gemini·Î Àü¼Û

2. Gemini°¡ ¿øÀÎ ºÐ¼® ¹× ¼öÁ¤ ÆÐÄ¡ Á¦¾È

3. ÆÐÄ¡ Á¦¾ÈÀ» ·Î±× ÆÄÀÏ¿¡ ÀúÀå (ÀÚµ¿ Àû¿ëÀº ¼±ÅÃÀû)



ÁÖÀÇ»çÇ×:

- ÀÚµ¿ ÆÐÄ¡ Àû¿ëÀº À§ÇèÇÒ ¼ö ÀÖÀ¸¹Ç·Î ±âº»ÀûÀ¸·Î ºñÈ°¼ºÈ­

- ÆÐÄ¡ Á¦¾ÈÀ» ·Î±×·Î ÀúÀåÇÏ¿© °³¹ßÀÚ°¡ °ËÅä ÈÄ Àû¿ëÇÏµµ·Ï ±ÇÀå

"""



import os

import traceback

import json

from pathlib import Path

from typing import Dict, Optional, Any, List

from datetime import datetime

from dataclasses import dataclass, asdict



try:

    import google.generativeai as genai

    GEMINI_AVAILABLE = True

except ImportError:

    GEMINI_AVAILABLE = False



try:

    from loguru import logger

except ImportError:

    import logging

    logger = logging.getLogger(__name__)

    logger.setLevel(logging.INFO)





@dataclass

class ErrorContext:

    """¿¡·¯ ¹ß»ý ÄÁÅØ½ºÆ® Á¤º¸"""

    error_type: str

    error_message: str

    traceback: str

    file_path: Optional[str] = None

    line_number: Optional[int] = None

    function_name: Optional[str] = None

    iteration: Optional[int] = None

    game_time: Optional[float] = None

    instance_id: Optional[int] = None





@dataclass

class PatchSuggestion:

    """Gemini°¡ Á¦¾ÈÇÑ ÆÐÄ¡ Á¤º¸"""

    description: str

    file_path: str

    old_code: str

    new_code: str

    confidence: float  # 0.0 ~ 1.0

    reasoning: str





class GenAISelfHealing:

    """

    Gen-AI Self-Healing ½Ã½ºÅÛ

    

    Google Gemini API¸¦ »ç¿ëÇÏ¿© ¿¡·¯¸¦ ºÐ¼®ÇÏ°í ÆÐÄ¡¸¦ Á¦¾ÈÇÕ´Ï´Ù.

    """

    

    def __init__(

        self,

        api_key: Optional[str] = None,

        model_name: str = "gemini-1.5-flash",

        enable_auto_patch: bool = False,

        log_dir: Optional[Path] = None

    ):

        """

        Args:

            api_key: Google Gemini API Å° (È¯°æ º¯¼ö GOOGLE_API_KEY¿¡¼­µµ ÀÐÀ½)

            model_name: »ç¿ëÇÒ Gemini ¸ðµ¨ ÀÌ¸§

            enable_auto_patch: ÀÚµ¿ ÆÐÄ¡ Àû¿ë ¿©ºÎ (±âº»°ª: False, ±ÇÀåÇÏÁö ¾ÊÀ½)

            log_dir: ÆÐÄ¡ ·Î±× ÀúÀå µð·ºÅä¸®

        """

        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

        self.model_name = model_name

        self.enable_auto_patch = enable_auto_patch

        self.log_dir = log_dir or Path("data/self_healing")

        self.log_dir.mkdir(parents=True, exist_ok=True)

        

        # Gemini API ÃÊ±âÈ­

        self.client = None

        if GEMINI_AVAILABLE and self.api_key:

            try:

                genai.configure(api_key=self.api_key)

                self.client = genai.GenerativeModel(model_name)

                logger.info(f"[SELF-HEALING] Gemini API initialized (model: {model_name})")

            except Exception as e:

                logger.warning(f"[SELF-HEALING] Failed to initialize Gemini API: {e}")

                self.client = None

        else:

            if not GEMINI_AVAILABLE:

                logger.warning("[SELF-HEALING] google-generativeai package not installed")

            if not self.api_key:

                logger.warning("[SELF-HEALING] GOOGLE_API_KEY or GEMINI_API_KEY not set")

    

    def is_available(self) -> bool:

        """Gemini API°¡ »ç¿ë °¡´ÉÇÑÁö È®ÀÎ"""

        return self.client is not None

    

    def analyze_error(

        self,

        error: Exception,

        context: Optional[Dict[str, Any]] = None,

        source_files: Optional[Dict[str, str]] = None

    ) -> Optional[PatchSuggestion]:

        """

        ¿¡·¯¸¦ ºÐ¼®ÇÏ°í ÆÐÄ¡¸¦ Á¦¾È

        

        Args:

            error: ¹ß»ýÇÑ ¿¹¿Ü °´Ã¼

            context: Ãß°¡ ÄÁÅØ½ºÆ® Á¤º¸ (iteration, game_time, instance_id µî)

            source_files: °ü·Ã ¼Ò½º ÆÄÀÏ ³»¿ë (ÆÄÀÏ °æ·Î -> ÆÄÀÏ ³»¿ë)

        

        Returns:

            PatchSuggestion °´Ã¼ (ºÐ¼® ½ÇÆÐ ½Ã None)

        """

        if not self.is_available():

            logger.warning("[SELF-HEALING] Gemini API not available, skipping error analysis")

            return None

        

        try:

            # ¿¡·¯ ÄÁÅØ½ºÆ® ¼öÁý

            error_context = self._collect_error_context(error, context)

            

            # ¼Ò½º ÆÄÀÏ ÀÐ±â (°ü·Ã ÆÄÀÏÀÌ ÀÖ´Â °æ¿ì)

            if source_files is None:

                source_files = self._extract_source_files(error_context)

            

            # Gemini¿¡ Àü¼ÛÇÒ ÇÁ·ÒÇÁÆ® »ý¼º

            prompt = self._build_analysis_prompt(error_context, source_files)

            

            # Gemini API È£Ãâ

            response = self.client.generate_content(prompt)

            

            # ÀÀ´ä ÆÄ½Ì

            patch_suggestion = self._parse_gemini_response(response.text, error_context)

            

            if patch_suggestion:

                # ÆÐÄ¡ Á¦¾È ·Î±× ÀúÀå

                self._save_patch_suggestion(error_context, patch_suggestion)

                logger.info(f"[SELF-HEALING] Patch suggestion generated: {patch_suggestion.description}")

            

            return patch_suggestion

            

        except Exception as e:

            logger.error(f"[SELF-HEALING] Error analysis failed: {e}")

            logger.debug(traceback.format_exc())

            return None
    
    def analyze_gap_feedback(
        self,
        gap_feedback: str,
        source_files: Optional[Dict[str, str]] = None
    ) -> Optional[PatchSuggestion]:
        """
        Build-Order Gap Analyzer 피드백 분석 및 패치 제안
        
        Args:
            gap_feedback: StrategyAudit에서 생성한 피드백 문자열
            source_files: 관련 소스 파일 내용 (선택사항)
        
        Returns:
            PatchSuggestion 객체 (분석 실패 시 None)
        """
        if not self.is_available():
            logger.warning("[SELF-HEALING] Gemini API not available, skipping gap analysis")
            return None
        
        try:
            # Gap Analysis 전용 프롬프트 생성
            prompt = self._build_gap_analysis_prompt(gap_feedback, source_files)
            
            # Gemini API 호출
            response = self.client.generate_content(prompt)
            
            # 응답 파싱
            patch_suggestion = self._parse_gemini_gap_response(response.text, gap_feedback)
            
            if patch_suggestion:
                # 패치 제안 로컬 저장
                error_context = ErrorContext(
                    error_type="BuildOrderGap",
                    error_message="Performance gap detected vs pro gamers",
                    traceback=gap_feedback,
                    file_path=None,
                    line_number=None,
                    function_name=None,
                    iteration=None,
                    game_time=None,
                    instance_id=None,
                )
                self._save_patch_suggestion(error_context, patch_suggestion)
                logger.info(f"[SELF-HEALING] Gap analysis patch suggestion generated: {patch_suggestion.description}")
            
            return patch_suggestion
            
        except Exception as e:
            logger.error(f"[SELF-HEALING] Gap analysis failed: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def _build_gap_analysis_prompt(
        self,
        gap_feedback: str,
        source_files: Optional[Dict[str, str]] = None
    ) -> str:
        """Gap Analysis 전용 프롬프트 생성"""
        prompt_parts = []
        
        prompt_parts.append("=== Build-Order Gap Analysis Request ===")
        prompt_parts.append("")
        prompt_parts.append("You are analyzing a StarCraft II Zerg bot's performance gap compared to professional gamers.")
        prompt_parts.append("The bot is losing games because it builds structures too late or in wrong order.")
        prompt_parts.append("")
        prompt_parts.append("Gap Analysis Feedback:")
        prompt_parts.append(gap_feedback)
        prompt_parts.append("")
        prompt_parts.append("Please analyze the feedback and suggest code patches to improve the bot's build order timing.")
        prompt_parts.append("Focus on:")
        prompt_parts.append("1. Optimizing economy_manager.py's drone production logic")
        prompt_parts.append("2. Improving production_manager.py's build order priority system")
        prompt_parts.append("3. Enhancing resource spending efficiency")
        prompt_parts.append("")
        
        if source_files:
            prompt_parts.append("=== Relevant Source Files ===")
            for file_path, content in source_files.items():
                prompt_parts.append(f"\n--- {file_path} ---")
                prompt_parts.append(content[:2000])  # 최대 2000자만
                prompt_parts.append("")
        
        prompt_parts.append("=== Response Format ===")
        prompt_parts.append("Please provide a JSON response with the following structure:")
        prompt_parts.append('{')
        prompt_parts.append('  "description": "Brief description of the issue and fix",')
        prompt_parts.append('  "file_path": "path/to/file.py",')
        prompt_parts.append('  "line_number": 123,')
        prompt_parts.append('  "old_code": "code to replace",')
        prompt_parts.append('  "new_code": "replacement code",')
        prompt_parts.append('  "explanation": "Why this fix improves build order timing"')
        prompt_parts.append('}')
        
        return "\n".join(prompt_parts)
    
    def _parse_gemini_gap_response(
        self,
        response_text: str,
        gap_feedback: str
    ) -> Optional[PatchSuggestion]:
        """Gemini의 Gap Analysis 응답 파싱"""
        try:
            # JSON 응답 추출 시도
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                import json
                data = json.loads(json_match.group())
                
                return PatchSuggestion(
                    description=data.get("description", "Build order timing optimization"),
                    file_path=data.get("file_path", ""),
                    line_number=data.get("line_number", 0),
                    old_code=data.get("old_code", ""),
                    new_code=data.get("new_code", ""),
                    explanation=data.get("explanation", ""),
                )
            
            # JSON이 없으면 텍스트에서 추출 시도
            # (간단한 파싱 로직)
            return PatchSuggestion(
                description="Build order timing optimization based on gap analysis",
                file_path="economy_manager.py",  # 기본값
                line_number=0,
                old_code="",
                new_code="",
                explanation=response_text[:500],  # 처음 500자만
            )
            
        except Exception as e:
            logger.error(f"[SELF-HEALING] Failed to parse gap analysis response: {e}")
            return None

    

    def _collect_error_context(

        self,

        error: Exception,

        context: Optional[Dict[str, Any]]

    ) -> ErrorContext:

        """¿¡·¯ ÄÁÅØ½ºÆ® ¼öÁý"""

        tb_str = traceback.format_exc()

        

        # Traceback¿¡¼­ ÆÄÀÏ °æ·Î¿Í ¶óÀÎ ¹øÈ£ ÃßÃâ

        file_path = None

        line_number = None

        function_name = None

        

        tb_lines = tb_str.split('\n')

        for i, line in enumerate(tb_lines):

            if 'File "' in line and '", line' in line:

                try:

                    parts = line.split('"')

                    if len(parts) >= 2:

                        file_path = parts[1]

                        if '", line' in line:

                            line_part = line.split('", line ')[1].split(',')[0]

                            line_number = int(line_part)

                except (ValueError, IndexError):

                    pass

            if 'def ' in line and function_name is None:

                try:

                    func_part = line.split('def ')[1].split('(')[0].strip()

                    if func_part:

                        function_name = func_part

                except (IndexError, AttributeError):

                    pass

        

        return ErrorContext(

            error_type=type(error).__name__,

            error_message=str(error),

            traceback=tb_str,

            file_path=file_path,

            line_number=line_number,

            function_name=function_name,

            iteration=context.get('iteration') if context else None,

            game_time=context.get('game_time') if context else None,

            instance_id=context.get('instance_id') if context else None,

        )

    

    def _extract_source_files(self, error_context: ErrorContext) -> Dict[str, str]:

        """¿¡·¯¿Í °ü·ÃµÈ ¼Ò½º ÆÄÀÏ ÀÐ±â"""

        source_files = {}

        

        if error_context.file_path and Path(error_context.file_path).exists():

            try:

                # ¿¡·¯°¡ ¹ß»ýÇÑ ÆÄÀÏ ÀÐ±â

                with open(error_context.file_path, 'r', encoding='utf-8') as f:

                    file_content = f.read()

                

                # °ü·Ã ¶óÀÎ ÁÖº¯ ÄÚµå ÃßÃâ (¿¡·¯ ¶óÀÎ ¡¾20 ¶óÀÎ)

                if error_context.line_number:

                    lines = file_content.split('\n')

                    start_line = max(0, error_context.line_number - 21)

                    end_line = min(len(lines), error_context.line_number + 20)

                    relevant_code = '\n'.join(lines[start_line:end_line])

                    source_files[error_context.file_path] = relevant_code

                else:

                    source_files[error_context.file_path] = file_content

                    

            except Exception as e:

                logger.warning(f"[SELF-HEALING] Failed to read source file {error_context.file_path}: {e}")

        

        return source_files

    

    def _build_analysis_prompt(

        self,

        error_context: ErrorContext,

        source_files: Dict[str, str]

    ) -> str:

        """Gemini¿¡ Àü¼ÛÇÒ ÇÁ·ÒÇÁÆ® »ý¼º"""

        prompt = f"""You are a Python debugging assistant. Analyze the following error and suggest a fix.



ERROR INFORMATION:

- Error Type: {error_context.error_type}

- Error Message: {error_context.error_message}

- File: {error_context.file_path or 'Unknown'}

- Line: {error_context.line_number or 'Unknown'}

- Function: {error_context.function_name or 'Unknown'}



TRACEBACK:

```

{error_context.traceback}

```



"""

        

        if source_files:

            prompt += "SOURCE CODE (relevant section):\n"

            for file_path, code in source_files.items():

                prompt += f"\n--- {file_path} ---\n"

                prompt += code

                prompt += "\n"

        

        prompt += """

Please analyze the error and provide a fix in the following JSON format:

{

    "description": "Brief description of the fix",

    "file_path": "path/to/file.py",

    "old_code": "the problematic code section",

    "new_code": "the fixed code section",

    "confidence": 0.0-1.0,

    "reasoning": "Explanation of why this fix should work"

}



IMPORTANT:

- Only suggest fixes that are clearly correct based on the error

- Be conservative with confidence scores

- Provide complete, runnable code blocks

- Preserve code structure and indentation

"""

        

        return prompt

    

    def _parse_gemini_response(self, response_text: str, error_context: ErrorContext) -> Optional[PatchSuggestion]:

        """Gemini ÀÀ´ä ÆÄ½Ì"""

        try:

            # JSON ÄÚµå ºí·Ï ÃßÃâ

            if '```json' in response_text:

                json_start = response_text.find('```json') + 7

                json_end = response_text.find('```', json_start)

                json_str = response_text[json_start:json_end].strip()

            elif '```' in response_text:

                json_start = response_text.find('```') + 3

                json_end = response_text.find('```', json_start)

                json_str = response_text[json_start:json_end].strip()

            else:

                # JSONÀÌ ¾øÀ¸¸é ÀüÃ¼ ÅØ½ºÆ®¸¦ JSONÀ¸·Î ½Ãµµ

                json_str = response_text.strip()

            

            # JSON ÆÄ½Ì

            patch_data = json.loads(json_str)

            

            return PatchSuggestion(

                description=patch_data.get('description', 'No description'),

                file_path=patch_data.get('file_path', error_context.file_path or 'unknown'),

                old_code=patch_data.get('old_code', ''),

                new_code=patch_data.get('new_code', ''),

                confidence=float(patch_data.get('confidence', 0.5)),

                reasoning=patch_data.get('reasoning', 'No reasoning provided')

            )

            

        except (json.JSONDecodeError, KeyError, ValueError) as e:

            logger.warning(f"[SELF-HEALING] Failed to parse Gemini response: {e}")

            logger.debug(f"[SELF-HEALING] Response text: {response_text[:500]}")

            return None

    

    def _save_patch_suggestion(self, error_context: ErrorContext, patch: PatchSuggestion):

        """ÆÐÄ¡ Á¦¾ÈÀ» ÆÄÀÏ¿¡ ÀúÀå"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        patch_file = self.log_dir / f"patch_{timestamp}.json"

        

        patch_data = {

            "timestamp": timestamp,

            "error_context": asdict(error_context),

            "patch_suggestion": asdict(patch),

        }

        

        try:

            with open(patch_file, 'w', encoding='utf-8') as f:

                json.dump(patch_data, f, indent=2, ensure_ascii=False)

            logger.info(f"[SELF-HEALING] Patch suggestion saved to {patch_file}")

        except Exception as e:

            logger.error(f"[SELF-HEALING] Failed to save patch suggestion: {e}")

    

    def apply_patch(self, patch: PatchSuggestion) -> bool:

        """

        ÆÐÄ¡ Àû¿ë (ÁÖÀÇ: ÀÚµ¿ ÆÐÄ¡´Â À§ÇèÇÒ ¼ö ÀÖÀ½)

        

        Args:

            patch: Àû¿ëÇÒ ÆÐÄ¡ Á¦¾È

        

        Returns:

            ¼º°ø ¿©ºÎ

        """

        if not self.enable_auto_patch:

            logger.warning("[SELF-HEALING] Auto-patch is disabled. Patch suggestion saved but not applied.")

            return False

        

        if patch.confidence < 0.7:

            logger.warning(f"[SELF-HEALING] Patch confidence too low ({patch.confidence}), not applying")

            return False

        

        try:

            file_path = Path(patch.file_path)

            if not file_path.exists():

                logger.error(f"[SELF-HEALING] File not found: {file_path}")

                return False

            

            # ÆÄÀÏ ¹é¾÷

            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

            with open(file_path, 'r', encoding='utf-8') as f:

                original_content = f.read()

            with open(backup_path, 'w', encoding='utf-8') as f:

                f.write(original_content)

            

            # ÆÐÄ¡ Àû¿ë

            if patch.old_code in original_content:

                new_content = original_content.replace(patch.old_code, patch.new_code)

                with open(file_path, 'w', encoding='utf-8') as f:

                    f.write(new_content)

                logger.info(f"[SELF-HEALING] Patch applied to {file_path} (backup: {backup_path})")

                return True

            else:

                logger.warning(f"[SELF-HEALING] Old code not found in file, patch not applied")

                return False

                

        except Exception as e:

            logger.error(f"[SELF-HEALING] Failed to apply patch: {e}")

            logger.debug(traceback.format_exc())

            return False





# Àü¿ª ÀÎ½ºÅÏ½º (¼±ÅÃÀû »ç¿ë)

_global_self_healing: Optional[GenAISelfHealing] = None





def get_self_healing() -> Optional[GenAISelfHealing]:

    """Àü¿ª Self-Healing ÀÎ½ºÅÏ½º °¡Á®¿À±â"""

    return _global_self_healing





def init_self_healing(

    api_key: Optional[str] = None,

    enable_auto_patch: bool = False

) -> GenAISelfHealing:

    """

    Àü¿ª Self-Healing ÀÎ½ºÅÏ½º ÃÊ±âÈ­

    

    Args:

        api_key: Google Gemini API Å°

        enable_auto_patch: ÀÚµ¿ ÆÐÄ¡ Àû¿ë ¿©ºÎ (±âº»°ª: False)

    

    Returns:

        GenAISelfHealing ÀÎ½ºÅÏ½º

    """

    global _global_self_healing

    _global_self_healing = GenAISelfHealing(

        api_key=api_key,

        enable_auto_patch=enable_auto_patch

    )

    return _global_self_healing

