# special-measures

`specialmeasures` is a machine-readable registry of FinCEN special measures, with a Federal Register or eCFR citation on every event, the status of each measure on any date, and a screener for payment counterparties.

FinCEN publishes these actions as Federal Register documents and, for the 311 rules, as sections of 31 CFR part 1010 subpart F. There is no official structured feed of them. The section 9714 and section 2313a orders are not codified at all, effective dates get moved after publication, proposals sit open for months, and some are withdrawn years later. Teams end up keeping a spreadsheet by hand.

Standard library only. Python 3.11+.

Built and maintained by Art Akopian, CEO of [Banrox](https://banrox.com). Banrox builds consumer credit and fraud-prevention software and publishes the general-purpose pieces.

> **Engineering checklist, not legal advice.** A hit means a counterparty resembles a party named in a FinCEN action, and says where that action stood on the payment date. Whether a given payment is prohibited depends on the type of institution, the account, the scope language of the order or rule and the facts. A person has to read the source document. This package is not a substitute for OFAC screening either: special measures and OFAC sanctions are separate regimes, and many parties are under both.

## Why now

FinCEN issued an order under section 9714 on November 6, 2026 finding MEXC Global, a Seychelles-incorporated CVC exchanger, to be of primary money laundering concern in connection with Russian illicit finance. The order was published in the Federal Register on November 10, 2026 ([91 FR 72420](https://www.federalregister.gov/d/2026-22962)) and its DATES line reads "This action is effective December 10, 2026." From that date a covered financial institution may not send funds to or receive funds from MEXC Global. The order names current and former affiliates in footnote 1: MEXC Global Ltd and MX Global Ltd (Seychelles), MEXC Estonia OÜ, GIDA Technology AG (Switzerland), MXC Global Ltd (United Kingdom), and the formerly Singapore-incorporated MEXC Global Foundation Ltd and MEXC Singapore Pte Ltd. It covers successor entities and excludes MEXC offices located in the United States. The order assesses that since May 2021 MEXC Global "has facilitated at least USD 16.7 billion in likely illicit activity" ([91 FR 72424](https://www.federalregister.gov/d/2026-22962)), including exposure to Garantex, Grinex and the A7 Network. Treasury's [press release](https://home.treasury.gov/news/press-releases/sb0685) of November 6 uses "at least $16 billion"; the registry cites the order's figure.

That one order shows every problem with keeping these lists by hand:

- The order has three dates: issued (November 6), published (November 10) and effective (December 10). Only the last one changes what a bank may do. A payment on December 9 and one on December 10 get different answers.
- The names in a payment message are not the name in the order. `MX GLOBAL LTD`, `GIDA TECHNOLOGY AG` and `mexc.com` are all MEXC Global under the order's definition.
- The scope has an exclusion (U.S. offices) that a name match alone cannot see.
- It is a section 9714 order, so it will never appear in 31 CFR. A team that tracks only the eCFR misses it, along with Bitzlato, PM2BTC and the three Mexican institutions ordered under the FEND Off Fentanyl Act in 2025.

## What is in the registry

20 actions, as of 2026-11-16, built from the eCFR (issue date 2026-11-12) and every FinCEN Federal Register document matching "special measure" published since January 2022:

| Status on 2026-11-16 | Measures |
| --- | --- |
| In force | Burma, Commercial Bank of Syria, FBME Bank, North Korea, Bank of Dandong, Iran, Al-Huda Bank, Huione Group (all section 311, codified); Bitzlato, PM2BTC (section 9714 orders); CIBanco, Intercam, Vector Casa de Bolsa (section 2313a orders) |
| Pending | MEXC Global, effective 2026-12-10 |
| Proposed | A7 Network sub-agents, ten Mexican gambling establishments, MBaer Merchant Bank, Banque Misr UAE, and the Huione Group definition change adding H-Pay Service PLC |
| Withdrawn | CVC mixing as a class of transactions; ABLV Bank |

Each entry records the target, the authority (311, 9714 or 2313a), the measure type, the scope in plain words, the aliases and domains taken from the definition in the source document, and a dated event list: proposed, final, effective, effective date extended, amended, withdrawn.

Every event carries its Federal Register publication date in `date`. Where FinCEN's own [special measures table](https://www.fincen.gov/resources/statutes-and-regulations/special-measures/) dates the action earlier (it lists the day FinCEN issued or signed it, usually one to five days before publication, ten for the 2019 Iran rule and fifteen for PM2BTC), that date is in `issued`. `effective` events carry the effective date stated in the document's DATES line. Status logic:

- `pending` starts on the issue date of a final rule or order, or the publication date when no issue date is recorded.
- `in_force` starts on the recorded effective date and never on the issue date.
- `proposed` and `withdrawn` run from the Federal Register date. A withdrawal takes effect "as of" its publication date. The full table with citations is in [docs/sources.md](docs/sources.md).

## Install

```sh
pip install git+https://github.com/BanroxArt/special-measures
```

## Use

```python
import datetime as dt
from specialmeasures import Counterparty, load, screen

reg = load()
for hit in screen(reg, Counterparty("MX GLOBAL LTD", country="SC"), dt.date(2026, 12, 10)):
    print(hit.disposition, hit.measure_id, hit.cite, hit.matched, hit.method)
# hit mexc-global 91 FR 72420 MX Global Ltd exact

reg.get("cibanco").status_on(
    dt.date(2025, 9, 15)
)  # Status.PENDING: effective date moved to 2025-10-20
reg.get("mexc-global").status_on(dt.date(2026, 12, 9))  # Status.PENDING
```

Dispositions:

| Disposition | Meaning |
| --- | --- |
| `hit` | Measure in force on the date, and an exact name, in-order token, domain or jurisdiction match. Stop and escalate. |
| `review` | Measure in force, but the match is fuzzy, or the counterparty is in a country the measure excludes. A person compares the details. |
| `pending` | Final, but the effective date is after the payment date. Useful for planning, and for payments that settle across the date. |
| `watch` | Proposed only, or a name that only a pending proposal would add. Nothing is in force. |
| `info` | The action was withdrawn. |

## Command line

```sh
specialmeasures list --on 2026-12-10
specialmeasures status mexc-global
specialmeasures screen "Huione Pay PLC" --on 2026-11-16      # exit 1 on a hit
specialmeasures screen --domain https://btc2cashin.me/
specialmeasures screen-csv examples/payments.csv               # id,name,country,domain,date
specialmeasures watch --since 2026-01-01                       # exit 3 if FinCEN published something not in the registry
```

`watch` reads the public Federal Register API (no key, GET only) and lists FinCEN documents with "special measure" in the title whose document number the registry does not cite. Run it on a schedule; when it exits 3, someone reads the new document and adds an entry.

## How matching works

Names are folded (accents stripped, `ł`, `ø` and dotless `ı` mapped, case-folded, punctuation removed) and legal forms are dropped on both sides: `S.A., Institución de Banca Múltiple`, `S.A. de C.V.`, `Spółka z ograniczoną odpowiedzialnością`, `sp. z o.o.`, `OÜ`, `LLC-FZ`, `FZCO`, `Ltd`, `PLC`, `AG`. Then, in order:

1. Exact match of the folded names.
2. Every alias token appears in the name, in order (`ORDERING INST: INTERCAM BANCO S.A. MEXICO CITY`).
3. Host equals or is a subdomain of a listed domain (`api.mexc.com`, not `mexc.com.example`).
4. Institution country is a listed jurisdiction (Iran, North Korea, Burma).
5. Padded character-trigram Jaccard similarity of at least 0.62, for names of six characters or more. A name that is an alias minus a word is never a fuzzy match, because the missing word is usually what scopes the measure: `Banque Misr` is not `Banque Misr UAE`.

The tests include ordinary names that must not hit, such as `Mexico City Credit Union`, `Vector Capital LLC`, `Commercial Bank of Dubai` and `Midas Touch Auto Repair`.

## Limits

- The registry starts in 2022 for Federal Register documents. Older sections are included because they are in the current eCFR; their history before codification is not.
- For Burma and Commercial Bank of Syria the registry records no date at all and reports them as in force. The other pre-2022 final rules (FBME, North Korea, Bank of Dandong, Iran) carry their Federal Register publication and effective dates, but not the proposals that came before them.
- Issue dates come from FinCEN's special measures table, which is a web page, not a legal document. They are there so the registry lines up with Treasury press releases; they never decide whether a measure is in force.
- The eCFR does not show administrative rulings or exceptions. None have been checked for this release.
- Jurisdiction measures match on the country you pass. The package does not look up a bank's country from a BIC or routing number.
- Class-of-transactions measures (A7 sub-agents, the Mexican gambling establishments) match only the names listed in the proposal. FinCEN's definitions reach further ("any other entity identified by FinCEN").
- No OFAC data. Use an OFAC screening tool as well.

## Development

```sh
pip install -e '.[dev]'
ruff check . && ruff format --check . && python scripts/check.py && mypy && pytest -q
python bench/run.py
```

## License

MIT, copyright 2026 Banrox Inc.
