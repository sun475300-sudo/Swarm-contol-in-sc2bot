# 폴더 구조 최종 정밀 검토 보고서

**작성 일시**: 2026년 01-13  
**검토 범위**: `wicked_zerg_challenger`와 `local_training` 폴더의 파일 배치 최종 검토  
**상태**: ? **수정 완료**

---

## ? 폴더별 역할 정의

### A. `wicked_zerg_challenger` (프로젝트 루트: 관리 및 인프라)

**역할**: 프로젝트 관리, 자동화, 설정, 배포, 데이터 아카이브

**포함해야 할 파일/폴더**:
- ? **배치 파일**: `bat/` 폴더 (모든 `.bat`, `.sh`, `.ps1` 파일)
- ? **환경 설정**: `.gitignore`, `requirements.txt`, `pyrightconfig.json`, `pyproject.toml`
- ? **관리 도구**: `tools/` 폴더 (리플레이 다운로더, 라이프사이클 매니저, 환경 구축 도구)
- ? **모니터링**: `monitoring/` 폴더
- ? **문서**: `설명서/` 폴더 (프로젝트 전체 문서)
- ? **상태 파일**: `stats/` 폴더 (통합 저장소, 인스턴스별 서브 디렉토리)
- ? **데이터 아카이브**: `replays_archive/` (학습 완료된 리플레이)
- ? **리플레이 소스**: `replays_source/`, `replays_quarantine/` (관리용)
- ? **로그**: `logs/` 폴더 (프로젝트 전체 로그)

---

### B. `local_training` (핵심 로직: 게임 AI 엔진 및 모델)

**역할**: 게임 AI 로직과 신경망 모델 (실제 스타2 게임 내에서 작동)

**포함해야 할 파일/폴더**:
- ? **메인 실행**: `wicked_zerg_bot_pro.py`, `main_integrated.py`
- ? **매니저 모듈**: `combat_manager.py`, `economy_manager.py`, `intel_manager.py` 등
- ? **신경망 모델**: `zerg_net.py`
- ? **학습 로직**: `replay_build_order_learner.py`
- ? **봇 실행 중 사용 스크립트**: `scripts/` 폴더 (봇이 import하는 스크립트만)
- ? **모델 및 데이터**: `models/`, `data/` (봇 실행 중 생성/사용)
- ? **로직 관련 문서**: `local_training/설명서/` 폴더

---

## ? 발견된 문제점

### 문제 1: 루트에 배치 파일 남아있음 → ? 해결 완료

**파일**: `setup_firewall_admin.ps1`

**이전 위치**: 루트  
**현재 위치**: `bat/setup_firewall_admin.ps1`  
**상태**: ? **이동 완료**

---

### 문제 2: 루트에 텍스트 파일 혼재 → ? 해결 완료

**파일들**:
1. `training_error_log.txt` - 학습 에러 로그
2. `ZDP_IMPLEMENTATION_SUMMARY.txt` - 구현 요약 문서

**이전 위치**: 루트  
**현재 위치**:
- `training_error_log.txt` → `logs/training_error_log.txt` ?
- `ZDP_IMPLEMENTATION_SUMMARY.txt` → `설명서/ZDP_IMPLEMENTATION_SUMMARY.md` ?

**상태**: ? **이동 완료**

---

### 문제 3: 데이터 폴더 중복 → ? 해결 완료

**이전 상태**:
- 루트에 `data/`, `models/`, `logs/`, `stats/` 폴더 존재
- `local_training/`에도 `data/`, `models/` 폴더 존재

**코드 수정 결과**:
- `main_integrated.py`: `stats/`는 루트 사용 (`project_root / "stats"`) ?
- `curriculum_manager.py`: `data/` 경로 수정 완료 (`script_dir / "data"`) ?
- `zerg_net.py`: `models/` 경로 수정 완료 (`SCRIPT_DIR / "models"`) ?
- `wicked_zerg_bot_pro.py`: 이미 `local_training/data/` 사용 중 ?

