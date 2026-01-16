# 다음 단계 요약

**작성일**: 2026-01-16

## 완료된 작업

### 1. 들여쓰기 오류 수정 ?
- `tools/continuous_improvement_system.py`
- `tools/auto_error_fixer.py`
- `tools/code_quality_improver.py`

### 2. 코드 스타일 통일화 ?
- `python tools/code_quality_improver.py --fix-style` 실행 완료
- 174개 Python 파일의 스타일 수정 완료

### 3. 일일 자동 개선 시스템 ?
- `bat/daily_improvement.bat` 정상 작동 확인
- 작업 스케줄러에 등록 가능

## 남은 작업

### 1. 불필요한 파일 삭제

**방법 1: 배치 파일 사용**
```bash
cd wicked_zerg_challenger
bat\cleanup_unnecessary_files.bat
```

**방법 2: Python 스크립트 사용 (인코딩 문제 해결 후)**
```bash
python tools/cleanup_unnecessary_files.py --execute
```

**삭제 대상**:
- 백업 파일(.bak): 73개
- 캐시 파일(.pyc, .pyo): 여러 개
- `__pycache__` 디렉토리: 여러 개

### 2. 남은 스타일 이슈 (182개)

**수정 방법**:
```bash
cd wicked_zerg_challenger
python tools\code_quality_improver.py --fix-style
```

**스타일 이슈 유형**:
- 탭 문자 사용
- 긴 줄 (120자 초과)
- 공백 문제

### 3. 큰 파일 분리 (2개)

**큰 파일 목록**:
1. `local_training\main_integrated.py`: 1367줄
2. `tools\download_and_train.py`: 1179줄

**분리 제안**:
- `local_training\main_integrated.py`:
  - `local_training/core/training_runner.py`
  - `local_training/core/data_loader.py`
  - `local_training/core/model_manager.py`

- `tools\download_and_train.py`:
  - `tools/replay_downloader.py`
  - `tools/replay_processor.py`
  - `tools/training_orchestrator.py`

### 4. 복잡한 함수 단순화 (5개)

**복잡한 함수 목록**:
1. `tools\fix_markdown_warnings.py:15` - `fix_markdown_file` (복잡도: 32)
2. `tools\fix_all_markdown_warnings.py:12` - `fix_markdown_content` (복잡도: 28)
3. `tools\optimize_for_training.py:130` - `scan_for_removal` (복잡도: 22)
4. `tools\code_quality_improver.py:29` - `remove_unused_imports` (복잡도: 20)
5. `tools\fix_md_warnings.py:12` - `fix_content` (복잡도: 20)

**단순화 제안**:
- 각 함수를 작은 함수로 분리
- 조건문 로직을 별도 메서드로 추출
- 중복 코드 제거

## 작업 스케줄러 등록

**작업 스케줄러 열기**:
```
taskschd.msc
```

**작업 생성**:
- **이름**: "Daily Improvement"
- **프로그램**: `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat\daily_improvement.bat`
- **트리거**: 매일 원하는 시간 (예: 오전 7시)
- **동작**: 시작 프로그램

## 우선순위

1. **높음**: 불필요한 파일 삭제 (디스크 공간 확보)
2. **중간**: 남은 스타일 이슈 수정 (코드 품질)
3. **낮음**: 큰 파일 분리 (장기적 유지보수)
4. **낮음**: 복잡한 함수 단순화 (장기적 유지보수)

## 진행 상황

- ? 코드 스타일 통일화
- ? 들여쓰기 오류 수정
- ? 일일 자동 개선 시스템
- ? 불필요한 파일 삭제 (인코딩 문제 해결 필요)
- ? 남은 스타일 이슈 수정
- ? 큰 파일 분리
- ? 복잡한 함수 단순화

## 참고 문서

- `CONTINUOUS_IMPROVEMENT_REPORT.md`: 상세 개선 리포트
- `DAILY_IMPROVEMENT_SUMMARY.md`: 일일 개선 작업 요약
- `INDENTATION_ERRORS_FIXED.md`: 들여쓰기 오류 수정 완료
