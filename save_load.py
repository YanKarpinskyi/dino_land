"""save_load.py — збереження та завантаження повної симуляції."""
import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world import World
    from scheduler import Scheduler
    from logger import Logger

SAVES_DIR = "saves"


def ensure_saves_dir() -> None:
    if not os.path.exists(SAVES_DIR):
        os.makedirs(SAVES_DIR)


def save_simulation(name: str, world: "World", scheduler: "Scheduler",
                    logger: "Logger") -> None:
    """Зберегти повний стан симуляції в JSON."""
    ensure_saves_dir()
    path = os.path.join(SAVES_DIR, f"{name}.json")

    processes_data = []
    for pcb in world.processes.values():
        proc_data = {
            "pid": pcb.pid,
            "type": pcb.type,
            "state": pcb.state,
            "x": pcb.x,
            "y": pcb.y,
            "direction": pcb.direction,
            "hp": pcb.hp,
            "priority": pcb.priority,
            "instructions_per_tick": pcb.instructions_per_tick,
            "crystal_boost_until": pcb.crystal_boost_until,
            "lifespan": pcb.lifespan,
            "pc": pcb.pc,
            "registers": pcb.registers,
            "flags": pcb.flags,
            "created_at_tick": pcb.created_at_tick,
            "creator_pid": pcb.creator_pid,
            "active_spears": pcb.active_spears,
            "filename": _get_filename_for_type(pcb.type),  # для відновлення program
        }
        processes_data.append(proc_data)

    data = {
        "tick_count": scheduler.tick_count,
        "grid": world.grid,
        "queue_order": scheduler.get_queue_order(),
        "processes": processes_data,
        "population_history": logger.population_history,
        "events": logger.events[-1000:],  # останні 1000 подій
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Simulation saved to {path}")


def load_simulation(name: str, world: "World", scheduler: "Scheduler",
                    logger: "Logger") -> None:
    """Відновити симуляцію з файлу."""
    import parser as p
    from pcb import PCB

    path = os.path.join(SAVES_DIR, f"{name}.json")
    if not os.path.exists(path):
        print(f"Save file not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    world.processes.clear()
    world.entity_map = [[None] * world.width for _ in range(world.height)]
    world.dirty_cells.clear()
    logger.events = data.get("events", [])
    logger.population_history = data.get("population_history", [])

    world.grid = data["grid"]

    for proc_data in data["processes"]:
        filename = proc_data.pop("filename")
        instructions, labels = p.parse_program(filename)

        pcb = PCB(
            **{k: v for k, v in proc_data.items() if k != "filename"}
        )
        pcb.program = instructions
        pcb.labels = labels
        world.add_entity(pcb)

    scheduler.tick_count = data["tick_count"]
    scheduler._pid_counter = max([pcb.pid for pcb in world.processes.values()] + [0])
    scheduler.queues = [deque() for _ in range(11)]
    scheduler.restore_queue_order(data["queue_order"], world)

    print(f"Simulation loaded from {path}")


def _get_filename_for_type(typ: str) -> str:
    """Повернути ім'я файлу поведінки для типу."""
    return f"{typ}.txt"