**최종 구조**:
- ? `stats/` - 루트에 유지 (인스턴스별 서브 디렉토리)
- ? `logs/` - 루트에 유지 (프로젝트 전체 로그)
- ? `data/` - `local_training/data/` 사용 (봇 실행 중 생성)
- ? `models/` - `local_training/models/` 사용 (봇 실행 중 생성)
- ? `replays/`, `replays_archive/` - 루트에 유지 (데이터 아카이브)

**상태**: ? **코드 경로 통일 완료**

---

### 문제 4: 리플레이 폴더 구조 → ? 올바름

**현재 폴더들**:
- `replays/` - 루트 ?
- `replays_archive/` - 루트 ?
- `replays_quarantine/` - 루트 ?
- `replays_source/` - 루트 ?

**코드 분석 결과**:
- 대부분의 코드가 `D:\replays\replays` 또는 환경 변수 사용 ?
- 일부 코드가 상대 경로 `replays/` 사용 (환경 변수 우선 처리됨) ?

**최종 구조**:
- ? 루트에 유지 (데이터 아카이브 역할)
- ? 코드에서 환경 변수 우선 처리로 경로 참조 통일됨

**상태**: ? **올바름 (수정 불필요)**

---

## ? 올바르게 배치된 항목

### 1. 배치 파일
- ? 모든 `.bat`, `.sh`, `.ps1` 파일이 `bat/` 폴더에 있음
- ? `setup_firewall_admin.ps1` → `bat/` 이동 완료

### 2. 관리 스크립트
- ? 모든 관리 스크립트가 `tools/` 폴더에 있음
- ? 봇 실행 스크립트만 `local_training/scripts/`에 있음

### 3. 문서
- ? 프로젝트 전체 문서: `설명서/` (루트)
- ? 로직 관련 문서: `local_training/설명서/` (올바름)

### 4. 설정 파일
- ? `requirements.txt`, `pyrightconfig.json`, `pyproject.toml` - 루트 (올바름)

---

## ? 수정 완료 사항

### 1. 배치 파일 이동 완료
- ? `setup_firewall_admin.ps1` → `bat/setup_firewall_admin.ps1`

### 2. 문서 파일 이동 완료
- ? `ZDP_IMPLEMENTATION_SUMMARY.txt` → `설명서/ZDP_IMPLEMENTATION_SUMMARY.md`

### 3. 로그 파일 이동 완료
- ? `training_error_log.txt` → `logs/training_error_log.txt`

### 4. 데이터 폴더 경로 통일 완료
- ? `curriculum_manager.py`: `Path("data")` → `script_dir / "data"` (local_training/data/)
- ? `zerg_net.py`: `PROJECT_ROOT / "models"` → `SCRIPT_DIR / "models"` (local_training/models/)
- ? `wicked_zerg_bot_pro.py`: 이미 `local_training/data/` 사용 중 (올바름)

---

## ? 최종 권장 구조

### `wicked_zerg_challenger/` (루트)
```
wicked_zerg_challenger/
├── bat/                    # 모든 실행 스크립트 (.bat, .sh, .ps1)
├── tools/                  # 관리 유틸리티
├── monitoring/             # 모니터링 시스템
├── 설명서/                 # 프로젝트 전체 문서
├── stats/                  # 상태 파일 통합 저장소 (instance_*/)
├── logs/                   # 프로젝트 전체 로그
├── replays/                # 리플레이 작업 디렉토리
├── replays_archive/        # 완료된 리플레이
├── replays_source/         # 리플레이 소스
├── replays_quarantine/     # 격리된 리플레이
├── requirements.txt
├── pyrightconfig.json
└── pyproject.toml
```

