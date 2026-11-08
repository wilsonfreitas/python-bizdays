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
        "dates_to": dates + np.timedelta64(30, "D"),
        "counts": counts,
        "months": years if common else months,
        "years": years,
    }
    if common:
        inp = {
            key: value.astype(str).tolist() if key.startswith("dates") else value.tolist() for key, value in inp.items()
        }
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


# Operation cases in report order: name -> call on (calendar, inputs).
CASES: dict[str, Callable[[Any, dict[str, Any]], object]] = {
    "bizdays": lambda cal, inp: cal.bizdays(inp["dates"], inp["dates_to"]),
    "bizdays[str]": lambda cal, inp: cal.bizdays(inp["dates_str"], inp["dates_to_str"]),
    "isbizday": lambda cal, inp: cal.isbizday(inp["dates"]),
    "offset": lambda cal, inp: cal.offset(inp["dates"], inp["counts"]),
    "following": lambda cal, inp: cal.following(inp["dates"]),
    "modified_following": lambda cal, inp: cal.modified_following(inp["dates"]),
    "seq": lambda cal, inp: cal.seq("2000-01-03", "2099-12-22"),
    "getdate": lambda cal, inp: cal.getdate("last bizday", inp["months"]),
    "getbizdays": lambda cal, inp: cal.getbizdays(inp["years"]),
}


def _cell(value: float | None, digits: int) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _row(case: str, n: int, seconds: float | None, mib: float | None, common: bool, scale: float) -> tuple[str, bool]:
    """Format one table row; return it and whether it is over budget."""
    limits = None if common else budget(case, n)
    limit_s, limit_mib = limits if limits else (None, None)
    if seconds is None:
        status = "skipped"
    elif limits is None:
        status = "-"
    else:
        over = seconds > limit_s * scale or (mib is not None and limit_mib is not None and mib > limit_mib * scale)
        status = "OVER" if over else "ok"
    cells = [case, str(n), _cell(seconds, 4), _cell(mib, 1), _cell(limit_s, 2), _cell(limit_mib, 0), status]
    return "| " + " | ".join(cells) + " |", status == "OVER"


def main(argv: list[str] | None = None) -> int:
    import argparse
    import importlib.metadata
    import platform

    import pandas

    import bizdays

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sizes", type=int, nargs="+", default=[1, 1000, 1_000_000])
    parser.add_argument("--calendars", nargs="+")
    parser.add_argument("--check", action="store_true", help="exit 1 if a row is over its budget")
    parser.add_argument("--scale", type=float, default=1.0, help="multiply every budget by this factor")
    parser.add_argument("--common", action="store_true", help="only the API and inputs that bizdays 1.0.19 also has")
    args = parser.parse_args(argv)
    if args.common and args.check:
        parser.error("--check cannot be used with --common (no budgets apply)")
    calendars = args.calendars or (list(PACKAGED) if args.common else [*PACKAGED, "PMC/B3", "XCAL/BVMF", "WORK/BR"])

    print(
        f"bizdays {importlib.metadata.version('bizdays')} at {bizdays.__file__}; Python {platform.python_version()}; "
        f"numpy {np.__version__}; pandas {pandas.__version__}; {platform.platform()}"
    )
    print()
    print("| case | n | seconds | peak MiB | budget s | budget MiB | status |")
    print("|---|---|---|---|---|---|---|")
    failed = False

    def emit(*row_args: Any) -> None:
        nonlocal failed
        line, over = _row(*row_args, args.common, args.scale)
        print(line, flush=True)
        failed = failed or over

    for name in calendars:
        loads = load_in_fresh_process(name)
        emit(f"load:{name}", 1, loads and loads["first_s"], loads and loads["first_mib"])
        emit(f"index:{name}", 1, loads and loads["second_s"], loads and loads["second_mib"])

    cal = bizdays.Calendar.load(name="ANBIMA")
    seq_done = False
    for n in args.sizes:
        inp = make_inputs(n, common=args.common)
        if not args.common:
            inp["dates_str"] = inp["dates"].astype(str)
            inp["dates_to_str"] = inp["dates_to"].astype(str)
        for case, call in CASES.items():
            if (case == "bizdays[str]" and args.common) or (case == "seq" and seq_done):
                continue
            size = 1 if case == "seq" else n
            seq_done = seq_done or case == "seq"
            # tracing makes Python loops about 35x slower, so big traced runs would take minutes
            memory = not ((case == "getdate" and size > 100_000) or (args.common and size >= 100_000))
            seconds, mib = measure(lambda: call(cal, inp), repeat=3 if size < 100_000 else 1, memory=memory)
            emit(case, size, seconds, mib)
    return 1 if args.check and failed else 0


if __name__ == "__main__":
    sys.exit(main())
