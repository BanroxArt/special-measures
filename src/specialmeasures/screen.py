"""Screen a counterparty against the registry.

A hit says which measure a counterparty resembles, how the match was made,
and where that measure stood on the transaction date. It never says a
payment is prohibited: that depends on the institution type, the account,
the scope text of the measure and the facts, which a person has to read.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum

from .normalize import host_matches, key, similarity, tokens
from .registry import Measure, Registry, Status

FUZZY_THRESHOLD = 0.62
# Below this many characters a fuzzy score is noise ("MX" vs "MEXC").
MIN_FUZZY_LEN = 6


class Method(StrEnum):
    EXACT = "exact"  # normalised name equals an alias
    TOKENS = "tokens"  # every alias token appears in the name, in order
    DOMAIN = "domain"  # host is a listed domain or a subdomain of one
    COUNTRY = "country"  # institution country is a listed jurisdiction
    FUZZY = "fuzzy"  # trigram similarity above the threshold


class Disposition(StrEnum):
    HIT = "hit"  # in force, strong match: escalate before the payment moves
    REVIEW = "review"  # in force, weak match: a person compares the details
    PENDING = "pending"  # final but not yet effective on the payment date
    WATCH = "watch"  # proposed only, or a name only a proposal would add
    INFO = "info"  # withdrawn


_STRONG = frozenset({Method.EXACT, Method.TOKENS, Method.DOMAIN, Method.COUNTRY})


@dataclass(frozen=True, slots=True)
class Counterparty:
    name: str = ""
    country: str = ""  # ISO 3166-1 alpha-2 of the institution, if known
    domain: str = ""  # host or URL, for CVC exchangers


@dataclass(frozen=True, slots=True)
class Hit:
    measure_id: str
    target: str
    authority: str
    cite: str
    matched: str
    method: Method
    score: float
    status: Status
    disposition: Disposition
    scope: str

    def as_dict(self) -> dict[str, object]:
        return {
            "measure": self.measure_id,
            "target": self.target,
            "authority": self.authority,
            "cite": self.cite,
            "matched": self.matched,
            "method": str(self.method),
            "score": round(self.score, 3),
            "status": str(self.status),
            "disposition": str(self.disposition),
            "scope": self.scope,
        }


def _contains_in_order(hay: tuple[str, ...], needle: tuple[str, ...]) -> bool:
    if not needle or len(needle) > len(hay):
        return False
    n = len(needle)
    return any(hay[i : i + n] == needle for i in range(len(hay) - n + 1))


def _name_method(query: str, alias: str) -> tuple[Method, float] | None:
    qk, ak = key(query), key(alias)
    if not qk or not ak:
        return None
    if qk == ak:
        return Method.EXACT, 1.0
    if _contains_in_order(tokens(query), tokens(alias)):
        return Method.TOKENS, 1.0
    q_toks, a_toks = set(tokens(query)), set(tokens(alias))
    if q_toks < a_toks:
        # The query is the alias minus a qualifier ("Banque Misr" vs "Banque Misr UAE").
        # The qualifier is what scopes the measure, so this is not evidence of a match.
        return None
    if min(len(qk), len(ak)) >= MIN_FUZZY_LEN:
        s = similarity(query, alias)
        if s >= FUZZY_THRESHOLD:
            return Method.FUZZY, s
    return None


def _disposition(status: Status, method: Method, alias_kind: str) -> Disposition | None:
    if alias_kind == "withdrawn" or status is Status.WITHDRAWN:
        return Disposition.INFO
    if alias_kind == "proposed" or status is Status.PROPOSED:
        return Disposition.WATCH
    if status is Status.PENDING:
        return Disposition.PENDING
    if status is Status.IN_FORCE:
        return Disposition.HIT if method in _STRONG else Disposition.REVIEW
    return None


def _best(
    m: Measure, cp: Counterparty
) -> list[tuple[str, Method, float, str]]:  # (matched, method, score, alias_kind)
    found: list[tuple[str, Method, float, str]] = []
    if cp.name:
        for kind, aliases in (
            ("current", m.match.names),
            ("proposed", m.match.proposed_names),
            ("withdrawn", m.match.withdrawn_names),
        ):
            for alias in aliases:
                r = _name_method(cp.name, alias)
                if r:
                    found.append((alias, r[0], r[1], kind))
        for scoped in m.match.proposed_scoped:
            r = _name_method(cp.name, scoped.name)
            if r and cp.country.upper() == scoped.country:
                found.append((f"{scoped.name} [{scoped.country}]", r[0], r[1], "proposed"))
    if cp.domain:
        for d in m.match.domains:
            if host_matches(cp.domain, d):
                found.append((d, Method.DOMAIN, 1.0, "current"))
    if cp.country and cp.country.upper() in m.match.countries:
        found.append((cp.country.upper(), Method.COUNTRY, 1.0, "current"))
    return found


_RANK = {Method.EXACT: 0, Method.DOMAIN: 1, Method.COUNTRY: 2, Method.TOKENS: 3, Method.FUZZY: 4}


def screen(registry: Registry, cp: Counterparty, on: dt.date) -> list[Hit]:
    """All measures the counterparty resembles, strongest first, one hit per measure."""
    hits: list[Hit] = []
    for m in registry.measures:
        candidates = _best(m, cp)
        if not candidates:
            continue
        candidates.sort(key=lambda c: (_RANK[c[1]], -c[2], c[3] != "current"))
        matched, method, score, alias_kind = candidates[0]
        status = m.status_on(on)
        disp = _disposition(status, method, alias_kind)
        if disp is None:
            continue
        if disp is Disposition.HIT and cp.country.upper() in m.match.excluded_countries:
            # e.g. MEXC Global's U.S. offices are outside the order.
            disp = Disposition.REVIEW
        hits.append(
            Hit(
                m.id,
                m.target,
                m.authority,
                m.primary_cite(),
                matched,
                method,
                score,
                status,
                disp,
                m.scope,
            )
        )
    order = list(Disposition)
    hits.sort(key=lambda h: (order.index(h.disposition), _RANK[h.method], -h.score))
    return hits
