# Code Quality Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Address the critical and high-priority issues identified in the code review to improve correctness, maintainability, and CI reliability.

**Architecture:** Issues are grouped into six logical tasks executed sequentially. Each task is independently testable and committable. The dual-Calendar architecture (legacy `bizdays.py` + new `calendar.py`) is preserved throughout — we are not removing the legacy implementation.

**Tech Stack:** Python 3.9+, numpy, pandas, uv, pytest, hatchling

---

## Verification

Before starting, confirm the test suite passes:

```bash
uv run pytest -v
```

All tests must pass before any changes are made.

---

### Task 1: Fix the CI Pipeline (broken, no code changes needed)

**Files:**
- Modify: `.github/workflows/pytest.yml`

The CI pipeline still references Poetry even though the project migrated to `uv`. It also tests Python 3.8, which conflicts with `pyproject.toml`'s `requires-python = ">=3.9"`. This task has no code changes and requires no tests — it's a config fix.

**Step 1: Update the CI workflow**

Replace the entire contents of `.github/workflows/pytest.yml`:

```yaml
name: Test Python package

on:
  push:
    branches: [ master ]
  pull_request:
    branches: [ master ]

jobs:
  pytest:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4
    - name: Install uv
      uses: astral-sh/setup-uv@v5
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: uv sync --extra dev
    - name: Run tests
      run: uv run pytest -v
```

**Step 2: Commit**

```bash
git add .github/workflows/pytest.yml
git commit -m "ci: migrate from Poetry to uv, update Python matrix to 3.9-3.12"
```

---

### Task 2: Fix `pyproject.toml` — Add Missing `numpy` Dep, Make PMC Optional, Remove Stale `setup.cfg`

**Files:**
- Modify: `pyproject.toml`
- Delete: `setup.cfg`

`numpy` is used throughout the new implementation but is not listed as a dependency. `pandas-market-calendars` is a ~50 MB optional dependency used only for `Calendar.load("PMC/...")`, yet it's a hard requirement today.

**Step 1: Update `pyproject.toml`**

Change the `[project]` section:

```toml
[project]
name = "bizdays"
version = "1.0.16"
description = "Functions to handle business days calculations"
authors = [{ name = "wilsonfreitas", email = "wilson.freitas@gmail.com" }]
readme = "README.md"
requires-python = ">=3.9"
dependencies = ["numpy>=1.24", "pandas>=2,<3"]

[project.optional-dependencies]
pmc = ["pandas-market-calendars>=4,<5"]
dev = ["pytest", "pycodestyle", "ipykernel"]
docs = ["Sphinx", "nbsphinx", "matplotlib", "lxml", "alabaster", "ipywidgets"]
```

**Step 2: Run the tests to verify nothing broke**

```bash
uv sync --extra dev
uv run pytest -v
```

Expected: all tests pass.

**Step 3: Delete `setup.cfg`**

This file is a stale remnant from before `pyproject.toml` was adopted. It has version `1.0.2` while `pyproject.toml` has `1.0.16`.

```bash
rm setup.cfg
```

**Step 4: Verify tests still pass**

```bash
uv run pytest -v
```

**Step 5: Commit**

```bash
git add pyproject.toml
git rm setup.cfg
git commit -m "fix: add numpy dep, make pmc optional extra, remove stale setup.cfg"
```

---

### Task 3: Expose a Public API from `__init__.py`

**Files:**
- Modify: `bizdays/__init__.py`

Right now `__init__.py` is empty. Anyone doing `from bizdays import Calendar` gets nothing. The intended public API is the new numpy-based `Calendar` from `calendar.py`, plus the legacy option helpers from `bizdays.py`.

**Step 1: Write a test that verifies the public import**

Add to `tests/test_calendar.py`:

