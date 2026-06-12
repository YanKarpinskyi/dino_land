"""renderer.py — Pygame рендеринг карти, панелі, tooltip."""
import pygame
import os
import constants as C
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world import World
    from scheduler import Scheduler
    from shell import Shell

COLOR_MAP = {
    C.CELL_EMPTY:    (34, 139, 34),
    C.CELL_FERN:     (50, 205, 50),
    C.CELL_BUSH:     (85, 107, 47),
    C.CELL_WATER:    (70, 130, 180),
    C.CELL_ROCK:     (105, 105, 105),
    C.CELL_CRYSTAL:  (138, 43, 226),
    C.CELL_BORDER:   (139, 69, 19),
}

ENTITY_COLORS = {
    C.TYPE_HERBIVORE:    (255, 255, 100),
    C.TYPE_PREDATOR:     (255, 50, 50),
    C.TYPE_PTERODACTYL:  (200, 200, 255),
    C.TYPE_HUNTER:       (255, 165, 0),
    C.TYPE_SPEAR:        (255, 255, 255),
}

_H_CREATE = "CREATE <file> <x> <y>   — spawn entity"
_H_KILL   = "KILL <pid>              — remove process"
_H_SPEED  = "SPEED <1-10>            — set sim speed"
_H_INFO   = "INFO <pid>              — show process info"
_H_PAUSE  = "PAUSE                   — pause simulation"
_H_START  = "START                   — resume simulation"
_H_SAVE   = "SAVE_SIM <name>         — save state"
_H_LOAD   = "LOAD_SIM <name>         — load state"

SHELL_HINTS = {
    "cr": _H_CREATE, "cre": _H_CREATE, "crea": _H_CREATE,
    "creat": _H_CREATE, "create": _H_CREATE,
    "ki": _H_KILL, "kil": _H_KILL, "kill": _H_KILL,
    "sp": _H_SPEED, "spe": _H_SPEED, "spee": _H_SPEED, "speed": _H_SPEED,
    "in": _H_INFO, "inf": _H_INFO, "info": _H_INFO,
    "pa": _H_PAUSE, "pau": _H_PAUSE, "pause": _H_PAUSE,
    "st": _H_START, "sta": _H_START, "star": _H_START, "start": _H_START,
    "sa": _H_SAVE, "sav": _H_SAVE, "save": _H_SAVE,
    "lo": _H_LOAD, "loa": _H_LOAD, "load": _H_LOAD,
}

# Базова папка спрайтів (відносно dino_land/)
_SPRITES = os.path.join(os.path.dirname(__file__), "assets", "sprites")

def _sp(*parts: str) -> str:
    return os.path.join(_SPRITES, *parts)


class SpriteCache:
    """Завантажує і кешує всі потрібні спрайти, нарізає кадри."""

    def __init__(self, cell_size: int):
        self.cs = cell_size
        self._cache: dict = {}
        self._anim_frame: int = 0          # глобальний лічильник кадрів
        self._anim_tick: int = 0

        # Описи: (шлях, ширина_кадру, висота_кадру, кількість_кадрів)
        _defs = {
            "herbivore":    (_sp("stegosaurus", "PNG", "Stego_Idle.png"),   32, 32, 10),
            "predator":     (_sp("trex", "trex", "PNG", "Trex_Run.png"),    32, 32,  3),
            "pterodactyl":  (_sp("pterodactyl", "pterodactyl", "PNG", "ptero fly.png"), 16, 16, 2),
            "hunter":       (_sp("triceratops", "triceratops", "PNG", "Tricer_Idle.png"), 16, 16, 9),
            "spear":        (_sp("Pixel Weapons Pack 1 - Spears", "Fire Spear", "Fire Spear_1x.png"), 32, 32, 1),
            "crystal":      (_sp("Pixel Crystal Pack Vol. 1", "Amethyst.png"), 32, 32, 1),
            "water":        (_sp("SERENE_VILLAGE_REVAMPED", "Animated stuff", "water_waves_16x16.png"), 16, 16, 14),
        }

        for key, (path, fw, fh, n_frames) in _defs.items():
            frames = self._load_frames(path, fw, fh, n_frames, cell_size)
            self._cache[key] = frames

    def _load_frames(self, path: str, fw: int, fh: int,
                     n_frames: int, target: int) -> list[pygame.Surface]:
        try:
            sheet = pygame.image.load(path).convert_alpha()
        except Exception:
            return []
        frames = []
        for i in range(n_frames):
            frame = pygame.Surface((fw, fh), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), pygame.Rect(i * fw, 0, fw, fh))
            scaled = pygame.transform.scale(frame, (target, target))
            frames.append(scaled)
        return frames

    def tick(self) -> None:
        """Викликати раз на кадр для анімації (міняємо кадр кожні 8 рендер-кадрів)."""
        self._anim_tick += 1
        if self._anim_tick >= 8:
            self._anim_tick = 0
            self._anim_frame += 1

    def get_entity_frame(self, entity_type: str) -> pygame.Surface | None:
        frames = self._cache.get(entity_type)
        if not frames:
            return None
        return frames[self._anim_frame % len(frames)]

    def get_tile_frame(self, key: str, index: int = 0) -> pygame.Surface | None:
        frames = self._cache.get(key)
        if not frames:
            return None
        return frames[index % len(frames)]

    def get_water_frame(self) -> pygame.Surface | None:
        return self.get_tile_frame("water", self._anim_frame)

    def get_crystal_frame(self) -> pygame.Surface | None:
        return self.get_tile_frame("crystal", 0)


