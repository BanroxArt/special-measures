# Benchmarks

`python bench/run.py` screens 20,000 synthetic names (2 to 5 words from a fixed word list, every thousandth replaced by `MX GLOBAL LTD`) against the full registry with the payment date 2026-12-15.

| Machine | Python | Names per second | Hits |
| --- | --- | --- | --- |
| 8 vCPU Linux VM | 3.11 | about 5,800 | 20 of 20 planted |

Most of the time is trigram similarity for the fuzzy step. Token and trigram sets are cached, so repeated names are cheap. For millions of rows a day, screen distinct names once and join the result back.
