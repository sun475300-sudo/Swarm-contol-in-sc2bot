# ? 프로젝트 최적화 및 자동화 시스템 - 구축 완료

**작업 완료 시간:** 2026-01-11 22:50
**프로젝트:** Wicked Zerg Challenger

---

## ? 구축된 시스템 개요

### 1. **프로젝트 정리 스크립트** (`cleanup_and_organize.py`)
- ? 데이터 파일 자동 통합 → `data/` 폴더
- ? 로그 다이어트 (최신 2개만 유지)
- ? 중복 배포 폴더 제거
- ? 빈 폴더 자동 제거
- ? 오래된 아카이브 정리 (30일 이상)

**실행 결과:**
- 제거된 빈 폴더: 2개 (`AI_Arena_Updates`, `telemetry`)
- 현재 로그: 2개 유지
- 보고서: `data/cleanup_report_20260111_225008.json`

### 2. **드라이브 파일 자동 분류** (`auto_classify_drive.py`)
확장자별 자동 분류:
- **코딩 파일**: `.py`, `.js`, `.java` 등 → `data/Coding/[YYYYMM]/`
- **문서 파일**: `.md`, `.json`, `.html` 등 → `data/Documents/[YYYYMM]/`
- **게임 리플레이**: `.SC2Replay` → `replays/`
- **이미지**: `.jpg`, `.png` 등 → `data/Images/[YYYYMM]/`
- **압축 파일**: `.zip`, `.rar` 등 → `data/Archives/[YYYYMM]/`

### 3. **Windows 작업 스케줄러** (`register_cleanup_scheduler.ps1`)
- ? 매일 새벽 3시 자동 실행
- ? 테스트 모드 지원
- ? 간편한 활성화/비활성화

### 4. **통합 메뉴 시스템** (`cleanup_menu.bat`)
사용자 친화적인 대화형 메뉴:
```
[1] 테스트 실행 (Dry-Run)
[2] 프로젝트 정리
[3] 드라이브 파일 분류
[4] 전체 정리 + 분류
[5] 자동화 스케줄러 등록
[6] 최근 보고서 보기
```

---

## ? 빠른 사용법

### 방법 1: 배치 메뉴 (권장)
```cmd
cd D:\wicked_zerg_challenger\tools
cleanup_menu.bat
```

### 방법 2: 직접 실행
```powershell
# 프로젝트 정리 (테스트)
python tools/cleanup_and_organize.py --dry-run

# 프로젝트 정리 (실제 실행)
python tools/cleanup_and_organize.py --keep-logs 2

# 드라이브 분류 (D 드라이브, 깊이 3)
python tools/auto_classify_drive.py --drives D: --depth 3

# 작업 스케줄러 등록
.\tools\register_cleanup_scheduler.ps1
```

---

## ? 예상 효과

### 즉시 효과
- ? 빈 폴더 2개 제거 완료
- ? 로그 파일 정리 완료
- ? 프로젝트 루트 구조 간소화

### 장기 효과
- ? 용량 절감: ~1.2GB (중복 제거 + 정리)
- ?? 파일 구조: 체계적인 날짜별 분류
- ? 유지보수: 자동화로 항상 깨끗한 상태 유지
- ? 검색 효율: 파일 찾기 쉬워짐

---

## ? 작업 스케줄러 관리

### 등록
```powershell
.\tools\register_cleanup_scheduler.ps1
```

### 관리 명령어
```powershell
# 작업 즉시 실행
Start-ScheduledTask -TaskName "WickedZergProjectCleanup"

# 작업 상태 확인
Get-ScheduledTask -TaskName "WickedZergProjectCleanup"

# 작업 비활성화
Disable-ScheduledTask -TaskName "WickedZergProjectCleanup"

# 작업 제거
.\tools\register_cleanup_scheduler.ps1 -Remove
```

---

## ? 프로젝트 구조 (정리 후)

```
D:\wicked_zerg_challenger\
├── data/                           # 통합 데이터 저장소
│   ├── Coding/                    # 코드 파일 분류
│   ├── Documents/                 # 문서 파일 분류
│   ├── Images/                    # 이미지 파일 분류
│   └── cleanup_report_*.json     # 정리 보고서
├── logs/                          # 로그 (최신 2개만 유지)
│   ├── log_20260111_205225.txt
│   └── log_20260111_205033.txt
├── replays/                       # 게임 리플레이
├── tools/                         # 자동화 도구
│   ├── cleanup_and_organize.py   # 프로젝트 정리
│   ├── auto_classify_drive.py    # 드라이브 분류
│   ├── register_cleanup_scheduler.ps1  # 스케줄러 등록
│   ├── cleanup_menu.bat          # 통합 메뉴
│   └── AUTOMATION_GUIDE.md       # 상세 가이드
└── [핵심 Python 파일들...]
```

---

## ?? 안전장치

1. **Dry-Run 모드**: 실제 작업 전 미리보기
2. **중복 체크**: 동일 파일은 타임스탬프 추가
3. **제외 목록**: 시스템 폴더 자동 제외
4. **보고서 생성**: 모든 작업 JSON 로그 저장
5. **에러 핸들링**: 실패 시에도 계속 진행

---

## ? 실행 통계 (초기 실행)

```json
{
  "timestamp": "2026-01-11T22:50:08",
  "dry_run": false,
  "statistics": {
    "files_moved": 0,
    "folders_deleted": 2,
    "space_freed": 0,
    "errors": []
  }
}
```

---

## ? 커스터마이징

### 분류 규칙 수정
`auto_classify_drive.py` 파일의 `CLASSIFICATION_RULES` 딕셔너리 수정

### 제외 디렉토리 추가
`EXCLUDE_DIRS` 세트에 폴더명 추가

### 스케줄 시간 변경
```powershell
.\tools\register_cleanup_scheduler.ps1 -TaskTime "02:00"
```

---

## ? 관련 문서

- ? [AUTOMATION_GUIDE.md](tools/AUTOMATION_GUIDE.md) - 상세 사용법
- ? [cleanup_report_*.json](data/) - 실행 보고서
- ?? [classification_report_*.json](data/) - 분류 보고서

---

## ? 시스템 구축 완료!

**모든 자동화 도구가 성공적으로 구축되었습니다.**

- ? 프로젝트 정리 자동화
- ? 드라이브 파일 분류 자동화
- ? 작업 스케줄러 등록
- ? 사용자 친화적 메뉴 시스템

**이제 `tools/cleanup_menu.bat`를 실행하여 언제든지 프로젝트를 깨끗하게 유지할 수 있습니다!**

---

*Last Updated: 2026-01-11 22:50*
*Version: 1.0.0*