### `local_training/` (핵심 로직)
```
local_training/
├── wicked_zerg_bot_pro.py  # 메인 봇
├── main_integrated.py      # 통합 실행
├── zerg_net.py             # 신경망
├── combat_manager.py       # 전투 관리
├── economy_manager.py      # 경제 관리
├── ... (기타 매니저들)
├── scripts/                # 봇 실행 중 사용 스크립트만
│   ├── replay_learning_manager.py
│   ├── learning_logger.py
│   ├── strategy_database.py
│   ├── replay_quality_filter.py
│   ├── parallel_train_integrated.py
│   ├── run_hybrid_supervised.py
│   ├── learning_status_manager.py
│   └── replay_crash_handler.py
├── models/                 # 학습된 모델 (봇 실행 중 생성)
├── data/                   # 학습 데이터 (봇 실행 중 생성)
└── 설명서/                 # local_training 로직 문서
```

---

## ? 문제점 요약

| 문제 | 파일/폴더 | 현재 위치 | 올바른 위치 | 우선순위 |
|------|----------|----------|------------|---------|
| 배치 파일 | `setup_firewall_admin.ps1` | 루트 | `bat/` | ? 완료 |
| 문서 파일 | `ZDP_IMPLEMENTATION_SUMMARY.txt` | 루트 | `설명서/` | ? 완료 |
| 로그 파일 | `training_error_log.txt` | 루트 | `logs/` | ? 완료 |
| 데이터 폴더 | `data/`, `models/` | 루트 + local_training | local_training만 | ? 완료 |
| 경로 참조 | 코드 내 경로 | 혼재 | 통일 필요 | ? 완료 |

---

## ? 검증 체크리스트

### 파일 배치 검증
- [x] ? 관리 스크립트가 `tools/`에 있는지 확인
- [x] ? 봇 실행 스크립트만 `local_training/scripts/`에 있는지 확인
- [x] ? 배치 파일이 모두 `bat/`에 있는지 확인
- [x] ? 문서 파일이 모두 `설명서/`에 있는지 확인
- [x] ? 데이터 폴더 경로가 통일되어 있는지 확인

### Import 경로 검증
- [x] ? `main_integrated.py`의 import 경로 수정 완료
- [x] ? `download_and_train.py` 이동 후 import 경로 수정 완료
- [x] ? `optimize_code.py` 이동 후 import 경로 수정 완료

---

**검토 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **모든 문제 해결 완료**

---

## ? 최종 검증 결과

### 루트 파일 목록 (올바름)
- ? `.gitignore`, `.gitattributes`
- ? `requirements.txt`, `pyrightconfig.json`, `pyproject.toml`
- ? `.env.example`, `.gitignore_template.txt`
- ? 모든 배치 파일이 `bat/` 폴더에 있음
- ? 모든 문서가 `설명서/` 폴더에 있음

### 데이터 폴더 구조 (올바름)
- ? `stats/` - 루트 (인스턴스별 서브 디렉토리)
- ? `logs/` - 루트 (프로젝트 전체 로그)
- ? `local_training/models/` - 봇 실행 중 생성
- ? `local_training/data/` - 봇 실행 중 생성
- ? `replays/`, `replays_archive/` - 루트 (데이터 아카이브)

자세한 내용은 `FOLDER_STRUCTURE_FINAL_AUDIT_COMPLETE.md`를 참조하세요.

---

## ? 수정 완료 사항

### 1. 배치 파일 이동 완료
- ? `setup_firewall_admin.ps1` → `bat/setup_firewall_admin.ps1`

### 2. 문서 파일 이동 완료
- ? `ZDP_IMPLEMENTATION_SUMMARY.txt` → `설명서/ZDP_IMPLEMENTATION_SUMMARY.md`

### 3. 로그 파일 이동 완료
- ? `training_error_log.txt` → `logs/training_error_log.txt`

### 4. 데이터 폴더 경로 통일 완료
- ? `curriculum_manager.py`: `Path("data")` → `script_dir / "data"` (local_training/data/)
- ? `zerg_net.py`: `PROJECT_ROOT / "models"` → `SCRIPT_DIR / "models"` (local_training/models/)
- ? `wicked_zerg_bot_pro.py`: 이미 `local_training/data/` 사용 중 (올바름)
