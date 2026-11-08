"""Unit tests for tests/smoke_installed.py and tests/validate_rc.py (WIL-153).

They run in the source checkout, against an installed wheel or sdist (CI ``build`` job,
only pytest) and in the validate_rc suite jobs (``bizdays[dev]``).
"""

import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path

import bizdays
import numpy as np
import pytest

from tests import smoke_installed, validate_rc
from tests.validate_rc import EXTRAS, PYTHONS, Job, build_jobs

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


def test_main_reports_run_checks_error_as_json(capsys, monkeypatch):
    def broken(extras):
        raise ImportError("no provider")

    monkeypatch.setattr(smoke_installed, "run_checks", broken)
    monkeypatch.setattr(smoke_installed, "providers_absent", lambda: [])
    rc = smoke_installed.main(["--version", importlib.metadata.version("bizdays")])
    data = json.loads(capsys.readouterr().out)
    assert rc == 1 and any("ImportError: no provider" in p for p in data["problems"])


@pytest.mark.skipif(
    not Path(bizdays.__file__).resolve().is_relative_to(ROOT),
    reason="bizdays is installed, not imported from the repo",
)
def test_main_reports_leak_from_repo(capsys, monkeypatch):
    rc, data = _run_main(capsys, monkeypatch)
    assert rc == 1
    assert any(bizdays.__file__ in p for p in data["problems"])


# --- driver (tests/validate_rc.py) ---

WHL, SDIST = "bizdays-2.0.0-py3-none-any.whl", "bizdays-2.0.0.tar.gz"
GOOD_SUMS = f"{hashlib.sha256(b'a').hexdigest()}  {WHL}\n{hashlib.sha256(b'b').hexdigest()}  {SDIST}\n"


def _fake_dist(path):
    path.mkdir(parents=True, exist_ok=True)
    (path / WHL).write_bytes(b"a")
    (path / SDIST).write_bytes(b"b")
    return path


def _wrong_digit(line):
    return ("0" if line[0] != "0" else "1") + line[1:]


def test_build_jobs_full_matrix():
    jobs = build_jobs(PYTHONS)
    assert len(jobs) == 61
    names = [j.name for j in jobs]
    assert len(set(names)) == len(names)
    assert {j.name for j in jobs if not j.suite} == {
        f"{p}-{a}-{e}" for p in PYTHONS for a in ("wheel", "sdist") for e in EXTRAS
    }
    assert {j.name for j in jobs if j.suite} == {f"{p}-{a}-suite" for p in PYTHONS for a in ("wheel", "sdist")} | {
        "3.12-wheel-suite-pandas2"
    }
    (pandas2,) = [j for j in jobs if j.name == "3.12-wheel-suite-pandas2"]
    assert pandas2.requirement == "pandas<3"
    assert all(j.extras == "dev" for j in jobs if j.suite)


def test_build_jobs_no_suite():
    jobs = build_jobs(PYTHONS, suite=False)
    assert len(jobs) == 50
    assert not any(j.suite for j in jobs)
    assert len(build_jobs(["3.10"], suite=True)) == 12


def test_install_spec_extras(tmp_path):
    whl = tmp_path / WHL
    uri = whl.resolve().as_uri()
    assert validate_rc.install_spec(Job("3.12", "wheel", "core"), whl) == f"bizdays @ {uri}"
    assert validate_rc.install_spec(Job("3.12", "wheel", "pmc"), whl) == f"bizdays[pmc] @ {uri}"
    assert validate_rc.install_spec(Job("3.12", "wheel", "all"), whl) == f"bizdays[pmc,xcal,work] @ {uri}"
    assert validate_rc.install_spec(Job("3.12", "wheel", "dev", suite=True), whl) == f"bizdays[dev] @ {uri}"


def test_sha256sums_format(tmp_path):
    _fake_dist(tmp_path)
    (tmp_path / ".gitignore").write_text("*\n")
    assert validate_rc.sha256sums(tmp_path) == GOOD_SUMS


