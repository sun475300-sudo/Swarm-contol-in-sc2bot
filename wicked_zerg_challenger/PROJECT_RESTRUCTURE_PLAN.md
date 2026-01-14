# 프로젝트 구조 재정리 계획

**작성 일시**: 2026-01-14  
**목적**: Single Source of Truth 원칙에 따라 루트 폴더와 local_training 폴더 역할 분리

## 현재 상황

### 루트 폴더 (`wicked_zerg_challenger/`)
- 봇 로직 파일: **없음**
- 관리 도구: `tools/`, `bat/`, `scripts/`
- 모니터링: `monitoring/`
- 문서: `설명서/`
- 설정: `requirements.txt`, `pyrightconfig.json`, `run.py`

### `local_training/` 폴더
- 봇 로직 파일: **모두 여기에 있음**
  - `wicked_zerg_challenger.py`
  - `combat_manager.py`, `economy_manager.py`, `production_manager.py` 등
  - `zerg_net.py`, `config.py` 등
- 훈련 스크립트: `main_integrated.py`, `build_order_learner.py`
- 데이터: `data/`, `models/`, `logs/`

## 목표 구조

### 루트 폴더 (Single Source of Truth)
**역할**: 봇의 핵심 로직만 존재

필수 파일:
- `wicked_zerg_bot_pro.py`
- `combat_manager.py`
- `economy_manager.py`
- `production_manager.py`
- `intel_manager.py`
- `queen_manager.py`
- `micro_controller.py`
- `zerg_net.py`
- `config.py`
- `unit_factory.py`
- 기타 매니저 모듈들

### `local_training/` 폴더
**역할**: 훈련 스크립트와 데이터만

필수 파일/폴더:
- `main_integrated.py` (훈련 실행 스크립트)
- `build_order_learner.py` (빌드 오더 학습기)
- `scripts/` (훈련 관련 스크립트)
- `data/` (학습 데이터)
- `models/` (학습된 모델)
- `logs/` (훈련 로그)

삭제해야 할 파일:
- `wicked_zerg_bot_pro.py` ?
- `combat_manager.py` ?
- `economy_manager.py` ?
- `production_manager.py` ?
- `intel_manager.py` ?
- `unit_factory.py` ?
- `zerg_net.py` ?
- `config.py` ?
- 기타 매니저 모듈들 ?

## 작업 순서

1. ? 현재 구조 분석 및 계획 수립
2. ? 루트 폴더에 봇 로직 파일 이동 (또는 생성 확인)
3. ? `local_training/` 폴더의 중복 파일 삭제
4. ? 훈련 스크립트의 import 경로 수정
5. ? 테스트 및 검증

## 주의사항

?? **중요**: 루트 폴더에 현재 봇 로직 파일이 없는 것으로 확인됨
- 작업 전 백업 필수
- 기존 동작 확인 필요