class Renderer:
    def __init__(self, screen: pygame.Surface, world: "World",
                 scheduler: "Scheduler", shell: "Shell"):
        self.screen = screen
        self.world = world
        self.scheduler = scheduler
        self.shell = shell
        self.font = pygame.font.SysFont("monospace", 12)
        self.large_font = pygame.font.SysFont("monospace", 14, bold=True)

        self.cell_size = C.CELL_SIZE_PX
        self.map_width_px = C.MAP_WIDTH * self.cell_size
        self.map_height_px = C.MAP_HEIGHT * self.cell_size
        self.panel_x = self.map_width_px + 10
        self.panel_width = 1280 - self.panel_x - 10

        self.selected_pid: int | None = None
        self._messages: list[tuple[str, tuple]] = []
        self._MAX_MESSAGES = 6

        self.sprites = SpriteCache(self.cell_size)
        self._full_drawn = False

    def post_message(self, text: str, color: tuple = (255, 255, 150)) -> None:
        self._messages.append((text, color))
        if len(self._messages) > self._MAX_MESSAGES:
            self._messages.pop(0)

    def draw_frame(self, world, scheduler, shell, paused):
        self.sprites.tick()

        if not self._full_drawn or len(world.dirty_cells) > world.width * world.height // 2:
            self.screen.fill((20, 20, 20))
            for y in range(world.height):
                for x in range(world.width):
                    self._draw_cell(x, y, world)
            self._full_drawn = True
        else:
            for (x, y) in world.dirty_cells:
                self._draw_cell(x, y, world)

        # Воду перемальовуємо щокадру для анімації
        for y in range(world.height):
            for x in range(world.width):
                if world.get_cell(x, y) == C.CELL_WATER:
                    self._draw_cell(x, y, world)

        world.clear_dirty()

        mouse_x, mouse_y = pygame.mouse.get_pos()
        # if (0 <= mouse_x < self.map_width_px and 0 <= mouse_y < self.map_height_px):
        #     self._draw_tooltip(mouse_x, mouse_y)
        self._draw_tooltip(mouse_x, mouse_y)
        self._draw_panel(scheduler, world, paused)
        self._draw_shell_bar(shell)
        self._draw_messages()

    def _draw_cell(self, x: int, y: int, world: "World") -> None:
        rect = pygame.Rect(x * self.cell_size, y * self.cell_size,
                           self.cell_size, self.cell_size)
        code = world.get_cell(x, y)

        color = COLOR_MAP.get(code, (100, 100, 100))
        pygame.draw.rect(self.screen, color, rect)

        if code == C.CELL_WATER:
            spr = self.sprites.get_water_frame()
            if spr:
                self.screen.blit(spr, rect)
        elif code == C.CELL_CRYSTAL:
            spr = self.sprites.get_crystal_frame()
            if spr:
                self.screen.blit(spr, rect)

        pygame.draw.rect(self.screen, (0, 0, 0), rect, 1)

        # Істота
        pid = world.entity_map[y][x]
        if pid is not None and pid in world.processes:
            pcb = world.processes[pid]
            spr = self.sprites.get_entity_frame(pcb.type)
            if spr:
                self.screen.blit(spr, rect)
            else:
                ent_color = ENTITY_COLORS.get(pcb.type, (255, 255, 255))
                pygame.draw.circle(self.screen, ent_color,
                                   rect.center, self.cell_size // 3)

            if self.selected_pid == pid:
                pygame.draw.rect(self.screen, (255, 255, 0), rect, 2)

    def _draw_tooltip(self, mx: int, my: int) -> None:
        if mx < 0 or mx >= self.map_width_px or my < 0 or my >= self.map_height_px:
            return

        x = mx // self.cell_size
        y = my // self.cell_size
        pid = self.world.entity_map[y][x]

        if pid is None or pid not in self.world.processes:
            return

        pcb = self.world.processes[pid]
        lines = [
            f"PID: {pcb.pid}",
            f"Type: {pcb.type}",
            f"HP: {pcb.hp}",
            f"State: {pcb.state}",
            f"Dir: {pcb.direction}",
        ]
        max_w = max(self.font.size(l)[0] for l in lines)
        total_h = len(lines) * self.font.get_height() + 4
        surf = pygame.Surface((max_w + 8, total_h))
        surf.set_alpha(220)
        surf.fill((0, 0, 0))
        for i, line in enumerate(lines):
            txt = self.font.render(line, True, (255, 255, 255))
            surf.blit(txt, (4, 2 + i * self.font.get_height()))
        self.screen.blit(surf, (mx + 12, my + 12))

    def _draw_panel(self, scheduler: "Scheduler", world: "World", paused: bool) -> None:
        panel_rect = pygame.Rect(self.panel_x, 0, self.panel_width, self.map_height_px)
        pygame.draw.rect(self.screen, (45, 45, 45), panel_rect)
        pygame.draw.rect(self.screen, (90, 90, 90), panel_rect, 1)

        y_offset = 10
        pause_text = "PAUSED" if paused else "RUNNING"
        pause_color = (255, 100, 100) if paused else (100, 255, 100)
        status = self.large_font.render(pause_text, True, pause_color)
        self.screen.blit(status, (self.panel_x + 10, y_offset))

        tick_text = self.font.render(f"TICK: {scheduler.tick_count}", True, (200, 200, 200))
        self.screen.blit(tick_text, (self.panel_x + 10, y_offset + 18))
        y_offset += 40

        counts: dict[str, int] = {}
        for pcb in world.processes.values():
            counts[pcb.type] = counts.get(pcb.type, 0) + 1
        for t, col in ENTITY_COLORS.items():
            txt = self.font.render(f"{t[:3].upper()}: {counts.get(t, 0)}", True, col)
            self.screen.blit(txt, (self.panel_x + 10, y_offset))
            y_offset += 15
        y_offset += 8

        sep = self.font.render("─" * 22, True, (80, 80, 80))
        self.screen.blit(sep, (self.panel_x + 10, y_offset))
        y_offset += 14
        headers_txt = self.font.render("PID  TYPE  HP   ST  PC", True, (160, 160, 160))
        self.screen.blit(headers_txt, (self.panel_x + 10, y_offset))
        y_offset += 16

        for pcb in sorted(world.processes.values(), key=lambda p: p.pid):
            color = (255, 255, 200) if pcb.pid == self.selected_pid else (200, 200, 200)
            line = f"{pcb.pid:<4} {pcb.type[:4]:<5} {pcb.hp:<4} {pcb.state[:2]:<3} {pcb.pc}"
            txt = self.font.render(line, True, color)
            self.screen.blit(txt, (self.panel_x + 10, y_offset))
            y_offset += 15
            if y_offset > self.map_height_px - 100:
                more = self.font.render(f"... +{len(world.processes)} total", True, (120, 120, 120))
                self.screen.blit(more, (self.panel_x + 10, y_offset))
                break
        cmd_y = self.map_height_px - 290
        self.screen.blit(self.font.render("── COMMANDS ──", True, (100, 100, 100)),
                         (self.panel_x + 10, cmd_y))
        cmd_y += 15
        commands_help = [
            ("/          — відкрити shell", (150, 150, 255)),
            ("SPACE      — пауза / старт",  (200, 200, 200)),
            ("CREATE f x y — створити",     (200, 200, 200)),
            ("KILL <pid>   — знищити",       (200, 200, 200)),
            ("INFO <pid>   — інфо",          (200, 200, 200)),
            ("SPEED <1-10> — швидкість",     (200, 200, 200)),
            ("PAUSE / START",                (200, 200, 200)),
            ("SAVE_SIM / LOAD_SIM <name>",   (200, 200, 200)),
        ]
        for line, col in commands_help:
            self.screen.blit(self.font.render(line, True, col),
                             (self.panel_x + 10, cmd_y))
            cmd_y += 14

        leg_y = self.map_height_px - 145
        self.screen.blit(self.font.render("── MAP LEGEND ──", True, (100, 100, 100)),
                         (self.panel_x + 10, leg_y))
        leg_y += 15
        cell_legend = [
            ((50, 205, 50),   "Fern  (їжа трав.)"),
            ((85, 107, 47),   "Bush  (непрохідно)"),
            ((70, 130, 180),  "Water (непрохідно)"),
            ((105, 105, 105), "Rock  (непрохідно)"),
            ((138, 43, 226),  "Crystal (буст)"),
        ]
        for col, label in cell_legend:
            pygame.draw.rect(self.screen, col,
                             pygame.Rect(self.panel_x + 10, leg_y + 2, 10, 10))
            txt = self.font.render(label, True, (180, 180, 180))
            self.screen.blit(txt, (self.panel_x + 24, leg_y))
            leg_y += 14
        y_offset += 15
        cell_legend = [
            ((50, 205, 50),   "Fern  (їжа трав.)"),
            ((85, 107, 47),   "Bush  (непрохідно)"),
            ((70, 130, 180),  "Water (непрохідно)"),
            ((105, 105, 105), "Rock  (непрохідно)"),
            ((138, 43, 226),  "Crystal (буст)"),
        ]
        for col, label in cell_legend:
            pygame.draw.rect(self.screen, col,
                             pygame.Rect(self.panel_x + 10, y_offset + 2, 10, 10))
            txt = self.font.render(label, True, (180, 180, 180))
            self.screen.blit(txt, (self.panel_x + 24, y_offset))
            y_offset += 14

    def _draw_shell_bar(self, shell: "Shell") -> None:
        bar_y = self.map_height_px + 2
        bar_h = 44
        bar_rect = pygame.Rect(0, bar_y, self.map_width_px, bar_h)
        pygame.draw.rect(self.screen, (25, 25, 35), bar_rect)
        pygame.draw.rect(self.screen, (70, 70, 120), bar_rect, 1)

        if shell.active:
            cursor = "█" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
            prompt_txt = self.font.render(f"> {shell.input_buffer}{cursor}", True, (255, 255, 255))
            self.screen.blit(prompt_txt, (8, bar_y + 4))
            word = shell.input_buffer.strip().split()[0].lower() if shell.input_buffer.strip() else ""
            hint = SHELL_HINTS.get(word, "")
            if hint:
                self.screen.blit(self.font.render(hint, True, (120, 180, 255)), (8, bar_y + 22))
            else:
                self.screen.blit(self.font.render(
                    "ESC — закрити  |  ENTER — виконати  |  ↑↓ — історія",
                    True, (90, 90, 120)), (8, bar_y + 22))
        else:
            self.screen.blit(self.font.render(
                "> _   (натисніть  /  щоб ввести команду: CREATE KILL SPEED INFO PAUSE START SAVE_SIM LOAD_SIM)",
                True, (80, 80, 110)), (8, bar_y + 14))

    def _draw_messages(self) -> None:
        if not self._messages:
            return
        x, y = 4, 4
        for text, color in self._messages:
            surf = pygame.Surface((self.font.size(text)[0] + 6,
                                   self.font.get_height() + 2))
            surf.set_alpha(200)
            surf.fill((0, 0, 0))
            txt = self.font.render(text, True, color)
            surf.blit(txt, (3, 1))
            self.screen.blit(surf, (x, y))
            y += self.font.get_height() + 3