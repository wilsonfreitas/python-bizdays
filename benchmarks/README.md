# bizdays benchmarks

`bench.py` measures the time and the memory of the main `Calendar` operations, and the cost of
loading calendars. It uses only the Python standard library, NumPy and bizdays, so it also runs
against older bizdays versions.

## Run

From the repository root:

```bash
# Full run, with budgets checked (about 20 s to 2 minutes). Exit code 1 if a row is over budget.
uv run python benchmarks/bench.py --check

# Smoke run, the same one the test suite does (a few seconds).
uv run python benchmarks/bench.py --sizes 1 1000 --calendars ANBIMA --check

# v1 against v2: the API both versions share, with plain Python inputs.
uv run --no-project --isolated --with bizdays==1.0.19 python benchmarks/bench.py --common --sizes 1000 100000
uv run python benchmarks/bench.py --common --sizes 1000 100000
```

The first line of the output says which bizdays was measured (version and path), and the Python,
NumPy, pandas and platform versions. Check it: the v1 run must say `bizdays 1.0.19`.

Options:

* `--sizes N ...`: vector sizes for the operations (default `1 1000 1000000`). Size 1 means
  scalar inputs.
* `--calendars NAME ...`: calendars whose loading is measured (default
  `ANBIMA B3 Actual PMC/B3 XCAL/BVMF WORK/BR`; with `--common`, `ANBIMA B3 Actual`). A calendar
  whose provider package is not installed gives a `skipped` row.
* `--check`: exit with code 1 if a row is over its budget.
* `--scale F`: multiply every budget by `F` (default 1). Use 2 or 3 on a slow machine.
* `--common`: only the API that 1.0.19 also has, with lists of ISO date strings, lists of `int`
  and year `int` refs for `getdate`. No budgets apply, so `--common --check` is an error.

The output is a Markdown table, ready to paste into a PR or a Linear comment. The test suite runs
the smoke run in `tests/test_benchmarks.py`, so CI checks the budgets at sizes 1 and 1000 on
every Python version.

## What is measured

All operations use the ANBIMA calendar (range 2000-01-01 to 2099-12-25). Inputs come from
`numpy.random.default_rng(0)`, so every run uses the same data: dates from 2001-01-01 plus 0 to
29999 days, counts in [-100, 100), months from 2001-01 plus 0 to 999 months, years in
[2001, 2098]. Every input and result stays inside the ANBIMA range.

| case | call |
|---|---|
| `bizdays` | `cal.bizdays(dates, dates + 30)` with `datetime64` arrays |
| `bizdays[str]` | the same with arrays of ISO strings (not in `--common`) |
| `isbizday` | `cal.isbizday(dates)` |
| `offset` | `cal.offset(dates, counts)` |
| `following` | `cal.following(dates)` |
| `modified_following` | `cal.modified_following(dates)` |
| `seq` | `cal.seq("2000-01-03", "2099-12-22")`, run once, reported with n=1 |
| `getdate` | `cal.getdate("last bizday", months)`; in `--common`, year `int` refs |
| `getbizdays` | `cal.getbizdays(years)` |
| `load:<NAME>` | first `Calendar.load(name=NAME)` in a fresh process, with the import of the provider package |
| `index:<NAME>` | a second `Calendar.load(name=NAME)` in the same process: calendar data and `DateIndex` only |

How a row is measured:

* Time is the best (smallest) wall time of 3 calls (1 call for n of 100,000 or more), with
  `tracemalloc` off.
* Memory is the peak of one more call with `tracemalloc` (the standard-library memory tracer) on.
  Timing and tracing never share a call, because tracing makes Python loops about 35x slower.
* `getdate` above n=100,000 has no memory value (`-`): the traced call would take about 95 s.
  Its memory is linear in n, and the n=1000 row shows it.
* In `--common` mode, rows with n of 100,000 or more have no memory value either: v1 works in
  Python loops, so the traced calls would take minutes.
* Loads run in new Python processes, never in the benchmark process, so the import of one
  provider never hides the cost of another. The `load:` row is what a user pays on the first
  load. The `index:` row shows the part that is bizdays' own work, so a `DateIndex` regression
  on a large calendar does not hide inside the provider import.

