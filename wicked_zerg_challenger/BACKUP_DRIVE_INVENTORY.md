# BackUP 드라이브 백업 파일 목록

**작성 일시**: 2026-01-14  
**경로**: `D:\BackUP`  
**상태**: ? **경로 확인 완료**

---

## ? BackUP 드라이브 구조

**경로**: `D:\BackUP`  
**총 디렉토리 수**: 15개

---

## ? 백업 폴더 목록

### 1. 일반 백업 폴더
- `backup/` - 일반 백업 폴더
- `backups/` - 백업 폴더 (복수형)
- `cleanup_backup/` - 정리 작업 백업
- `replay_archive/` - 리플레이 아카이브

### 2. 프로젝트 관련 백업
- `wicked_zerg_challenger_pro/` - 프로젝트 백업
- `local_training_cleanup/` - local_training 정리 백업
- `local_training_replays_backup/` - local_training 리플레이 백업

### 3. 정리 작업 백업 (타임스탬프)
- `massive_cleanup_20260113_155330/` - 대규모 정리 작업 (2026-01-13 15:53:30)
- `project_cleanup_20260113_154750/` - 프로젝트 정리 작업 (2026-01-13 15:47:50)
- `redundant_scripts_20260113_205203/` - 중복 스크립트 정리 (2026-01-13 20:52:03)
- `redundant_scripts_20260113_205219/` - 중복 스크립트 정리 (2026-01-13 20:52:19)

### 4. 기타 백업
- `StarCraft Zerg AI Development and Design Guide/` - 개발 가이드 백업
- `training_snapshots/` - 훈련 스냅샷
- (한글 이름 폴더 2개)

---

## ? 백업 폴더 분류

| 카테고리 | 폴더 수 | 설명 |
|---------|--------|------|
| 일반 백업 | 4개 | backup, backups, cleanup_backup, replay_archive |
| 프로젝트 백업 | 3개 | wicked_zerg_challenger_pro, local_training_* |
| 타임스탬프 백업 | 4개 | 정리 작업 타임스탬프 백업 |
| 기타 | 4개 | 가이드, 스냅샷, 한글 폴더 등 |

---

## ? 코드에서 참조되는 백업 경로

### 1. `tools/code_diet_cleanup.py`
- **백업 경로**: `D:\백업용\cleanup_backup` (한글 경로)
- **용도**: 코드 정리 작업 백업

### 2. `tools/package_for_aiarena.py`
- **백업 경로**: (코드 내부 백업 디렉토리 사용)
- **용도**: AI Arena 패키징 백업

---

## ? 참고사항

### 백업 경로 차이
- **`D:\BackUP`** (영문 경로): 실제 백업 파일이 저장된 경로
- **`D:\백업용`** (한글 경로): 코드에서 참조하는 경로 (`code_diet_cleanup.py`)

**권장사항:**
- 코드의 백업 경로를 `D:\BackUP`으로 통일하는 것을 고려
- 한글 경로는 인코딩 문제로 인해 프로그램에서 접근이 어려울 수 있음

---

## ? 다음 단계 (선택사항)

### 1. 백업 경로 통일
- `tools/code_diet_cleanup.py`의 백업 경로를 `D:\BackUP\cleanup_backup`으로 변경

### 2. 백업 파일 정리
- 오래된 타임스탬프 백업 폴더 검토
- 불필요한 중복 백업 삭제

### 3. 백업 정책 수립
- 백업 보관 기간 설정
- 자동 정리 스크립트 추가

---

**생성 일시**: 2026-01-14  
**상태**: ? **목록 작성 완료**
