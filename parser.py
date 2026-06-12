"""parser.py — парсер файлів поведінки (.txt) з кешуванням."""
from __future__ import annotations
import os
import constants as C

behavior_cache: dict[str, tuple[list, dict]] = {}


class ParseError(Exception):
    def __init__(self, line_no: int, message: str):
        super().__init__(f"Рядок {line_no}: {message}")
        self.line_no = line_no
        self.message = message


_INSTRUCTIONS = {
    "ШАГ":            0,
    "НАЛІВО":         0,
    "НАПРАВО":        0,
    "РОЗВЕРНУТИСЬ":   0,
    "ПОРІВНЯТИ":      2,
    "ПЕРЕЙТИ":        1,
    "ПЕРЕЙТИ_РІВНО":  1,
    "ПЕРЕЙТИ_БІЛЬШЕ": 1,
    "ПЕРЕЙТИ_МЕНШЕ":  1,
    "ВСТАНОВИТИ":     2,
    "ДОДАТИ":         2,
    "ЗМЕНШИТИ":       2,
    "АТАКА":          1,
    "SCAN":           2,
    "LOOK":           0,
    "CREATE":         1,
    "ЗЦІЛИТИ":        1,
    "ВИПАДКОВО":      0,
    "МІТКА":          1,
}


def parse_program(filename: str) -> tuple[list, dict]:
    """
    Парсить файл поведінки та повертає (instructions, labels).
    Результат кешується. Кидає ParseError при синтаксичній помилці.
    """
    path = _resolve_path(filename)
    if path in behavior_cache:
        return behavior_cache[path]

    instructions: list[tuple] = []  
    labels: dict[str, int] = {}  

    with open(path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    for line_no, raw in enumerate(raw_lines, start=1):
        line = raw.split(";")[0].strip()
        if not line:
            continue

        parts = line.split()
        opcode = parts[0].upper()

        if opcode not in _INSTRUCTIONS:
            raise ParseError(line_no, f"Невідома інструкція: '{parts[0]}'")

        expected_args = _INSTRUCTIONS[opcode]
        actual_args = parts[1:]

        if opcode == "МІТКА":
            if len(actual_args) != 1:
                raise ParseError(line_no, "МІТКА потребує одного аргументу")
            label_name = actual_args[0]
            labels[label_name] = len(instructions)
            continue

        if len(actual_args) != expected_args:
            raise ParseError(
                line_no,
                f"{opcode} очікує {expected_args} аргументів, отримано {len(actual_args)}"
            )

        instructions.append(tuple([opcode] + actual_args))

    result = (instructions, labels)
    behavior_cache[path] = result
    return result


def invalidate_cache(filename: str) -> None:
    """Інвалідувати кеш для конкретного файлу (для RELOAD у shell)."""
    path = _resolve_path(filename)
    behavior_cache.pop(path, None)


def _resolve_path(filename: str) -> str:
    """Якщо шлях не абсолютний — шукати у папці behaviors/."""
    if os.path.isabs(filename):
        return filename
    if os.path.exists(filename):
        return os.path.abspath(filename)
    candidate = os.path.join(C.BEHAVIORS_DIR, filename)
    if os.path.exists(candidate):
        return os.path.abspath(candidate)
    return os.path.abspath(filename)  # поверне навіть якщо не існує (помилка при відкритті)