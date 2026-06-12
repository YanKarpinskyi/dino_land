"""interpreter.py — виконання інструкцій асемблерної мови."""
from __future__ import annotations
import random
from typing import TYPE_CHECKING
import constants as C
from pcb import PCB

if TYPE_CHECKING:
    from world import World
    from logger import Logger
    from scheduler import Scheduler


class ProcessRuntimeError(Exception):
    pass


def execute_instruction(pcb: PCB, world: "World", logger: "Logger",
                        scheduler: "Scheduler", tick: int) -> None:
    """
    Виконати одну інструкцію з program[pc].
    Після виконання pc += 1 (або перехід). Якщо pc >= len(program) → pc = 0.
    """
    if not pcb.program:
        return

    if pcb.pc >= len(pcb.program):
        pcb.pc = 0

    instr = pcb.program[pcb.pc]
    opcode = instr[0]
    args = instr[1:]

    try:
        _dispatch(opcode, args, pcb, world, logger, scheduler, tick)
    except ProcessRuntimeError as e:
        logger.log_event(tick, "CRASH", pid=pcb.pid, reason=str(e))
        pcb.hp = 0
        return

def _dispatch(opcode: str, args: tuple, pcb: PCB, world: "World",
              logger: "Logger", scheduler: "Scheduler", tick: int) -> None:
    """Велика конструкція match/case по opcode."""

    if opcode == "ШАГ":
        _do_step(pcb, world, tick)
        pcb.pc += 1

    elif opcode == "НАЛІВО":
        pcb.direction = C.TURN_LEFT[pcb.direction]
        pcb.pc += 1

    elif opcode == "НАПРАВО":
        pcb.direction = C.TURN_RIGHT[pcb.direction]
        pcb.pc += 1

    elif opcode == "РОЗВЕРНУТИСЬ":
        pcb.direction = C.TURN_AROUND[pcb.direction]
        pcb.pc += 1

    elif opcode == "ПОРІВНЯТИ":
        a = pcb.resolve_arg(args[0])
        b = pcb.resolve_arg(args[1])
        pcb.flags["eq"] = (a == b)
        pcb.flags["gt"] = (a > b)
        pcb.flags["lt"] = (a < b)
        pcb.pc += 1

    elif opcode == "ПЕРЕЙТИ":
        _jump_to(pcb, args[0])

    elif opcode == "ПЕРЕЙТИ_РІВНО":
        if pcb.flags["eq"]:
            _jump_to(pcb, args[0])
        else:
            pcb.pc += 1

    elif opcode == "ПЕРЕЙТИ_БІЛЬШЕ":
        if pcb.flags["gt"]:
            _jump_to(pcb, args[0])
        else:
            pcb.pc += 1

    elif opcode == "ПЕРЕЙТИ_МЕНШЕ":
        if pcb.flags["lt"]:
            _jump_to(pcb, args[0])
        else:
            pcb.pc += 1

    elif opcode == "ВСТАНОВИТИ":
        reg, val = args[0].upper(), pcb.resolve_arg(args[1])
        pcb.set_register(reg, val)
        pcb.pc += 1

    elif opcode == "ДОДАТИ":
        reg = args[0].upper()
        val = pcb.resolve_arg(args[1])
        pcb.set_register(reg, pcb.get_register(reg) + val)
        pcb.pc += 1

    elif opcode == "ЗМЕНШИТИ":
        reg = args[0].upper()
        val = pcb.resolve_arg(args[1])
        pcb.set_register(reg, pcb.get_register(reg) - val)
        pcb.pc += 1

    elif opcode == "АТАКА":
        _do_attack(pcb, args[0], world, logger, scheduler, tick)
        pcb.pc += 1

    elif opcode == "SCAN":
        radius = int(args[0])
        if radius < 0:
            raise ProcessRuntimeError("invalid argument: negative radius")
        target_type = args[1].lower()
        target = world.find_nearest(pcb.x, pcb.y, radius, target_type)
        pcb.set_register("R1", target.pid if target else 0)
        pcb.pc += 1

    elif opcode == "LOOK":
        nx, ny = world.get_front_cell(pcb)
        front_pid = world.entity_map[ny][nx] if (0 <= ny < world.height and
                                                   0 <= nx < world.width) else None
        if front_pid is not None:
            pcb.set_register("R1", front_pid)  
        else:
            code = world.get_cell(nx, ny)
            if code == C.CELL_EMPTY or code == C.CELL_FERN or code == C.CELL_CRYSTAL:
                pcb.set_register("R1", 0)           
            else:
                pcb.set_register("R1", -code)        
        pcb.pc += 1

    elif opcode == "CREATE":
        _do_create(pcb, args[0], world, logger, scheduler, tick)
        pcb.pc += 1

    elif opcode == "ЗЦІЛИТИ":
        val = pcb.resolve_arg(args[0])
        pcb.hp += val
        pcb.pc += 1

    elif opcode == "ВИПАДКОВО":
        pcb.set_register("R1", random.randint(0, 3))
        pcb.pc += 1

    else:
        raise ProcessRuntimeError(f"unknown opcode: {opcode}")

    if pcb.pc >= len(pcb.program):
        pcb.pc = 0


