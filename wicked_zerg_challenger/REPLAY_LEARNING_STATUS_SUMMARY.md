# 리플레이 학습 상태 요약

**생성일**: 2026-01-14  
**마지막 업데이트**: 2026-01-14 16:37:18

---

## ? 학습 진행 상황

### 전체 통계
- **총 리플레이 수**: 207개
- **처리된 리플레이**: ~100개 (학습 추적 중)
- **완료된 리플레이**: 24개 (5회 반복 완료)
- **진행 중인 리플레이**: ~76개

### 반복 횟수별 분포
- **5회 완료**: 24개 리플레이 ?
- **4회 반복**: 4개 리플레이
- **3회 반복**: 4개 리플레이
- **2회 반복**: ~50개 리플레이
- **1회 반복**: ~6개 리플레이

---

## ? 파일 위치

### 학습 추적 파일
- **`.learning_tracking.json`**: `D:\replays\replays\.learning_tracking.json`
  - 각 리플레이의 학습 횟수, 완료 상태, 마지막 학습 시간 추적
  - 상태: ? 정상 작동

### 학습 로그
- **`learning_log.txt`**: `D:\replays\replays\learning_log.txt`
  - 각 리플레이의 학습 완료 로그 (반복 횟수, 단계, 추출된 전략 등)
  - 상태: ? 정상 작동

### 학습 상태 파일
- **`learning_status.json`**: `D:\replays\replays\learning_status.json`
  - 하드 요구사항: 각 리플레이당 최소 5회 반복
  - 상태: ?? 비어있음 (업데이트 필요)

### 완료된 리플레이
- **`completed/`**: `D:\replays\replays\completed\`
  - 5회 반복 완료된 리플레이가 자동으로 이동
  - 현재: 24개 리플레이

---

## ? 완료된 리플레이 (5회 반복)

1. 20240208 - GAME 1 - Scarlett vs Spirit - ZvT - Alcyone.SC2Replay
2. 20240208 - GAME 1 - Serral vs Firefly - ZvP - Oceanborn.SC2Replay
3. 20240208 - GAME 1 - Serral vs Kelazhur - ZvT - Oceanborn.SC2Replay
4. 20240208 - GAME 2 - Dark vs herO - ZvP - Hard Lead.SC2Replay
5. 20240208 - GAME 2 - Dark vs ShoWTimE - ZvP - Oceanborn.SC2Replay
6. 20240208 - GAME 2 - Scarlett vs Spirit - ZvT - Solaris.SC2Replay
7. 20240208 - GAME 2 - Serral vs Kelazhur - ZvT - Alcyone.SC2Replay
8. 20240208 - GAME 2 - Solar vs Scarlett - ZvZ - Oceanborn.SC2Replay
9. 20240208 - GAME 3 - Dark vs ShoWTimE - ZvP - Site Delta.SC2Replay
10. 20240208 - GAME 3 - Scarlett - Spirit - ZvT - Site Delta.SC2Replay
11. 20240209 - GAME 1 - Dark vs Cyan - ZvP - Oceanborn.SC2Replay
12. 20240209 - GAME 1 - Dark vs Reynor - ZvZ - Hard Lead.SC2Replay
13. 20240209 - GAME 1 - Reynor vs herO - ZvP - Hard Lead.SC2Replay
14. 20240209 - GAME 1 - Scarlett vs trigger - ZvP - Site Delta.SC2Replay
15. 20240209 - GAME 1 - Serral vs Astrea - ZvP - Site Delta.SC2Replay
16. 20240209 - GAME 1 - Serral vs SKillous - ZvP - Solaris.SC2Replay
17. 20240209 - GAME 1 - SHIN vs Stats - ZvP - Hard Lead.SC2Replay
18. 20240209 - GAME 2 - Dark vs Reynor - ZvZ - Site Delta.SC2Replay
19. 20240209 - GAME 2 - Scarlett vs trigger - ZvP - Alcyone.SC2Replay
20. 20240209 - GAME 2 - Serral vs Astrea - ZvP - Oceanborn.SC2Replay
21. 20240209 - GAME 2 - Serral vs SKillous - ZvP - Site Delta.SC2Replay
22. 20240209 - GAME 2 - SHIN vs Stats - ZvP - Alcyone.SC2Replay
23. 20240209 - GAME 3 - Dark vs Reynor - ZvZ - Hecate.SC2Replay
24. 20240210 - GAME 1 - Dark vs Maru - ZvT - Alcyone.SC2Replay

---

## ? 학습 단계별 진행

### Phase 1-2 (Early Game)
- 빌드오더 집중 학습
- 대부분의 리플레이가 이 단계에서 시작

### Phase 3-4 (Mid Game)
- 유닛 조합, 소규모 교전 학습
- 많은 리플레이가 현재 이 단계 진행 중

### Phase 5+ (Late Game)
- 매크로, 스펠 유닛 학습
- 완료된 리플레이들이 이 단계까지 완료

---

## ? 학습된 파라미터

- **`hive_supply`**: 12 (42 샘플)
- **`lair_supply`**: 12 (35 샘플)

---

## ?? 알려진 이슈

1. **`learning_status.json` 비어있음**
   - `LearningStatusManager`가 제대로 업데이트하지 않음
   - `.learning_tracking.json`은 정상 작동 중
   - 영향: 하드 요구사항 추적에 문제 없음 (`.learning_tracking.json` 사용)

2. **일부 건물 타입 추출 안 됨**
   - SpawningPool, RoachWarren, Extractor 등
   - 원인: 리플레이에 해당 건물이 없거나 건물 이름 매핑 문제

---

## ? 다음 단계

1. **학습 계속 진행**: 나머지 리플레이들이 5회 반복 완료될 때까지 대기
2. **`learning_status.json` 업데이트**: `LearningStatusManager` 수정 필요
3. **추가 건물 타입 추출**: 건물 이름 매핑 확인 및 수정

---

**상태**: ? **리플레이 학습 정상 진행 중**
