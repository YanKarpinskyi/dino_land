"""constants.py — завантажує config.json та оголошує всі числові константи."""
import json
import os

_config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(_config_path, "r", encoding="utf-8") as _f:
    _cfg = json.load(_f)

# --- Map ---
MAP_WIDTH: int = _cfg["MAP_WIDTH"]
MAP_HEIGHT: int = _cfg["MAP_HEIGHT"]

# --- Rendering ---
FPS: int = _cfg["FPS"]
TICKS_PER_FRAME: int = _cfg["TICKS_PER_FRAME"]
CELL_SIZE_PX: int = _cfg["CELL_SIZE_PX"]
SHELL_PAUSES: bool = _cfg["SHELL_PAUSES"]

# --- Simulation limits ---
MAX_PROCESSES: int = _cfg["MAX_PROCESSES"]
MAX_SPEARS_PER_HUNTER: int = _cfg["MAX_SPEARS_PER_HUNTER"]

# --- Fern respawn ---
FERN_RESPAWN_INTERVAL: int = _cfg["FERN_RESPAWN_INTERVAL"]
FERN_RESPAWN_COUNT: int = _cfg["FERN_RESPAWN_COUNT"]

# --- HP ---
HP_DECAY_PER_TICK: int = _cfg["HP_DECAY_PER_TICK"]
HP_DECAY_INTERVAL: int = _cfg["HP_DECAY_INTERVAL"]
ATTACK_POWER: dict = _cfg["ATTACK_POWER"]    
INITIAL_HP: dict = _cfg["INITIAL_HP"]         

# --- Crystal ---
CRYSTAL_BOOST_TICKS: int = _cfg["CRYSTAL_BOOST_TICKS"]
CRYSTAL_BOOST_IPT: int = 3                   

# --- Spear ---
SPEAR_LIFESPAN_MIN: int = _cfg["SPEAR_LIFESPAN_MIN"]
SPEAR_LIFESPAN_MAX: int = _cfg["SPEAR_LIFESPAN_MAX"]

# --- Cell codes ---
CELL_EMPTY = 0
CELL_FERN = 1
CELL_BUSH = 2
CELL_WATER = 3
CELL_ROCK = 4
CELL_CRYSTAL = 5
CELL_BORDER = 255

PASSABLE_CELLS = {CELL_EMPTY, CELL_FERN, CELL_CRYSTAL}
IMPASSABLE_CELLS = {CELL_BUSH, CELL_WATER, CELL_ROCK, CELL_BORDER}

# Pterodactyl ignores water/rock
PTERODACTYL_PASSABLE = PASSABLE_CELLS | {CELL_WATER, CELL_ROCK}

# --- Entity types ---
TYPE_HERBIVORE = "herbivore"
TYPE_PREDATOR = "predator"
TYPE_PTERODACTYL = "pterodactyl"
TYPE_HUNTER = "hunter"
TYPE_SPEAR = "spear"

ALL_TYPES = {TYPE_HERBIVORE, TYPE_PREDATOR, TYPE_PTERODACTYL, TYPE_HUNTER, TYPE_SPEAR}

# --- Directions ---
DIR_N = "N"
DIR_S = "S"
DIR_E = "E"
DIR_W = "W"

DIRECTION_DELTA = {
    DIR_N: (0, -1),
    DIR_S: (0, 1),
    DIR_E: (1, 0),
    DIR_W: (-1, 0),
}

TURN_LEFT = {DIR_N: DIR_W, DIR_W: DIR_S, DIR_S: DIR_E, DIR_E: DIR_N}
TURN_RIGHT = {DIR_N: DIR_E, DIR_E: DIR_S, DIR_S: DIR_W, DIR_W: DIR_N}
TURN_AROUND = {DIR_N: DIR_S, DIR_S: DIR_N, DIR_E: DIR_W, DIR_W: DIR_E}

# --- Process states ---
STATE_NEW = "NEW"
STATE_READY = "READY"
STATE_RUNNING = "RUNNING"
STATE_TERMINATED = "TERMINATED"

# --- Behaviors directory ---
BEHAVIORS_DIR = os.path.join(os.path.dirname(__file__), "behaviors")
MAPS_DIR = os.path.join(os.path.dirname(__file__), "maps")

FERN_HEAL = 15

CORPSE_HEAL = 30