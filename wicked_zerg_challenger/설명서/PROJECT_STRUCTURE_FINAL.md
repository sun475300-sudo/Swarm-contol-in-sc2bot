# 프로젝트 구조 최종 정리

**정리 일시**: 2026년 01-13  
**정리 범위**: 설명서 폴더 통일, 파일 구조 명확화  
**기준**: 모든 문서는 루트의 `설명서/` 폴더에 통일

---

## ? 폴더 구조 원칙

### 1. wicked_zerg_challenger (프로젝트 루트)
**역할**: 프로젝트 관리, 자동화, 설정, 배포

```
wicked_zerg_challenger/
├── bat/                    # 자동화 스크립트 (.bat)
├── tools/                  # 관리 유틸리티
├── monitoring/             # 모니터링 시스템
├── 설명서/                 # 모든 문서 (통일된 위치) ?
├── stats/                  # 상태 파일 (통일된 위치)
├── replays_archive/        # 완료된 리플레이
├── requirements.txt
├── pyrightconfig.json
└── ...
```

### 2. local_training (핵심 로직 폴더)
**역할**: 게임 AI 로직과 신경망 모델

```
local_training/
├── wicked_zerg_bot_pro.py  # 메인 봇
├── main_integrated.py      # 통합 실행
├── zerg_net.py             # 신경망
├── config.py               # 설정
├── combat_manager.py       # 전투 관리
├── economy_manager.py      # 경제 관리
├── production_manager.py   # 생산 관리
├── intel_manager.py        # 정보 관리
├── scouting_system.py      # 정찰 시스템
├── scripts/                # 봇 실행 중 사용 스크립트
│   ├── replay_learning_manager.py
│   ├── learning_logger.py
│   ├── strategy_database.py
│   └── ...
├── models/                 # 학습된 모델
├── data/                   # 학습 데이터
└── ...
```

**중요**: 
- `local_training/설명서/` - `local_training` 로직 관련 문서 (파일 구조, 코드 수정 등)
- 루트 `설명서/` - 프로젝트 전체 관리 문서 (설정, 배포, 가이드 등)

---

## ? 완료된 정리 작업

### 1. 설명서 폴더 역할 구분 ?
- **구조**: 
  - `local_training/설명서/` - `local_training` 로직 관련 문서
  - 루트 `설명서/` - 프로젝트 전체 관리 문서
- **내용**:
  - `local_training/설명서/FILE_STRUCTURE.md` - local_training 폴더 구조
  - `local_training/설명서/FIXES_SUMMARY.md` - local_training 코드 수정 사항
  - 루트 `설명서/` - 프로젝트 설정, 배포, 가이드 등

### 2. 파일 구조 문서화 ?
- `설명서/FILE_STRUCTURE.md` 생성/업데이트
- `설명서/FIXES_SUMMARY.md` 생성/업데이트
- 프로젝트 구조 원칙 명시

---

## ? 최종 파일 구조

### 설명서 폴더 위치
- ? **루트의 `설명서/` 폴더**: 프로젝트 전체 관리 문서
- ? **`local_training/설명서/` 폴더**: local_training 로직 관련 문서

### 문서 분류

#### 루트 `설명서/` (프로젝트 전체 관리 문서)
- 프로젝트 설정 가이드
- 배포 가이드
- 학습 파이프라인 가이드
- 프로젝트 구조 개요
- 코드 리뷰 보고서 (프로젝트 전체)
- 버그 리포트 (프로젝트 전체)

#### `local_training/설명서/` (로직 관련 문서)
- local_training 폴더 구조 (`FILE_STRUCTURE.md`)
- local_training 코드 수정 사항 (`FIXES_SUMMARY.md`)
- 모듈별 구현 상세
- 로직 구현 세부사항

---

## ? 주요 효과

### 구조 명확화
- **역할별 분리**: 프로젝트 전체 문서와 로직 문서 분리
- **명확한 구조**: 각 폴더의 역할이 명확히 구분
- **일관성**: 프로젝트 구조 원칙에 맞게 정리

### 유지보수성 향상
- **문서 찾기 용이**: 역할별로 문서 위치가 명확
- **혼동 방지**: 각 설명서 폴더의 역할이 명확히 구분
- **일관성**: 프로젝트 구조 원칙에 맞게 정리

---

**정리 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **설명서 폴더 역할 구분 완료**
