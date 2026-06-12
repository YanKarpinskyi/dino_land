"""main.py — точка входу, головний цикл."""
import sys
import pygame
import random                          # ← додати
from typing import Optional

import constants as C
from world import World
from scheduler import Scheduler
from logger import Logger
from renderer import Renderer
from shell import Shell
from save_load import save_simulation, load_simulation
from interpreter import _terminate
from pcb import PCB                     # ← додати
import parser as p                     # ← додати (бажано перейменувати модуль пізніше)


class DinoLand:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 700))
        pygame.display.set_caption("Країна Динозаврів")
        self.clock = pygame.time.Clock()
        self.world = World()
        self.scheduler = Scheduler()
        self.logger = Logger()
        self.shell = Shell(self)
        self.renderer = Renderer(self.screen, self.world, self.scheduler, self.shell)
        self.shell.renderer = self.renderer
        self.paused = False
        self.running = True
        
        # Завантажити початкову карту
        self.world.load_map(C.MAPS_DIR + "/default.txt")
        self._spawn_initial_population()

    def _spawn_initial_population(self):
        spawns = [
            ("herbivore.txt", 10),
            ("predator.txt", 4),
            ("pterodactyl.txt", 3),
            ("hunter.txt", 2),
        ]
        for filename, count in spawns:
            filepath = C.BEHAVIORS_DIR + "/" + filename
            try:
                instructions, labels = p.parse_program(filepath)
            except Exception as e:
                print(f"Не вдалося завантажити {filename}: {e}")
                continue

            placed = 0
            attempts = 0
            while placed < count and attempts < 1000:
                attempts += 1
                x = random.randint(1, self.world.width - 2)
                y = random.randint(1, self.world.height - 2)
                
                if self.world.is_occupied(x, y) or not self.world.is_passable(x, y, "herbivore"):
                    continue

                pid = self.scheduler.next_pid()
                pcb = PCB.from_file(
                    pid=pid, 
                    filename=filepath, 
                    x=x, 
                    y=y,
                    direction=random.choice(["N", "S", "E", "W"]),
                    tick=0
                )
                pcb.program = instructions
                pcb.labels = labels
                
                self.world.add_entity(pcb)
                self.scheduler.enqueue(pcb)
                placed += 1

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if self.shell.active:
                # Shell активний — всі клавіші йдуть до нього
                self.shell.handle_keydown(event)
            elif event.key == pygame.K_SLASH or event.unicode == "/":
                self.shell.activate()
            elif event.key == pygame.K_SPACE:
                self.paused = not self.paused

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                self._handle_event(event)

            if not self.paused:
                for _ in range(C.TICKS_PER_FRAME):
                    self.scheduler.tick(self.world, self.logger)

            self.renderer.draw_frame(self.world, self.scheduler, self.shell, self.paused)
            pygame.display.flip()
            self.clock.tick(C.FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = DinoLand()
    game.run()