#!/usr/bin/env python3
"""build skill artifact through the shared toolkit."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.skill_project_toolkit import main
if __name__ == '__main__':
    main(['build', *sys.argv[1:]])
