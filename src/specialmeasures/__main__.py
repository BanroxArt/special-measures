"""Command line: list, status, screen, screen-csv, watch."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import watch
from .registry import Registry, load
from .screen import Counterparty, Disposition, screen

DISCLAIMER = "Engineering checklist, not legal advice."


def _date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _cmd_list(reg: Registry, args: argparse.Namespace) -> int:
    on: dt.date = args.on
    for m in reg.measures:
        eff = m.effective_date()
        print(
            f"{m.id:32} {m.status_on(on):10} {m.authority:6} {m.measure:26} "
            f"{eff.isoformat() if eff else '-':10}  {m.primary_cite()}"
        )
    print(f"\nregistry as of {reg.as_of.isoformat()}; status on {on.isoformat()}. {DISCLAIMER}")
    return 0


def _cmd_status(reg: Registry, args: argparse.Namespace) -> int:
    m = reg.get(args.measure)
    print(
        json.dumps(
            {
                "id": m.id,
                "target": m.target,
                "status": str(m.status_on(args.on)),
                "on": args.on.isoformat(),
                "authority": m.authority,
                "measure": m.measure,
                "scope": m.scope,
                "events": [
                    {
                        "type": e.type,
                        "date": e.date.isoformat() if e.date else None,
                        "cite": e.cite,
                        "url": e.url,
                        "note": e.note,
                    }
                    for e in m.events
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def _cmd_screen(reg: Registry, args: argparse.Namespace) -> int:
    cp = Counterparty(args.name or "", args.country or "", args.domain or "")
    hits = screen(reg, cp, args.on)
    print(json.dumps([h.as_dict() for h in hits], indent=2, ensure_ascii=False))
    return 1 if any(h.disposition is Disposition.HIT for h in hits) else 0


def _cmd_screen_csv(reg: Registry, args: argparse.Namespace) -> int:
    worst = 0
    with Path(args.file).open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            on = _date(row["date"]) if row.get("date") else args.on
            cp = Counterparty(row.get("name", ""), row.get("country", ""), row.get("domain", ""))
            for h in screen(reg, cp, on):
                if h.disposition is Disposition.HIT:
                    worst = 1
                print(
                    json.dumps(
                        {"row": row.get("id", ""), "date": on.isoformat(), **h.as_dict()},
                        ensure_ascii=False,
                    )
                )
    return worst


def _cmd_watch(reg: Registry, args: argparse.Namespace) -> int:
    payload = (
        json.loads(Path(args.from_file).read_text("utf-8"))
        if args.from_file
        else watch.fetch(args.since)
    )
    new = watch.unknown(reg, watch.parse(payload))
    for d in new:
        print(f"{d.published}  {d.type:14} {d.citation:12} {d.number}  {d.title}\n    {d.url}")
    if not new:
        print("no special-measure documents missing from the registry")
    return 3 if new else 0


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="specialmeasures", description=DISCLAIMER)
    p.add_argument("--registry", help="path to a measures.json (default: bundled)")
    sub = p.add_subparsers(dest="cmd", required=True)
    today = dt.date.today()

    s = sub.add_parser("list", help="every measure and its status on a date")
    s.add_argument("--on", type=_date, default=today)
    s = sub.add_parser("status", help="one measure with its full event history")
    s.add_argument("measure")
    s.add_argument("--on", type=_date, default=today)
    s = sub.add_parser("screen", help="screen one counterparty; exit 1 on a hit")
    s.add_argument("name", nargs="?")
    s.add_argument("--country")
    s.add_argument("--domain")
    s.add_argument("--on", type=_date, default=today)
    s = sub.add_parser("screen-csv", help="screen rows with id,name,country,domain,date")
    s.add_argument("file")
    s.add_argument("--on", type=_date, default=today)
    s = sub.add_parser("watch", help="list Federal Register documents missing from the registry")
    s.add_argument("--since", default="2022-01-01")
    s.add_argument("--from-file", help="read a saved API response instead of the network")

    args = p.parse_args(argv)
    reg = load(args.registry)
    handlers = {
        "list": _cmd_list,
        "status": _cmd_status,
        "screen": _cmd_screen,
        "screen-csv": _cmd_screen_csv,
        "watch": _cmd_watch,
    }
    return handlers[args.cmd](reg, args)


if __name__ == "__main__":
    sys.exit(main())
