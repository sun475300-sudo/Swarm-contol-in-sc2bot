# 훈련 실행 최종 가이드

**작성 일시**: 2026년 01-13  
**목적**: 본격적인 훈련 실행을 위한 완전한 가이드  
**상태**: ✅ **훈련 실행 준비 완료**

---

## 🎯 빠른 시작 (3단계)

### 1단계: 환경 확인

```cmd
python tools\setup_verify.py
```

**확인 사항**:
- ✅ Python 버전 (3.10+)
- ✅ 필수 패키지 (torch, numpy, sc2reader)
- ✅ 리플레이 디렉토리 접근 권한
- ✅ 모델 저장 디렉토리 접근 권한

---

### 2단계: 사전 정리 (선택 사항, 권장)

```cmd
bat\fix_replay_learning.bat
```

**수행 작업**:
- Python 캐시 정리
- NumPy 버전 업그레이드
- `crash_log.json`의 `in_progress` 엔트리 정리

---

### 3단계: 훈련 실행

#### 옵션 A: 리플레이 학습만 (권장 시작점)

```cmd
bat\start_replay_learning.bat
```

**실행 내용**:
- 리플레이 분석 및 빌드 오더 추출
- 학습 횟수 카운팅 (최소 5회)
- Bad replay 자동 제외

**예상 시간**: 리플레이당 1-3분

---

#### 옵션 B: 게임 학습만

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

#### 옵션 C: 전체 파이프라인 (자동화)

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

## 📋 훈련 실행 전 체크리스트

### 필수 확인
- [ ] 리플레이 파일이 `D:\replays\replays\`에 있는지 확인
- [ ] StarCraft II가 설치되어 있고 실행 가능한지 확인
- [ ] Python 가상 환경이 활성화되어 있는지 확인
- [ ] NumPy 버전이 호환되는지 확인

### 권장 확인
- [ ] 환경 검증 스크립트 실행: `python tools\setup_verify.py`
- [ ] `crash_log.json` 정리: `bat\force_clear_crash_log.bat`
- [ ] Python 캐시 정리: `bat\fix_replay_learning.bat`

---

## 🔧 주요 개선 사항 적용 확인

### ✅ 적용 완료된 개선 사항

1. ✅ **신경망 입력 정규화 개선**
   - Self 5 + Enemy 5 스케일 차이 해결
   - 가중치 기반 정규화 적용

2. ✅ **배치 파일 경로 일관성**
   - 모든 배치 파일에 `cd /d "%~dp0.."` 추가
   - 어느 디렉토리에서 실행해도 정상 작동

3. ✅ **전술 로직 통합**
   - `rogue_tactics.update()` 호출 (8프레임마다)
   - 이병렬 선수 전술 활성화

4. ✅ **마법 유닛 타겟팅 최적화**
   - `spell_unit_manager.update()` 호출 (16프레임마다)
   - CPU 부하 감소

5. ✅ **리플레이 빌드 추출 정밀도**
   - 취소/손실 필터링 로직 추가
   - 노이즈 없는 깨끗한 학습 데이터

6. ✅ **리플레이 학습 강제 모드**
   - `is_in_progress` 체크 주석 처리
   - 모든 리플레이 강제 처리

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

## 🚨 문제 발생 시 해결 방법

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

### StarCraft II 실행 오류
- StarCraft II가 설치되어 있는지 확인
- 게임이 최신 버전인지 확인
- 관리자 권한으로 실행 시도

---

## 📁 관련 문서

- `FINAL_PRE_TRAINING_CHECKLIST.md` - 최종 점검 체크리스트
- `FINAL_CODE_REVIEW_AND_IMPROVEMENTS.md` - 코드 개선 사항 상세
- `REPLAY_LEARNING_ISSUES_RESOLVED.md` - 리플레이 학습 이슈 해결

---

## ✅ 최종 확인

모든 시스템이 훈련 실행 준비가 완료되었습니다.

**다음 단계**: `bat\start_replay_learning.bat` 실행

---

**작성일**: 2026년 01-13  
**상태**: ✅ **훈련 실행 준비 완료**
