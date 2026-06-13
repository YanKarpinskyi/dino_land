"""logger.py — логування подій та статистика."""
from __future__ import annotations
import json
import os
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world import World
    from pcb import PCB

class Logger:
    def __init__(self):
        self.events: list[dict] = []
        self.deaths: dict[str, list[int]] = defaultdict(list) 
        self.population_history: list[dict] = []  

    def log_event(self, tick: int, event_type: str, **kwargs) -> None:
        """Записати подію в лог."""
        event = {"tick": tick, "event": event_type, **kwargs}
        self.events.append(event)

    def record_death(self, pcb: "PCB", tick: int, lifespan: int) -> None:
        """Записати смерть процесу."""
        self.log_event(tick, "DEATH", pid=pcb.pid, type=pcb.type, lifespan=lifespan)
        self.deaths[pcb.type].append(lifespan)

    def snapshot(self, world: "World", tick: int) -> None:
        """Зробити знімок популяції."""
        counts = world.count_processes_by_type()
        counts["tick"] = tick
        self.population_history.append(counts)

    def save_report(self, filename: str = "stats.txt") -> None:
        """Зберегти статистику у файл."""
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=== DINO LAND STATISTICS ===\n\n")

            f.write("Average Lifespan by Type:\n")
            for typ, lifespans in self.deaths.items():
                avg = sum(lifespans) / len(lifespans) if lifespans else 0
                f.write(f"  {typ}: {avg:.1f} ticks (n={len(lifespans)})\n")

            f.write("\nLast 10 Events:\n")
            for ev in self.events[-10:]:
                f.write(f"  [TICK {ev['tick']}] {ev['event']}: {ev}\n")

            f.write("\nPopulation History (every 100 ticks):\n")
            for snap in self.population_history[-20:]:
                tick = snap["tick"]
                snap_display = {k: v for k, v in snap.items() if k != "tick"}
                f.write(f"  TICK {tick}: {snap_display}\n")

        print(f"Statistics saved to {filename}")