## Budgets and regressions

Budgets are hard ceilings, about 10x the baseline, so they hold on slower CI machines and catch
only real breakage. `--check` compares every row with them.

| case | n=1 | n=1000 | n=1,000,000 |
|---|---|---|---|
| `bizdays`, `isbizday`, `offset`, `following`, `modified_following`, `getbizdays` | 0.01 s / 8 MiB | 0.05 s / 8 MiB | 1 s / 512 MiB |
| `bizdays[str]` | 0.01 s / 8 MiB | 0.05 s / 8 MiB | 5 s / 1024 MiB |
| `getdate` | 0.01 s / 8 MiB | 0.5 s / 32 MiB | 60 s / - |
| `seq` | 0.05 s / 32 MiB | | |
| `load:` and `index:` of ANBIMA, B3, Actual | 0.5 s / 32 MiB | | |
| `load:` and `index:` of PMC/..., XCAL/..., WORK/... | 10 s / 128 MiB | | |

A size that is not in the table uses the budget of the next larger size (n=100,000 uses the
n=1,000,000 budget). Above 1,000,000 there is no budget.

Regression rule: run the full benchmark on the same machine as the baseline below. A case that is
more than 2x slower, or uses more than 1.5x the memory, is a regression. Fix it, or write the
reason under "Trade-offs" in the same PR.

When to run the full benchmark:

* before a release;
* in every PR that changes `bizdays/dateindex.py`, `bizdays/calendar.py`, `bizdays/convert.py` or
  `bizdays/external.py`.

A row over its budget in the full `--check` run blocks the release.

## Baseline (feature/typing at b4fdd13)

Machine: Linux x86_64, 12 cores. Python 3.14.0, NumPy 2.3.4, pandas 2.3.3,
pandas_market_calendars 4.6.1, exchange_calendars 4.11.3, workalendar 17.0.0. Date: 2026-11-07.
The checkout still says version 1.0.20, and B3 still ends in 2026.

The table is the wave-I baseline. Before the release, WIL-153 runs `bench.py --check` and records
the full table in its Linear comment.

| case | n | seconds | peak MiB | budget s | budget MiB | status |
|---|---|---|---|---|---|---|
| load:ANBIMA | 1 | 0.0048 | 4.2 | 0.50 | 32 | ok |
| index:ANBIMA | 1 | 0.0032 | 3.9 | 0.50 | 32 | ok |
| load:B3 | 1 | 0.0024 | 1.4 | 0.50 | 32 | ok |
| index:B3 | 1 | 0.0011 | 1.1 | 0.50 | 32 | ok |
| load:Actual | 1 | 0.0027 | 4.1 | 0.50 | 32 | ok |
| index:Actual | 1 | 0.0015 | 4.1 | 0.50 | 32 | ok |
| load:PMC/B3 | 1 | 0.1061 | 20.3 | 10.00 | 128 | ok |
| index:PMC/B3 | 1 | 0.0608 | 12.4 | 10.00 | 128 | ok |
| load:XCAL/BVMF | 1 | 0.1084 | 6.1 | 10.00 | 128 | ok |
| index:XCAL/BVMF | 1 | 0.0020 | 1.0 | 10.00 | 128 | ok |
| load:WORK/BR | 1 | 0.0175 | 8.7 | 10.00 | 128 | ok |
| index:WORK/BR | 1 | 0.0013 | 2.4 | 10.00 | 128 | ok |
| bizdays | 1 | 0.0000 | 0.0 | 0.01 | 8 | ok |
| bizdays[str] | 1 | 0.0001 | 0.0 | 0.01 | 8 | ok |
| isbizday | 1 | 0.0000 | 0.0 | 0.01 | 8 | ok |
| offset | 1 | 0.0000 | 0.0 | 0.01 | 8 | ok |
| following | 1 | 0.0000 | 0.0 | 0.01 | 8 | ok |
| modified_following | 1 | 0.0000 | 0.0 | 0.01 | 8 | ok |
| seq | 1 | 0.0001 | 0.2 | 0.05 | 32 | ok |
| getdate | 1 | 0.0000 | 0.0 | 0.01 | 8 | ok |
| getbizdays | 1 | 0.0000 | 0.0 | 0.01 | 8 | ok |
| bizdays | 1000 | 0.0000 | 0.1 | 0.05 | 8 | ok |
| bizdays[str] | 1000 | 0.0002 | 0.4 | 0.05 | 8 | ok |
| isbizday | 1000 | 0.0000 | 0.0 | 0.05 | 8 | ok |
| offset | 1000 | 0.0001 | 0.1 | 0.05 | 8 | ok |
| following | 1000 | 0.0000 | 0.1 | 0.05 | 8 | ok |
| modified_following | 1000 | 0.0001 | 0.1 | 0.05 | 8 | ok |
| getdate | 1000 | 0.0137 | 0.2 | 0.50 | 32 | ok |
| getbizdays | 1000 | 0.0001 | 0.1 | 0.05 | 8 | ok |
| bizdays | 1000000 | 0.0640 | 96.3 | 1.00 | 512 | ok |
| bizdays[str] | 1000000 | 0.3008 | 339.6 | 5.00 | 1024 | ok |
| isbizday | 1000000 | 0.0079 | 36.2 | 1.00 | 512 | ok |
| offset | 1000000 | 0.0210 | 81.1 | 1.00 | 512 | ok |
| following | 1000000 | 0.0189 | 74.4 | 1.00 | 512 | ok |
| modified_following | 1000000 | 0.0724 | 89.6 | 1.00 | 512 | ok |
| getdate | 1000000 | 13.6112 | - | 60.00 | - | ok |
| getbizdays | 1000000 | 0.0710 | 104.0 | 1.00 | 512 | ok |

