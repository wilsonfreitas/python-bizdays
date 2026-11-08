"""Unit tests for tests/smoke_installed.py and tests/validate_rc.py (WIL-153).

They run in the source checkout, against an installed wheel or sdist (CI ``build`` job,
only pytest) and in the validate_rc suite jobs (``bizdays[dev]``).
"""

import importlib.metadata
import json
import os
import sys
from pathlib import Path

import bizdays
import numpy as np
import pytest

from tests import smoke_installed

ROOT = Path(__file__).resolve().parent.parent
NUMPY2 = np.lib.NumpyVersion(np.__version__) >= "2.0.0"


def test_source_leak_detects_tree_and_foreign_paths():
    ok = "/venv/lib/python3.12/site-packages/bizdays/__init__.py"
    assert smoke_installed.source_leak(ok, "/venv", "/run") is None
    for bad in ("/run/bizdays/__init__.py", "/home/x/repo/bizdays/__init__.py"):
        msg = smoke_installed.source_leak(bad, "/venv", "/run")
        assert msg is not None and bad in msg


@pytest.mark.skipif(not NUMPY2, reason="scalar reprs differ before NumPy 2")
def test_run_checks_core_values():
    v = smoke_installed.run_checks(frozenset())
    assert v["b3_bizdays_2024"] == "np.float64(250.0)"
    assert v["anbima_getdate"] == "2024-02-29"
    assert v["anbima_getbizdays_2024"] == "np.float64(253.0)"
    assert v["b3_offset_carnival"] == "2024-02-14"
    assert v["json_file"] == "np.float64(255.0)"
    assert not {"pmc", "xcal", "work"} & set(v)


@pytest.mark.skipif(not NUMPY2, reason="scalar reprs differ before NumPy 2")
def test_run_checks_with_all_extras():
    for mod in ("pandas_market_calendars", "exchange_calendars", "workalendar"):
        pytest.importorskip(mod)
    v = smoke_installed.run_checks(frozenset({"pmc", "xcal", "work"}))
    assert v["pmc"] == "np.float64(250.0)"
    assert v["xcal"] == "np.float64(251.0)"
    assert v["work"] == "np.float64(251.0)"


def test_providers_absent_reports_installed(monkeypatch):
    def fake_find_spec(name, *args, **kwargs):
        return object() if name == "workalendar" else None

    monkeypatch.setattr(smoke_installed.importlib.util, "find_spec", fake_find_spec)
    problems = smoke_installed.providers_absent()
    assert any("workalendar" in p for p in problems)


def test_check_metadata_wrong_version():
    problems = smoke_installed.check_metadata("0.0.0")
    assert any("0.0.0" in p for p in problems)


def _run_main(capsys, monkeypatch):
    monkeypatch.setattr(smoke_installed, "run_checks", lambda extras: {"k": "v"})
    monkeypatch.setattr(smoke_installed, "providers_absent", lambda: [])
    rc = smoke_installed.main(["--version", importlib.metadata.version("bizdays"), "--extras", "core"])
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    return rc, json.loads(lines[0])


def test_main_prints_one_json_line(capsys, monkeypatch):
    rc, data = _run_main(capsys, monkeypatch)
    assert data["values"] == {"k": "v"}
    assert data["ok"] == (rc == 0)
    leak = smoke_installed.source_leak(bizdays.__file__, sys.prefix, os.getcwd())
    assert (leak in data["problems"]) == (leak is not None)


@pytest.mark.skipif(
    not Path(bizdays.__file__).resolve().is_relative_to(ROOT),
    reason="bizdays is installed, not imported from the repo",
)
def test_main_reports_leak_from_repo(capsys, monkeypatch):
    rc, data = _run_main(capsys, monkeypatch)
    assert rc == 1
    assert any(bizdays.__file__ in p for p in data["problems"])
