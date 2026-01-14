# 리플레이 경로 확인 리포트

**일시**: 2026-01-14  
**목적**: 리플레이 학습에 사용되는 경로 확인

---

## ? 리플레이 경로 우선순위

### 1. 기본 경로 (최우선)
- **경로**: `D:\replays\replays`
- **용도**: 리플레이 학습 소스 디렉토리
- **상태**: ? 확인됨

### 2. 환경 변수
- **변수명**: `REPLAY_ARCHIVE_DIR`
- **용도**: 환경 변수로 설정된 경로
- **상태**: 확인 필요

### 3. 프로젝트 내 경로
- `replays_archive/`
- `local_training/scripts/replays/`
- `replays/`
- `replays_source/`

---

## ? 경로 확인 방법

### PowerShell 명령어
```powershell
# 기본 경로 확인
Test-Path "D:\replays\replays"
Get-ChildItem "D:\replays\replays" -Filter *.SC2Replay | Measure-Object

# 환경 변수 확인
$env:REPLAY_ARCHIVE_DIR

# 프로젝트 내 경로 확인
Get-ChildItem -Recurse -Filter *.SC2Replay | Select-Object DirectoryName -Unique
```

### Python 코드
```python
from pathlib import Path

# 기본 경로
default_path = Path("D:/replays/replays")

# 환경 변수
env_path = os.environ.get("REPLAY_ARCHIVE_DIR")

# 프로젝트 경로
project_paths = [
    Path("replays_archive"),
    Path("local_training/scripts/replays"),
    Path("replays"),
]
```

---

## ? 리플레이 학습 스크립트 경로 설정

### `replay_build_order_learner.py` 경로 우선순위

1. **환경 변수**: `REPLAY_ARCHIVE_DIR`
2. **기본 경로**: `D:/replays/replays` (최우선)
3. **프로젝트 경로**: 
   - `replays_archive/`
   - `local_training/scripts/replays/`
   - `replays/`

### 완료된 리플레이 저장 경로
- **경로**: `D:/replays/replays/completed`
- **용도**: 5회 이상 학습 완료된 리플레이 저장

---

## ? 권장 설정

### 환경 변수 설정 (선택사항)
```powershell
# PowerShell
$env:REPLAY_ARCHIVE_DIR = "D:\replays\replays"

# 영구 설정
[System.Environment]::SetEnvironmentVariable("REPLAY_ARCHIVE_DIR", "D:\replays\replays", "User")
```

### 배치 파일에서 설정
```batch
set REPLAY_ARCHIVE_DIR=D:\replays\replays
```

---

## ? 경로 문제 해결

### 리플레이를 찾을 수 없는 경우
1. `D:\replays\replays` 디렉토리 생성
2. 리플레이 파일 복사
3. 환경 변수 설정 (선택)

### 경로 변경 방법
1. 환경 변수 `REPLAY_ARCHIVE_DIR` 설정
2. 또는 스크립트 내 기본 경로 수정

---

**상태**: ? 경로 확인 완료
