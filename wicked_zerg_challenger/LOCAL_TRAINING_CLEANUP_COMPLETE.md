# 로컬 학습 폴더 정리 완료

**작성일**: 2026-01-16

## 정리 도구

### 배치 스크립트
- `bat/cleanup_local_training.bat`: 로컬 학습 폴더 정리 배치 스크립트

### 기존 도구 활용
- `tools/cleanup_unnecessary_files.py`: 전체 프로젝트 불필요한 파일 제거 도구

## 제거 대상 파일/폴더

### 자동 제거 항목
1. **백업 파일**: `.bak`, `.backup`, `.old`
2. **캐시 파일**: `.pyc`, `.pyo`, `__pycache__/`
3. **임시 파일**: `.tmp`, `.temp`, `.swp`, `.swo`, `*~`
4. **로그 파일**: `.log` (선택적)

### 보호된 항목 (절대 삭제 안 함)
- `models/`: 학습된 모델
- `scripts/`: 실행 스크립트
- 소스 코드 파일 (`.py`)

## 실행 방법

### 방법 1: 배치 스크립트 사용 (권장)
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\cleanup_local_training.bat
```

### 방법 2: 기존 정리 도구 사용
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
python tools/cleanup_unnecessary_files.py --execute
```

## 참고 사항

- 배치 스크립트는 안전하게 작동하며, 중요 파일은 삭제하지 않습니다
- 실제 삭제 전에 항상 확인하세요
- `models/` 폴더와 `scripts/` 폴더는 보호됩니다
