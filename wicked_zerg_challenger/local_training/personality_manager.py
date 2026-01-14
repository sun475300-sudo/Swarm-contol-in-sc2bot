# -*- coding: utf-8 -*-
"""
Personality Manager - Bot personality and chat system
Manages bot personality, chat messages, and in-game communication.

Core features:
    1. Persona-based playstyle (Serral, Dark, Reynor)
    2. In-game chat management
    3. GG detection and handling
    4. Bot internal thoughts broadcast
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

import random
from typing import Any


class PersonalityManager:
    """Manager for bot personality and chat"""

    def __init__(self, bot: Any, personality: str = "serral"):
        """
        Initialize PersonalityManager

        Args:
            bot: WickedZergBotPro instance
            personality: Persona ("serral", "dark", "reynor")
        """
        self.bot = bot
        self.personality = personality.lower()
        self.last_chat_time = -120

        # Personality parameters by persona
        self.personality_params = {
            "serral": {
                "name": "Serral (AI)",
                "drone_limit": 80,
                "aggression": 0.6,
                "macro_focus": 0.8,
                "chat_frequency": 0.3,
                "chat_style": "calm",
            },
            "dark": {
                "name": "Dark (AI)",
                "drone_limit": 75,
                "aggression": 0.8,
                "macro_focus": 0.6,
                "chat_frequency": 0.5,
                "chat_style": "aggressive",
            },
            "reynor": {
                "name": "Reynor (AI)",
                "drone_limit": 70,
                "aggression": 0.9,
                "macro_focus": 0.5,
                "chat_frequency": 0.4,
                "chat_style": "creative",
            },
        }

        # Current persona settings
        if self.personality not in self.personality_params:
            print(f"[WARNING] Unknown personality '{self.personality}', using 'serral'")
            self.personality = "serral"

        self.params = self.personality_params[self.personality]

        # Chat message templates
        self.chat_templates = {
            "calm": {
                "greeting": ["GL HF!", "Good luck!", "Let's play!"],
                "win": ["GG WP!", "Good game!", "Well played!"],
                "taunt": ["Interesting strategy...", "Nice move!", "Impressive macro!"],
            },
            "aggressive": {
                "greeting": ["GL HF!", "Let's go!", "Show me what you got!"],
                "win": ["GG!", "Victory!", "Too easy!"],
                "taunt": ["Is that all?", "You can do better!", "Nice try!"],
            },
            "creative": {
                "greeting": ["GL HF!", "Time to play!", "Let's have fun!"],
                "win": ["GG!", "Good game!", "That was fun!"],
                "taunt": ["Unexpected move!", "Creative strategy!", "Nice one!"],
            },
        }

    def get_personality_name(self) -> str:
        """Get persona name"""
        return self.params["name"]

    def get_drone_limit(self) -> int:
        """Get persona drone limit"""
        return self.params["drone_limit"]

    def get_aggression(self) -> float:
        """Get persona aggression"""
        return self.params["aggression"]

    def get_macro_focus(self) -> float:
        """Get persona macro focus"""
        return self.params["macro_focus"]

    def should_chat(self, current_time: float) -> bool:
        """
        Determine if bot should chat

        Args:
            current_time: Current game time

        Returns:
            bool: Whether to chat
        """
        # Cooldown check (minimum 120 seconds)
        if current_time - self.last_chat_time < 120:
            return False

        # Persona-based probability check
        if random.random() < self.params["chat_frequency"]:
            self.last_chat_time = current_time
            return True

        return False

    def get_greeting_message(self) -> str:
        """Get greeting message"""
        chat_style = self.params["chat_style"]
        messages = self.chat_templates[chat_style]["greeting"]
        return random.choice(messages)

    def get_win_message(self) -> str:
        """Get victory message"""
        chat_style = self.params["chat_style"]
        messages = self.chat_templates[chat_style]["win"]
        return random.choice(messages)

    def get_taunt_message(self) -> str:
        """Get taunt message"""
        chat_style = self.params["chat_style"]
        messages = self.chat_templates[chat_style]["taunt"]
        return random.choice(messages)

    async def send_chat(self, message: str) -> None:
        """
        Send chat message

        Args:
            message: Message to send
        """
        try:
            await self.bot.chat_send(message)
            print(f"[CHAT] {self.get_personality_name()}: {message}")
        except Exception as e:
            print(f"[WARNING] Chat send failed: {e}")

    async def broadcast_internal_thoughts(self) -> None:
        """
        Broadcast bot internal thoughts (optional)
        Send strategy hints via chat at game start
        """
        try:
            # Strategy hints by persona
            hints = {
                "serral": "I will macro hard and overwhelm you with units!",
                "dark": "Aggressive play incoming! Watch out for early aggression!",
                "reynor": "Creative strategies ahead! Let's make this interesting!",
            }

            hint = hints.get(self.personality, "Let's play!")

            # 20% chance to send strategy hint
            if random.random() < 0.2:
                await self.send_chat(hint)
        except Exception:
            pass  # Silent fail

    async def process_chat_message(self, chat_message: Any) -> bool:
        """
        Process opponent chat message

        Args:
            chat_message: ChatMessage object

        Returns:
            bool: Whether GG was detected
        """
        try:
            # Ignore own messages
            if chat_message.is_from_self:
                return False

            message_text = chat_message.message.lower().strip()

            # GG / surrender keyword detection (expanded)
            gg_keywords = [
                "gg", "ggwp", "gg wp", "good game", "gg!", "gg.",
                "ff", "forfeit", "i forfeit", "surrender", "i surrender",
                "give up", "i give up", "i concede", "concede",
            ]

            if any(keyword in message_text for keyword in gg_keywords):
                instance_id = getattr(self.bot, "instance_id", 0)
                instance_tag = f"[ID:{instance_id}]"

                print(f"{instance_tag} Victory! Opponent declared GG!")
                print(f"{instance_tag} Opponent message: '{chat_message.message}'")

                # GG response
                await self.send_chat("GG WP!")

                return True  # GG/surrender detected

            # General message response (optional)
            if self.should_chat(self.bot.time):
                # Persona-based response
                if "rush" in message_text or "cheese" in message_text:
                    response = random.choice(
                        [
                            "No cheese, just macro!",
                            "Clean game only!",
                            "I prefer standard play!",
                        ]
                    )
                    await self.send_chat(response)

            return False

        except Exception as e:
            if hasattr(self.bot, "iteration") and self.bot.iteration % 100 == 0:
                print(f"[WARNING] Chat processing error: {e}")
            return False

    def get_personality_description(self) -> str:
        """Get persona description"""
        descriptions = {
            "serral": "Serral style: Stable macro + High drone count (80) + Medium aggression",
            "dark": "Dark style: Aggressive play + Medium drone count (75) + High aggression",
            "reynor": "Reynor style: Creative strategy + Low drone count (70) + Very high aggression",
        }
        return descriptions.get(self.personality, "Unknown personality")

    def log_personality_info(self) -> None:
        """Log persona information"""
        print("\n" + "=" * 70)
        print(f"Persona: {self.get_personality_name()}")
        print(self.get_personality_description())
        print(f"   - Drone limit: {self.get_drone_limit()}")
        print(f"   - Aggression: {self.get_aggression():.1%}")
        print(f"   - Macro focus: {self.get_macro_focus():.1%}")
        print(f"   - Chat style: {self.params['chat_style']}")
        print("=" * 70 + "\n")
