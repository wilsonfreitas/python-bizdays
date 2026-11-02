# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

This project uses `uv` for dependency and environment management.

```bash
# Install dependencies (including dev tools like pytest)
uv sync --extra dev

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_calendar.py

# Run a specific test
uv run pytest tests/test_calendar.py::test_Calendar_seq

# Run tests with verbose output
uv run pytest -v

# Run Ruff checks
uv run ruff check .

# Run mypy checks
uv run mypy

# Run all pre-commit checks
uv run pre-commit run --all-files
```

## Architecture

**bizdays** is a Python library for financial business day calculations. It provides two parallel implementations of the `Calendar` class:

### Dual Calendar Implementation

- **`bizdays/bizdays.py`** — Legacy implementation using pure Python `datetime.date` objects and a dict-based `DateIndex`. Also defines `VectorizedOps` for sequence operations via iteration, and `get_option`/`set_option` for runtime mode switching (python vs pandas); these options do not affect the NumPy `Calendar`. It is not the public `Calendar`: `bizdays/__init__.py` only re-exports `get_option`/`set_option` from it.

- **`bizdays/calendar.py`** — New numpy-based `Calendar` implementation that wraps the numpy `DateIndex` from `dateindex.py`. Uses `np.datetime64` arrays throughout for vectorized operations. Methods handle both scalar and array inputs via `isseq()` detection and `recycle_arrays()`. This is the public `bizdays.Calendar`: `bizdays/__init__.py` exports `Calendar` and `list_calendars` from here.

### Supporting modules

- **`bizdays/dateindex.py`** — Numpy-based `DateIndex`: builds forward/reverse cumulative sum indices (`_fwd_index`, `_rev_index`) over the date range for O(1) bizday lookups, offsets, and sequences.

- **`bizdays/bizdays.py`** (also contains) — Legacy `DateIndex` using a Python dict mapping `date → DateIndexNode` (with `workday`, `revworkday`, `currentday`, `isholiday` fields).

- **`bizdays/date.py`** — `Date` wrapper supporting `str`, `datetime.date`, `datetime.datetime`, `np.datetime64`, and `None`.

- **`bizdays/getdate_parser.py`** — Parser for `getdate` expressions such as `"last bizday"` or `"1st bizday before 2nd fri"`; `DateIndex.getdate` resolves them.

- **`bizdays/utils.py`** — Shared utilities: `isseq()`, `isstr()`, `match()`, `recycle_arrays()`, `DateOutOfRange`.

### Calendar data files

Built-in JSON files (in `bizdays/data/`) for **B3**, **ANBIMA**, and **Actual** calendars, using the R-bizdays-style schema (parsed by `bizdays/calendarfile.py`). `Calendar.load()` is keyword-only: `name=` for built-in calendars, `filename=` for a custom JSON file. External calendars use name prefixes, each behind an optional extra, with adapters in `bizdays/external.py`: `name="PMC/<name>"` (`pandas_market_calendars`, extra `pmc`), `name="XCAL/<name>"` (`exchange_calendars`, extra `xcal`) and `name="WORK/<code>"` (`workalendar`, extra `work`).

### Key design pattern

All public Calendar methods handle scalar vs. sequence inputs uniformly: detect with `isseq()`, convert to `np.atleast_1d`, apply vectorized numpy ops, then return scalar if input was scalar (`result[0]`) or array otherwise.
