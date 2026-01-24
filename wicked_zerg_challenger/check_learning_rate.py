# -*- coding: utf-8 -*-
"""
현재 학습률 확인 스크립트
"""

from pathlib import Path
import json
import sys
import io

# UTF-8 출력 설정 (Windows 콘솔 인코딩 문제 해결)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 1. Adaptive Learning Rate 확인
adaptive_lr_path = Path("local_training/adaptive_lr_stats.json")

print("=" * 60)
print("현재 학습률 상태 확인")
print("=" * 60)

if adaptive_lr_path.exists():
    print("\n[ADAPTIVE_LR] 적응형 학습률 통계 로드됨")
    with open(adaptive_lr_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"\n[OK] 현재 학습률: {data['learning_rate']:.6f}")
    print(f"[OK] 최적 학습률: {data['best_learning_rate']:.6f}")
    print(f"[OK] 최고 승률: {data['best_win_rate']:.2%}")
    print(f"[OK] 총 게임 수: {data['total_games']}")
    print(f"[OK] 총 승리 수: {data['total_wins']}")
    if data['total_games'] > 0:
        print(f"[OK] 전체 승률: {data['total_wins']/data['total_games']:.2%}")
    else:
        print(f"[OK] 전체 승률: 0.00%")
    print(f"[OK] 개선 없음: {data['games_without_improvement']}/10게임")

    if data.get('adjustment_history'):
        print(f"\n[HISTORY] 조정 이력 ({len(data['adjustment_history'])}회):")
        for adj in data['adjustment_history'][-5:]:
            action_mark = "[UP]" if adj["action"] == "increase" else "[DOWN]" if adj["action"] == "decrease" else "[RESET]"
            print(f"  {action_mark} Game {adj['game']}: {adj['old_lr']:.6f} -> {adj['new_lr']:.6f} ({adj['action']})")
else:
    print("\n[INFO] 적응형 학습률 통계 없음 (아직 게임 실행 안 함)")
    print(f"\n[INIT] 초기 설정값:")
    print(f"  - 초기 학습률: 0.001000")
    print(f"  - 최소 학습률: 0.000100")
    print(f"  - 최대 학습률: 0.010000")
    print(f"  - 조정 배율: 1.2 (±20%)")
    print(f"  - Patience: 10게임")

# 2. RL Agent 모델 확인
model_path = Path("local_training/models/rl_agent_model.npz")

print("\n" + "=" * 60)
print("RL Agent 모델 상태")
print("=" * 60)

if model_path.exists():
    import numpy as np
    data = np.load(str(model_path))

    print(f"\n[OK] 모델 파일 존재: {model_path}")
    print(f"[OK] 에피소드 수: {int(data['episode_count'][0])}")
    print(f"[OK] 베이스라인: {float(data['baseline'][0]):.4f}")
    print(f"\n[MODEL] 모델 파라미터:")
    print(f"  - W1 shape: {data['W1'].shape}")
    print(f"  - W2 shape: {data['W2'].shape}")
    print(f"  - W3 shape: {data['W3'].shape}")
else:
    print(f"\n[INFO] RL Agent 모델 없음 (첫 게임 실행 후 생성됨)")
    print(f"  - 모델 저장 위치: {model_path}")

# 3. Game Analytics 확인
analytics_path = Path("local_training/game_analytics.json")

print("\n" + "=" * 60)
print("게임 분석 통계")
print("=" * 60)

if analytics_path.exists():
    with open(analytics_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"\n[OK] 총 게임: {data['total_games']}")
    print(f"[OK] 총 승리: {data['total_wins']}")
    win_rate = (data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0.0
    print(f"[OK] 승률: {win_rate:.2f}%")
    print(f"[OK] 평균 게임 시간: {int(data['timing_stats']['avg_game_time'])}초")

    print(f"\n[RACE] 종족별 승률:")
    for race, stats in data['race_stats'].items():
        if stats['games'] > 0:
            race_wr = (stats['wins'] / stats['games'] * 100)
            print(f"  vs {race}: {stats['wins']}/{stats['games']}승 ({race_wr:.1f}%)")
else:
    print(f"\n[INFO] 게임 분석 통계 없음 (첫 게임 실행 후 생성됨)")

print("\n" + "=" * 60)
print("요약")
print("=" * 60)

if adaptive_lr_path.exists():
    with open(adaptive_lr_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"\n[CURRENT] 현재 학습률: {data['learning_rate']:.6f}")
    print(f"[BEST] 최고 성과: {data['best_win_rate']:.2%} (LR: {data['best_learning_rate']:.6f})")

    # 다음 조정 예측
    games_until_adjustment = 10 - data['games_without_improvement']
    if games_until_adjustment > 0:
        print(f"[NEXT] 다음 조정까지: {games_until_adjustment}게임")
    else:
        print(f"[WARNING] 다음 게임에서 학습률 조정 가능")
else:
    print(f"\n[CURRENT] 초기 학습률: 0.001000 (아직 게임 실행 안 함)")
    print(f"[INFO] 첫 게임 실행 후 적응형 학습률 시작")

print("\n" + "=" * 60)
print("\n게임 실행: python run_with_training.py")
print("=" * 60)
