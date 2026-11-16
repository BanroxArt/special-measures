"""Typed view of the special-measures registry and its status-on-a-date logic.

The registry is a JSON file shipped with the package. Each entry is one
FinCEN action (or proposed action) under 31 U.S.C. 5318A (section 311),
section 9714 of the Combating Russian Money Laundering Act, or 21 U.S.C.
2313a (FEND Off Fentanyl Act), with the Federal Register or eCFR citation
for every event that changed its status.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from enum import StrEnum
from importlib import resources
from pathlib import Path
from typing import Any, Literal

Kind = Literal["institution", "jurisdiction", "class_of_transactions"]
Authority = Literal["311", "9714", "2313a"]
MeasureType = Literal["correspondent_prohibition", "transmittal_prohibition", "recordkeeping"]

MEASURE_TYPES = frozenset({"correspondent_prohibition", "transmittal_prohibition", "recordkeeping"})
EVENT_TYPES = frozenset(
    {
        "proposed",
        "final",
        "effective",
        "effective_extended",
        "amended",
        "amendment_proposed",
        "withdrawn",
        "codified",
    }
)


class Status(StrEnum):
    """Where a measure stands on a given date."""

    IN_FORCE = "in_force"
    PENDING = "pending"  # final order or rule published, effective date not reached
    PROPOSED = "proposed"
    WITHDRAWN = "withdrawn"
    NONE = "none"  # the date is before anything was published


@dataclass(frozen=True, slots=True)
class Event:
    type: str
    date: dt.date | None
    cite: str
    url: str
    note: str = ""


@dataclass(frozen=True, slots=True)
class ScopedName:
    name: str
    country: str


@dataclass(frozen=True, slots=True)
class MatchSpec:
    names: tuple[str, ...] = ()
    proposed_names: tuple[str, ...] = ()
    withdrawn_names: tuple[str, ...] = ()
    proposed_scoped: tuple[ScopedName, ...] = ()
    countries: tuple[str, ...] = ()
    excluded_countries: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Measure:
    id: str
    target: str
    kind: Kind
    authority: Authority
    measure: MeasureType
    cfr: str | None
    scope: str
    match: MatchSpec
    events: tuple[Event, ...] = field(default_factory=tuple)

    def effective_date(self) -> dt.date | None:
        """Last recorded effective date, or None when the registry has none."""
        dates = [e.date for e in self.events if e.type == "effective" and e.date is not None]
        return max(dates) if dates else None

    def status_on(self, on: dt.date) -> Status:
        """Status of the measure on ``on``.

        Rules, in order:

        1. A withdrawal dated on or before ``on`` wins.
        2. A codified section with no dated events is in force (the registry
           only records sections present in the current eCFR).
        3. A final rule or order with a recorded effective date is pending
           before that date and in force from it. Extensions are honoured
           because the last ``effective`` event is the one that counts.
        4. A final rule with no recorded effective date is in force from its
           publication date. This is the one place the registry is coarse;
           record an ``effective`` event to sharpen it.
        5. Otherwise a proposal dated on or before ``on`` makes it proposed.
        """
        dated = [e for e in self.events if e.date is not None and e.date <= on]
        if any(e.type == "withdrawn" for e in dated):
            return Status.WITHDRAWN
        undated = all(e.date is None for e in self.events)
        if self.events and undated and any(e.type == "codified" for e in self.events):
            return Status.IN_FORCE
        finals = [e for e in dated if e.type == "final"]
        if finals:
            eff = self.effective_date()
            if eff is None or eff <= on:
                return Status.IN_FORCE
            return Status.PENDING
        if any(e.type == "proposed" for e in dated):
            return Status.PROPOSED
        return Status.NONE

    def primary_cite(self) -> str:
        if self.cfr:
            return self.cfr
        finals = [e for e in self.events if e.type == "final"]
        return (finals or list(self.events))[0].cite


@dataclass(frozen=True, slots=True)
class Registry:
    as_of: dt.date
    sources_checked: tuple[str, ...]
    measures: tuple[Measure, ...]

    def get(self, measure_id: str) -> Measure:
        for m in self.measures:
            if m.id == measure_id:
                return m
        raise KeyError(measure_id)

    def known_documents(self) -> frozenset[str]:
        """Federal Register document numbers referenced by any event."""
        out: set[str] = set()
        for m in self.measures:
            for e in m.events:
                marker = "federalregister.gov/d/"
                if marker in e.url:
                    out.add(e.url.split(marker, 1)[1].strip("/"))
        return frozenset(out)


class RegistryError(ValueError):
    """The registry file does not satisfy the schema."""


def _date(value: Any, where: str) -> dt.date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RegistryError(f"{where}: date must be a string or null")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise RegistryError(f"{where}: bad date {value!r}") from exc


def _strs(obj: dict[str, Any], key: str, where: str) -> tuple[str, ...]:
    raw = obj.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(x, str) and x.strip() for x in raw):
        raise RegistryError(f"{where}: {key} must be a list of non-empty strings")
    return tuple(raw)


def _measure(raw: dict[str, Any]) -> Measure:
    where = str(raw.get("id", "?"))
    for key in ("id", "target", "kind", "authority", "measure", "scope", "match", "events"):
        if key not in raw:
            raise RegistryError(f"{where}: missing {key}")
    if raw["kind"] not in ("institution", "jurisdiction", "class_of_transactions"):
        raise RegistryError(f"{where}: bad kind {raw['kind']!r}")
    if raw["authority"] not in ("311", "9714", "2313a"):
        raise RegistryError(f"{where}: bad authority {raw['authority']!r}")
    if raw["measure"] not in (
        "correspondent_prohibition",
        "transmittal_prohibition",
        "recordkeeping",
    ):
        raise RegistryError(f"{where}: bad measure {raw['measure']!r}")
    m = raw["match"]
    scoped = []
    for s in m.get("proposed_scoped", []):
        if not isinstance(s, dict) or not {"name", "country"} <= s.keys():
            raise RegistryError(f"{where}: proposed_scoped entries need name and country")
        scoped.append(ScopedName(str(s["name"]), str(s["country"]).upper()))
    countries = _strs(m, "countries", where)
    excluded = _strs(m, "excluded_countries", where)
    if any(len(c) != 2 or not c.isupper() for c in countries + excluded):
        raise RegistryError(f"{where}: countries must be ISO 3166-1 alpha-2, upper case")
    spec = MatchSpec(
        names=_strs(m, "names", where),
        proposed_names=_strs(m, "proposed_names", where),
        withdrawn_names=_strs(m, "withdrawn_names", where),
        proposed_scoped=tuple(scoped),
        countries=countries,
        excluded_countries=excluded,
        domains=tuple(d.lower() for d in _strs(m, "domains", where)),
    )
    events = []
    for i, e in enumerate(raw["events"]):
        ew = f"{where}.events[{i}]"
        if e.get("type") not in EVENT_TYPES:
            raise RegistryError(f"{ew}: bad type {e.get('type')!r}")
        if not str(e.get("cite", "")).strip() or not str(e.get("url", "")).startswith("https://"):
            raise RegistryError(f"{ew}: cite and an https url are required")
        events.append(
            Event(e["type"], _date(e.get("date"), ew), e["cite"], e["url"], e.get("note", ""))
        )
    if not events:
        raise RegistryError(f"{where}: at least one event is required")
    return Measure(
        id=raw["id"],
        target=raw["target"],
        kind=raw["kind"],
        authority=raw["authority"],
        measure=raw["measure"],
        cfr=raw.get("cfr"),
        scope=raw["scope"],
        match=spec,
        events=tuple(events),
    )


def parse(doc: dict[str, Any]) -> Registry:
    if doc.get("schema") != 1:
        raise RegistryError("unsupported schema version")
    measures = tuple(_measure(r) for r in doc["measures"])
    ids = [m.id for m in measures]
    if len(set(ids)) != len(ids):
        raise RegistryError("duplicate measure ids")
    as_of = _date(doc.get("as_of"), "as_of")
    if as_of is None:
        raise RegistryError("as_of is required")
    return Registry(as_of, tuple(doc.get("sources_checked", [])), measures)


def load(path: str | Path | None = None) -> Registry:
    """Load the bundled registry, or one at ``path`` (for a locally extended copy)."""
    if path is None:
        text = resources.files("specialmeasures").joinpath("data/measures.json").read_text("utf-8")
    else:
        text = Path(path).read_text("utf-8")
    return parse(json.loads(text))
