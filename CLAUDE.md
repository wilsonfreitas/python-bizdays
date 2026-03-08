# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run a single test file
poetry run pytest test_bizdays.py

# Run a single test
poetry run pytest test_bizdays.py::test_name -v

# Build distribution
poetry build
```

## Architecture

This is a pure Python library for financial market business day calculations, focused on Brazilian markets (B3, ANBIMA).

**Package layout** (restructured in v1.0.19 from single-file to package):
- `bizdays/__init__.py` — all core logic (~1137 lines)
- `bizdays/*.cal` — bundled holiday calendar files (B3, ANBIMA, Actual)
- `test_*.py` — tests at repo root (legacy location, not in `tests/`)

**Core classes** (all in `bizdays/__init__.py`):

| Class | Purpose |
|---|---|
| `Calendar` | Public API — wraps `DateIndex` and exposes business day methods |
| `DateIndex` | Internal index structure for O(1) business day lookups |
| `Date` | Flexible date input wrapper (accepts str, date, datetime, Date) |
| `VectorizedOps` | Enables batch operations; handles pandas.DatetimeIndex and lists |

**Data flow:**
1. `Calendar` is created with a list of holidays and non-working weekdays
2. `Calendar` constructs a `DateIndex` over a fixed date range
3. `DateIndex` builds sorted arrays and positional mappings for fast lookups
4. Scalar calls go directly to `DateIndex`; vectorized calls go through `VectorizedOps`
5. Return type is controlled by the global `options` dict (`mode`, `mode.datetype`)

**Calendar file format** (`.cal`):
```
Saturday
Sunday
2000-01-01
2000-03-06
```
First lines are non-working weekday names; subsequent ISO dates are holidays.

**Loading calendars:**
```python
Calendar.load("B3")                         # built-in
Calendar.load(filename="/path/to/file.cal") # custom file
Calendar.load("PMC/NYSE")                   # pandas_market_calendars
```

**Output mode configuration:**
```python
set_option("mode", "pandas")           # return pd.Timestamp
set_option("mode.datetype", "iso")     # return ISO strings
```

## Key Conventions

- All public `Calendar` methods support both scalar and vectorized (list/DatetimeIndex) inputs via `VectorizedOps`.
- The `@daterangecheck` / `@daterangecheck2` decorators enforce that dates fall within the calendar's built range and raise `DateOutOfRange`.
- Pandas is an optional dependency — code guards with `PANDAS_INSTALLED` flag. Tests for pandas integration live in `test_bizdays_pandas.py`.
- The `tests/` directory exists but is empty; all tests are at the repo root.
