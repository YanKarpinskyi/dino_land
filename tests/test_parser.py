import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import parser

def test_parse_herbivore():
    instr, labels = parser.parse_program("herbivore.txt")
    assert len(instr) > 0
    print("test_parse_herbivore OK")

if __name__ == "__main__":
    test_parse_herbivore()