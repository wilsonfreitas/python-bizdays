[![Downloads](https://img.shields.io/pypi/dm/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)
[![Latest Version](https://img.shields.io/pypi/v/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)

# [python-bizdays](https://wilsonfreitas.github.io/python-bizdays/)

`bizdays` computes business days with holiday calendars. This README covers
bizdays 2.0, which runs on Python 3.10 to 3.14 with NumPy 1.24 or newer and
pandas 2 or 3. `bizdays.Calendar` accepts single dates, Python sequences,
NumPy arrays and pandas date-like inputs, and returns NumPy scalars or arrays.

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
>>> from bizdays import Calendar
>>> cal = Calendar.load(name="ANBIMA")
>>> cal.bizdays("2014-01-13", "2015-01-13")
np.float64(253.0)
>>> cal.following("2015-12-25")
np.datetime64('2015-12-28')
>>> cal.offset(["2014-01-02", "2014-01-03"], [1, 5])
array(['2014-01-03', '2014-01-10'], dtype='datetime64[D]')
>>> cal.seq("2014-01-02", "2014-01-07")
array(['2014-01-02', '2014-01-03', '2014-01-06', '2014-01-07'],
      dtype='datetime64[D]')
>>> cal.getdate("15th day", "2002-05")
np.datetime64('2002-05-15')
>>> cal.getbizdays(2024)
np.float64(253.0)

```

## Calendars that come with the package

- `ANBIMA`: 2000-01-01 to 2099-12-25. Official ANBIMA holidays up to 2079;
  later years are projected with the national holiday rule.
- `B3`: official B3 holidays for 2000-2026. Years 2027-2099 are projected:
  ANBIMA holidays, plus December 24, plus the last weekday of the year.
  Projected years are replaced when B3 publishes them.
- `Actual`: no holidays, every day is a business day; 1900-01-01 to 2199-12-31.

You can list them with `list_calendars()`:

```python
>>> from bizdays import list_calendars
>>> list_calendars()["packaged"]
['ANBIMA', 'B3', 'Actual']

```

Use `Calendar.load(name="...")` for packaged calendars and
`Calendar.load(filename="...")` for custom JSON calendar files.

External providers are also available through prefixed names:

- `Calendar.load(name="PMC/<calendar>")` for `pandas_market_calendars`
- `Calendar.load(name="XCAL/<calendar>")` for `exchange_calendars`
- `Calendar.load(name="WORK/<code>")` for `workalendar`

## Create a calendar from scratch

```python
>>> custom = Calendar(
...     holidays=["2024-01-01", "2024-12-25"],
...     weekdays=["Saturday", "Sunday"],
...     startdate="2024-01-01",
...     enddate="2024-12-31",
...     name="Example",
... )
>>> custom.bizdays("2024-12-20", "2024-12-31")
np.float64(6.0)

```

## JSON calendar layout

`Calendar.load(filename="...")` expects a JSON object with these fields:

- `name`: string
- `weekdays`: list of weekday names
- `holidays`: list of ISO date strings
- `financial`: boolean
- `start.date` and `end.date`: optional ISO date strings (`YYYY-MM-DD`) that
  set `startdate` and `enddate`; a bad value raises `ValueError`
- `adjust.from` and `adjust.to`: optional; only the defaults `"following"` and
  `"preceding"` are accepted, and other values raise `ValueError`

Example:

```json
{
  "name": "Custom",
  "weekdays": ["saturday", "sunday"],
  "holidays": ["2024-01-01", "2024-12-25"],
  "financial": true,
  "start.date": "2024-01-01",
  "end.date": "2024-12-31"
}
```

## API notes

- packaged calendars: `ANBIMA`, `B3`, and `Actual`
- `PMC/...` names require the optional `bizdays[pmc]` extra
- `XCAL/...` names require the optional `bizdays[xcal]` extra
- `WORK/...` names require the optional `bizdays[work]` extra
- `Calendar` methods return NumPy values such as `numpy.datetime64`,
  `numpy.float64` counts (`NaN` for missing), `numpy.ndarray`, and masked
  arrays for `isbizday` vectors (`fill_value=False`)
- results are positional NumPy values: assign them to a DataFrame column, and
  give `index=` if you wrap them in a pandas Series; see the API reference
- pandas timestamps, indexes, and series can be passed directly to the public API

## Documentation

- [Documentation site](https://wilsonfreitas.github.io/python-bizdays/)
- [API reference](https://wilsonfreitas.github.io/python-bizdays/api.html)
- [Migration guide from bizdays 1.x](https://wilsonfreitas.github.io/python-bizdays/migration.html)
- [Release notes](https://github.com/wilsonfreitas/python-bizdays/blob/master/CHANGELOG.md)
