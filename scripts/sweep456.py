#!/usr/bin/env python3
"""Full 456-sentence clean sweep: every '# text =' line of the UD-GDT test set."""

import argparse
import sys

from cadmus.eval import harness


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Full 456-sentence clean sweep over a UD conllu file."
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Path to an alternative .conllu file (default: bundled el_gdt-ud-test.conllu)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each violation as it is found",
    )
    args = parser.parse_args(argv)
    print(harness.run_sweep(verbose=args.verbose, path=args.path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
