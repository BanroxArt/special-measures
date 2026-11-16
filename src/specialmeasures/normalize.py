"""Name normalisation for screening.

Institution names arrive in payment messages truncated, upper-cased,
transliterated and with or without their legal form. Normalisation folds
those differences away before comparison. It is applied identically to the
query and to every alias, so dropping a token is safe as long as it is
dropped on both sides.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# Legal forms and filler that carry no identity. Multi-word forms are matched
# as token sequences before single tokens are dropped.
_LEGAL_PHRASES: tuple[tuple[str, ...], ...] = (
    ("institucion", "de", "banca", "multiple"),
    ("spolka", "z", "ograniczona", "odpowiedzialnoscia"),
    ("sp", "z", "o", "o"),
    ("s", "a", "de", "c", "v"),
    ("sa", "de", "cv"),
    ("llc", "fz"),
    ("fz", "llc"),
    ("s", "a"),
    ("d", "b", "a"),
)
_LEGAL_TOKENS = frozenset(
    {
        "ltd",
        "limited",
        "plc",
        "llc",
        "ag",
        "as",
        "pte",
        "fzco",
        "fze",
        "ou",
        "co",
        "inc",
        "corp",
        "corporation",
        "company",
        "sa",
        "the",
        "dba",
    }
)
_NON_ALNUM = re.compile(r"[^0-9a-z]+")
# Letters NFKD does not decompose into a base letter plus a mark.
_FOLD = str.maketrans(
    {
        "ł": "l",
        "Ł": "L",
        "ø": "o",
        "Ø": "O",
        "đ": "d",
        "Đ": "D",
        "ß": "ss",
        "\u0131": "i",
        "æ": "ae",
        "Æ": "AE",
    }
)


def fold(text: str) -> str:
    """Strip accents, case-fold and reduce punctuation to single spaces."""
    text = text.translate(_FOLD)
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _NON_ALNUM.sub(" ", ascii_only.casefold()).strip()


@lru_cache(maxsize=65536)
def tokens(text: str) -> tuple[str, ...]:
    """Folded tokens with legal forms removed."""
    toks = fold(text).split()
    out: list[str] = []
    i = 0
    while i < len(toks):
        for phrase in _LEGAL_PHRASES:
            if tuple(toks[i : i + len(phrase)]) == phrase:
                i += len(phrase)
                break
        else:
            if toks[i] not in _LEGAL_TOKENS:
                out.append(toks[i])
            i += 1
    return tuple(out)


def key(text: str) -> str:
    """Canonical comparison key."""
    return " ".join(tokens(text))


@lru_cache(maxsize=65536)
def trigrams(text: str) -> frozenset[str]:
    padded = f"  {key(text)} "
    return frozenset(padded[i : i + 3] for i in range(len(padded) - 2))


def similarity(a: str, b: str) -> float:
    """Jaccard similarity of padded character trigrams of the two keys."""
    ta, tb = trigrams(a), trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def host_matches(host: str, domain: str) -> bool:
    """True when ``host`` is ``domain`` or a subdomain of it."""
    h = host.strip().lower().rstrip(".")
    if "://" in h:
        h = h.split("://", 1)[1]
    h = h.split("/", 1)[0].split(":", 1)[0]
    return h == domain or h.endswith("." + domain)
