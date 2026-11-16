---
name: special-measures
description: Check whether a payment counterparty is named in a FinCEN special measure (section 311, section 9714 or FEND Off Fentanyl section 2313a) and where that measure stood on the payment date. Use when the user asks about MEXC Global, Huione, Bitzlato, PM2BTC, CIBanco, Intercam, Vector, the A7 Network or other FinCEN 311-type actions, wants to screen a list of payees or originating institutions, or asks what changed in FinCEN special measures. Uses the specialmeasures package from this repo. Engineering checklist only, not legal advice.
---

# FinCEN special measures

You help someone screen counterparties against FinCEN special measures. You report matches and dates with citations. You do not decide whether a payment is prohibited; say so if asked.

## 1. Get the facts that change the answer

- The payment or settlement date. Measures have effective dates, and MEXC Global's order was issued 2026-11-06, published 2026-11-10 and takes effect on 2026-12-10. Use the effective date, not the announcement.
- The counterparty name as it appears in the message, the country of the institution, and for crypto the exchange domain or service name.
- What kind of institution the user is (bank, MSB, broker-dealer, VASP). Correspondent-account measures and transmittal prohibitions reach different institutions; quote the scope, do not guess.

## 2. Screen

- `screen(load(), Counterparty(name, country, domain), date)` or `specialmeasures screen-csv file.csv` for a batch.
- Report every hit with its disposition, measure, citation, the alias that matched and how (`exact`, `tokens`, `domain`, `country`, `fuzzy`).
- A `review` needs a person to compare the details. A `watch` is a proposal; nothing is in force.
- If the registry's `as_of` date is old, run `specialmeasures watch` first and tell the user about any document it lists.

## 3. Report

Give the measure, its status on the date, the citation with its federalregister.gov link, the scope text, and what a person should read next. Mention that OFAC screening is separate and still needed. End with: engineering checklist, not legal advice.

Use made-up names in examples and tests, never real customer data.
