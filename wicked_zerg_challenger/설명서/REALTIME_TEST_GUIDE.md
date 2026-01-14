# ? Phase 7 최종: 실전 게임 테스트 가이드

## ? 현재 상황

**대군주 생산 로직 리팩토링 완료** ?
- 4개의 중복 위치 → 1개의 SSOT (ProductionManager)로 통합
- 동적 버퍼 시스템 (8-16 supply) 구현
- 예측 기반 생산 및 긴급 대응 로직 완성
- 3개 bot 파일 완전 동기화

**검증 프레임워크 완성** ?
- ProductionManager 메트릭 추가
- 초반 3분 자원 효율성 추적
- 후반 인구수 버퍼 추적
- 자동 분석 스크립트 구현

---

## ? 실전 게임 테스트 시작

### 준비 단계

```bash
# 1. 텔레메트리 백업 (선택)
mkdir backup_telemetry_phase7
cp telemetry_*.json backup_telemetry_phase7/ 2>/dev/null || true
rm telemetry_*.json 2>/dev/null || true

# 2. 게임 시작
python wicked_zerg_bot_pro.py
```

---

## ? 관찰할 포인트 (초반 3~4분)

### 1?? **대군주 "미리" 생산 확인**

**시나리오**: 인구수가 거의 찬 상태 (예: 22/22, 28/28, 36/36)

**예상 결과**:
```
? "막히기 직전"에 대군주 생산 시작
   예: 24/30 상태에서 미리 대군주 주문 (버퍼 기반)
   → 26/30 → 28/30 → 30/30 (자동 도착)
   → 완벽한 타이밍 ?

? "막힌 후" 생산 (비효율적)
   예: 30/30 상태에서 대군주 주문
   → 유닛 생산 지연 발생
   → 지난 프레임 라바 낭비
```

**콘솔 로그로 확인**:
```
[OVERLORD] Predictive production: 2 overlords (supply: 8/30)
→ 예측 기반 생산 (최적) ?

[OVERLORD] Emergency production at 2 supply left
→ 긴급 생산 (허용) ??

[WARNING] Supply block risk! Need 2 overlords but can't afford
→ 자원 부족 (나쁨) ?
```

---

### 2?? **자원 절약 효과 확인**

**추적 항목**:

| 항목 | 기대값 | 확인 방법 |
|------|--------|---------|
| **180초 드론 수** | 23-25마리 | 게임 보고서 또는 콘솔 |
| **초반 라바 효율** | 높음 (낭비 없음) | 라바 최대값 vs 생산 유닛 |
| **미네랄 활용** | 적절 (50-200 보유) | 게임 중 미네랄 그래프 |
| **인구수 막힘** | 0회 | "Supply block risk" 경고 개수 |

**관찰 방법**:
```python
# 게임 종료 후 메트릭 확인
bot.production_manager.validation_metrics["early_game"]
{
    "drones_at_180s": 24,      # 드론 2마리 증가 ?
    "supply_blocks": 0,         # 인구수 막힘 없음 ?
    "efficiency_score": 85.5    # 자원 효율 우수 ?
}
```

---

### 3?? **후반 버퍼 안정성 확인 (180+ 인구수)**

**시나리오**: 후반 대규모 전투 중 병력 급속 소모

**예상 결과**:
```
? 병력이 소모되면서 인구수 떨어짐
   예: 195 → 180 → 165 → 150
   
? 대군주가 즉시 생산됨
   인구수 보유: 항상 >= 5 (안정적)
   [OVERLORD] Predictive production ...
   [OVERLORD] Emergency production ...
   
? 대군주 생산 지연
   인구수 < 2 상황 발생
   유닛 생산 불가능 상황 발생
```

**콘솔 로그로 확인**:
```python
# 게임 종료 후 메트릭 확인
bot.production_manager.validation_metrics["late_game"]
{
    "min_supply_ever": 6,      # 최소 인구수 6 (5 이상 ?)
    "supply_blocks": 0,        # 인구수 막힘 0회 (좋음 ?)
    "overlord_productions": [
        (456.0, "emergency", 3),  # 긴급 생산
        (820.0, "predictive", 6), # 예측 생산
        (1120.0, "predictive", 4) # 예측 생산
    ]
}
```