## v1 1.0.19 against v2

`--common` mode, same machine and date. v1 is bizdays 1.0.19 from PyPI on Python 3.11.14 and
NumPy 2.4.6 (the versions `uv run --isolated` picked); v2 is the baseline checkout above. Times
in seconds. The load rows are left out: both versions load the packaged calendars in a few
milliseconds.

| case | n | v1 1.0.19 | v2 | v2 speed-up |
|---|---|---|---|---|
| `bizdays` | 1000 | 0.0054 | 0.0005 | 11x |
| `isbizday` | 1000 | 0.0020 | 0.0002 | 10x |
| `offset` | 1000 | 0.0025 | 0.0006 | 4x |
| `following` | 1000 | 0.0024 | 0.0002 | 12x |
| `modified_following` | 1000 | 0.0029 | 0.0003 | 10x |
| `seq` | 1 | 0.0031 | 0.0001 | 31x |
| `getdate` | 1000 | 0.0123 | 0.0139 | 0.9x |
| `getbizdays` | 1000 | 0.0053 | 0.0003 | 18x |
| `bizdays` | 100000 | 0.5472 | 0.0270 | 20x |
| `isbizday` | 100000 | 0.2011 | 0.0126 | 16x |
| `offset` | 100000 | 0.2654 | 0.0359 | 7x |
| `following` | 100000 | 0.2454 | 0.0130 | 19x |
| `modified_following` | 100000 | 0.2532 | 0.0186 | 14x |
| `getdate` | 100000 | 1.2518 | 1.3667 | 0.9x |
| `getbizdays` | 100000 | 0.5335 | 0.0220 | 24x |

## Trade-offs

* `getdate` still loops in Python, once per element: about 13 µs per ref, so about 13.5 s per
  million refs. This is the same speed as 1.0.19, so it is not a regression, but it is not
  vectorized like the other operations. It is tracked in the backlog issue
  "Vectorize getdate in DateIndex".
* String inputs cost about 0.3 to 0.45 s per million dates to parse, and they use the most memory
  (about 340 MiB peak for two arrays of a million strings). For big jobs, pass `datetime64`
  arrays.
* The first load of a PMC or XCAL calendar takes about 0.1 s (about 1 s with a cold disk cache),
  mostly the import of the provider package. The `index:` rows show the part that is bizdays'
  own work.
