### version 2.0.0 (2026-11-07)

bizdays 2.0.0 is a major release with breaking changes, compared with 1.0.19 (1.0.20 has the same API and only adds B3 data).
Read the [migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html) before you upgrade.

#### Upgrade

* Install: `pip install --upgrade "bizdays==2.0.0"`.
* `pandas_market_calendars` is no longer installed by default. Install the extra for the provider you use: `pip install "bizdays[pmc]"`, `pip install "bizdays[xcal]"` or `pip install "bizdays[work]"`.
* To stay on 1.x: `pip install "bizdays<2"`.

#### Supported environments

* Python 3.10 to 3.14.
* Dependencies: `numpy>=1.24` and `pandas>=2`. Tested on pandas 2 and pandas 3.

#### Breaking changes

* v1 needed Python 3.9 or newer and pandas 2 (not 3); v2 needs Python 3.10 or newer, and names `numpy>=1.24` as a dependency ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-python-and-dependencies)).
* v1 always installed `pandas_market_calendars`; v2 makes each provider an optional extra (`pmc`, `xcal`, `work`), and loading a provider calendar without its extra raises `ImportError` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-optional-providers)).
* v1 exported many helpers at the top level (`Date`, `load_holidays`, `isseq`, ...); v2 exports only `Calendar`, `list_calendars` and `DateOutOfRange` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-removed-top-level-names)).
* v1 had `get_option` and `set_option` with pandas and ISO modes; v2 removes them and always returns NumPy values ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-options-and-modes)).
* v1 used `cal.vec` for vector calls; v2 removes it, and every method takes a single value or a vector ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-vec-removed)).
* v1 `DateOutOfRange` was a plain `Exception`; v2 makes it a `ValueError` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-date-out-of-range)).
* v1 `Calendar(...)` accepted bad setups; v2 changes some defaults and raises `ValueError` for bad arguments, such as unknown weekday names or a calendar with no business days ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-constructor)).
* v1 `Calendar.load("ANBIMA")` worked by position; v2 takes keywords only: `name=` or `filename=` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-load-keyword-only)).
* v1 read text `.cal` files; v2 reads only JSON calendar files ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-cal-files)).
* v1 raised a plain `Exception` for an unknown calendar or a missing file; v2 raises `ValueError` or `FileNotFoundError` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-load-errors)).
* v1 accepted loose date strings such as `"2024-1-2"`; v2 accepts only `YYYY-MM-DD` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-strict-date-strings)).
* v1 accepted any iterable as a vector; v2 rejects sets, generators, `range`, dicts and 2-D inputs such as a `DataFrame` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-input-containers)).
* v1 read `True` as a count of 1; v2 needs whole numbers and raises `ValueError` for `True` or `1.5` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-whole-counts)).
* v1 returned Python values (`datetime.date`, `int`, `bool`, lists); v2 returns NumPy values (`datetime64`, `float64`, `bool_`, arrays) ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-return-types)).
* v1 used `None` for missing values; v2 uses `NaN`, `NaT` or a masked array ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-missing-values)).
* v1 recycled vectors of different lengths; v2 needs equal lengths, or one of length 1 ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-vector-lengths)).
* v1 wrapped some results past the calendar ends; v2 raises `DateOutOfRange` for any input or result outside the calendar range ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-calendar-range)).
* v1 had `getdate(expr, year, month)`; v2 has `getdate(expr, ref)`, where `ref` is a year, a month or a date ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-getdate-signature)).
* v1 accepted some wrong `getdate` expressions, such as `"2st bizday"`; v2 follows the R bizdays grammar more closely ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-getdate-grammar)).
* v1 `getbizdays` returned `int` and partial counts at the calendar ends; v2 returns `float64`, raises `DateOutOfRange` for periods outside the range, and rejects `month=0` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-getbizdays)).

#### New features

See the [API reference](https://wilsonfreitas.github.io/python-bizdays/api.html) for details.

* `Calendar` is built on NumPy, and every method is vectorized.
* `list_calendars()` lists the packaged and provider calendars.
* `Calendar.inrange` tells which dates are inside the calendar range.
* `DateOutOfRange.positions` lists every element that is out of range.
* `getdate(expr, ref)` accepts date refs, `previous <weekday>`, and vectors of expressions and refs.
* `getbizdays` is rebuilt: the whole period must be inside the calendar range.
* New calendar providers `XCAL/<name>` (`exchange_calendars`) and `WORK/<code>` (`workalendar`), next to `PMC/<name>`.
* Calendars are JSON files, in the same format as R bizdays ([#57](https://github.com/wilsonfreitas/python-bizdays/issues/57)).
* Inline type hints, with a `py.typed` marker.
* `numpy.datetime64` values and pandas `Timestamp`, `Series` and `DatetimeIndex` inputs work everywhere.

#### Bug fixes

* `getdate("1st bizday before 2nd fri", ...)` works ([#31](https://github.com/wilsonfreitas/python-bizdays/issues/31)). In 1.0.19 it raised `ValueError`. In v2, `getdate("1st bizday before 2nd fri", "2024-01")` gives 2024-01-11 on ANBIMA.
* `offset` no longer wraps around past the calendar ends: on ANBIMA, `offset("2000-01-03", -3)` gave 2099-12-22, and now it raises `DateOutOfRange` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-calendar-range)).
* `getdate("first bizday before first day", 2024)` gives 2023-12-29, not 2024-01-02 ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-getdate-year-ref)).
* `getbizdays(2099)` on ANBIMA no longer returns a partial count (245); it raises `DateOutOfRange` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-getbizdays)).
* Empty inputs give empty results instead of `ZeroDivisionError` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-vector-lengths)).
* `Calendar(startdate=..., enddate=...)` with the start after the end raises `ValueError` instead of `KeyError` ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-constructor)).

