# Contributing

Corrections to the registry are the most useful contribution. Open an issue or a pull request with:

- The Federal Register document number or eCFR section, and the exact sentence that supports the change.
- For a new alias, where in the definition or the order it comes from. Aliases from news articles or vendor lists are not accepted; the registry only carries names that appear in FinCEN's own documents.

Code changes:

- `ruff check .`, `ruff format --check .`, `python scripts/check.py`, `mypy` and `pytest -q` must pass.
- Add a test for every matching change, including at least one ordinary name that must still not hit.
- Use made-up names in tests unless the name is taken from a FinCEN document.
