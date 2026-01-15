# -*- coding: utf-8 -*-
"""
Telemetry Logger with Atomic Write - Thread-safe file writing
Atomic write pattern을 사용하여 파일 쓰기 중 읽기 오류를 방지합니다.
"""

import json
import csv
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def atomic_write_json(filepath: Path, data: Any) -> bool:
    """
    Atomic write for JSON files
    
    임시 파일에 쓰고 완료 후 원본 파일로 교체하여
    읽기 중 쓰기가 발생해도 데이터 무결성을 보장합니다.
    
    Args:
        filepath: 대상 파일 경로
        data: 저장할 데이터 (JSON 직렬화 가능)
    
    Returns:
        bool: 성공 여부
    """
    try:
        # 임시 파일 생성
        temp_file = filepath.with_suffix(filepath.suffix + '.tmp')
        
        # 임시 파일에 쓰기
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # 원자적 교체 (Windows에서는 rename이 실패할 수 있으므로 try-except)
        try:
            # Unix/Linux/Mac: rename는 원자적 연산
            temp_file.replace(filepath)
        except OSError:
            # Windows: rename가 실패할 수 있으므로 copy + remove
            shutil.copy2(temp_file, filepath)
            temp_file.unlink()
        
        return True
        
    except Exception as e:
        logger.error(f"Atomic write 실패: {e}")
        # 임시 파일 정리
        try:
            if temp_file.exists():
                temp_file.unlink()
        except Exception:
            pass
        return False


def atomic_write_csv(filepath: Path, data: List[Dict[str, Any]]) -> bool:
    """
    Atomic write for CSV files
    
    Args:
        filepath: 대상 파일 경로
        data: 저장할 데이터 (리스트의 딕셔너리)
    
    Returns:
        bool: 성공 여부
    """
    if not data:
        return False
    
    try:
        # 임시 파일 생성
        temp_file = filepath.with_suffix(filepath.suffix + '.tmp')
        
        # 임시 파일에 쓰기
        with open(temp_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        # 원자적 교체
        try:
            temp_file.replace(filepath)
        except OSError:
            shutil.copy2(temp_file, filepath)
            temp_file.unlink()
        
        return True
        
    except Exception as e:
        logger.error(f"Atomic CSV write 실패: {e}")
        try:
            if temp_file.exists():
                temp_file.unlink()
        except Exception:
            pass
        return False


def atomic_append_jsonl(filepath: Path, data: Dict[str, Any]) -> bool:
    """
    Atomic append for JSONL files (JSON Lines)
    
    JSONL 파일에 한 줄씩 추가하는 경우에도 원자적 쓰기를 보장합니다.
    
    Args:
        filepath: 대상 파일 경로
        data: 추가할 데이터 (딕셔너리)
    
    Returns:
        bool: 성공 여부
    """
    try:
        # 기존 내용 읽기
        existing_lines = []
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_lines = [line.strip() for line in f if line.strip()]
            except Exception:
                pass
        
        # 새 라인 추가
        new_line = json.dumps(data, ensure_ascii=False)
        existing_lines.append(new_line)
        
        # 임시 파일에 전체 내용 쓰기
        temp_file = filepath.with_suffix(filepath.suffix + '.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            for line in existing_lines:
                f.write(line + '\n')
        
        # 원자적 교체
        try:
            temp_file.replace(filepath)
        except OSError:
            shutil.copy2(temp_file, filepath)
            temp_file.unlink()
        
        return True
        
    except Exception as e:
        logger.error(f"Atomic JSONL append 실패: {e}")
        try:
            if temp_file.exists():
                temp_file.unlink()
        except Exception:
            pass
        return False


# 기존 telemetry_logger.py를 위한 패치 함수
def patch_telemetry_logger():
    """
    기존 telemetry_logger.py의 save_telemetry 메서드를
    atomic write를 사용하도록 패치합니다.
    """
    try:
        from telemetry_logger import TelemetryLogger
        
        original_save = TelemetryLogger.save_telemetry
        
        async def patched_save_telemetry(self):
            """Atomic write를 사용하는 패치된 save_telemetry"""
            try:
                if not self.telemetry_data:
                    print("[TELEMETRY] No data to save")
                    return
                
                # Atomic write for JSON
                json_file = Path(self.telemetry_file)
                if atomic_write_json(json_file, self.telemetry_data):
                    print(f"[TELEMETRY] Data saved (atomic): {self.telemetry_file}")
                
                # Atomic write for CSV
                csv_file = json_file.with_suffix('.csv')
                if atomic_write_csv(csv_file, self.telemetry_data):
                    print(f"[TELEMETRY] CSV saved (atomic): {csv_file}")
                
            except Exception as e:
                print(f"[WARNING] Telemetry save error: {e}")
        
        TelemetryLogger.save_telemetry = patched_save_telemetry
        logger.info("TelemetryLogger에 atomic write 패치 적용됨")
        
    except ImportError:
        logger.warning("telemetry_logger를 찾을 수 없습니다. 패치를 건너뜁니다.")


if __name__ == "__main__":
    # 테스트
    test_data = [
        {"time": 100, "minerals": 500, "vespene": 200},
        {"time": 200, "minerals": 600, "vespene": 250}
    ]
    
    test_json = Path("test_telemetry.json")
    test_csv = Path("test_telemetry.csv")
    
    print("Atomic write 테스트...")
    if atomic_write_json(test_json, test_data):
        print(f"✅ JSON 저장 성공: {test_json}")
    
    if atomic_write_csv(test_csv, test_data):
        print(f"✅ CSV 저장 성공: {test_csv}")
    
    # 정리
    if test_json.exists():
        test_json.unlink()
    if test_csv.exists():
        test_csv.unlink()
