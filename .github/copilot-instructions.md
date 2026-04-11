# Copilot Instructions

## Build, test, and lint commands

This project uses `uv` for environment and dependency management. `uv sync` installs the package in editable mode because `pyproject.toml` sets `[tool.uv] package = true`.

```bash
# Install runtime + dev dependencies
uv sync --extra dev

# Run the full test suite
uv run pytest

# Run one test file
uv run pytest tests/test_calendar.py

# Run one test
uv run pytest tests/test_calendar.py::test_calendar_load

# Run style checks
uv run pycodestyle bizdays tests

# Build the Sphinx docs
uv sync --all-extras
make -C docs html
```

## High-level architecture

`bizdays` currently carries **two Calendar implementations**:

- `bizdays/calendar.py` is the **current public Calendar API**. `bizdays/__init__.py` re-exports this `Calendar`, so `from bizdays import Calendar` and `from bizdays.calendar import Calendar` both point to the numpy-backed implementation.
- `bizdays/bizdays.py` is the **legacy implementation**. It still matters because it owns the global `get_option` / `set_option` runtime switches and older behavior around `python` vs `pandas` modes.

The numpy-backed path is split across a few modules:

- `bizdays/calendar.py` normalizes user inputs, applies scalar-vs-sequence handling, and delegates date math to `DateIndex`.
- `bizdays/dateindex.py` precomputes the full date range, business-day mask, and forward/reverse cumulative indices so `bizdays`, `offset`, `adjust`, and `seq` can run as indexed array operations instead of scanning day by day.
- `bizdays/date.py` converts supported inputs (`str`, `date`, `datetime`, `np.datetime64`, `None`) into a common date wrapper.
- `bizdays/utils.py` contains the shared helpers that the vectorized API relies on, especially `isseq()` and `recycle_arrays()`.

Calendar definitions come from packaged `.cal` files in `bizdays/data/`. `Calendar.load("B3")` and `Calendar.load("ANBIMA")` read those bundled files; `Calendar.load(filename=...)` reads an arbitrary calendar file; `Calendar.load("PMC/<name>")` delegates to `pandas_market_calendars`.

## Key conventions

- Preserve the **scalar/sequence contract** in `bizdays/calendar.py`: public methods detect sequences with `isseq()`, normalize with `np.atleast_1d(...)`, recycle mismatched argument lengths with `recycle_arrays()`, and return a scalar only when the original input was scalar.
- Treat the repo as a **transition state between the new and legacy APIs**. The top-level `Calendar` is the new numpy implementation, but `get_option` / `set_option` still come from `bizdays/bizdays.py`, and some tests/docs still reflect legacy behavior.
- Tests that change runtime mode should explicitly set and restore it. The mode is global process state, not per-calendar state.
- `Calendar.load()` is the preferred entry point for bundled calendars. Use `name=` for packaged calendars, `filename=` for custom `.cal` files, and the `PMC/` prefix only when the pandas-market-calendars integration is intended.
- Weekday names are parsed leniently: both full names and short forms such as `"sat"` / `"sun"` are accepted because matching is based on the first three letters.
- `Calendar(name="actual")` is the common “all days are business days” calendar used throughout the tests.
