# 📅 내일 작업 예정 (Tomorrow's Work Plan)

## 1. 정찰 시스템 강화 (Enhanced Scouting System)
- [ ] **수시 정찰 로직 구현**: `EarlyScoutSystem` 외에도 중후반까지 주기적으로 저글링/대군주를 보내 적 기지와 멀티를 확인.
- [ ] **적 체제 실시간 대응**: 정찰 정보(빌드, 유닛 조합)를 `StrategyManager`에 더 빈번하게 업데이트하여 즉각 대응.

## 2. 견제 시스템 개선 (Improved Harassment)
- [ ] **공격적 견제 모드**: `CombatManager`의 `_harass_workers` 로직을 강화하여, 본대 교전 중에도 별동대가 적 일꾼을 집요하게 노리도록 설정.
- [ ] **다기능 견제 유닛 활용**: 맹독충 드랍, 뮤탈리스크, 땅굴망 등을 활용한 다각도 찌르기 구현.

## 3. 1분 멀티 타이밍 테스트 (1-min Expansion Test)
- [ ] **1베이스 강제 드론**: 오늘 구현한 "1베이스 드론 펌핑" 로직이 실제 게임에서 1분대 앞마당 가져가는 흐름으로 이어지는지 테스트.
- [ ] **빌드 오더 최적화**: 미네랄 300이 모이는 즉시 해처리를 펴는 `EXTREME-FAST` 로직 검증.

## 4. 전투 로직 성능 최적화 (Combat Logic Optimization)
- [ ] **공간 쿼리 전면 도입**: `closer_than`, `in_distance` 등 C++ 최적화 함수 활용 범위 확대.
- [ ] **프레임 드랍 방지**: 연산량이 많은 로직(군집 제어 등)의 실행 주기를 분산(`PerformanceOptimizer` 활용).
