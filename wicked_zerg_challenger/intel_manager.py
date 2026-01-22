#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intel Manager - lightweight information manager with update/on_step bridge.
"""

from __future__ import annotations

import asyncio
from typing import Optional


class IntelManager:
    """Collects intel and bridges update() to on_step()."""

    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0
        self.update_interval = 8
        self.enemy_race_name: Optional[str] = None

    async def on_step(self, iteration: int) -> None:
        if iteration - self.last_update < self.update_interval:
            return
        self.last_update = iteration

        try:
            result = self.update(iteration)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            return

    def update(self, iteration: int) -> None:
        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race is None:
            self.enemy_race_name = None
            return
        if hasattr(enemy_race, "name"):
            self.enemy_race_name = str(enemy_race.name)
        else:
            self.enemy_race_name = str(enemy_race)