---

## ? 게임 종료 후 자동 분석

### 방법 1: 빠른 분석 (1초)

```bash
python verify_overlord_optimization.py
```

**출력 예시**:
```
? [초반 3분] 자원 절약 효과
  라바 최대: 12마리
  드론 생산: 12마리
  저글링 생산: 8마리
  효율성 점수: 85.5점 ?

? [후반] 인구수 버퍼 효율성
  평균 남은 인구수: 7.2 (안정적)
  최소 인구수: 6 (좋음)
  버퍼 효율성 점수: 82.3점 ?

? 최종 평가: 83.9/100
? 최적화가 매우 효과적입니다!
```

### 방법 2: JSON 보고서 검토

```bash
# 자동 생성된 파일 확인
ls -lrt overlord_optimization_report_*.json | tail -1

# 내용 확인
cat overlord_optimization_report_*.json | python -m json.tool
```

---

## ? 성공 기준 체크리스트

### 초반 3분 성공 기준

- [ ] 대군주가 "막히기 직전"에 생산됨 (예측 기반)
- [ ] 인구수 막힘 경고 없음 (0회)
- [ ] 180초 드론 수 >= 23마리
- [ ] 효율성 점수 >= 70점

### 후반 안정성 기준

- [ ] 최소 인구수 >= 5 유지
- [ ] 대군주 생산 >= 2회 (예측 + 긴급)
- [ ] 예측 생산 비율 >= 70%
- [ ] 버퍼 효율성 점수 >= 70점

### 종합 평가

- [ ] 초반 + 후반 모두 70점 이상
- [ ] "? PASS" 판정 또는 "? CAUTION"

---

## ? 라이브 관찰 팁

### 1. 초반 관찰 포인트 (0-180초)

```
시간대          관찰 내용              기대 결과
────────────────────────────────────────────────────
0-30s   산란못/산란못 건설 시작          정상 진행
30-60s  첫 저글링 생산                  7~8마리 정도
60-90s  대군주 유지, 드론 생산          인구수 여유있음
90-120s 전력 증강 시작                 드론 22마리 정도
120-180s 확장/업그레이드               드론 24+ 마리
```

### 2. 콘솔 로그 모니터링

```bash
# 게임 실행 중 로그에서 찾을 것
grep OVERLORD /game.log      # 대군주 생산 타이밍
grep WARNING /game.log        # 인구수 막힘 경고
```

### 3. 게임 보고서 확인

게임 종료 후:
```
telemetry_*.json
→ supply_left, larva_count, drone_count 추적
→ 자동 분석 스크립트로 변환

overlord_optimization_report_*.json
→ 효율성 점수 및 상세 분석
```

---

## ? 테스트 권장 절차

### 방법 A: 싱글 게임 (가장 빠름)

```bash
# 1. 게임 1판 실행 (약 10-15분)
python wicked_zerg_bot_pro.py

# 2. 자동 분석 (1초)
python verify_overlord_optimization.py

# 3. 결과 검토
# 성공 기준 만족 시 ?
# 실패 시 미세 조정 후 재테스트
```

### 방법 B: 배치 테스트 (정확성 높음)

```bash
# 1. 게임 5판 연속 실행 (약 1시간)
python test_overlord_optimization.py --games 5

# 2. 자동 분석 및 성공률 계산
python test_overlord_optimization.py --analyze

# 3. 종합 평가 (5판 평균)
```

---

## ? 예상 성능 개선

### 이전 (중복 로직)

```
초반 3분:
- 대군주 중복 생산: 3-5마리 (낭비)
- 라바 손실: 3-5마리
- 미네랄 손실: 150-250
- 드론 부족: 1-2마리

후반:
- 인구수 막힘 자주 발생 (3-5회/게임)
- 최소 인구수: 2-3 (불안정)
```

