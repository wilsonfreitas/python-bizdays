[![Downloads](https://img.shields.io/pypi/dm/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)
[![Latest Version](https://img.shields.io/pypi/v/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)

# [python-bizdays](http://wilsonfreitas.github.io/python-bizdays/)

`bizdays` provides business-day calculations around the current NumPy-backed
`Calendar` API. The top-level `bizdays.Calendar` accepts scalar dates, Python
sequences, NumPy arrays, and pandas date-like inputs while returning NumPy
scalars or arrays.

## Install

```bash
pip install bizdays
```

Install the optional integrations with:

```bash
pip install "bizdays[pmc]"
pip install "bizdays[xcal]"
pip install "bizdays[work]"
```

## Quickstart

```python
from bizdays import Calendar

cal = Calendar.load(name="ANBIMA")

cal.bizdays("2014-01-13", "2015-01-13")
cal.following("2015-12-25")
cal.seq("2014-01-02", "2014-01-07")
cal.getdate("15th day", "2002-05")
```

## Calendars that come with the package

- `ANBIMA`: 2000-2099, ANBIMA's own holiday list.
- `B3`: official B3 holidays for 2000-2026. Years 2027-2099 are projected:
  ANBIMA holidays, plus December 24, plus the last weekday of the year.
  Projected years are replaced when B3 publishes them.
- `Actual`: no holidays, every day is a business day; 1900-01-01 to 2199-12-31.

You can discover them programmatically with `list_calendars()`:

```python
from bizdays import list_calendars

list_calendars()
```

Use `Calendar.load(name="...")` for packaged calendars and
`Calendar.load(filename="...")` for custom JSON calendar files.

External providers are also available through prefixed names:

- `Calendar.load(name="PMC/<calendar>")` for `pandas_market_calendars`
- `Calendar.load(name="XCAL/<calendar>")` for `exchange_calendars`
- `Calendar.load(name="WORK/<code>")` for `workalendar`

## Create a calendar from scratch

```python
from bizdays import Calendar

custom = Calendar(
    holidays=["2024-01-01", "2024-12-25"],
    weekdays=["Saturday", "Sunday"],
    startdate="2024-01-01",
    enddate="2024-12-31",
    name="Example",
)
```

## JSON calendar layout

`Calendar.load(filename="...")` expects a JSON object with these fields:

- `name`: string
- `weekdays`: list of weekday names
- `holidays`: list of ISO date strings
- `financial`: boolean
- `adjust.from` and `adjust.to`: optional strings accepted for schema compatibility

Example:

```json
{
  "name": "Custom",
  "weekdays": ["saturday", "sunday"],
  "holidays": ["2024-01-01", "2024-12-25"],
  "financial": true
}
```

## API notes

- packaged calendars: `ANBIMA`, `B3`, and `Actual`
- `PMC/...` names require the optional `bizdays[pmc]` extra
- `XCAL/...` names require the optional `bizdays[xcal]` extra
- `WORK/...` names require the optional `bizdays[work]` extra
- top-level `Calendar` methods return NumPy-native values such as
  `numpy.datetime64`, `numpy.float64` counts (`NaN` for missing), `numpy.ndarray`,
  and masked arrays for `isbizday` vectors (`fill_value=False`)
- pandas timestamps, indexes, and series can be passed directly to the public API

## Migration

See the [migration guide](docs/source/migration.rst) for updates from older
examples that used positional `Calendar.load(...)`, `.cal` packaged files, or
older return-type expectations.
