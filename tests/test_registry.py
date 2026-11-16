import datetime as dt
import json
import re
from importlib import resources

import pytest

from specialmeasures import RegistryError, Status, load
from specialmeasures.registry import parse

D = dt.date
REG = load()


def raw() -> dict:
    return json.loads(resources.files("specialmeasures").joinpath("data/measures.json").read_text())


def test_every_event_is_cited_and_dated_in_order() -> None:
    cite = re.compile(r"^(\d{2} FR \d+|31 CFR 1010\.\d{3})$")
    for m in REG.measures:
        dates = [e.date for e in m.events if e.date is not None]
        assert dates == sorted(dates), m.id
        for e in m.events:
            assert cite.match(e.cite), (m.id, e.cite)
            assert e.url.startswith(
                ("https://www.federalregister.gov/d/", "https://www.ecfr.gov/")
            ), e.url


def test_codified_sections_are_the_current_ecfr_subpart_f_list() -> None:
    # 31 CFR part 1010 subpart F, special-measure sections at eCFR issue date 2026-11-12.
    codified = sorted(m.cfr for m in REG.measures if m.cfr)
    assert codified == [f"31 CFR 1010.{s}" for s in (651, 653, 658, 659, 660, 661, 663, 664)]


@pytest.mark.parametrize(
    ("measure", "on", "expected"),
    [
        ("mexc-global", D(2026, 11, 9), Status.NONE),
        ("mexc-global", D(2026, 11, 10), Status.PENDING),
        ("mexc-global", D(2026, 12, 9), Status.PENDING),
        ("mexc-global", D(2026, 12, 10), Status.IN_FORCE),
        # Effective date was moved twice; the last one counts.
        ("cibanco", D(2025, 7, 20), Status.PENDING),
        ("cibanco", D(2025, 9, 4), Status.PENDING),
        ("cibanco", D(2025, 10, 19), Status.PENDING),
        ("cibanco", D(2025, 10, 20), Status.IN_FORCE),
        ("intercam", D(2026, 1, 1), Status.IN_FORCE),
        ("huione-group", D(2025, 6, 1), Status.PROPOSED),
        ("huione-group", D(2025, 11, 16), Status.PENDING),
        ("huione-group", D(2025, 11, 17), Status.IN_FORCE),
        ("al-huda-bank", D(2024, 7, 10), Status.PENDING),
        ("bitzlato", D(2023, 1, 31), Status.PENDING),
        ("bitzlato", D(2023, 2, 1), Status.IN_FORCE),
        ("pm2btc", D(2024, 10, 11), Status.IN_FORCE),
        ("a7-sub-agents", D(2026, 11, 16), Status.PROPOSED),
        ("a7-sub-agents", D(2026, 10, 4), Status.NONE),
        ("cvc-mixing", D(2024, 1, 1), Status.PROPOSED),
        ("cvc-mixing", D(2026, 10, 6), Status.WITHDRAWN),
        ("ablv-bank", D(2024, 9, 26), Status.PROPOSED),
        ("ablv-bank", D(2024, 9, 27), Status.WITHDRAWN),
        ("iran", D(2019, 11, 13), Status.NONE),
        ("iran", D(2019, 11, 14), Status.IN_FORCE),
        ("burma", D(2000, 1, 1), Status.IN_FORCE),
    ],
)
def test_status_on(measure: str, on: dt.date, expected: Status) -> None:
    assert REG.get(measure).status_on(on) is expected


def test_known_documents_cover_every_federal_register_url() -> None:
    docs = REG.known_documents()
    assert "2026-22962" in docs and "2025-16080" in docs
    assert all(re.fullmatch(r"\d{4}-\d{5}", d) for d in docs)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("schema",), 2, "schema"),
        (("measures", 0, "kind"), "bank", "bad kind"),
        (("measures", 0, "authority"), "312", "bad authority"),
        (("measures", 0, "events"), [], "at least one event"),
        (("measures", 0, "events", 0, "url"), "http://example.com", "https url"),
        (("measures", 0, "events", 0, "type"), "rumoured", "bad type"),
        (("measures", 0, "match", "countries"), ["mm"], "alpha-2"),
        (("measures", 1, "id"), "burma", "duplicate"),
        (("measures", 6, "events", 0, "date"), "2024-02-30", "bad date"),
    ],
)
def test_schema_errors(path: tuple, value: object, message: str) -> None:
    doc = raw()
    node = doc
    for p in path[:-1]:
        node = node[p]
    node[path[-1]] = value
    with pytest.raises(RegistryError, match=message):
        parse(doc)


def test_load_from_path(tmp_path) -> None:  # type: ignore[no-untyped-def]
    p = tmp_path / "m.json"
    p.write_text(json.dumps(raw()), encoding="utf-8")
    assert len(load(p).measures) == len(REG.measures)