### 이후 (일원화 로직)

```
초반 3분:
- 대군주 예측 생산: 1-2마리 (최적)
- 라바 절약: 1-2마리
- 미네랄 절약: 100-200
- 드론 추가: +1-2마리

후반:
- 인구수 막힘: 0-1회/게임 (안정적)
- 최소 인구수: 5-8 (안정적)
```

---

## ? 문제 발생 시 빠른 해결

### 초반에 자주 인구수 막힘

**증상**:
```
[WARNING] Supply block risk! Need overlords but can't afford
→ 3회 이상 발생
```

**원인**: 초반 미네랄 소비가 많아 대군주 생산 불가능

**해결**:
```python
# production_manager.py line 500
aggressive_flush_threshold = 600  # 증가: 500 → 600
```

### 후반에 자주 인구수 막힘

**증상**:
```
min_supply_ever < 3 (불안정)
```

**원인**: 예측 버퍼가 충분하지 않음

**해결**:
```python
# production_manager.py line 670
if game_time < 600:
    supply_buffer = 14  # 증가: 12 → 14
```

### 대군주가 너무 많이 생산

**증상**:
```
overlord_productions 항목이 5개 이상
```

**원인**: 버퍼 값이 너무 높음

**해결**:
```python
# production_manager.py line 670
if game_time < 600:
    supply_buffer = 10  # 감소: 12 → 10
```

---

## ? 최종 체크리스트

### 테스트 전

- [ ] telemetry_*.json 파일 백업 (또는 삭제)
- [ ] 게임 실행 환경 확인
- [ ] ProductionManager 메트릭 추가 확인 (3개 파일)
- [ ] 검증 스크립트 준비 확인

### 테스트 중

- [ ] 초반 3~4분 대군주 타이밍 관찰
- [ ] 콘솔 로그 확인 (OVERLORD, WARNING)
- [ ] 인구수 그래프 모니터링

### 테스트 후

- [ ] telemetry_*.json 생성 확인
- [ ] verify_overlord_optimization.py 실행
- [ ] 성공 기준 평가
- [ ] 필요시 미세 조정

### 최종 결과

- [ ] 초반 효율성 >= 70점
- [ ] 후반 효율성 >= 70점
- [ ] 종합 평가 >= 70점
- [ ] ? PASS 또는 ? CAUTION

---

## ? 다음 단계

### 검증 완료 후

1. **현재**: 실전 게임 테스트 진행 ← **지금 여기**
2. **완료**: 검증 보고서 분석
3. **조정**: 필요시 미세 조정 (버퍼 값)
4. **마무리**: Phase 8 진입 (최적화 완료)

### Phase 8: 최종 최적화 및 배포

- 3개 bot 파일 배포
- AI Arena 제출
- 최종 성능 모니터링

---

## ? 검증 완료 확인

**성공 신호**:
```
? PASS: 초반 0회 막힘, 후반 최소 5+, 점수 70+
→ 최적화 완전 성공 ?
```

**주의 신호**:
```
? CAUTION: 초반 1-2회 막힘, 후반 최소 3-4
→ 미세 조정 후 재테스트 필요
```

**실패 신호**:
```
? FAIL: 초반 3회 이상 막힘, 후반 최소 < 3
→ 로직 재검토 필요 (문제 없어야 함)
```

---

## ? 즉시 시작

```bash
# 1. 게임 실행
python wicked_zerg_bot_pro.py

# 2. 초반 3~4분 동안 대군주 타이밍 관찰
#    "막히기 직전"에 생산되는지 확인

# 3. 게임 종료 후
python verify_overlord_optimization.py

# 4. 결과 확인
#    초반/후반 모두 70점 이상이면 성공! ?
```

---

**이제 준비가 모두 완료되었습니다!** ?
게임을 실행하여 대군주 생산 로직 일원화의 실제 효과를 직접 확인해보세요.

대군주가 **정확한 타이밍**에 **매끄럽게** 생산되는 모습을 보실 수 있을 겁니다. ?

