# 게임 훈련 시작 상태 리포트

**일시**: 2026-01-14  
**상태**: ? **훈련 시작됨**

---

## ? 사전 검사 완료

### 1. StarCraft II 설치 확인
- ? **설치 경로**: `C:\Program Files (x86)\StarCraft II`
- ? **환경 변수**: SC2PATH 설정됨

### 2. Python 패키지 확인
- ? `sc2` - 설치됨
- ? `numpy` - 설치됨
- ? `loguru` - 설치됨
- ?? `torch` - 없음 (선택 사항, CPU 모드로 실행 가능)

### 3. 프로세스 상태
- ? **SC2 프로세스**: 실행 중이 아님 (정상)
- ? **훈련 시작**: 백그라운드로 실행됨

---

## ? 훈련 실행 방법

### 방법 1: 배치 파일 사용
```batch
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\start_game_training.bat
```

### 방법 2: 직접 Python 실행
```bash
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training
python main_integrated.py
```

---

## ? 훈련 모니터링

### 로그 파일 위치
- **훈련 로그**: `local_training/logs/training_log.log`
- **크래시 리포트**: `local_training/crash_report.txt`

### 프로세스 확인 명령어
```powershell
# Python 프로세스 확인
Get-Process python*

# SC2 프로세스 확인
Get-Process | Where-Object { $_.ProcessName -like '*SC2*' }
```

### 로그 확인 명령어
```powershell
# 최신 로그 확인
Get-Content local_training\logs\training_log.log -Tail 50 -Encoding UTF8
```

---

## ?? 훈련 설정

### 기본 설정
- **모드**: 단일 게임 모드 (Single Game Mode)
- **상태 벡터**: 15차원 (Self 5 + Enemy 10)
- **Rogue Tactics**: 활성화됨 (Baneling drops, Larva saving)
- **적대 난이도**: Very Hard

### 재시작 설정
- **최대 연속 실패**: 5회
- **연결 오류 처리**: 자동 재시도
- **GPU 캐시 정리**: 자동

---

## ? 주의사항

1. **SC2 클라이언트**: 훈련 시작 전 SC2가 실행 중이 아니어야 함
2. **메모리**: 충분한 메모리 확보 (최소 4GB 권장)
3. **디스크 공간**: 로그 및 리플레이 저장 공간 확인
4. **CPU/GPU 온도**: 장시간 훈련 시 온도 모니터링 권장

---

## ? 문제 해결

### 훈련이 시작되지 않는 경우
1. SC2PATH 환경 변수 확인
2. Python 패키지 설치 확인: `pip install -r requirements.txt`
3. 로그 파일 확인: `logs/training_log.log`

### 연결 오류 발생 시
- 자동으로 재시도됨 (최대 5회)
- 연속 실패 시 훈련 중단 및 크래시 리포트 생성

### 프로세스 종료 방법
```powershell
# Python 프로세스 종료
Stop-Process -Name python -Force

# SC2 프로세스 종료
Stop-Process -Name SC2_x64 -Force
```

---

**상태**: ? **훈련 실행 중**
