# python-bizdays

`bizdays` provides business-day calculations around the current NumPy-backed
`Calendar` API.

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

## Using `Calendar`

```python
from bizdays import Calendar

cal = Calendar.load(name="ANBIMA")

cal.isbizday("2014-01-13")
cal.bizdays("2014-01-13", "2015-01-13")
cal.following("2015-12-25")
cal.seq("2014-01-02", "2014-01-07")
cal.offset("2014-01-02", 5)
cal.getdate("15th day", "2002-05")
```

## Calendars that come with the package

- `ANBIMA`
- `B3`
- `Actual`

You can discover them programmatically with `list_calendars()`:

```python
from bizdays import list_calendars

list_calendars()
```

Use `Calendar.load(name="...")` for packaged calendars and
`Calendar.load(filename="...")` for your own JSON calendar files.

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

## Current API notes

- packaged calendars: `ANBIMA`, `B3`, and `Actual`
- `PMC/...` names require the optional `bizdays[pmc]` extra
- `XCAL/...` names require the optional `bizdays[xcal]` extra
- `WORK/...` names require the optional `bizdays[work]` extra
- top-level `Calendar` returns NumPy-native values such as `numpy.datetime64`,
  `numpy.int_`, `numpy.ndarray`, and masked arrays
- pandas timestamps, indexes, and series can be passed directly to the public API
- `Calendar.getdate` is supported on the top-level API

## Migration

See the [migration guide](docs/source/migration.rst) for updates from older
examples that used positional `Calendar.load(...)`, `.cal` packaged files, or
older return-type expectations.
