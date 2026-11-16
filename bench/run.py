"""Screening throughput on synthetic names. Prints names per second."""

from __future__ import annotations

import datetime as dt
import random
import time

from specialmeasures import Counterparty, load, screen

WORDS = [
    "acme",
    "north",
    "river",
    "capital",
    "trade",
    "bank",
    "credit",
    "union",
    "global",
    "pay",
    "services",
    "holding",
    "group",
]


def main() -> None:
    rnd = random.Random(7)
    reg = load()
    names = [" ".join(rnd.choice(WORDS) for _ in range(rnd.randint(2, 5))) for _ in range(20_000)]
    names[::1000] = ["MX GLOBAL LTD"] * len(names[::1000])
    on = dt.date(2026, 12, 15)
    t0 = time.perf_counter()
    hits = sum(1 for n in names for h in screen(reg, Counterparty(n), on) if h.disposition == "hit")
    dt_s = time.perf_counter() - t0
    print(f"{len(names)} names in {dt_s:.2f} s ({len(names) / dt_s:,.0f}/s), {hits} hits")


if __name__ == "__main__":
    main()
