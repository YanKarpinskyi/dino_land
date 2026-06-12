"""shell.py — парсер shell-команд."""
from __future__ import annotations
import pygame
import constants as C
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import DinoLand


class Shell:
    def __init__(self, game: "DinoLand"):
        self.game = game
        self.active = False
        self.input_buffer = ""
        self.history: list[str] = []
        self.history_idx = 0
        self.renderer = None

    def activate(self) -> None:
        """Відкрити shell-консоль."""
        self.active = True
        self.input_buffer = ""
        self.history_idx = len(self.history)

    def deactivate(self) -> None:
        self.active = False

    def handle_keydown(self, event: pygame.event.Event) -> None:
        if not self.active:
            return

        if event.key == pygame.K_RETURN:
            self._execute(self.input_buffer)
            self.input_buffer = ""
            if C.SHELL_PAUSES:  # з constants.py: SHELL_PAUSES
                self.game.paused = True
        elif event.key == pygame.K_ESCAPE:
            self.deactivate()
        elif event.key == pygame.K_BACKSPACE:
            self.input_buffer = self.input_buffer[:-1]
        elif event.key == pygame.K_UP:
            if self.history_idx > 0:
                self.history_idx -= 1
                self.input_buffer = self.history[self.history_idx]
        elif event.key == pygame.K_DOWN:
            if self.history_idx < len(self.history) - 1:
                self.history_idx += 1
                self.input_buffer = self.history[self.history_idx]
            else:
                self.history_idx = len(self.history)
                self.input_buffer = ""
        else:
            self.input_buffer += event.unicode

    def _msg(self, text: str, color: tuple = (255, 255, 150)) -> None:
        """Вивести повідомлення на екран через renderer."""
        if self.renderer:
            self.renderer.post_message(text, color)
        else:
            print(text)

    def _execute(self, cmd_line: str) -> None:
        if not cmd_line.strip():
            return
        self.history.append(cmd_line)
        self.history_idx = len(self.history)
        parts = cmd_line.strip().split()
        if not parts:
            return
        try:
            self._dispatch(parts[0].upper(), parts)
        except Exception as e:
            self._msg(f"Error: {e}", (255, 80, 80))

    def _dispatch(self, command: str, parts: list[str]) -> None:
        if command == "CREATE" and len(parts) == 4:
            self._cmd_create(parts[1], int(parts[2]), int(parts[3]))
        elif command == "KILL" and len(parts) == 2:
            self._cmd_kill(int(parts[1]))
        elif command == "PAUSE":
            self.game.paused = True
            self._msg("Simulation paused.", (255, 200, 100))
        elif command == "START":
            self.game.paused = False
            self._msg("Simulation started.", (100, 255, 100))
        elif command == "SPEED" and len(parts) == 2:
            self._cmd_speed(int(parts[1]))
        elif command == "INFO" and len(parts) == 2:
            self._cmd_info(int(parts[1]))
        elif command == "RELOAD" and len(parts) == 2:
            self._cmd_reload(parts[1])
        elif command == "SAVE_STATS":
            self.game.logger.save_report()
        elif command == "SAVE_SIM" and len(parts) == 2:
            self._cmd_save_sim(parts[1])
        elif command == "LOAD_SIM" and len(parts) == 2:
            self._cmd_load_sim(parts[1])
        elif command == "MAP" and len(parts) == 3 and parts[1].upper() == "SAVE":
            self.game.world.save_map(parts[2])
        elif command == "MAP" and len(parts) == 3 and parts[1].upper() == "LOAD":
            self.game.world.load_map(parts[2])
        else:
            self._msg(f"Unknown: {command}  — спробуйте / і введіть команду", (255, 150, 50))

    def _cmd_create(self, filename: str, x: int, y: int) -> None:
        import parser as p
        from pcb import PCB, _type_from_filename
        import random

        if not (0 <= x < self.game.world.width and 0 <= y < self.game.world.height):
            self._msg("Coordinates out of bounds", (255, 80, 80))
            return
        if self.game.world.is_occupied(x, y):
            self._msg("Cell occupied", (255, 80, 80))
            return
        if len(self.game.world.processes) >= C.MAX_PROCESSES:
            self._msg("MAX_PROCESSES reached", (255, 80, 80))
            return

        try:
            instructions, labels = p.parse_program(filename)
        except FileNotFoundError:
            self._msg(f"File not found: {filename}", (255, 80, 80))
            return

        new_type = _type_from_filename(filename)
        lifespan = None
        if new_type == C.TYPE_SPEAR:
            lifespan = random.randint(C.SPEAR_LIFESPAN_MIN, C.SPEAR_LIFESPAN_MAX)

        new_pid = self.game.scheduler.next_pid()
        pcb = PCB.from_file(
            pid=new_pid, filename=filename, x=x, y=y,
            direction=C.DIR_N, tick=self.game.scheduler.tick_count,
            lifespan=lifespan
        )
        pcb.program = instructions
        pcb.labels = labels
        self.game.world.add_entity(pcb)
        self.game.scheduler.enqueue(pcb)

    def _cmd_kill(self, pid: int) -> None:
        from interpreter import _terminate
        pcb = self.game.world.processes.get(pid)
        if pcb:
            _terminate(pcb, self.game.world, self.game.logger,
                       self.game.scheduler, self.game.scheduler.tick_count)

    def _cmd_speed(self, speed: int) -> None:
        import constants as C
        C.TICKS_PER_FRAME = max(1, min(10, speed))

    def _cmd_info(self, pid: int) -> None:
        pcb = self.game.world.processes.get(pid)
        if pcb:
            lines = [
                f"PID:{pcb.pid} Type:{pcb.type} HP:{pcb.hp}",
                f"Pos:({pcb.x},{pcb.y}) Dir:{pcb.direction} State:{pcb.state}",
                f"R1={pcb.registers[0]} R2={pcb.registers[1]} R3={pcb.registers[2]} R4={pcb.registers[3]}",
                f"PC:{pcb.pc} IPT:{pcb.instructions_per_tick} Pri:{pcb.priority}",
            ]
            for l in lines:
                self._msg(l, (180, 230, 255))
        else:
            self._msg(f"PID {pid} not found", (255, 80, 80))

    def _cmd_reload(self, filename: str) -> None:
        import parser as p
        p.invalidate_cache(filename)
        self._msg(f"Reloaded {filename}")

    def _cmd_save_sim(self, name: str) -> None:
        from save_load import save_simulation
        save_simulation(name, self.game.world, self.game.scheduler, self.game.logger)

    def _cmd_load_sim(self, name: str) -> None:
        from save_load import load_simulation
        load_simulation(name, self.game.world, self.game.scheduler, self.game.logger)

    def render(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        if not self.active:
            return
        # Чорна смуга знизу
        rect = pygame.Rect(0, surface.get_height() - 40, surface.get_width(), 40)
        pygame.draw.rect(surface, (0, 0, 0), rect)
        pygame.draw.rect(surface, (255, 255, 255), rect, 1)

        prompt = font.render("> " + self.input_buffer, True, (255, 255, 255))
        surface.blit(prompt, (5, surface.get_height() - 35))