def test_check_sums_order_free_but_strict():
    assert validate_rc.check_sums(GOOD_SUMS, GOOD_SUMS) == []
    first, second = GOOD_SUMS.splitlines()
    assert validate_rc.check_sums(GOOD_SUMS, f"{second}\n{first}\n\n") == []
    problems = validate_rc.check_sums(GOOD_SUMS, f"{_wrong_digit(first)}\n{second}\n")
    assert problems and all(p.startswith("SHA256SUMS:") for p in problems)
    assert validate_rc.check_sums(GOOD_SUMS, f"{first}\n")


def test_main_fails_on_wrong_sums(tmp_path, monkeypatch):
    monkeypatch.setattr(validate_rc, "check_dist", lambda d, v: [])
    dist = _fake_dist(tmp_path / "dist")
    first, second = GOOD_SUMS.splitlines()
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"{_wrong_digit(first)}\n{second}\n")
    w = tmp_path / "w"
    args = [str(dist), "--version", "2.0.0", "--no-suite", "--sums", str(sums), "--work", str(w)]
    assert validate_rc.main(args) == 1
    assert not (w / "venvs").exists()


def _result(values, files, ok=True):
    return {"ok": ok, "python": "3.12.12", "numpy": "2.4.6", "pandas": "3.1.1", "detail": "", "values": values, "files": files}


def test_compare_pairs_flags_differences():
    wheel, sdist = Job("3.12", "wheel", "all"), Job("3.12", "sdist", "all")
    values, files = {"b3_bizdays_2024": "np.float64(250.0)"}, ["bizdays/__init__.py", "bizdays/py.typed"]
    assert validate_rc.compare_pairs({wheel: _result(values, files), sdist: _result(values, files)}) == []

    changed = validate_rc.compare_pairs({wheel: _result(values, files), sdist: _result({"b3_bizdays_2024": "x"}, files)})
    assert len(changed) == 1
    assert "3.12" in changed[0] and "all" in changed[0] and "b3_bizdays_2024" in changed[0]

    dropped = validate_rc.compare_pairs({wheel: _result(values, files), sdist: _result(values, files[:1])})
    assert len(dropped) == 1 and "bizdays/py.typed" in dropped[0]

    assert len(validate_rc.compare_pairs({wheel: _result(values, files)})) == 1


def test_render_report_has_sums_rows_and_result():
    results = {Job("3.10", "wheel", "core"): _result({}, [])}
    meta = {"version": "2.0.0", "source commit": "abc"}
    report = validate_rc.render_report(meta, GOOD_SUMS, results, [])
    assert GOOD_SUMS.strip() in report
    assert any(line.startswith("| 3.10-wheel-core |") for line in report.splitlines())
    assert report.rstrip().endswith("RESULT: PASS")
    report = validate_rc.render_report(meta, GOOD_SUMS, results, ["3.10 core: wheel and sdist differ"])
    assert report.rstrip().endswith("RESULT: FAIL")


def test_main_fails_on_bad_dist(tmp_path, capsys):
    w = tmp_path / "w"
    assert validate_rc.main([str(tmp_path), "--version", "2.0.0", "--no-suite", "--work", str(w)]) == 1
    assert "expected exactly one wheel and one sdist" in capsys.readouterr().out
    assert not (w / "venvs").exists()


def test_main_rejects_dirty_source(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(validate_rc, "check_dist", lambda d, v: [])
    monkeypatch.setattr(validate_rc, "sha256sums", lambda d: "")
    dist = _fake_dist(tmp_path / "dist")
    src = tmp_path / "src"
    src.mkdir()
    subprocess.run(["git", "init", "-q", str(src)], check=True)
    # one commit, so only the dirty check (not "no commit") can make main fail
    git_id = ["-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "-C", str(src), *git_id, "commit", "-q", "--allow-empty", "-m", "init"], check=True)
    (src / "untracked.txt").write_text("x")
    w = tmp_path / "w"
    assert validate_rc.main([str(dist), "--version", "2.0.0", "--source", str(src), "--work", str(w)]) == 1
    assert "is not a clean git tree" in capsys.readouterr().out
    assert not (w / "venvs").exists()
