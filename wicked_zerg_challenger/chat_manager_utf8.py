# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Set, List
from collections import deque
import os
from datetime import datetime

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
except Exception:
    UnitTypeId = object
    UpgradeId = object


class ChatManager:
    def __init__(self, bot):
        self.bot = bot
        self.announced_buildings = set()
        self.announced_buildings_counts = {}
        self.announced_upgrades = set()
        self._prev_ready_counts = {}
        self._prev_in_progress = set()
        self._prev_pending_upgrades = set()
        self._last_update_iter = -9999
        self._update_interval_frames = 112
        self._gg_replied = False
        self._greeted = False
        self._message_queue = deque()
        self._max_queue = 50
        self._max_msgs_per_update = 3
        # 로그 파일 준비
        try:
            os.makedirs("logs", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._chat_log_file = os.path.join("logs", f"chat_capture_{ts}.log")
        except Exception:
            self._chat_log_file = None

    def _log_msg(self, msg: str):
        try:
            if not msg:
                return
            if self._chat_log_file:
                with open(self._chat_log_file, "a", encoding="utf-8", errors="replace") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        except Exception:
            pass

    async def greet(self) -> None:
        """게임 시작 시 인사 메시지 전송."""
        try:
            msg = "gl hf"
            await self.bot.chat_send(msg)
            self._log_msg(msg)
            self._greeted = True
        except Exception:
            pass

    def _structures_of_interest(self):
        return [
            UnitTypeId.SPAWNINGPOOL,
            UnitTypeId.ROACHWARREN,
            UnitTypeId.HYDRALISKDEN,
            UnitTypeId.BANELINGNEST,
            UnitTypeId.EVOLUTIONCHAMBER,
            UnitTypeId.LAIR,
            UnitTypeId.HIVE,
            UnitTypeId.SPIRE,
            getattr(UnitTypeId, 'GREATERSPIRE', UnitTypeId.SPIRE),
        ]

    def _upgrades_of_interest(self):
        return [x for x in [
            getattr(UpgradeId, 'ZERGLINGMOVEMENTSPEED', None),
            getattr(UpgradeId, 'GROOVEDSPINES', getattr(UpgradeId, 'GROOVED_SPINES', None)),
            getattr(UpgradeId, 'MUSCULARAUGMENTS', getattr(UpgradeId, 'HYDRALISKSPEED', None)),
            getattr(UpgradeId, 'GLIALRECONSTITUTION', None),
            getattr(UpgradeId, 'CENTRIFUGALHOOKS', getattr(UpgradeId, 'CENTRIFUGAL_HOOKS', None)),
        ] if x]

    async def on_chat(self, chat_message):
        try:
            is_from_self = getattr(chat_message, "is_from_self", False)
            if isinstance(chat_message, str):
                msg_text = chat_message
            else:
                msg_text = getattr(chat_message, "message", "") or getattr(chat_message, "text", "")
            if not msg_text and chat_message is not None:
                msg_text = str(chat_message)
            msg = (msg_text or "").lower()
            if not self._gg_replied and not is_from_self and msg and ('gg' in msg or 'gg wp' in msg):
                await self.bot.chat_send('GG! Good game.')
                self._log_msg('GG! Good game.')
                self._gg_replied = True
        except Exception:
            pass

    def enqueue_message(self, msg: str) -> None:
        if not msg:
            return
        try:
            if len(self._message_queue) >= self._max_queue:
                self._message_queue.popleft()
            self._message_queue.append(msg)
        except Exception:
            pass

    # 호환용 별칭: 외부에서 on_chat_message를 호출하는 코드 지원
    async def on_chat_message(self, chat_message):
        await self.on_chat(chat_message)

    async def update(self):
        b = self.bot
        try:
            # Fallback greeting: ensure one-time greeting even if on_start send failed
            if not self._greeted:
                try:
                    await self.bot.chat_send("gl hf")
                    self._log_msg("gl hf")
                except Exception:
                    pass
                finally:
                    self._greeted = True

            if b.iteration - self._last_update_iter < self._update_interval_frames:
                return
            self._last_update_iter = b.iteration

            msgs = []
            in_progress_now = set()

            for tid in self._structures_of_interest():
                struct_q = b.structures(tid)
                if not struct_q:
                    continue

                ready_count = not_ready_count = max_build_progress_pct = 0

                try:
                    for s in struct_q:
                        if getattr(s, 'is_ready', False):
                            ready_count += 1
                        else:
                            not_ready_count += 1
                            prog = getattr(s, 'build_progress', None)
                            if isinstance(prog, (float, int)):
                                pct = int(float(prog) * 100)
                                max_build_progress_pct = max(max_build_progress_pct, pct)
                except Exception:
                    pass

                prev_ready = self._prev_ready_counts.get(tid, 0)
                if ready_count > prev_ready:
                    last_announced = self.announced_buildings_counts.get(tid, 0)
                    if ready_count > last_announced:
                        msgs.append(f'완료: {tid.name} x{ready_count - prev_ready}')
                        self.announced_buildings.add(tid)
                        self.announced_buildings_counts[tid] = ready_count
                    self._prev_ready_counts[tid] = ready_count

                if not_ready_count > 0:
                    in_progress_now.add(tid)
                    if max_build_progress_pct > 0:
                        msgs.append(f'진행: {tid.name} ({max_build_progress_pct}%)')

            for tid in in_progress_now - self._prev_in_progress:
                if tid not in self.announced_buildings:
                    msgs.append(f'진행: {tid.name}')
            self._prev_in_progress = in_progress_now

            pending_now = set()
            completed_now = set(getattr(b.state, 'upgrades', set()))

            for upg in self._upgrades_of_interest():
                try:
                    if b.already_pending_upgrade(upg) > 0:
                        pending_now.add(upg)
                except Exception:
                    pass

            for upg in pending_now - self._prev_pending_upgrades:
                msgs.append(f'업그레이드: {upg.name}')
            self._prev_pending_upgrades = pending_now

            for upg in completed_now - self.announced_upgrades:
                msgs.append(f'완료: {upg.name}')
                self.announced_upgrades.add(upg)

            try:
                for tid in [UnitTypeId.SPAWNINGPOOL, UnitTypeId.ROACHWARREN, UnitTypeId.HYDRALISKDEN,
                           UnitTypeId.BANELINGNEST, UnitTypeId.EVOLUTIONCHAMBER, UnitTypeId.LAIR, UnitTypeId.HIVE]:
                    for s in b.structures(tid):
                        if not getattr(s, 'is_idle', True):
                            max_order_pct = 0
                            for order in getattr(s, 'orders', []):
                                prog = getattr(order, 'progress', None)
                                if isinstance(prog, (float, int)):
                                    pct = int(float(prog) * 100)
                                    max_order_pct = max(max_order_pct, pct)
                            if max_order_pct > 0:
                                msgs.append(f'진행중: {tid.name} (~{max_order_pct}%)')
            except Exception:
                pass

            send_msgs = []
            try:
                while self._message_queue and len(send_msgs) < self._max_msgs_per_update:
                    send_msgs.append(self._message_queue.popleft())
            except Exception:
                pass

            for msg in msgs:
                if len(send_msgs) >= self._max_msgs_per_update:
                    break
                send_msgs.append(msg)

            for msg in send_msgs:
                try:
                    await b.chat_send(msg)
                except Exception:
                    pass
                finally:
                    self._log_msg(msg)
        except Exception:
            pass