```python
def test_public_import():
    """Verify Calendar is importable from the top-level package."""
    from bizdays import Calendar
    cal = Calendar.load("B3")
    assert cal.name == "B3"


def test_public_option_import():
    """Verify get_option and set_option are importable from the top-level package."""
    from bizdays import get_option, set_option
    set_option("mode", "python")
    assert get_option("mode") == "python"
```

**Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_calendar.py::test_public_import tests/test_calendar.py::test_public_option_import -v
```

Expected: `ImportError: cannot import name 'Calendar' from 'bizdays'`

**Step 3: Populate `__init__.py`**

```python
from bizdays.calendar import Calendar
from bizdays.bizdays import get_option, set_option

__all__ = ["Calendar", "get_option", "set_option"]
```

**Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_calendar.py -v
```

Expected: all tests pass.

**Step 5: Run the full suite to check for regressions**

```bash
uv run pytest -v
```

**Step 6: Commit**

```bash
git add bizdays/__init__.py tests/test_calendar.py
git commit -m "feat: expose public API from bizdays/__init__.py"
```

---

### Task 4: Fix Mutable Default Arguments in Both `Calendar` Classes

**Files:**
- Modify: `bizdays/calendar.py:101-108`
- Modify: `bizdays/bizdays.py:588-596`

Using `[]` as a default argument is a classic Python bug — the same list object is shared across all calls. Use `None` as the sentinel.

**Step 1: Write a test that demonstrates the issue (and will document the fix)**

Add to `tests/test_calendar.py`:

```python
def test_calendar_default_args_are_not_shared():
    """Mutable default arguments must not be shared between instances."""
    cal1 = Calendar()
    cal2 = Calendar()
    # Mutating one instance's internal list must not affect the other
    cal1._holidays  # just access — the real check is that both construct independently
    assert cal1.holidays == cal2.holidays
    assert cal1.holidays is not cal2.holidays
```

**Step 2: Run test to confirm it currently passes (no mutation bug triggered yet)**

```bash
uv run pytest tests/test_calendar.py::test_calendar_default_args_are_not_shared -v
```

**Step 3: Fix `bizdays/calendar.py`**

Change the `Calendar.__init__` signature (lines 101-108):

```python
def __init__(
    self,
    holidays: date_list_types | None = None,
    weekdays: list[str] | None = None,
    startdate: date | datetime | str = "",
    enddate: date | datetime | str = "",
    name: str = "",
    financial: bool = True,
):
    if holidays is None:
        holidays = []
    if weekdays is None:
        weekdays = []
```

**Step 4: Fix `bizdays/bizdays.py`**

Apply the same change to `Calendar.__init__` (lines 588-596) in the legacy file:

```python
def __init__(
    self,
    holidays: list[date | datetime | str] | None = None,
    weekdays: list[str] | None = None,
    startdate: date | datetime | str = "",
    enddate: date | datetime | str = "",
    name: str = "",
    financial: bool = True,
):
    if holidays is None:
        holidays = []
    if weekdays is None:
        weekdays = []
```

**Step 5: Run the full suite**

```bash
uv run pytest -v
```

Expected: all tests pass.

**Step 6: Commit**

```bash
git add bizdays/calendar.py bizdays/bizdays.py tests/test_calendar.py
git commit -m "fix: replace mutable default args with None sentinel in Calendar"
```

---

### Task 5: Fix the Relative Path in `test_dateindex_numpy.py`

**Files:**
- Modify: `tests/test_dateindex_numpy.py:196-197`

The test file loads a calendar with `"data/ANBIMA.cal"` — a path relative to wherever pytest is invoked. If you run `pytest` from a subdirectory, or if a CI runner uses a different working directory, it breaks.

**Step 1: Run the affected tests from a different directory to confirm the bug**

```bash
cd /tmp && uv --project /home/wilson/dev/python/python-bizdays run pytest /home/wilson/dev/python/python-bizdays/tests/test_dateindex_numpy.py -v 2>&1 | head -20
cd /home/wilson/dev/python/python-bizdays
```

