#!/usr/bin/env python3
"""Full 456-sentence clean sweep: every '# text =' line of the UD-GDT test set."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cadmus.eval.harness import run_sweep

if __name__ == "__main__":
    print(run_sweep())
