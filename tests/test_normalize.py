from hypothesis import given
from hypothesis import strategies as st

from specialmeasures.normalize import fold, host_matches, key, similarity, tokens


def test_legal_forms_drop_out() -> None:
    assert key("CIBanco S.A., Institución de Banca Múltiple") == "cibanco"
    assert key("Vector Casa de Bolsa, S.A. de C.V.") == "vector casa de bolsa"
    assert key("Huione Crypto Spółka z ograniczoną odpowiedzialnością") == "huione crypto"
    assert key("Huione Crypto sp. z o.o.") == "huione crypto"
    assert key("MEXC Estonia OÜ") == "mexc estonia"
    assert key("Gimli Trade LLC-FZ") == "gimli trade"
    assert key("Hydrofusion Resources FZ-LLC") == "hydrofusion resources"


def test_fold_handles_letters_nfkd_misses() -> None:
    assert fold("Spółka") == "spolka"
    assert fold("ØRSTED") == "orsted"


def test_similarity_bounds() -> None:
    assert similarity("Bitzlato", "Bitzlato") == 1.0
    assert similarity("", "Bitzlato") == 0.0
    assert similarity("Bitzlatto", "Bitzlato") > 0.62


@given(st.text(max_size=60))
def test_key_is_idempotent(s: str) -> None:
    assert key(key(s)) == key(s)


@given(
    st.text(
        alphabet=st.characters(max_codepoint=0x7F, categories=["L", "N", "P", "Zs"]), max_size=40
    )
)
def test_case_and_spacing_do_not_matter(s: str) -> None:
    assert key(s.upper()) == key(s.lower())
    assert tokens("  " + s + "  ") == tokens(s)


def test_turkish_dotless_i() -> None:
    assert key("KUVEYT TÜRK KATILIM BANKASI") == key("kuveyt türk kat\u0131l\u0131m bankas\u0131")


def test_host_matching() -> None:
    assert host_matches("https://www.MEXC.com/login", "mexc.com")
    assert host_matches("api.mexc.com:443", "mexc.com")
    assert host_matches("pm2btc.me.", "pm2btc.me")
    assert not host_matches("notmexc.com", "mexc.com")
    assert not host_matches("mexc.com.evil.example", "mexc.com")
