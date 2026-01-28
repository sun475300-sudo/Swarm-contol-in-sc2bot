# -*- coding: utf-8 -*-
"""
Personality Module - 봇 성격 및 채팅 시스템

게임 중 적절한 타이밍에 채팅:
1. 게임 시작 인사
2. 상황별 도발 (우위 시)
3. 칭찬 (좋은 플레이)
4. GG (게임 종료)
5. 성격 모드 (공손, 중립, 도발적)
"""

from enum import Enum
from typing import List, Optional
from utils.logger import get_logger
import random


class PersonalityMode(Enum):
    """성격 모드"""
    POLITE = "polite"  # 공손함
    NEUTRAL = "neutral"  # 중립
    COCKY = "cocky"  # 도발적
    SILENT = "silent"  # 조용함


class GamePhase(Enum):
    """게임 단계"""
    OPENING = "opening"  # 0-5분
    EARLY = "early"  # 5-10분
    MID = "mid"  # 10-15분
    LATE = "late"  # 15분+
    ENDING = "ending"  # 게임 종료


class PersonalityModule:
    """
    Personality Module

    게임 상황에 맞는 채팅을 자동으로 보냅니다.
    """

    def __init__(self, bot, mode: PersonalityMode = PersonalityMode.NEUTRAL):
        self.bot = bot
        self.logger = get_logger("Personality")
        self.mode = mode

        # 채팅 이력
        self.messages_sent: List[str] = []
        self.last_message_time = 0
        self.message_cooldown = 60.0  # 메시지 최소 간격 (초)

        # 게임 상태 추적
        self.game_start_greeted = False
        self.good_game_sent = False
        self.victory_declared = False
        self.taunt_count = 0

        # 메시지 데이터베이스
        self._init_messages()

    def _init_messages(self):
        """메시지 초기화"""
        self.messages = {
            # 게임 시작
            "greeting": {
                PersonalityMode.POLITE: [
                    "gl hf!",
                    "Good luck, have fun!",
                    "May the best player win!",
                ],
                PersonalityMode.NEUTRAL: [
                    "glhf",
                    "hf",
                ],
                PersonalityMode.COCKY: [
                    "gl, you'll need it",
                    "Prepare to be outplayed",
                    "This won't take long",
                ],
                PersonalityMode.SILENT: [],
            },

            # 우위 시 도발
            "ahead": {
                PersonalityMode.POLITE: [
                    "Nice economy!",
                    "Good defense",
                ],
                PersonalityMode.NEUTRAL: [
                    "Interesting strategy",
                ],
                PersonalityMode.COCKY: [
                    "Is that all you got?",
                    "My swarm grows stronger",
                    "You cannot stop the Swarm",
                    "Resistance is futile",
                ],
                PersonalityMode.SILENT: [],
            },

            # 적 좋은 플레이
            "respect": {
                PersonalityMode.POLITE: [
                    "Nice move!",
                    "Well played",
                    "That was impressive",
                ],
                PersonalityMode.NEUTRAL: [
                    "wp",
                ],
                PersonalityMode.COCKY: [
                    "Not bad",
                ],
                PersonalityMode.SILENT: [],
            },

            # 승리
            "victory": {
                PersonalityMode.POLITE: [
                    "gg wp!",
                    "Good game, well played!",
                    "That was fun!",
                ],
                PersonalityMode.NEUTRAL: [
                    "gg",
                ],
                PersonalityMode.COCKY: [
                    "gg ez",
                    "The Swarm always wins",
                    "Better luck next time",
                ],
                PersonalityMode.SILENT: ["gg"],
            },

            # 패배
            "defeat": {
                PersonalityMode.POLITE: [
                    "gg wp!",
                    "Well played! You deserved that win",
                ],
                PersonalityMode.NEUTRAL: [
                    "gg",
                ],
                PersonalityMode.COCKY: [
                    "gg",
                    "Lucky win",
                ],
                PersonalityMode.SILENT: ["gg"],
            },

            # 긴 게임
            "long_game": {
                PersonalityMode.POLITE: [
                    "This is an epic battle!",
                    "What a game!",
                ],
                PersonalityMode.NEUTRAL: [
                    "Long game",
                ],
                PersonalityMode.COCKY: [
                    "You're persistent, I'll give you that",
                    "How are you still alive?",
                ],
                PersonalityMode.SILENT: [],
            },
        }

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 게임 시작 인사 (15초)
            if not self.game_start_greeted and game_time > 15:
                await self._send_greeting(game_time)
                self.game_start_greeted = True

            # 주기적 체크 (30초마다)
            if iteration % 660 == 0:
                await self._check_game_situation(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[PERSONALITY] Error: {e}")

    async def _send_greeting(self, game_time: float):
        """게임 시작 인사"""
        message = self._get_random_message("greeting")
        if message:
            await self._send_message(message, game_time)

    async def _check_game_situation(self, game_time: float):
        """게임 상황 체크 및 적절한 메시지"""
        # 쿨다운 체크
        if game_time - self.last_message_time < self.message_cooldown:
            return

        # 게임 단계 판단
        phase = self._get_game_phase(game_time)

        # 우위 판단
        if self._is_ahead():
            # 우위일 때 도발 (15% 확률, 최대 3회)
            if random.random() < 0.15 and self.taunt_count < 3:
                message = self._get_random_message("ahead")
                if message:
                    await self._send_message(message, game_time)
                    self.taunt_count += 1

        # 긴 게임 (20분 이상)
        if game_time > 1200 and phase == GamePhase.LATE:
            if random.random() < 0.1:  # 10% 확률
                message = self._get_random_message("long_game")
                if message:
                    await self._send_message(message, game_time)

    async def on_victory(self):
        """승리 시 호출"""
        if not self.victory_declared:
            message = self._get_random_message("victory")
            if message:
                await self._send_message(message, self.bot.time)
            self.victory_declared = True

    async def on_defeat(self):
        """패배 시 호출"""
        if not self.good_game_sent:
            message = self._get_random_message("defeat")
            if message:
                await self._send_message(message, self.bot.time)
            self.good_game_sent = True

    async def send_respect(self, reason: str = ""):
        """적의 좋은 플레이에 칭찬"""
        message = self._get_random_message("respect")
        if message:
            await self._send_message(message, self.bot.time)
            if reason:
                self.logger.info(f"[RESPECT] Sent for: {reason}")

    def _get_random_message(self, category: str) -> Optional[str]:
        """랜덤 메시지 선택"""
        messages = self.messages.get(category, {}).get(self.mode, [])
        if not messages:
            return None
        return random.choice(messages)

    async def _send_message(self, message: str, game_time: float):
        """메시지 전송"""
        try:
            await self.bot.chat_send(message)
            self.messages_sent.append(message)
            self.last_message_time = game_time
            self.logger.info(f"[{int(game_time)}s] CHAT: {message}")
        except Exception as e:
            self.logger.error(f"[PERSONALITY] Failed to send message: {e}")

    def _get_game_phase(self, game_time: float) -> GamePhase:
        """게임 단계 판단"""
        if game_time < 300:
            return GamePhase.OPENING
        elif game_time < 600:
            return GamePhase.EARLY
        elif game_time < 900:
            return GamePhase.MID
        else:
            return GamePhase.LATE

    def _is_ahead(self) -> bool:
        """우위 판단"""
        # 간단한 우위 판단 (서플라이 기반)
        our_supply = self.bot.supply_used
        enemy_supply = self.bot.supply_used_by_enemy if hasattr(self.bot, "supply_used_by_enemy") else 0

        # 인텔 정보 사용 (있으면)
        if hasattr(self.bot, "intel") and self.bot.intel:
            enemy_army = getattr(self.bot.intel, "enemy_army_supply", 0)
            our_army = self.bot.supply_used - self.bot.workers.amount

            # 병력 비교
            if our_army > enemy_army * 1.3:  # 30% 이상 우위
                return True

        # 서플라이 비교
        if enemy_supply > 0 and our_supply > enemy_supply * 1.3:
            return True

        return False

    def set_mode(self, mode: PersonalityMode):
        """성격 모드 변경"""
        self.mode = mode
        self.logger.info(f"[PERSONALITY] Mode changed to: {mode.value}")

    def get_statistics(self) -> dict:
        """통계 반환"""
        return {
            "mode": self.mode.value,
            "messages_sent": len(self.messages_sent),
            "taunt_count": self.taunt_count,
            "recent_messages": self.messages_sent[-5:] if self.messages_sent else []
        }