# ── Допоміжні функції ─────────────────────────────────────────────────────────

def _do_step(pcb: PCB, world: "World", tick: int) -> None:
    nx, ny = world.get_front_cell(pcb)
    if not world.is_passable(nx, ny, pcb.type):
        return 
    if world.is_occupied(nx, ny):
        return
    world.move_entity(pcb, nx, ny)
    world.consume_cell(pcb, tick)


def _jump_to(pcb: PCB, label: str) -> None:
    if label not in pcb.labels:
        raise ProcessRuntimeError(f"label not found: {label}")
    pcb.pc = pcb.labels[label]


def _do_attack(pcb: PCB, arg: str, world: "World", logger: "Logger",
               scheduler: "Scheduler", tick: int) -> None:
    target_pid = pcb.resolve_arg(arg)
    victim = world.processes.get(target_pid)
    if victim is None:
        logger.log_event(tick, "MISS", attacker_pid=pcb.pid, target_pid=target_pid)
        return
    if pcb.type == C.TYPE_SPEAR and victim.type == C.TYPE_SPEAR:
        return

    damage = C.ATTACK_POWER.get(pcb.type, 0)
    victim.hp -= damage
    logger.log_event(tick, "KILLED" if victim.hp <= 0 else "HIT",
                     attacker_pid=pcb.pid, target_pid=victim.pid,
                     hp_dealt=damage, victim_type=victim.type)
    if victim.hp <= 0:
        _terminate(victim, world, logger, scheduler, tick)


def _terminate(pcb: PCB, world: "World", logger: "Logger",
               scheduler: "Scheduler", tick: int) -> None:
    pcb.hp = 0
    pcb.state = C.STATE_TERMINATED
    lifespan_ticks = tick - pcb.created_at_tick
    logger.record_death(pcb, tick, lifespan_ticks)

    if pcb.type == C.TYPE_SPEAR and pcb.creator_pid is not None:
        creator = world.processes.get(pcb.creator_pid)
        if creator:
            creator.active_spears = max(0, creator.active_spears - 1)

    if pcb.type in (C.TYPE_HERBIVORE, C.TYPE_PTERODACTYL):
        world.add_corpse(pcb)

    world.remove_entity(pcb)
    scheduler.remove(pcb.pid)


def _do_create(pcb: PCB, filename: str, world: "World", logger: "Logger",
               scheduler: "Scheduler", tick: int) -> None:
    import parser as p
    import random

    if len(world.processes) >= C.MAX_PROCESSES:
        return
    if pcb.type == C.TYPE_HUNTER and pcb.active_spears >= C.MAX_SPEARS_PER_HUNTER:
        return

    nx, ny = world.get_front_cell(pcb)
    if world.is_occupied(nx, ny) or not world.is_passable(nx, ny, C.TYPE_SPEAR):
        return

    try:
        instructions, labels = p.parse_program(filename)
    except (FileNotFoundError, p.ParseError) as e:
        logger.log_event(tick, "CREATE_FAIL", creator_pid=pcb.pid, file=filename, reason=str(e))
        return

    lifespan = None
    from pcb import _type_from_filename
    new_type = _type_from_filename(filename)
    if new_type == C.TYPE_SPEAR:
        lifespan = random.randint(C.SPEAR_LIFESPAN_MIN, C.SPEAR_LIFESPAN_MAX)

    new_pid = scheduler.next_pid()

    new_pcb = PCB.from_file(
        pid=new_pid,
        filename=filename,
        x=nx, y=ny,
        direction=pcb.direction,
        tick=tick,
        creator_pid=pcb.pid,
        lifespan=lifespan,
    )
    new_pcb.program = instructions
    new_pcb.labels = labels

    world.add_entity(new_pcb)
    scheduler.enqueue(new_pcb)
    new_pcb.state = C.STATE_READY

    if pcb.type == C.TYPE_HUNTER and new_type == C.TYPE_SPEAR:
        pcb.active_spears += 1

    logger.log_event(tick, "CREATED", pid=new_pid, type=new_type,
                     x=nx, y=ny, creator_pid=pcb.pid)