"""Tests and CI smoke run for ``benchmarks/bench.py``."""

import importlib.util
import re
import subprocess
import sys
import tracemalloc
from pathlib import Path

import numpy as np
import pytest

import bizdays
from bizdays import Calendar

BENCH = Path(__file__).parents[1] / "benchmarks" / "bench.py"

# WIL-151's build job copies only tests/ and pyproject.toml next to the installed package.
pytestmark = pytest.mark.skipif(not BENCH.exists(), reason="benchmarks/ not in this tree")


@pytest.fixture(scope="module")
def bench():
    spec = importlib.util.spec_from_file_location("bench", BENCH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cli(*args):
    return subprocess.run([sys.executable, str(BENCH), *args], capture_output=True, text=True, timeout=120)


def test_measure_times_untraced_then_traces_once(bench):
    seen = []

    def fn():
        seen.append(tracemalloc.is_tracing())

    seconds, peak = bench.measure(fn, repeat=3)
    assert seen == [False, False, False, True]
    assert seconds >= 0
    assert isinstance(peak, float) and peak >= 0

    seen.clear()
    seconds, peak = bench.measure(fn, repeat=2, memory=False)
    assert seen == [False, False]
    assert peak is None
    assert not tracemalloc.is_tracing()


def test_inputs_stay_inside_anbima(bench):
    inp = bench.make_inputs(1_000_000)
    cal = Calendar.load(name="ANBIMA")
    assert cal.inrange(inp["dates"]).all()
    assert cal.inrange(inp["dates_to"]).all()
    cal.offset(inp["dates"], inp["counts"])
    cal.getdate("last bizday", inp["months"][:1000])
    assert inp["years"].min() >= 2001 and inp["years"].max() <= 2098
    assert inp["counts"].min() >= -100 and inp["counts"].max() < 100
    assert np.array_equal(bench.make_inputs(1_000_000)["dates"], inp["dates"])


def test_scalar_and_common_inputs(bench):
    one = bench.make_inputs(1)
    assert isinstance(one["dates"], np.datetime64)
    assert isinstance(one["counts"], int)

    c = bench.make_inputs(10, common=True)
    assert isinstance(c["dates"], list) and len(c["dates"]) == 10
    assert all(isinstance(d, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in c["dates"])
    for key in ("counts", "months", "years"):
        assert isinstance(c[key], list) and all(type(v) is int for v in c[key])


def test_budget_lookup(bench):
    assert bench.budget("bizdays", 1) == (0.01, 8)
    assert bench.budget("bizdays", 1000) == (0.05, 8)
    assert bench.budget("bizdays", 100_000) == (1, 512)
    assert bench.budget("bizdays", 10_000_000) is None
    assert bench.budget("getdate", 1_000_000) == (60, None)
    assert bench.budget("load:ANBIMA", 1) == (0.5, 32)
    assert bench.budget("load:XCAL/BVMF", 1) == (10, 128)
    assert bench.budget("index:ANBIMA", 1) == (0.5, 32)
    assert bench.budget("index:PMC/B3", 1) == (10, 128)


def test_load_in_fresh_process(bench, tmp_path, monkeypatch):
    r = bench.load_in_fresh_process("ANBIMA")
    assert 0 < r["first_s"] < 0.5
    assert 0 < r["second_s"] < 0.5
    assert 0 < r["first_mib"] < 32
    assert 0 < r["second_mib"] < 32

    with pytest.raises(RuntimeError, match="NOPE"):
        bench.load_in_fresh_process("NOPE")

    (tmp_path / "pandas_market_calendars.py").write_text('raise ImportError("blocked")\n')
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    assert bench.load_in_fresh_process("PMC/B3") is None


OPERATIONS = (
    "bizdays",
    "bizdays[str]",
    "isbizday",
    "offset",
    "following",
    "modified_following",
    "getdate",
    "getbizdays",
)


def test_cli_smoke_check_passes():
    r = run_cli("--sizes", "1", "1000", "--calendars", "ANBIMA", "--check")
    assert r.returncode == 0, r.stdout + r.stderr
    first = r.stdout.splitlines()[0]
    assert first.startswith("bizdays ")
    assert str(Path(bizdays.__file__)) in first
    assert "| case | n | seconds | peak MiB | budget s | budget MiB | status |" in r.stdout
    for row in ("| load:ANBIMA | 1 |", "| index:ANBIMA | 1 |", "| seq | 1 |"):
        assert row in r.stdout
    for name in OPERATIONS:
        for n in (1, 1000):
            assert f"| {name} | {n} |" in r.stdout
    assert "OVER" not in r.stdout


def test_cli_check_fails_over_budget():
    r = run_cli("--sizes", "1", "--calendars", "ANBIMA", "--check", "--scale", "0")
    assert r.returncode == 1
    assert "OVER" in r.stdout
    assert run_cli("--sizes", "1", "--calendars", "ANBIMA", "--scale", "0").returncode == 0


def test_cli_common_mode():
    r = run_cli("--common", "--sizes", "10", "--calendars", "ANBIMA")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "bizdays[str]" not in r.stdout
    assert "| getdate | 10 |" in r.stdout
    assert "OVER" not in r.stdout
    assert "| ok |" not in r.stdout
    assert run_cli("--common", "--check").returncode == 2


def test_cli_missing_provider_is_skipped(bench, monkeypatch, capsys):
    monkeypatch.setattr(bench, "load_in_fresh_process", lambda name: None)
    assert bench.main(["--sizes", "1", "--calendars", "XCAL/BVMF", "--check"]) == 0
    lines = capsys.readouterr().out.splitlines()
    for case in ("load:XCAL/BVMF", "index:XCAL/BVMF"):
        assert any(line.startswith(f"| {case} |") and line.endswith("| skipped |") for line in lines)

    bench.main(["--sizes", "1000", "--calendars", "ANBIMA"])
    out = capsys.readouterr().out
    assert "| seq | 1 |" in out
    assert "| seq | 1000 |" not in out