Expected: `FileNotFoundError` or similar.

**Step 2: Fix the path using `pathlib`**

At the top of `tests/test_dateindex_numpy.py`, after the imports, change:

```python
# Before:
HOL, WD = load_calendar_from_file("data/ANBIMA.cal")

# After — add this import near the top with other imports:
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "bizdays" / "data"

HOL, WD = load_calendar_from_file(str(_DATA_DIR / "ANBIMA.cal"))
```

Also update the three calls inside individual tests that still use `"data/ANBIMA.cal"`:

In `test_dateindex_bizdays`, `test_dateindex_bizdays_reversed`, `test_dateindex_bizdays_vectorized`, `test_dateindex_bizdays_vectorized_reversed`, `test_offset_single_values`, `test_offset_vectorized`, `test_adjust_single_values`, `test_adjust_vectorized` — they all call `load_calendar_from_file("data/ANBIMA.cal")`. Change each to:

```python
hol, wd = load_calendar_from_file(str(_DATA_DIR / "ANBIMA.cal"))
```

**Step 3: Run the tests**

```bash
uv run pytest tests/test_dateindex_numpy.py -v
```

Expected: all pass.

**Step 4: Commit**

```bash
git add tests/test_dateindex_numpy.py
git commit -m "fix: use absolute path for ANBIMA.cal in test_dateindex_numpy"
```

---

### Task 6: Expand `test_calendar.py` — Cover the New numpy `Calendar`

**Files:**
- Modify: `tests/test_calendar.py`

The new numpy-based `Calendar` (in `calendar.py`) has only 3 tests. The core methods — `bizdays`, `isbizday`, `offset`, `seq`, `adjust_next`, `adjust_previous`, `modified_following`, `modified_preceding`, `diff` — are completely untested at the `Calendar` layer.

Use the B3 or ANBIMA fixture to keep tests realistic. Each test below is independent; add them all to `tests/test_calendar.py`.

**Step 1: Add a shared fixture**

```python
import pytest
import numpy as np
from bizdays.calendar import Calendar


@pytest.fixture(scope="module")
def anbima():
    return Calendar.load("ANBIMA")


@pytest.fixture(scope="module")
def actual():
    return Calendar(name="actual")
```

**Step 2: Add `bizdays` tests**

```python
def test_bizdays_scalar(anbima):
    assert anbima.bizdays("2013-01-02", "2013-01-31") == 21


def test_bizdays_reversed_is_negative(anbima):
    assert anbima.bizdays("2013-01-31", "2013-01-02") == -21


def test_bizdays_same_date(anbima):
    assert anbima.bizdays("2013-01-02", "2013-01-02") == 0


def test_bizdays_vectorized(anbima):
    result = anbima.bizdays(
        ["2013-01-02", "2013-01-02"],
        ["2013-01-31", "2013-02-28"],
    )
    assert list(result) == [21, 39]
```

**Step 3: Add `isbizday` tests**

```python
def test_isbizday_true(anbima):
    assert anbima.isbizday("2013-01-02") is True


def test_isbizday_false_holiday(anbima):
    # 2013-01-01 is a holiday in ANBIMA
    assert anbima.isbizday("2013-01-01") is False


def test_isbizday_vectorized(anbima):
    result = anbima.isbizday(["2013-01-01", "2013-01-02"])
    assert list(result) == [False, True]
```

**Step 4: Add `offset` tests**

```python
def test_offset_positive(anbima):
    result = anbima.offset("2013-01-02", 1)
    assert str(result) == "2013-01-03"


def test_offset_zero(anbima):
    # offset by 0 returns the same date even if it's a holiday
    result = anbima.offset("2013-01-01", 0)
    assert str(result) == "2013-01-01"


def test_offset_negative(anbima):
    result = anbima.offset("2013-01-03", -1)
    assert str(result) == "2013-01-02"


def test_offset_vectorized(anbima):
    result = anbima.offset(["2013-01-02", "2013-01-03"], [1, 1])
    assert str(result[0]) == "2013-01-03"
    assert str(result[1]) == "2013-01-04"
```

