"""world.py — карта, entity_map, логіка світу."""
from __future__ import annotations
import random
import os
from typing import Optional, Callable
import constants as C
from pcb import PCB


class World:
    def __init__(self, width: int = C.MAP_WIDTH, height: int = C.MAP_HEIGHT):
        self.width = width
        self.height = height

         Ландшафт: grid[y][x] = код клітинки
        self.grid: list[list[int]] = [
            [C.CELL_EMPTY] * width for _ in range(height)
        ]

        self.entity_map: list[list[Optional[int]]] = [
            [None] * width for _ in range(height)
        ]

        self.processes: dict[int, PCB] = {}

        self.dirty_cells: set[tuple[int, int]] = set()

        self.corpses: dict[tuple[int, int], str] = {}

        self._dirty_callback: Optional[Callable] = None

        self._init_border()

    # ── Ініціалізація ─────────────────────────────────────────────────────────

    def _init_border(self) -> None:
        for x in range(self.width):
            self.grid[0][x] = C.CELL_BORDER
            self.grid[self.height - 1][x] = C.CELL_BORDER
        for y in range(self.height):
            self.grid[y][0] = C.CELL_BORDER
            self.grid[y][self.width - 1] = C.CELL_BORDER

    # ── Клітинки ──────────────────────────────────────────────────────────────

    def get_cell(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return C.CELL_BORDER

    def set_cell(self, x: int, y: int, code: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = code
            self.mark_dirty(x, y)

    def is_passable(self, x: int, y: int, entity_type: str) -> bool:
        code = self.get_cell(x, y)
        if entity_type == C.TYPE_PTERODACTYL:
            return code in C.PTERODACTYL_PASSABLE
        return code in C.PASSABLE_CELLS

    def is_occupied(self, x: int, y: int) -> bool:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.entity_map[y][x] is not None
        return True

    def mark_dirty(self, x: int, y: int) -> None:
        self.dirty_cells.add((x, y))
        if self._dirty_callback:
            self._dirty_callback(x, y)

    def clear_dirty(self) -> None:
        self.dirty_cells.clear()

    # ── Процеси ───────────────────────────────────────────────────────────────

    def add_entity(self, pcb: PCB) -> None:
        self.processes[pcb.pid] = pcb
        self.entity_map[pcb.y][pcb.x] = pcb.pid
        self.mark_dirty(pcb.x, pcb.y)

    def remove_entity(self, pcb: PCB) -> None:
        self.processes.pop(pcb.pid, None)
        if (0 <= pcb.x < self.width and 0 <= pcb.y < self.height and
                self.entity_map[pcb.y][pcb.x] == pcb.pid):
            self.entity_map[pcb.y][pcb.x] = None
        self.mark_dirty(pcb.x, pcb.y)

    def move_entity(self, pcb: PCB, nx: int, ny: int) -> None:
        if self.entity_map[pcb.y][pcb.x] == pcb.pid:
            self.entity_map[pcb.y][pcb.x] = None
        self.mark_dirty(pcb.x, pcb.y)
        pcb.x = nx
        pcb.y = ny
        self.entity_map[ny][nx] = pcb.pid
        self.mark_dirty(nx, ny)

    # ── SCAN ──────────────────────────────────────────────────────────────────

    def find_nearest(self, x: int, y: int, radius: int, entity_type: str) -> Optional[PCB]:
        """
        Манхеттенська відстань. Перешкоди не блокують.
        При рівній відстані — менший PID.
        """
        best: Optional[PCB] = None
        best_dist = radius + 1

        for pcb in self.processes.values():
            if pcb.type != entity_type:
                continue
            dist = abs(pcb.x - x) + abs(pcb.y - y)
            if dist > radius:
                continue
            if dist < best_dist or (dist == best_dist and best and pcb.pid < best.pid):
                best = pcb
                best_dist = dist

        return best

    # ── Їжа та кристали ───────────────────────────────────────────────────────

    def consume_cell(self, pcb: PCB, tick: int) -> None:
        """Обробити ефект клітинки після входу на неї."""
        code = self.get_cell(pcb.x, pcb.y)
        if code == C.CELL_FERN and pcb.type in (C.TYPE_HERBIVORE, C.TYPE_PTERODACTYL):
            pcb.hp += C.FERN_HEAL
            self.set_cell(pcb.x, pcb.y, C.CELL_EMPTY)
        elif code == C.CELL_CRYSTAL:
            pcb.crystal_boost_until = tick + C.CRYSTAL_BOOST_TICKS
            pcb.instructions_per_tick = C.CRYSTAL_BOOST_IPT
            self.set_cell(pcb.x, pcb.y, C.CELL_EMPTY)

    def eat_corpse(self, pcb: PCB) -> bool:
        """Хижак з'їдає труп на своїй клітинці. Повертає True якщо з'їв."""
        key = (pcb.x, pcb.y)
        if key in self.corpses:
            pcb.hp += C.CORPSE_HEAL
            del self.corpses[key]
            return True
        return False

    def add_corpse(self, pcb: PCB) -> None:
        self.corpses[(pcb.x, pcb.y)] = pcb.type

    # ── Відновлення папороті ──────────────────────────────────────────────────

    def respawn_fern(self, count: int) -> None:
        """Відновити 'count' клітинок папороті у випадкових порожніх місцях."""
        empty = [
            (x, y)
            for y in range(1, self.height - 1)
            for x in range(1, self.width - 1)
            if self.grid[y][x] == C.CELL_EMPTY and self.entity_map[y][x] is None
        ]
        if not empty:
            return
        chosen = random.sample(empty, min(count, len(empty)))
        for x, y in chosen:
            self.set_cell(x, y, C.CELL_FERN)

    # ── Завантаження / збереження карти ──────────────────────────────────────

    def load_map(self, filepath: str) -> None:
        """Завантажити map.txt. Перевіряє розмір та допустимі коди."""
        valid_codes = {0, 1, 2, 3, 4, 5, 255}
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        if len(lines) != self.height:
            raise ValueError(f"Карта повинна мати {self.height} рядків, отримано {len(lines)}")

        new_grid: list[list[int]] = []
        for row_idx, line in enumerate(lines):
            row = list(map(int, line.split()))
            if len(row) != self.width:
                raise ValueError(f"Рядок {row_idx + 1}: очікується {self.width} клітинок")
            for code in row:
                if code not in valid_codes:
                    raise ValueError(f"Недопустимий код клітинки: {code}")
            new_grid.append(row)

        self.grid = new_grid
        self.entity_map = [[None] * self.width for _ in range(self.height)]
        self.processes.clear()
        for y in range(self.height):
            for x in range(self.width):
                self.dirty_cells.add((x, y))

    def save_map(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            for row in self.grid:
                f.write(" ".join(map(str, row)) + "\n")

    # ── Утиліти ───────────────────────────────────────────────────────────────

    def get_front_cell(self, pcb: PCB) -> tuple[int, int]:
        dx, dy = C.DIRECTION_DELTA[pcb.direction]
        return pcb.x + dx, pcb.y + dy

    def count_processes_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for pcb in self.processes.values():
            counts[pcb.type] = counts.get(pcb.type, 0) + 1
        return counts