import argparse
import contextlib
import errno
import io
import json
import sys

from . import __version__
from .checker import CadmusChecker
from .corpora import BROKEN_SENTENCES, DEMO_SENTENCES
from .data import filter_violations


def _positive_int(value):
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("--batch-size must be >= 1")
    return n


def _read_error_line(path, exc):
    code = getattr(exc, "errno", None)
    if code == errno.ENOENT:
        return f"no such file: {path}"
    if code == errno.EISDIR:
        return f"is a directory: {path}"
    if code == errno.EACCES:
        return f"permission denied: {path}"
    return f"{path}: {exc}"


def _open_input(path):
    try:
        handle = open(path, encoding="utf-8")
    except OSError as exc:
        print(f"cadmus: error: {_read_error_line(path, exc)}", file=sys.stderr)
        return None
    try:
        data = handle.read()
    except (UnicodeDecodeError, OSError) as exc:
        handle.close()
        print(f"cadmus: error: {_read_error_line(path, exc)}", file=sys.stderr)
        return None
    handle.close()
    return io.StringIO(data)


def _render(violations):
    if not violations:
        print("OK: no violations found.")
        return
    for v in violations:
        extra = f"  → {v.suggestion}" if v.suggestion else ""
        mark = " ✓confirmed" if getattr(v, "confirmed", None) else ""
        print(f"[{v.rule}/{v.severity}] {v.message}{extra}{mark}  "
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
    p_check.add_argument("--deep", action="store_true",
                         help="confirm each suggestion with a second analysis pass "
                              "(slower: one extra analysis per suggestion)")

    sub.add_parser("demo", help="run on the built-in demo corpus")

    p_eval = sub.add_parser("eval", help="measure FP on clean UD text and recall on injected errors")
    p_eval.add_argument("--n", type=int, default=100)
    p_eval.add_argument("--seed", type=int, default=42)
    p_eval.add_argument("-v", "--verbose", action="store_true")
    p_eval.add_argument("--targeted-path", dest="targeted_path", default=None,
                        help="conllu file for the targeted construction pool "
                             "(default UD-GDT asset)")
    p_eval.add_argument("--no-targeted", dest="targeted", action="store_false", default=True,
                        help="skip the targeted construction-pool recall pass")
    p_eval.add_argument("--path", dest="path", default=None,
                        help="conllu file for the clean FP-scan and recall pools "
                             "(default UD-GDT asset)")

    p_export = sub.add_parser("export", help="emit aligned (broken->correct) training pairs from UD-GDT")
    p_export.add_argument("--n", type=int, default=200)
    p_export.add_argument("--seed", type=int, default=42)
    p_export.add_argument("--format", choices=["jsonl", "json"], default="jsonl")
    p_export.add_argument("--with-check", action="store_true", dest="with_check",
                          help="run the checker on each broken sentence and attach detected/suggestion (needs the model)")

    p_watch = sub.add_parser("watch", help="check a stream of texts (one per line) as they arrive")
    p_watch.add_argument("path", nargs="?", help="file to read; omit to read stdin")
    p_watch.add_argument("--json", action="store_true", dest="as_json")
    p_watch.add_argument("--severity", choices=["low", "medium", "high"],
                         help="only report violations at or above this severity")
    p_watch.add_argument("--rules", metavar="R1,R2",
                         help="comma-separated rule ids to report")

    p_batch = sub.add_parser("batch", help="check many texts (one per line) via batched processing")
    p_batch.add_argument("path", nargs="?", help="file to read; omit to read stdin")
    p_batch.add_argument("--json", action="store_true", dest="as_json")
    p_batch.add_argument("--severity", choices=["low", "medium", "high"],
                         help="only report violations at or above this severity")
    p_batch.add_argument("--rules", metavar="R1,R2",
                         help="comma-separated rule ids to report")
    p_batch.add_argument("--batch-size", type=_positive_int, default=32, dest="batch_size",
                         help="texts per pipeline batch (default 32)")

    p_diag = sub.add_parser("diagnose", help="report analyzer feature coverage (why rules stay silent)")
    p_diag.add_argument("path", nargs="?", help="text file (UTF-8); omit to read stdin")

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

        try:
            report = run_eval(n=args.n, seed=args.seed, verbose=args.verbose,
                              targeted=args.targeted, targeted_path=args.targeted_path,
                              path=args.path)
        except (OSError, UnicodeDecodeError) as exc:
            path = getattr(exc, "filename", None) or args.path or args.targeted_path
            if isinstance(exc, UnicodeDecodeError):
                line = f"invalid utf-8: {path}"
            else:
                line = _read_error_line(path, exc)
            print(f"cadmus: error: {line}", file=sys.stderr)
            return 2
        print(report)
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

    if args.cmd == "watch":
        from .stream import iter_checked

        rules = args.rules.split(",") if args.rules else None
        stream = (_open_input(args.path) if args.path
                  else contextlib.nullcontext(sys.stdin))
        if stream is None:
            return 2
        with stream as stream:
            for text, vs in iter_checked(stream, checker.check, min_severity=args.severity, rules=rules):
                if args.as_json:
                    print(json.dumps({"text": text, "violations": [v.as_dict() for v in vs]},
                                     ensure_ascii=False), flush=True)
                elif vs:
                    for v in vs:
                        extra = f"  → {v.suggestion}" if v.suggestion else ""
                        print(f"[{v.rule}/{v.severity}] {v.message}{extra}  :: {text}", flush=True)
        return 0

    if args.cmd == "batch":
        rules = args.rules.split(",") if args.rules else None
        stream = (_open_input(args.path) if args.path
                  else contextlib.nullcontext(sys.stdin))
        if stream is None:
            return 2
        with stream as stream:
            lines = [ln.rstrip("\n") for ln in stream if ln.strip()]
        for text, vs in zip(lines, checker.check_batch(lines, batch_size=args.batch_size)):
            vs = filter_violations(vs, min_severity=args.severity, rules=rules)
            if args.as_json:
                print(json.dumps({"text": text, "violations": [v.as_dict() for v in vs]},
                                 ensure_ascii=False))
            elif vs:
                for v in vs:
                    extra = f"  → {v.suggestion}" if v.suggestion else ""
                    print(f"[{v.rule}/{v.severity}] {v.message}{extra}  :: {text}")
        return 0

    if args.cmd == "diagnose":
        if args.path:
            f = _open_input(args.path)
            if f is None:
                return 2
            with f:
                text = f.read()
        else:
            text = sys.stdin.read()
        print(checker.diagnose(text))
        return 0

    if args.path:
        f = _open_input(args.path)
        if f is None:
            return 2
        with f:
            text = f.read()
    else:
        text = sys.stdin.read()
    violations = checker.check(text, deep=getattr(args, "deep", False))
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
