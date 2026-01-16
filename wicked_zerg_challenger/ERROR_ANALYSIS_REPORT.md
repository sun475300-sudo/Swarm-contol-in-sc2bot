# 에러 분석 보고서

**작성일**: 2026-01-16

## 분석 대상 파일

1. `tools/auto_error_fixer.py`
2. `monitoring/dashboard_api.py`
3. `COMPLETE_RUN_SCRIPT.py`

## 발견된 에러 및 원인

### 1. auto_error_fixer.py

#### 에러 내용
- **라인**: 20
- **에러 타입**: `IndentationError: unindent does not match any outer indentation level`

#### 원인 분석
- 클래스 메서드 정의 시 인덴테이션이 일관되지 않음
- `__init__` 메서드와 `fix_common_errors` 메서드가 클래스 내부에 있어야 하는데 들여쓰기가 잘못됨
- `try-except` 블록, `if` 문 등의 인덴테이션이 일관되지 않음

#### 수정 내용
- 모든 클래스 메서드를 4칸 들여쓰기로 통일
- `try-except` 블록 내부 코드를 올바른 인덴테이션으로 수정
- `if` 문 내부 코드를 올바른 인덴테이션으로 수정
- `main()` 함수 내부의 인덴테이션 수정

### 2. dashboard_api.py

#### 에러 내용
- **라인**: 228
- **에러 타입**: `IndentationError: expected an indented block after 'with' statement`

#### 원인 분석
- `with` 문 다음에 코드 블록이 인덴트되지 않음
- 함수 정의 내부의 인덴테이션이 일관되지 않음
- `global` 문 다음의 코드가 올바르게 인덴트되지 않음
- `if` 문 내부의 코드가 올바르게 인덴트되지 않음

#### 수정 내용
- `_load_json`, `_find_latest_instance_status`, `_load_training_stats` 함수의 인덴테이션 수정
- `with` 문 다음 코드 블록 인덴테이션 수정
- `global` 문 다음 코드 인덴테이션 수정
- `if` 문 내부 코드 인덴테이션 수정
- `serve_dashboard_ui()` 함수의 인덴테이션 수정

### 3. COMPLETE_RUN_SCRIPT.py

#### 에러 내용
- **없음** ?

#### 상태
- 문법 검사 통과
- 인덴테이션 정상

## 공통 원인

### 1. 인덴테이션 불일치
- Python은 공백(스페이스)과 탭을 구분하므로 일관된 들여쓰기가 필요
- 클래스 메서드는 클래스 정의보다 4칸 들여쓰기
- 함수 내부 코드는 함수 정의보다 4칸 들여쓰기
- 블록 내부 코드는 블록 시작보다 4칸 들여쓰기

### 2. 편집기 설정 문제
- 일부 편집기에서 탭과 스페이스를 혼용하거나 자동 변환하지 않아 발생
- 인코딩 문제로 인한 들여쓰기 깨짐

### 3. 복사-붙여넣기 오류
- 다른 파일에서 코드를 복사할 때 들여쓰기가 잘못 복사됨

## 해결 방법

### 1. 자동 수정 도구 사용
```bash
python tools/auto_error_fixer.py --all
```

### 2. 수동 검사
```bash
python -m py_compile 파일명.py
```

### 3. 편집기 설정
- Python 파일 편집 시 스페이스 4개 사용 (탭 비활성화)
- 저장 시 자동 들여쓰기 정리 활성화

## 수정 완료 상태

- ? `tools/auto_error_fixer.py` - 수정 완료 (문법 검사 통과)
- ? `monitoring/dashboard_api.py` - 수정 완료 (문법 검사 통과)
- ? `COMPLETE_RUN_SCRIPT.py` - 수정 불필요 (정상, 문법 검사 통과)

## 상세 수정 내용

### auto_error_fixer.py
- **20번 줄**: `__init__` 메서드 인덴테이션 수정 (4칸 들여쓰기)
- **23-73번 줄**: `fix_common_errors` 메서드 전체 인덴테이션 수정
- **75-106번 줄**: `scan_and_fix` 메서드 전체 인덴테이션 수정
- **109-150번 줄**: `main()` 함수 전체 인덴테이션 수정

### dashboard_api.py
- **213-218번 줄**: `try-except` 블록 내부 import 문 인덴테이션 수정
- **221-239번 줄**: `except ImportError` 블록 내부 함수들 인덴테이션 수정
- **248-260번 줄**: `root()` 함수의 `return` 문 인덴테이션 수정
- **265-268번 줄**: `health_check()` 함수의 `return` 문 인덴테이션 수정
- **479-484번 줄**: `update_learning_progress()` 함수의 `global` 문 인덴테이션 수정
- **487-500번 줄**: `get_bot_config()` 함수의 `if` 문 인덴테이션 수정
- **502-508번 줄**: `update_bot_config()` 함수의 `global` 문 인덴테이션 수정
- **515-539번 줄**: `send_control_command()` 함수의 `if-elif-else` 블록 인덴테이션 수정
- **547-564번 줄**: `websocket_game_state()` 함수 전체 인덴테이션 수정
- **569번 줄**: `websocket_game_status_alias()` 함수 인덴테이션 수정
- **735-786번 줄**: `get_file_content()` 함수의 `try-except` 블록 인덴테이션 수정
- **791-825번 줄**: `get_folder_stats()` 함수의 `try-except` 블록 인덴테이션 수정

## 권장 사항

1. **일관된 들여쓰기 사용**: 모든 Python 파일에서 4칸 스페이스 사용
2. **자동 검사 도구 활용**: 배포 전 `python -m py_compile` 실행
3. **코드 리뷰**: 복사-붙여넣기 후 들여쓰기 확인
4. **편집기 설정**: Python 개발 환경에서 들여쓰기 자동 정리 활성화
