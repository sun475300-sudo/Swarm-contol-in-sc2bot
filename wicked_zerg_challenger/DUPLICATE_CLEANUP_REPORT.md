# 중복 파일 정리 리포트

**작성 일시**: 2026-01-14  
**작업 목적**: 최신 업데이트된 파일만 유지하고 중복 파일 정리  
**상태**: ? **진행 중**

---

## ? 확인 완료 항목

### 1. `모니터링/` 폴더
- **상태**: ? 이미 제거됨 또는 존재하지 않음
- **이유**: `monitoring/` 폴더와 중복
- **결과**: `monitoring/` 폴더만 유지 (Single Source of Truth)

### 2. `chat_manager.py` vs `chat_manager_utf8.py`
- **상태**: ? 둘 다 유지 필요
- **이유**: 
  - `chat_manager.py`: 호환성 레이어 (4줄, `chat_manager_utf8`를 import)
  - `chat_manager_utf8.py`: 실제 구현
- **결과**: 현재 상태 유지 (호환성 패턴)

---

## ?? 확인 필요 항목

### 1. `local_training/` vs `아레나_배포/` 중복 파일

#### 중복 파일 목록 (20+ 파일)
- `wicked_zerg_bot_pro.py`
- `combat_manager.py`
- `economy_manager.py`
- `production_manager.py`
- `intel_manager.py`
- `queen_manager.py`
- `scouting_system.py`
- `micro_controller.py`
- `combat_tactics.py`
- `personality_manager.py`
- `production_resilience.py`
- `map_manager.py`
- `unit_factory.py`
- `telemetry_logger.py`
- `zerg_net.py`
- `config.py`
- `main_integrated.py`
- 기타 매니저 파일들

#### 문제점
1. **Version Drift 위험**: 두 폴더의 파일이 서로 다르게 진화할 수 있음
2. **최신 버전 식별 필요**: 각 파일의 수정 시간을 비교하여 최신 버전 확인 필요
3. **용도 차이**: 
   - `local_training/`: 로컬 훈련용
   - `아레나_배포/`: AI Arena 배포용

#### 권장 사항
- **옵션 A**: `local_training/`을 소스로 사용하고 `아레나_배포/`는 배포 시 복사본 생성
- **옵션 B**: 파일별로 최신 버전 확인 후 통합
- **옵션 C**: 현재 상태 유지 (별도 관리)

---

## ? 정리 계획

### 단계 1: 안전한 중복 제거 (완료)
- ? `모니터링/` 폴더 제거 확인

### 단계 2: 파일별 최신 버전 확인 (대기)
- ? `local_training/`과 `아레나_배포/` 중복 파일 비교
- ? 파일별 수정 시간 확인
- ? 최신 버전 식별

### 단계 3: 정리 실행 (대기)
- ? 최신 버전만 유지
- ? Import 경로 확인 및 수정

---

## ? 확인된 파일 수정 시간

### `monitoring/` 폴더 (최신)
- `dashboard_api.py`: 2026-01-14 08:45:43
- `dashboard.py`: 2026-01-14 08:44:48
- `monitoring_utils.py`: 2026-01-14 12:43:46
- `test_endpoints.py`: 2026-01-14 08:44:48
- `telemetry_logger.py`: 2026-01-14 12:26:50

### 루트 폴더
- `chat_manager.py`: 2026-01-14 12:43:46 (최신)
- `chat_manager_utf8.py`: 2026-01-14 08:44:48

---

## ? 참고 사항

1. **`local_training/`과 `아레나_배포/` 중복**: 
   - 이 두 폴더의 파일들은 용도가 다를 수 있음
   - 단순 제거보다는 용도별 관리가 필요할 수 있음
   - 파일별 최신 버전 확인 후 통합 권장

2. **Import 경로**: 
   - 파일 이동/제거 시 모든 import 경로 확인 필요
   - `local_training/wicked_zerg_bot_pro.py`의 import 경로 확인 필요

3. **백업**: 
   - 중요한 파일 제거 전 백업 권장
   - `backups/` 폴더 활용

---

## ? 다음 단계

1. **`local_training/`과 `아레나_배포/` 파일 비교 스크립트 작성**
   - 파일별 수정 시간 비교
   - 내용 차이 확인

2. **최신 버전 식별**
   - 파일별 최신 버전 결정
   - 통합 계획 수립

3. **안전한 정리 실행**
   - 백업 생성
   - 중복 제거
   - Import 경로 수정

---

**리포트 작성자**: Code Cleanup System  
**다음 업데이트**: 파일 비교 완료 후
