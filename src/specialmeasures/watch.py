"""Find FinCEN special-measure documents the registry does not know about.

The Federal Register API is public and needs no key. This module only reads
from it; it never writes anywhere.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .registry import Registry

API = "https://www.federalregister.gov/api/v1/documents.json"
USER_AGENT = "special-measures/0.1 (+https://github.com/BanroxArt/special-measures)"
# Titles that are about special measures but are not one (paperwork renewals).
_IGNORE_PREFIXES = ("agency information collection activities",)


@dataclass(frozen=True, slots=True)
class Document:
    number: str
    title: str
    type: str
    published: str
    citation: str
    url: str


def query_url(since: str) -> str:
    params = [
        ("per_page", "100"),
        ("order", "newest"),
        ("conditions[agencies][]", "financial-crimes-enforcement-network"),
        ("conditions[term]", '"special measure"'),
        ("conditions[publication_date][gte]", since),
    ]
    for f in ("document_number", "title", "type", "publication_date", "citation", "html_url"):
        params.append(("fields[]", f))
    return API + "?" + urllib.parse.urlencode(params)


def fetch(since: str, timeout: float = 20.0) -> dict[str, Any]:
    url = query_url(since)
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data: dict[str, Any] = json.load(resp)
    return data


def parse(payload: dict[str, Any]) -> list[Document]:
    out = []
    for r in payload.get("results", []):
        out.append(
            Document(
                number=str(r["document_number"]),
                title=str(r.get("title", "")),
                type=str(r.get("type", "")),
                published=str(r.get("publication_date", "")),
                citation=str(r.get("citation") or ""),
                url=str(r.get("html_url", "")),
            )
        )
    return out


def unknown(registry: Registry, docs: list[Document]) -> list[Document]:
    """Documents that mention special measures, are not paperwork notices, and are not cited."""
    known = registry.known_documents()
    return [
        d
        for d in docs
        if d.number not in known
        and not d.title.casefold().startswith(_IGNORE_PREFIXES)
        and "special measure" in d.title.casefold()
    ]
