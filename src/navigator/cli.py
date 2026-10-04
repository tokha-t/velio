from __future__ import annotations

import argparse


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="navigator")
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("extract", "resolve", "merge", "changes", "validate", "no-rule-findings", "export-web", "all"):
        commands.add_parser(name)
    lookup = commands.add_parser("lookup")
    lookup.add_argument("--as-of", required=True)
    lookup.add_argument("--address")
    extract = commands.choices["extract"]
    extract.add_argument("--pilot", action="store_true")
    extract.add_argument("--smoke", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "extract":
        from .extract import run

        run(pilot=args.pilot, smoke=args.smoke)
        return 0
    if args.command == "lookup":
        from .lookup import run

        run(as_of=args.as_of, address_id=args.address)
        return 0
    if args.command == "merge":
        from .merge import run

        run()
        return 0
    if args.command == "changes":
        from .changes import run

        run()
        return 0
    if args.command == "validate":
        from .validate import run

        run()
        return 0
    if args.command == "no-rule-findings":
        from .findings import run

        run()
        return 0
    if args.command == "export-web":
        from .export_web import run

        run()
        return 0
    if args.command == "all":
        from .changes import run as changes
        from .extract import run as extract
        from .export_web import run as export_web
        from .findings import run as findings
        from .lookup import run_required_dates
        from .validate import run as validate

        extract()
        run_required_dates()
        changes()
        findings()
        validate()
        export_web()
        return 0
    print(f"{args.command}: scaffolded; not part of the current P0/P1 pilot")
    return 0
