"""Smoke test of an installed bizdays, run inside a clean venv (WIL-153).

Usage: python -I smoke_installed.py --version VERSION [--extras pmc,xcal,work]

Prints one JSON line (keys ok, problems, python, numpy, pandas, values, files) and
exits 0 when there is no problem. Expected values come from R bizdays 1.0.17 where
R has them. Standard library, bizdays and numpy only.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.resources
import importlib.util
import json
import os
import platform
import sys
import tempfile
from typing import Any

import numpy as np

import bizdays
from bizdays import Calendar, list_calendars

EXPECTED_ALL = ["Calendar", "list_calendars", "DateOutOfRange"]
# extra -> (module, calendar, bizdays("2024-01-02", "2024-12-31"))
PROVIDERS: dict[str, tuple[str, str, float]] = {
    "pmc": ("pandas_market_calendars", "PMC/B3", 250.0),
    "xcal": ("exchange_calendars", "XCAL/XNYS", 251.0),
    "work": ("workalendar", "WORK/FR", 251.0),
}
YEAR = ("2024-01-02", "2024-12-31")


def _under(path: str, folder: str) -> bool:
    path, folder = os.path.realpath(path), os.path.realpath(folder)
    return os.path.commonpath([path, folder]) == folder


def source_leak(module_file: str, prefix: str, cwd: str) -> str | None:
    """A message if bizdays is imported from ``cwd`` or from outside ``prefix``."""
    if _under(module_file, cwd):
        return f"leak: bizdays imported from the current folder: {module_file}"
    if not _under(module_file, prefix):
        return f"leak: bizdays imported from outside {prefix}: {module_file}"
    return None


def check_metadata(version: str) -> list[str]:
    problems = []
    found = importlib.metadata.version("bizdays")
    if found != version:
        problems.append(f"version: installed {found}, expected {version}")
    meta = importlib.metadata.metadata("bizdays")
    if meta["Requires-Python"] != ">=3.10":
        problems.append(f"metadata: Requires-Python is {meta['Requires-Python']}, expected >=3.10")
    core = {r.replace(" ", "") for r in importlib.metadata.requires("bizdays") or [] if ";" not in r}
    if core != {"numpy>=1.24", "pandas>=2"}:
        problems.append(f"metadata: core requirements are {sorted(core)}")
    missing = {"pmc", "xcal", "work"} - set(meta.get_all("Provides-Extra") or [])
    if missing:
        problems.append(f"metadata: Provides-Extra misses {sorted(missing)}")
    return problems


def _check(values: dict[str, str], key: str, value: Any, ok: bool, text: str | None = None) -> None:
    values[key] = repr(value) if text is None else text
    if not ok:
        raise AssertionError(f"{key}: got {values[key]}")


def run_checks(extras: frozenset[str]) -> dict[str, str]:
    """Run the value checks; raise AssertionError naming the key on a wrong value."""
    v: dict[str, str] = {}
    _check(v, "all", bizdays.__all__, list(bizdays.__all__) == EXPECTED_ALL)
    py_typed = importlib.resources.files("bizdays").joinpath("py.typed").is_file()
    _check(v, "py_typed", py_typed, py_typed)
    packaged = list_calendars()["packaged"]
    _check(v, "packaged", packaged, {"ANBIMA", "B3", "Actual"} <= set(packaged))

    b3, anbima = Calendar.load(name="B3"), Calendar.load(name="ANBIMA")
    n = b3.bizdays(*YEAR)
    _check(v, "b3_bizdays_2024", n, n == 250.0)
    d = anbima.getdate("last bizday", "2024-02")
    _check(v, "anbima_getdate", d, d == np.datetime64("2024-02-29"), str(d))
    n = anbima.getbizdays(2024)
    _check(v, "anbima_getbizdays_2024", n, n == 253.0)
    d = b3.offset("2024-02-09", 1)
    _check(v, "b3_offset_carnival", d, d == np.datetime64("2024-02-14"), str(d))
    flags = (b3.isbizday("2027-12-24"), b3.isbizday("2027-12-31"), anbima.isbizday("2027-12-24"))
    _check(v, "b3_projected", flags, [bool(f) for f in flags] == [False, False, True])

    counts = b3.bizdays(["2024-01-02", None], "2024-12-31")
    ok = counts.dtype.kind == "f" and counts[0] == 250.0 and bool(np.isnan(counts[1]))
    _check(v, "missing_count", counts, ok)
    flag = b3.isbizday([None, "2024-01-02"])
    ok = isinstance(flag, np.ma.MaskedArray) and list(np.ma.getmaskarray(flag)) == [True, False] and bool(flag.data[1])
    _check(v, "missing_flag", flag, ok)

    try:
        anbima.offset("2099-12-25", 5)
    except bizdays.DateOutOfRange as e:
        ok = isinstance(e, ValueError) and list(e.positions) == [0]
        _check(v, "out_of_range", e, ok, f"DateOutOfRange positions={list(e.positions)}")
    else:
        _check(v, "out_of_range", None, False, "no error")

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "smoke.json")
        with open(path, "w") as f:
            json.dump({"name": "smoke", "weekdays": ["saturday", "sunday"], "holidays": ["2024-01-01", "2024-12-25"]}, f)
        n = Calendar.load(filename=path).bizdays("2024-01-02", "2024-12-24")
    _check(v, "json_file", n, n == 255.0)

    for extra in sorted(extras):
        _module, name, expected = PROVIDERS[extra]
        n = Calendar.load(name=name).bizdays(*YEAR)
        _check(v, extra, n, n == expected)
    return v


def providers_absent() -> list[str]:
    """Problems if a provider is importable, listed as available or loadable in a core install."""
    problems = []
    listed: dict[str, Any] = dict(list_calendars())
    for extra, (module, name, _expected) in PROVIDERS.items():
        if importlib.util.find_spec(module) is not None:
            problems.append(f"core: {module} is installed")
        if listed.get(module, {}).get("available"):
            problems.append(f"core: list_calendars() shows {module} available")
        try:
            Calendar.load(name=name)
        except ImportError as e:
            if f"bizdays[{extra}]" not in str(e):
                problems.append(f"core: loading {name} ({module}) raised ImportError without bizdays[{extra}]: {e}")
        else:
            problems.append(f"core: loading {name} ({module}) did not raise ImportError")
    return problems


def installed_files() -> list[str]:
    files = importlib.metadata.files("bizdays") or []
    return sorted(
        str(f.as_posix()) for f in files if f.parts and f.parts[0] == "bizdays" and "__pycache__" not in f.parts
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", required=True)
    parser.add_argument("--extras", default="")
    args = parser.parse_args(argv)
    names = {e for e in args.extras.split(",") if e and e != "core"}
    if "all" in names:
        names = (names - {"all"}) | set(PROVIDERS)
    extras = frozenset(names)

    problems = []
    leak = source_leak(bizdays.__file__, sys.prefix, os.getcwd())
    if leak:
        problems.append(leak)
    problems += check_metadata(args.version)
    if not extras:
        problems += providers_absent()
    values: dict[str, str] = {}
    try:
        values = run_checks(extras)
    except Exception as e:  # any failure must still give one JSON line
        problems.append(f"run_checks: {type(e).__name__}: {e}")
    try:
        pandas_version = importlib.metadata.version("pandas")
    except importlib.metadata.PackageNotFoundError:
        pandas_version = ""
    print(
        json.dumps(
            {
                "ok": not problems,
                "problems": problems,
                "python": platform.python_version(),
                "numpy": np.__version__,
                "pandas": pandas_version,
                "values": values,
                "files": installed_files(),
            }
        )
    )
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
