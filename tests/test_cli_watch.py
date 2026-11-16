import json
from pathlib import Path

import pytest

from specialmeasures import load
from specialmeasures.__main__ import main
from specialmeasures.watch import parse, query_url, unknown

FIX = Path(__file__).parent / "fixtures"


def test_watch_flags_only_new_special_measure_documents() -> None:
    docs = parse(json.loads((FIX / "fr_sample.json").read_text()))
    new = unknown(load(), docs)
    assert [d.number for d in new] == ["2099-00001"]


def test_query_url_is_read_only_federal_register() -> None:
    u = query_url("2022-01-01")
    assert u.startswith("https://www.federalregister.gov/api/v1/documents.json?")
    assert "financial-crimes-enforcement-network" in u


def test_cli_watch_from_file(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["watch", "--from-file", str(FIX / "fr_sample.json")]) == 3
    assert "2099-00001" in capsys.readouterr().out


def test_cli_screen_exit_codes(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["screen", "MEXC Global", "--on", "2026-12-10"]) == 1
    assert main(["screen", "MEXC Global", "--on", "2026-12-09"]) == 0
    assert main(["screen", "Acme Credit Union", "--on", "2026-12-10"]) == 0
    capsys.readouterr()


def test_cli_list_and_status(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list", "--on", "2026-11-16"]) == 0
    out = capsys.readouterr().out
    assert "mexc-global" in out and "pending" in out and "not legal advice" in out
    assert main(["status", "cibanco", "--on", "2026-11-16"]) == 0
    st = json.loads(capsys.readouterr().out)
    assert st["status"] == "in_force" and len(st["events"]) == 5


def test_cli_screen_csv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "p.csv"
    f.write_text(
        "id,name,country,domain,date\n"
        "t1,Acme Payroll,US,,2026-12-11\n"
        "t2,MX Global Ltd,SC,,2026-12-11\n"
        "t3,MX Global Ltd,SC,,2026-12-01\n"
        "t4,,,pm2wm.me,2026-12-11\n",
        encoding="utf-8",
    )
    assert main(["screen-csv", str(f)]) == 1
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [(r["row"], r["disposition"]) for r in rows] == [
        ("t2", "hit"),
        ("t3", "pending"),
        ("t4", "hit"),
    ]
