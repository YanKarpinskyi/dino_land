"""pcb.py — Process Control Block. Тільки дані, без логіки."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import constants as C


@dataclass
class PCB:
    pid: int
    type: str                      
    state: str = C.STATE_NEW           
    x: int = 0
    y: int = 0
    direction: str = C.DIR_N           
    hp: int = 0
    priority: int = 1
    instructions_per_tick: int = 1
    crystal_boost_until: Optional[int] = None
    lifespan: Optional[int] = None     
    pc: int = 0                        
    registers: list = field(default_factory=lambda: [0, 0, 0, 0])   
    flags: dict = field(default_factory=lambda: {"eq": False, "gt": False, "lt": False})
    labels: dict = field(default_factory=dict)
    program: list = field(default_factory=list)  
    created_at_tick: int = 0
    creator_pid: Optional[int] = None
    active_spears: int = 0           

    # --- Priority mapping per type ---
    TYPE_PRIORITY = {
        C.TYPE_HERBIVORE:   2,
        C.TYPE_PREDATOR:    4,
        C.TYPE_PTERODACTYL: 3,
        C.TYPE_HUNTER:      5,
        C.TYPE_SPEAR:       9,
    }

    @classmethod
    def from_file(cls, pid: int, filename: str, x: int, y: int,
                  direction: str, tick: int,
                  creator_pid: Optional[int] = None,
                  lifespan: Optional[int] = None) -> "PCB":
        """Фабричний метод. program та labels заповнює caller (після parse)."""
        from constants import INITIAL_HP, TYPE_SPEAR
        entity_type = _type_from_filename(filename)
        hp = INITIAL_HP.get(entity_type, 1) if entity_type != TYPE_SPEAR else 1
        priority = cls.TYPE_PRIORITY.get(entity_type, 1)
        return cls(
            pid=pid,
            type=entity_type,
            state=C.STATE_NEW,
            x=x,
            y=y,
            direction=direction,
            hp=hp,
            priority=priority,
            instructions_per_tick=1,
            created_at_tick=tick,
            creator_pid=creator_pid,
            lifespan=lifespan,
        )

    def get_register(self, name: str) -> int:
        """Повернути значення регістру R1–R4."""
        idx = int(name[1]) - 1
        return self.registers[idx]

    def set_register(self, name: str, value: int) -> None:
        idx = int(name[1]) - 1
        self.registers[idx] = value

    def resolve_arg(self, arg: str) -> int:
        """Розпізнати аргумент: регістр (R1–R4) або ціле число."""
        if isinstance(arg, str) and arg.upper().startswith("R") and len(arg) == 2:
            return self.get_register(arg.upper())
        return int(arg)


def _type_from_filename(filename: str) -> str:
    """Визначити тип істоти з імені файлу поведінки."""
    name = filename.lower().replace(".txt", "").split("/")[-1].split("\\")[-1]
    type_map = {
        "herbivore":   C.TYPE_HERBIVORE,
        "predator":    C.TYPE_PREDATOR,
        "pterodactyl": C.TYPE_PTERODACTYL,
        "hunter":      C.TYPE_HUNTER,
        "spear":       C.TYPE_SPEAR,
    }
    return type_map.get(name, name)