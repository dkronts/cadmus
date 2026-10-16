import argparse
import json
import sys

from . import __version__
from .checker import CadmusChecker
from .corpora import BROKEN_SENTENCES, DEMO_SENTENCES
from .data import filter_violations


def _render(violations):
    if not violations:
        print("OK: no violations found.")
        return
    for v in violations:
        extra = f"  → {v.suggestion}" if v.suggestion else ""
        print(f"[{v.rule}/{v.severity}] {v.message}{extra}  "
              f"(offset {v.start_char}-{v.end_char}) in: {v.sentence}")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="cadmus",
        description=f"Greek grammar/syntax checker (Cadmus v{__version__})",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="check text from a file or stdin")
    p_check.add_argument("path", nargs="?", help="text file (UTF-8); omit to read stdin")
    p_check.add_argument("--json", action="store_true", dest="as_json")
    p_check.add_argument("--severity", choices=["low", "medium", "high"],
                         help="only report violations at or above this severity")
    p_check.add_argument("--rules", metavar="R1,R2",
                         help="comma-separated rule ids to report")
    p_check.add_argument("--quiet", action="store_true",
                         help="print nothing; exit code 1 if any (filtered) violation remains")

    sub.add_parser("demo", help="run on the built-in demo corpus")

    p_eval = sub.add_parser("eval", help="measure FP on clean UD text and recall on injected errors")
    p_eval.add_argument("--n", type=int, default=100)
    p_eval.add_argument("--seed", type=int, default=42)
    p_eval.add_argument("-v", "--verbose", action="store_true")

    p_export = sub.add_parser("export", help="emit aligned (broken->correct) training pairs from UD-GDT")
    p_export.add_argument("--n", type=int, default=200)
    p_export.add_argument("--seed", type=int, default=42)
    p_export.add_argument("--format", choices=["jsonl", "json"], default="jsonl")
    p_export.add_argument("--with-check", action="store_true", dest="with_check",
                          help="run the checker on each broken sentence and attach detected/suggestion (needs the model)")

    args = p.parse_args(argv)
    checker = CadmusChecker()

    if args.cmd == "demo":
        for corpus, label in ((DEMO_SENTENCES, "demo corpus (expect clean)"), (BROKEN_SENTENCES, "LLM-style errors (expect flags)")):
            print(f"--- {label} ---")
            for s in corpus:
                vs = checker.check(s)
                mark = "FLAG" if vs else "ok"
                print(f"[{mark:4}] {s}")
                for v in vs:
                    extra = f"  → {v.suggestion}" if v.suggestion else ""
                    print(f"        [{v.severity}] {v.message}{extra}")
        return 0

    if args.cmd == "eval":
        from .eval.harness import run_eval

        print(run_eval(n=args.n, seed=args.seed, verbose=args.verbose))
        return 0

    if args.cmd == "export":
        from .export import annotate_with_check, corpus_pairs

        pairs = corpus_pairs(n=args.n, seed=args.seed)
        if args.with_check:
            annotate_with_check(pairs, checker.check)
        if args.format == "json":
            print(json.dumps(pairs, ensure_ascii=False, indent=2))
        else:
            for p in pairs:
                print(json.dumps(p, ensure_ascii=False))
        return 0

    text = open(args.path, encoding="utf-8").read() if args.path else sys.stdin.read()
    violations = checker.check(text)
    rules = args.rules.split(",") if args.rules else None
    violations = filter_violations(violations, min_severity=args.severity, rules=rules)
    if args.quiet:
        return 1 if violations else 0
    if args.as_json:
        print(json.dumps([v.as_dict() for v in violations], ensure_ascii=False, indent=2))
    else:
        _render(violations)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
