# ? AI Arena 제출 빠른 가이드

## ? 로컬 환경 vs 아레나 환경 - 명확한 분리!

### ? 로컬 훈련 환경
```bash
# 여러 게임 돌려서 학습
python parallel_train_integrated.py

# 단일 게임 테스트
python main_integrated.py
```

**로컬 전용 파일** (절대 아레나에 제출하지 마세요):
- `parallel_train_integrated.py` - 병렬 훈련 관리자
- `main_integrated.py` - 단일 훈련 루프
- `upload_to_aiarena.py` - 업로드 도구
- `arena_update.py` - 업데이트 스크립트
- `training_data/` - 훈련 통계 및 리플레이
- `__pycache__/` - 파이썬 캐시

---

### ? AI Arena 제출 환경
```bash
# 제출용 ZIP 생성 (자동 필터링 + 검증)
python package_for_aiarena.py

# 출력: deployment/WickedZerg_AIArena_YYYYMMDD_HHMMSS.zip
```

**아레나에 포함되는 파일**:
- ? `run.py` (아레나 전용 엔트리 포인트, `Bot` 클래스)
- ? `wicked_zerg_bot_pro.py` (봇 메인 로직 + **모델 자동 로드**)
- ? `zerg_net.py` (신경망 정의)
- ? `config.py` (설정)
- ? 모든 매니저 파일 (combat, economy, production 등)
- ? `models/zerg_net_model.pt` (최신 학습 모델, **자동 로드됨**)
- ? `requirements.txt` (의존성)

**자동으로 제외되는 파일**:
- ? 훈련 스크립트 (parallel_train, main_integrated 등)
- ? 업로드 도구 (upload_to_aiarena.py)
- ? 패키징 도구 자체 (package_for_aiarena.py)
- ? 캐시 파일 (__pycache__, *.pyc)
- ? 백업 파일 (*.backup, *.pt.backup)
- ? 훈련 데이터 (training_data/, replays/, logs/)
- ? 문서 파일 (README.md, AI_ARENA_DEPLOYMENT.md)

---

## ? 패키징 프로세스

### 1단계: 패키징 실행
```bash
python package_for_aiarena.py
```

### 2단계: 자동 검증 확인
패키징 스크립트가 자동으로 검증합니다:
```
? 패키지 내용 검증 중...
   필수 파일 확인:
      ? run.py
      ? wicked_zerg_bot_pro.py
      ? config.py
      ? zerg_net.py
      ? models/zerg_net_model.pt
   
   불필요한 파일 검사:
      ? 깨끗한 패키지 (불필요한 파일 없음)
   
   ? 패키지 통계:
      전체 파일: 20개
      Python 파일: 19개
      모델 파일: 1개
```

### 3단계: 용량 확인
```
? ZIP 생성 완료:
   파일명: WickedZerg_AIArena_20260112_153045.zip
   크기: 5.23 MB  ← AI Arena 권장 (50MB 이하)
```

?? 만약 50MB 이상이면 경고가 표시됩니다!

---

## ? 업로드

1. **ZIP 파일 위치**: `deployment/WickedZerg_AIArena_YYYYMMDD_HHMMSS.zip`
2. **AI Arena**: https://aiarena.net
3. **Upload Bot** 메뉴에서 ZIP 업로드
4. **첫 대전 결과** 모니터링

---

## ?? 흔한 실수들

### ? 실수 1: 현재 폴더를 그대로 압축
```bash
# 절대 이렇게 하지 마세요!
zip -r my_bot.zip .
```
→ 훈련 데이터, 캐시, 불필요한 스크립트가 모두 포함됨!

### ? 올바른 방법
```bash
# 반드시 패키징 스크립트 사용
python package_for_aiarena.py
```
→ 필요한 파일만 자동 선별 + 검증!

---

### ? 실수 2: run.py로 로컬 테스트
```bash
# 이건 안 됩니다!
python run.py
```
→ `run.py`는 아레나 서버 전용입니다!

### ? 올바른 방법
```bash
# 로컬 테스트는 main_integrated.py
python main_integrated.py
```

---

### ? 실수 3: 수동으로 파일 추가/제거
→ `ESSENTIAL_FILES` 목록이 이미 최적화되어 있습니다!

### ? 올바른 방법
→ 패키징 스크립트를 신뢰하고 그대로 사용하세요!

---

## ? 문제 발생 시

### ZIP 내용 확인
```bash
# Windows
tar -tf WickedZerg_AIArena_YYYYMMDD_HHMMSS.zip

# 또는 압축 프로그램으로 열어서 확인
```

### 필수 파일 체크리스트
- [ ] run.py 있음 (Bot 클래스, Computer 상대 없음)
- [ ] wicked_zerg_bot_pro.py 있음
- [ ] config.py 있음
- [ ] zerg_net.py 있음
- [ ] models/zerg_net_model.pt 있음 (학습된 가중치)
- [ ] 훈련 스크립트 없음 (parallel_train, main_integrated)
- [ ] 캐시 파일 없음 (__pycache__)

### 모델 로딩 확인
패키징 후 첫 대전에서 로그 확인:
```
[OK] Neural network initialized
[OK] ? Loaded trained model: zerg_net_model.pt  ← 이 메시지 필수!
     Model path: /arena/workspace/models/zerg_net_model.pt
```

?? 만약 "No trained model found" 메시지가 나오면:
- models/ 폴더에 zerg_net_model.pt가 있는지 확인
- 패키징 스크립트 실행 시 "모델 포함" 메시지 확인

---

## ? 지원

문제가 발생하면:
1. 패키징 스크립트 실행 로그 확인
2. ZIP 자동 검증 결과 확인
3. [FIXES_APPLIED.md](FIXES_APPLIED.md) 전체 문서 참조

---

## ? 성공을 기원합니다!

**준비 완료 체크리스트**:
- [x] 로컬 환경과 아레나 환경 분리 이해
- [x] `package_for_aiarena.py`로 ZIP 생성
- [x] 자동 검증 통과
- [x] 용량 50MB 이하 확인
- [x] AI Arena에 업로드

**이제 진짜 대전을 즐기세요! ?**
