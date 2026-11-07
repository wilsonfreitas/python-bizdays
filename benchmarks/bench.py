"""Time and memory benchmark for bizdays.

It measures the core ``Calendar`` operations on the ANBIMA calendar at several vector
sizes, and the construction of packaged and external calendars in fresh processes.
It needs only the standard library, NumPy and bizdays. See ``benchmarks/README.md``
for how to run it, the budgets and the baseline numbers.
"""

from __future__ import annotations

import subprocess
import sys
import time
import tracemalloc
from typing import Any, Callable

import numpy as np

MIB = 1024 * 1024
SKIP_EXIT = 3
PACKAGED = ("ANBIMA", "B3", "Actual")

_CORE = {1: (0.01, 8), 1000: (0.05, 8), 1_000_000: (1, 512)}
BUDGETS: dict[str, dict[int, tuple[float, float | None]]] = {
    "bizdays": _CORE,
    "isbizday": _CORE,
    "offset": _CORE,
    "following": _CORE,
    "modified_following": _CORE,
    "getbizdays": _CORE,
    "bizdays[str]": {1: (0.01, 8), 1000: (0.05, 8), 1_000_000: (5, 1024)},
    "getdate": {1: (0.01, 8), 1000: (0.5, 32), 1_000_000: (60, None)},
    "seq": {1: (0.05, 32)},
    "load:packaged": {1: (0.5, 32)},
    "load:external": {1: (10, 128)},
}


def budget(case: str, n: int) -> tuple[float, float | None] | None:
    """Return ``(seconds, MiB)`` for a case and size, using the next larger size in the table."""
    if case.startswith(("load:", "index:")):
        case = "load:packaged" if case.split(":", 1)[1] in PACKAGED else "load:external"
    sizes = BUDGETS.get(case, {})
    larger = [size for size in sizes if size >= n]
    return sizes[min(larger)] if larger else None


def measure(fn: Callable[[], object], repeat: int, memory: bool = True) -> tuple[float, float | None]:
    """Best untraced time of ``repeat`` calls, then one traced call for the peak in MiB."""
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - start)
    if not memory:
        return best, None
    tracemalloc.start()
    try:
        fn()
        peak = tracemalloc.get_traced_memory()[1] / MIB
    finally:
        tracemalloc.stop()
    return best, peak


def make_inputs(n: int, common: bool = False) -> dict[str, Any]:
    """Fixed random inputs inside the ANBIMA range; ``n == 1`` gives scalars."""
    rng = np.random.default_rng(0)
    dates = np.datetime64("2001-01-01", "D") + rng.integers(0, 30_000, n)
    counts = rng.integers(-100, 100, n)
    months = (np.datetime64("2001-01", "M") + rng.integers(0, 1000, n)).astype(str)
    years = rng.integers(2001, 2099, n)
    inp: dict[str, Any] = {
        "dates": dates,
        "dates_to": dates + 30,
        "counts": counts,
        "months": years if common else months,
        "years": years,
    }
    if common:
        inp = {key: value.astype(str).tolist() if key.startswith("dates") else value.tolist() for key, value in inp.items()}
    if n == 1:
        inp = {key: value[0] for key, value in inp.items()}
        if not common:
            inp["counts"] = int(inp["counts"])
            inp["years"] = int(inp["years"])
    return inp


_CHILD = f"""
import sys, time, tracemalloc, warnings
warnings.simplefilter("ignore")
import bizdays
name, mode = sys.argv[1], sys.argv[2]
def load():
    try:
        bizdays.Calendar.load(name=name)
    except ImportError:
        sys.exit({SKIP_EXIT})
if mode == "time":
    t0 = time.perf_counter(); load(); t1 = time.perf_counter(); load(); t2 = time.perf_counter()
    print(t1 - t0, t2 - t1)
else:
    tracemalloc.start(); load(); first = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
    tracemalloc.start(); load(); second = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
    print(first / {MIB}, second / {MIB})
"""


def load_in_fresh_process(name: str) -> dict[str, float] | None:
    """First and second ``Calendar.load(name=name)`` in new processes; ``None`` if the provider is missing."""
    result: dict[str, float] = {}
    for mode, unit in (("time", "s"), ("memory", "mib")):
        proc = subprocess.run([sys.executable, "-c", _CHILD, name, mode], capture_output=True, text=True)
        if proc.returncode == SKIP_EXIT:
            return None
        if proc.returncode != 0:
            raise RuntimeError(f"loading {name} failed:\n{proc.stderr}")
        first, second = proc.stdout.split()
        result[f"first_{unit}"] = float(first)
        result[f"second_{unit}"] = float(second)
    return result
