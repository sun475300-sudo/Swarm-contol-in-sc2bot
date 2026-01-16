# 로컬 학습 폴더 정리 완료

**작성일**: 2026-01-16

## 준비 완료

로컬 학습 폴더(`local_training`)의 불필요한 파일과 폴더를 제거하는 도구가 준비되었습니다.

## 생성된 파일

1. **`bat/cleanup_local_training.bat`**: 로컬 학습 폴더 정리 배치 스크립트
2. **`LOCAL_TRAINING_CLEANUP_COMPLETE.md`**: 정리 가이드

## 실행 방법

### 배치 스크립트 사용 (권장)
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\cleanup_local_training.bat
```

이 배치 스크립트는 다음 항목들을 제거합니다:
- `__pycache__/` 디렉토리
- `.pyc`, `.pyo` 파일
- `.bak` 파일
- `.tmp`, `.temp`, `.swp`, `.swo`, `*~` 임시 파일

## 제거 대상 파일/폴더

### 자동 제거
1. **백업 파일**: `.bak`, `.backup`, `.old`
2. **캐시 파일**: `.pyc`, `.pyo`, `__pycache__/`
3. **임시 파일**: `.tmp`, `.temp`, `.swp`, `.swo`, `*~`
4. **로그 파일**: `.log` (선택적)

### 보호된 항목 (절대 삭제 안 함)
- `models/`: 학습된 모델 폴더
- `scripts/`: 실행 스크립트 폴더
- 소스 코드 파일 (`.py`)
- 필요한 데이터 파일

## 현재 상태

스캔 결과, 현재 `local_training` 폴더에는 발견된 불필요한 파일이 없습니다.

## 참고 사항

- 배치 스크립트는 안전하게 작동하며, 중요 파일은 삭제하지 않습니다
- `models/`와 `scripts/` 폴더는 보호됩니다
- 필요시 수동으로 정리할 수 있습니다
