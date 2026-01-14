# ?? 프로젝트 최적화 및 자동화 시스템

## ? 구성 요소

### 1. **cleanup_and_organize.py**
프로젝트 내부 정리 스크립트
- ? 데이터 파일 data/ 폴더로 통합
- ? 로그 다이어트 (최신 N개만 유지)
- ? 중복 배포 폴더 제거
- ? 빈 폴더 자동 제거
- ? 오래된 아카이브 정리

### 2. **auto_classify_drive.py**
드라이브 전체 파일 자동 분류
- ? 코딩 파일: `.py`, `.js`, `.java` 등 → `data/Coding/[날짜]/`
- ? 문서 파일: `.md`, `.json`, `.html` 등 → `data/Documents/[날짜]/`
- ? 게임 리플레이: `.SC2Replay` → `replays/`
- ? 이미지, 압축 파일 등

### 3. **register_cleanup_scheduler.ps1**
Windows 작업 스케줄러 자동 등록
- ? 매일 지정 시간 자동 실행
- ? 테스트 모드 지원
- ? 쉬운 활성화/비활성화

---

## ? 빠른 시작

### 단계 1: 테스트 실행 (DRY-RUN)

실제로 파일을 이동하지 않고 미리 확인:

```powershell
# 프로젝트 정리 테스트
python tools/cleanup_and_organize.py --dry-run

# 드라이브 분류 테스트 (D 드라이브만, 깊이 2)
python tools/auto_classify_drive.py --drives D: --depth 2 --dry-run
```

### 단계 2: 실제 실행

테스트 결과가 만족스러우면 실행:

```powershell
# 프로젝트 정리 (로그 2개 유지)
python tools/cleanup_and_organize.py --keep-logs 2

# 드라이브 분류 (D 드라이브만)
python tools/auto_classify_drive.py --drives D: --depth 3
```

### 단계 3: 자동화 설정

매일 새벽 3시에 자동 실행되도록 설정:

```powershell
# 작업 스케줄러 등록 (관리자 권한 필요)
.\tools\register_cleanup_scheduler.ps1

# 다른 시간으로 설정 (예: 오전 2시)
.\tools\register_cleanup_scheduler.ps1 -TaskTime "02:00"

# 테스트 실행
.\tools\register_cleanup_scheduler.ps1 -Test

# 작업 제거
.\tools\register_cleanup_scheduler.ps1 -Remove
```

---

## ? 예상 효과

### 용량 절감
- 중복 폴더 제거: ~500MB
- 오래된 로그: ~300MB
- 중복 파일 정리: ~400MB
- **총 예상: ~1.2GB**

### 구조 개선
- 루트 디렉토리: 핵심 파일만 유지
- 데이터 파일: `data/` 폴더로 통합
- 로그: 최신 2개만 유지하여 가독성 향상

### 유지보수성
- 정기적 자동 정리로 클린한 상태 유지
- 파일 찾기 쉬워짐
- 백업 및 버전 관리 간편화

---

## ? 주요 옵션

### cleanup_and_organize.py
```bash
--dry-run          # 미리보기만 (실제 작업 X)
--keep-logs N      # 유지할 로그 파일 개수 (기본: 2)
```

### auto_classify_drive.py
```bash
--drives C: D:     # 스캔할 드라이브 지정
--depth N          # 스캔 깊이 (기본: 3)
--dry-run          # 미리보기만
--target PATH      # 분류 대상 기본 경로
```

### register_cleanup_scheduler.ps1
```powershell
-TaskName NAME     # 작업 이름 (기본: WickedZergProjectCleanup)
-TaskTime "HH:MM"  # 실행 시간 (기본: 03:00)
-Test              # 테스트 실행 (dry-run)
-Remove            # 작업 제거
```

---

## ? 작업 스케줄러 관리

```powershell
# 작업 상태 확인
Get-ScheduledTask -TaskName "WickedZergProjectCleanup"

# 작업 즉시 실행
Start-ScheduledTask -TaskName "WickedZergProjectCleanup"

# 작업 비활성화
Disable-ScheduledTask -TaskName "WickedZergProjectCleanup"

# 작업 활성화
Enable-ScheduledTask -TaskName "WickedZergProjectCleanup"

# 마지막 실행 결과 확인
Get-ScheduledTaskInfo -TaskName "WickedZergProjectCleanup"
```

---

## ?? 주의사항

1. **첫 실행 전 백업 권장**
   - 중요한 파일은 사전에 백업해두세요

2. **dry-run으로 먼저 테스트**
   - 실제 실행 전 `--dry-run` 옵션으로 확인

3. **드라이브 스캔 깊이 조절**
   - 시스템 폴더는 자동 제외되지만, 깊이를 너무 크게 하면 시간이 오래 걸림

4. **관리자 권한**
   - 작업 스케줄러 등록 시 관리자 권한 필요

---

## ? 실행 보고서

스크립트 실행 후 `data/` 폴더에 JSON 보고서가 생성됩니다:

```
data/
├── cleanup_report_20260111_220000.json
└── classification_report_20260111_220500.json
```

---

## ? 문제 해결

### Python을 찾을 수 없음
```powershell
# Python 경로 확인
where python

# 가상환경이 있다면 활성화
.\.venv\Scripts\Activate.ps1
```

### 권한 오류
```powershell
# 관리자 권한으로 PowerShell 실행
Start-Process powershell -Verb RunAs
```

### 작업 스케줄러 오류
- Windows 작업 스케줄러 (taskschd.msc)에서 직접 확인
- 로그 파일: `logs/scheduled_cleanup.log`

---

## ? 지원

- 스크립트 오류: `data/cleanup_report_*.json` 파일 확인
- 분류 규칙 커스터마이징: `auto_classify_drive.py`의 `CLASSIFICATION_RULES` 수정
- 제외 디렉토리 추가: `EXCLUDE_DIRS` 설정 수정
