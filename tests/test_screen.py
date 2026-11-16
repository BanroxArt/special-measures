import datetime as dt

import pytest

from specialmeasures import Counterparty, Disposition, Method, load, screen

D = dt.date
REG = load()
AFTER = D(2026, 12, 15)


def top(name: str = "", country: str = "", domain: str = "", on: dt.date = AFTER):  # type: ignore[no-untyped-def]
    hits = screen(REG, Counterparty(name, country, domain), on)
    return hits[0] if hits else None


@pytest.mark.parametrize(
    ("name", "measure"),
    [
        ("MEXC GLOBAL LTD", "mexc-global"),
        ("MX Global Limited", "mexc-global"),
        ("GIDA TECHNOLOGY AG", "mexc-global"),
        ("Haowang Guarantee", "huione-group"),
        ("HUIONE PAY PLC", "huione-group"),
        ("Huione Crypto Sp. z o.o.", "huione-group"),
        ("BANK OF DANDONG CO LTD", "bank-of-dandong"),
        ("FBME BANK LTD", "fbme-bank"),
        ("Syrian Lebanese Commercial Bank", "commercial-bank-of-syria"),
        ("CIBANCO SA INSTITUCION DE BANCA MULTIPLE", "cibanco"),
        ("VECTOR CASA DE BOLSA SA DE CV", "vector-casa-de-bolsa"),
        ("Bitzlato Ltd", "bitzlato"),
        ("ChangeBot", "bitzlato"),
        ("Al Huda Bank", "al-huda-bank"),
    ],
)
def test_strong_name_hits(name: str, measure: str) -> None:
    h = top(name)
    assert h is not None and h.measure_id == measure
    assert h.disposition is Disposition.HIT
    assert h.method in (Method.EXACT, Method.TOKENS)


def test_mexc_is_pending_before_december_10() -> None:
    h = top("MEXC Global", on=D(2026, 11, 16))
    assert h is not None and h.disposition is Disposition.PENDING


def test_mexc_us_office_is_review_not_hit() -> None:
    h = top("MEXC Global", country="US")
    assert h is not None and h.disposition is Disposition.REVIEW


def test_name_inside_a_longer_field() -> None:
    h = top("ORDERING INST: INTERCAM BANCO S.A. MEXICO CITY")
    assert h is not None and h.measure_id == "intercam" and h.method is Method.TOKENS


def test_typo_is_review() -> None:
    h = top("Bitzlatto Limited")
    assert h is not None and h.measure_id == "bitzlato"
    assert h.method is Method.FUZZY and h.disposition is Disposition.REVIEW


def test_domains() -> None:
    h = top(domain="https://btc2cashin.me/rates")
    assert h is not None and h.measure_id == "pm2btc" and h.method is Method.DOMAIN
    h = top(domain="www.mexc.com")
    assert h is not None and h.measure_id == "mexc-global"


@pytest.mark.parametrize(
    ("country", "measure"), [("IR", "iran"), ("kp", "north-korea"), ("MM", "burma")]
)
def test_jurisdictions(country: str, measure: str) -> None:
    h = top("Some Bank", country=country)
    assert h is not None and h.measure_id == measure and h.method is Method.COUNTRY


def test_proposed_names_only_watch() -> None:
    h = top("Galadriel Trading FZCO")
    assert h is not None and h.measure_id == "a7-sub-agents" and h.disposition is Disposition.WATCH
    h = top("H-Pay Service PLC")
    assert h is not None and h.measure_id == "huione-group" and h.disposition is Disposition.WATCH


def test_banque_misr_needs_uae() -> None:
    assert top("Banque Misr", country="EG") is None
    h = top("Banque Misr", country="AE")
    assert (
        h is not None and h.measure_id == "banque-misr-uae" and h.disposition is Disposition.WATCH
    )
    h = top("Banque Misr UAE")
    assert h is not None and h.disposition is Disposition.WATCH


def test_withdrawn_is_info() -> None:
    h = top("ABLV Bank AS")
    assert h is not None and h.disposition is Disposition.INFO


@pytest.mark.parametrize(
    "name",
    [
        "Mexico City Credit Union",
        "MX Logistics",
        "Global Bank of Commerce",
        "Commercial Bank of Dubai",
        "Vector Capital LLC",
        "Pearl Harbor Savings",
        "Midas Touch Auto Repair",
        "Bank of America",
        "Intercontinental Exchange",
    ],
)
def test_ordinary_names_do_not_hit(name: str) -> None:
    hits = [h for h in screen(REG, Counterparty(name), AFTER) if h.disposition is Disposition.HIT]
    assert hits == []


def test_one_hit_per_measure_and_ordering() -> None:
    hits = screen(REG, Counterparty("MEXC Global Ltd", domain="mexc.com"), AFTER)
    assert [h.measure_id for h in hits].count("mexc-global") == 1
    assert hits[0].method is Method.EXACT


def test_before_anything_published_no_hit() -> None:
    assert top("MEXC Global", on=D(2026, 1, 1)) is None