#### Calendar data

* ANBIMA: 2000-01-01 to 2099-12-25.
* B3: 2000-01-01 to 2099-12-31. Holidays up to 2026 are B3's official ones. From 2027 they are projected: ANBIMA holidays, plus December 24, plus the last weekday of the year.
* Actual: 1900-01-01 to 2199-12-31.
* Every packaged calendar covers at least 10 years ahead, and a test checks it ([migration guide](https://wilsonfreitas.github.io/python-bizdays/migration.html#migrate-calendar-data)).
* Provider calendars (`PMC/`, `XCAL/`, `WORK/`): bizdays does not set their range. It comes from the provider package. See [calendar data](https://wilsonfreitas.github.io/python-bizdays/calendar-data.html).

#### Known limitations

* A date or result outside the calendar range always raises `DateOutOfRange`. There are no partial results yet; `errors="coerce"` is planned for 2.1.
* A `DataFrame` is rejected; pass one column instead.
* Results are NumPy values only, and a pandas `Series` input does not keep its index.
* Counts are `float64`, with `NaN` for missing values.
* In JSON calendar files, `adjust.from` and `adjust.to` accept only the defaults (`following` and `preceding`). Other values are planned.
* ANBIMA holidays after 2079 are projected with the national holiday rule.
* B3 holidays after 2026 are projected, and may change when B3 publishes its official calendar.

#### Contributors

* Wilson Freitas (@wilsonfreitas)
* @RichardDale, for reporting [#31](https://github.com/wilsonfreitas/python-bizdays/issues/31)

### version 1.0.20 (unreleased, 1.x branch)

* B3 calendar: projected holidays for 2027 to 2099 (ANBIMA holidays + December 24 + the last weekday of the year). Official B3 data ends in 2026.

### version 1.0.19 (2026-01-04)

* Restructured package: converted from single module to package directory
* Calendar files (.cal) are now properly installed with the package

### version 1.0.18 (2026-01-03)

* Updated B3.cal with 2026's holidays

### version 1.0.16 (2025-01-05)

* Updated B3.cal with 2025's holidays (thanks @victorhugow)

### version 1.0.15 (2024-06-23)

* Organized dependencies (Issue #51)

### version 1.0.14 (2024-06-17)

* Support to Python 3.12 (Issue #50)

### version 1.0.13 (2024-xx-xx)

* [BUG] bizdays doesn't handle correctly non-business days in edges (Issue #47)

### version 1.0.12 (2024-01-25)

* Tests updated
* New workflow created for pytest (Github Actions)

### version 1.0.11 (2023-12-29)

* ANBIMA calendar updated with new holiday nov-20th

### version 1.0.10 (2023-12-12)

* B3 calendar updated with 2024 dates
* B3 calendar removed date 2023-02-22 (Issue #39)

### version 1.0.9 (2023-10-29)

* Actual Calendar created
* Integration with [pandas_market_calendar](https://github.com/rsheftel/pandas_market_calendars), all calendars from this package can be used.

### version 1.0.8 (2023-01-20)

* B3 Calendar updated: corrected dates

### version 1.0.7 (2023-01-18)

* B3 Calendar updated: included 2023 holidays

### version 1.0.6 (2022-11-20)

* B3 Calendar updated: 2020-01-25 wasn't a holiday.

### version 1.0.5 (2022-11-18)

* B3 Calendar updated: 2020-07-09 wasn't a holiday due to decisions made by the municipal government of São Paulo.

### version 0.1.2 (2013-09-15)

* Calendar's `offset` method implemented
* Calendar's read-only attribute `name` implemented
* Calendar's constructor receives startdate and enddate as optional parameters

### version 0.1.1 (2013-09-04)

* dates passed to `bizdays`, `seq` and `currentdays` weren't being checked
* updated docstrings

### version 0.1.0 (2013-09-01)

* First commit
