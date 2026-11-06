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

# Run Ruff checks
uv run ruff check .

# Run mypy checks
uv run mypy

# Run all pre-commit checks
uv run pre-commit run --all-files

# Run legacy style checks
uv run pycodestyle bizdays tests

# Build the Sphinx docs
uv sync --all-extras
make -C docs html
```

## High-level architecture

`bizdays` has **one Calendar implementation**:

- `bizdays/calendar.py` is the **current public Calendar API**. `bizdays/__init__.py` re-exports this `Calendar`, so `from bizdays import Calendar` and `from bizdays.calendar import Calendar` both point to the numpy-backed implementation.
- The public API is exactly `bizdays.__all__`: `Calendar`, `list_calendars` and `DateOutOfRange` (a `ValueError` subclass). Every submodule is internal. The legacy `bizdays/bizdays.py` and `get_option` / `set_option` were removed in 2.0.0.

The numpy-backed path is split across a few modules:

- `bizdays/calendar.py` normalizes user inputs, applies scalar-vs-sequence handling, and delegates date math to `DateIndex`.
- `bizdays/dateindex.py` precomputes the full date range, business-day mask, and forward/reverse cumulative indices so `bizdays`, `offset`, `adjust`, and `seq` can run as indexed array operations instead of scanning day by day.
- `bizdays/date.py` converts supported inputs (`str`, `date`, `datetime`, `np.datetime64`, `None`) into a common date wrapper.
- `bizdays/utils.py` contains the shared helpers that the vectorized API relies on, especially `isseq()` and `recycle_arrays()`.

Calendar definitions come from packaged JSON files in `bizdays/data/`, using the R-bizdays-style schema. `Calendar.load("B3")` and `Calendar.load("ANBIMA")` read those bundled files; `Calendar.load(filename=...)` reads an arbitrary JSON calendar file; `Calendar.load("PMC/<name>")` delegates to `pandas_market_calendars`.

## Key conventions

- Preserve the **scalar/sequence contract** in `bizdays/calendar.py`: public methods detect sequences with `isseq()`, normalize with `np.atleast_1d(...)`, recycle mismatched argument lengths with `recycle_arrays()`, and return a scalar only when the original input was scalar.
- There is no global runtime mode: the top-level `Calendar` always returns NumPy results. `tests/legacy/` is reference only and is not collected by pytest.
- `Calendar.load()` is the preferred entry point for bundled calendars. Use `name=` for packaged calendars, `filename=` for custom JSON calendar files, and the `PMC/` prefix only when the pandas-market-calendars integration is intended.
- Weekday names are parsed leniently: both full names and short forms such as `"sat"` / `"sun"` are accepted because matching is based on the first three letters.
- `Calendar(name="actual")` is the common “all days are business days” calendar used throughout the tests.
