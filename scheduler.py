"""scheduler.py — планувальник Multilevel Queue (10 черг, пріоритети 1–10)."""
from __future__ import annotations
from collections import deque
from typing import TYPE_CHECKING
import constants as C

if TYPE_CHECKING:
    from world import World
    from logger import Logger


class Scheduler:
    def __init__(self):
        self.queues: list[deque] = [deque() for _ in range(11)]
        self._pid_counter: int = 0
        self.tick_count: int = 0

    # ── PID ───────────────────────────────────────────────────────────────────

    def next_pid(self) -> int:
        self._pid_counter += 1
        return self._pid_counter

    # ── Черга ─────────────────────────────────────────────────────────────────

    def enqueue(self, pcb) -> None:
        priority = max(1, min(10, pcb.priority))
        self.queues[priority].append(pcb)
        pcb.state = C.STATE_READY

    def remove(self, pid: int) -> None:
        for q in self.queues:
            for pcb in list(q):
                if pcb.pid == pid:
                    q.remove(pcb)
                    return

    # ── Один тік ──────────────────────────────────────────────────────────────

    def tick(self, world: "World", logger: "Logger") -> None:
        from interpreter import execute_instruction, _terminate

        self.tick_count += 1
        tick = self.tick_count

        for priority in range(10, 0, -1):
            if not self.queues[priority]:
                continue

            pcb = self.queues[priority].popleft()

            if pcb.pid not in world.processes:
                continue
            if pcb.state == C.STATE_TERMINATED:
                continue

            pcb.state = C.STATE_RUNNING

            if pcb.type != C.TYPE_SPEAR:
                if pcb.type != C.TYPE_SPEAR:
                    if self.tick_count % C.HP_DECAY_INTERVAL == 0:
                        pcb.hp -= C.HP_DECAY_PER_TICK
                    if pcb.hp <= 0:
                        _terminate(pcb, world, logger, self, tick)
                        continue
                if pcb.hp <= 0:
                    _terminate(pcb, world, logger, self, tick)
                    continue

            if pcb.lifespan is not None:
                pcb.lifespan -= 1
                if pcb.lifespan <= 0:
                    pcb.hp = 0
                    logger.log_event(tick, "SPEAR_EXPIRED", pid=pcb.pid,
                                    lifespan=tick - pcb.created_at_tick)
                    _terminate(pcb, world, logger, self, tick)
                    continue

            if pcb.crystal_boost_until is not None and tick > pcb.crystal_boost_until:
                pcb.instructions_per_tick = 1
                pcb.crystal_boost_until = None

            for _ in range(pcb.instructions_per_tick):
                if pcb.pid not in world.processes:
                    break
                execute_instruction(pcb, world, logger, self, tick)

            if pcb.state != C.STATE_TERMINATED and pcb.pid in world.processes:
                pcb.state = C.STATE_READY
                self.queues[priority].append(pcb)

        if tick % C.FERN_RESPAWN_INTERVAL == 0:
            world.respawn_fern(C.FERN_RESPAWN_COUNT)

        if tick % 100 == 0:
            logger.snapshot(world, tick)

    # ── Серіалізація (для SAVE_SIM) ───────────────────────────────────────────

    def get_queue_order(self) -> list[list[int]]:
        """Повернути порядок PID у чергах (для збереження стану)."""
        return [[pcb.pid for pcb in q] for q in self.queues]

    def restore_queue_order(self, order: list[list[int]], world: "World") -> None:
        for priority, pids in enumerate(order):
            for pid in pids:
                pcb = world.processes.get(pid)
                if pcb:
                    self.queues[priority].append(pcb)
                    pcb.state = C.STATE_READY