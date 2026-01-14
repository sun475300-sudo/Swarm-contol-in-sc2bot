# -*- coding: utf-8 -*-
"""
================================================================================
        ? Zerg Neural Network - Model Architecture & Training
================================================================================
PyTorch 기반 강화학습 신경망 모듈

Components:
    - ZergNet: 신경망 모델 아키텍처
    - ReinforcementLearner: 강화학습 학습기
    - Action: 액션 정의
    - MODELS_DIR: 모델 저장 디렉토리 (?? AI Arena 환경 고려)
================================================================================
"""

import os
from pathlib import Path
from enum import Enum

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    print("[WARNING] PyTorch not available - neural network disabled")


# ?? AI Arena 환경: 상대 경로로 모델 디렉토리 지정
# 실행 파일 위치 기준으로 ./models/ 폴더 사용
SCRIPT_DIR = Path(__file__).parent.absolute()
MODELS_DIR = str(SCRIPT_DIR / "models")


class Action(Enum):
    """강화학습 액션 정의"""
    ATTACK = 0
    DEFENSE = 1
    ECONOMY = 2
    TECH_FOCUS = 3


if PYTORCH_AVAILABLE:
    class ZergNet(nn.Module):
        """
        Zerg 신경망 모델
        
        Input: 5D [minerals, vespene, supply, drones, army]
        Output: 4 actions [ATTACK, DEFENSE, ECONOMY, TECH_FOCUS]
        """
        
        def __init__(self, input_size=5, hidden_size=64, output_size=4):
            super(ZergNet, self).__init__()
            
            self.fc1 = nn.Linear(input_size, hidden_size)
            self.fc2 = nn.Linear(hidden_size, hidden_size)
            self.fc3 = nn.Linear(hidden_size, output_size)
            
            self.relu = nn.ReLU()
            self.dropout = nn.Dropout(0.2)
        
        def forward(self, x):
            """순전파"""
            x = self.relu(self.fc1(x))
            x = self.dropout(x)
            x = self.relu(self.fc2(x))
            x = self.dropout(x)
            x = self.fc3(x)
            return x


    class ReinforcementLearner:
        """
        강화학습 학습기
        
        - 모델 학습
        - 액션 선택
        - 경험 저장
        """
        
        def __init__(self, model, learning_rate=0.001):
            self.model = model
            self.optimizer = optim.Adam(model.parameters(), lr=learning_rate)
            self.criterion = nn.MSELoss()
            
            # 경험 버퍼
            self.experiences = []
            self.max_buffer_size = 10000
        
        def select_action(self, state, epsilon=0.1):
            """
            액션 선택 (epsilon-greedy)
            
            Args:
                state: 현재 상태 (numpy array)
                epsilon: 탐험 확률
            
            Returns:
                action: 선택된 액션 (int)
            """
            import random
            import numpy as np
            
            # Epsilon-greedy 정책
            if random.random() < epsilon:
                # 탐험: 랜덤 액션
                return random.randint(0, 3)
            else:
                # 활용: 모델 예측
                with torch.no_grad():
                    state_tensor = torch.FloatTensor(state).unsqueeze(0)
                    
                    # GPU 사용 시 텐서 이동
                    if next(self.model.parameters()).is_cuda:
                        state_tensor = state_tensor.cuda()
                    
                    q_values = self.model(state_tensor)
                    action = q_values.argmax().item()
                    return action
        
        def store_experience(self, state, action, reward, next_state, done):
            """경험 저장"""
            self.experiences.append({
                'state': state,
                'action': action,
                'reward': reward,
                'next_state': next_state,
                'done': done
            })
            
            # 버퍼 크기 제한
            if len(self.experiences) > self.max_buffer_size:
                self.experiences.pop(0)
        
        def train_step(self, batch_size=32, gamma=0.99):
            """
            학습 스텝
            
            Args:
                batch_size: 배치 크기
                gamma: 할인 계수
            """
            if len(self.experiences) < batch_size:
                return None
            
            import random
            
            # 미니배치 샘플링
            batch = random.sample(self.experiences, batch_size)
            
            states = torch.FloatTensor([exp['state'] for exp in batch])
            actions = torch.LongTensor([exp['action'] for exp in batch])
            rewards = torch.FloatTensor([exp['reward'] for exp in batch])
            next_states = torch.FloatTensor([exp['next_state'] for exp in batch])
            dones = torch.FloatTensor([exp['done'] for exp in batch])
            
            # GPU 사용 시 텐서 이동
            if next(self.model.parameters()).is_cuda:
                states = states.cuda()
                actions = actions.cuda()
                rewards = rewards.cuda()
                next_states = next_states.cuda()
                dones = dones.cuda()
            
            # Q-learning 업데이트
            current_q = self.model(states).gather(1, actions.unsqueeze(1)).squeeze()
            
            with torch.no_grad():
                next_q = self.model(next_states).max(1)[0]
                target_q = rewards + gamma * next_q * (1 - dones)
            
            loss = self.criterion(current_q, target_q)
            
            # 역전파
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            return loss.item()
        
        def load_model(self, path):
            """모델 로드"""
            if os.path.exists(path):
                self.model.load_state_dict(torch.load(path))
                print(f"? [모델 로드] {path}")
            else:
                print(f"??  [모델 없음] {path} - 새 모델로 시작")
        
        def save_model(self, path):
            """모델 저장"""
            os.makedirs(os.path.dirname(path), exist_ok=True)
            torch.save(self.model.state_dict(), path)
            print(f"? [모델 저장] {path}")

else:
    # PyTorch 없을 때 더미 클래스
    class ZergNet:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch not available")
    
    class ReinforcementLearner:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch not available")


# 모듈 내보내기
__all__ = [
    'ZergNet',
    'ReinforcementLearner',
    'Action',
    'MODELS_DIR',
    'PYTORCH_AVAILABLE',
]
