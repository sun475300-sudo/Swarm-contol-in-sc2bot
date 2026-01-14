# 🚀 훈련 실행 시작 가이드

**작성 일시**: 2026년 01-13  
**상태**: ✅ **모든 시스템 점검 완료 - 훈련 실행 준비 완료**

---

## ✅ 최종 점검 완료

모든 파일이 최종 점검을 통과했습니다:

1. ✅ 신경망 입력 정규화 개선 (Self 5 + Enemy 5 스케일 차이 해결)
2. ✅ 배치 파일 경로 일관성 (모든 .bat 파일에 `cd /d "%~dp0.."` 추가)
3. ✅ 전술 로직 통합 (`rogue_tactics.update()` 호출)
4. ✅ 마법 유닛 타겟팅 최적화 (`spell_unit_manager.update()` 호출)
5. ✅ 리플레이 빌드 추출 정밀도 (취소/손실 필터링)
6. ✅ 리플레이 학습 강제 모드 (`is_in_progress` 체크 주석 처리)

---

## 🎯 훈련 실행 방법

### 방법 1: 리플레이 학습만 (권장 시작점) ⭐

```cmd
bat\start_replay_learning.bat
```

**실행 내용**:
- 리플레이 분석 및 빌드 오더 추출
- 학습 횟수 카운팅 (최소 5회)
- Bad replay 자동 제외
- 학습 완료 후 `completed/` 폴더로 이동

**예상 시간**: 리플레이당 1-3분

---

### 방법 2: 게임 학습만

```cmd
bat\start_game_training.bat
```

**실행 내용**:
- StarCraft II 게임 실행
- 15차원 상태 벡터 수집 (Self 5 + Enemy 10)
- 신경망으로 행동 선택
- REINFORCE 알고리즘으로 학습

**예상 시간**: 게임당 5-20분

---

### 방법 3: 전체 파이프라인 (자동화)

```cmd
bat\start_full_training.bat
```

**실행 순서**:
1. 리플레이 추출
2. 리플레이 학습
3. 게임 학습
4. 정리 및 아카이브

**예상 시간**: 전체 프로세스 1-3시간

---

## ⚠️ 실행 전 확인 (선택 사항, 권장)

### 환경 검증
```cmd
python tools\setup_verify.py
```

### 사전 정리 (문제 발생 시)
```cmd
bat\fix_replay_learning.bat
```

---

## 📊 예상 실행 결과

### 리플레이 학습
- **처리 속도**: 리플레이당 약 1-3분
- **학습 횟수**: 리플레이당 최소 5회
- **출력 위치**: `D:\replays\archive\training_YYYYMMDD_HHMMSS\`
- **완료 위치**: `D:\replays\replays\completed\`

### 게임 학습
- **게임 시간**: 게임당 약 5-20분
- **학습 데이터**: `local_training/models/zerg_net_model.pt`
- **로그 파일**: `logs/training_log.txt`

---

## 🔧 문제 발생 시 해결 방법

### "Already being learned" 메시지
```cmd
bat\force_clear_crash_log.bat
bat\start_replay_learning.bat
```

### NumPy 버전 오류
```cmd
bat\fix_numpy.bat
```

### 권한 오류
```cmd
python tools\setup_verify.py
```

---

## ✅ 훈련 실행 준비 완료

모든 시스템이 훈련 실행 준비가 완료되었습니다.

**다음 단계**: `bat\start_replay_learning.bat` 실행

---

**작성일**: 2026년 01-13  
**상태**: ✅ **훈련 실행 준비 완료**