**Step 5: Add `seq` tests**

```python
def test_seq_returns_only_bizdays(anbima):
    seq = anbima.seq("2013-01-01", "2013-01-07")
    # 2013-01-01 is a holiday; 2013-01-05 and 2013-01-06 are weekend
    for d in seq:
        assert anbima.isbizday(str(d))


def test_seq_reversed(anbima):
    fwd = anbima.seq("2013-01-02", "2013-01-10")
    rev = anbima.seq("2013-01-10", "2013-01-02")
    assert list(fwd) == list(reversed(list(rev)))
```

**Step 6: Add `adjust_next` and `adjust_previous` tests**

```python
def test_adjust_next_on_holiday(anbima):
    # 2013-01-01 (New Year) -> next bizday
    result = anbima.adjust_next("2013-01-01")
    assert str(result) == "2013-01-02"


def test_adjust_next_on_bizday(anbima):
    result = anbima.adjust_next("2013-01-02")
    assert str(result) == "2013-01-02"


def test_adjust_previous_on_holiday(anbima):
    result = anbima.adjust_previous("2013-01-01")
    assert str(result) == "2012-12-31"


def test_adjust_previous_on_bizday(anbima):
    result = anbima.adjust_previous("2013-01-02")
    assert str(result) == "2013-01-02"
```

**Step 7: Add `modified_following` and `modified_preceding` tests**

```python
def test_modified_following_stays_in_month(anbima):
    # If following would cross into next month, use preceding instead
    # 2022-04-30 is Saturday; following = 2022-05-02 (different month)
    # so modified_following should return 2022-04-29
    result = anbima.modified_following("2022-04-30")
    assert str(result)[:7] == "2022-04"  # stays in April


def test_modified_preceding_stays_in_month(anbima):
    # If preceding would cross into previous month, use following instead
    # 2013-02-01 is Friday (bizday); no change needed - use a weekend that falls on 1st
    # 2015-03-01 is Sunday; preceding = 2015-02-27 (different month)
    result = anbima.modified_preceding("2015-03-01")
    assert str(result)[:7] == "2015-03"  # stays in March
```

**Step 8: Add `diff` test**

```python
def test_diff(anbima):
    dates = ["2013-01-02", "2013-01-03", "2013-01-04"]
    result = anbima.diff(dates)
    assert list(result) == [1, 1]


def test_diff_single_element(anbima):
    result = anbima.diff(["2013-01-02"])
    assert len(result) == 0
```

**Step 9: Run all new tests**

```bash
uv run pytest tests/test_calendar.py -v
```

Expected: all pass.

**Step 10: Run the full suite**

```bash
uv run pytest -v
```

**Step 11: Commit**

```bash
git add tests/test_calendar.py
git commit -m "test: expand calendar.py test coverage for all public methods"
```

---

## What's NOT in This Plan (Deferred)

The following lower-priority issues were identified in the review but are deferred to avoid scope creep. They can be addressed in follow-up plans:

- **Code duplication** (`Date`, `isstr`, `isseq` defined in both `bizdays.py` and new modules) — requires careful legacy compatibility testing
- **`TypeVar` misuse** — purely cosmetic, needs careful typing work on `feature/typing` branch
- **Recursive `following()`/`preceding()` in legacy `DateIndex`** — legacy code, low practical risk
- **Dict-loop vs pure numpy in `dateindex.py`** — performance optimization, separate plan
- **Error message cleanup** (`"cannot format"` in comparison methods) — low impact
- **Docstrings for `dateindex.py`, `utils.py`, `date.py`** — documentation sprint

---

## Final Verification

After all tasks are complete:

```bash
uv run pytest -v
```

All tests must pass. Then open a PR from `feature/typing` (or a new branch) to `master`.
