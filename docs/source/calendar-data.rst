Calendar data
=============

This page lists every calendar source, the dates it covers and how its data
is updated.

Ranges
------

Every calendar has a range: a first and a last date. A date outside the range
raises :class:`bizdays.DateOutOfRange`.

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Calendar
     - Range
     - Where the range comes from
   * - ``Calendar(...)`` without holidays or dates
     - 1970-01-01 to 2071-01-01
     - The constructor default (the same as R bizdays).
   * - ``Calendar(holidays=...)``
     - first to last holiday
     - The constructor default, unless you give ``startdate`` or ``enddate``.
   * - ``ANBIMA``
     - 2000-01-01 to 2099-12-25
     - First to last holiday in ``ANBIMA.json``.
   * - ``B3``
     - 2000-01-01 to 2099-12-31
     - First to last holiday in ``B3.json``.
   * - ``Actual``
     - 1900-01-01 to 2199-12-31
     - The ``start.date`` and ``end.date`` fields of ``Actual.json``.
   * - ``PMC/<name>``
     - first to last provider holiday
     - ``pandas_market_calendars``; for example ``PMC/B3`` covers
       1885-01-01 to 2200-12-31.
   * - ``XCAL/<name>``
     - first to last provider session
     - ``exchange_calendars``. It moves with today's date: about 20 years back
       and 1 year ahead.
   * - ``WORK/<code>``
     - 1 January to 31 December of the computable years in 1991..2051
     - ``workalendar``; for example ``WORK/FR`` covers 1991-01-01 to
       2051-12-31 and ``WORK/CN`` covers 2018-01-01 to 2023-12-31.

Official and projected years:

- ``ANBIMA``: official holidays as published by ANBIMA up to 2079-01-01.
  Later years, up to 2099, are projected with the national holiday rule
  (days based on Easter, fixed days, and 20 November from 2024).
- ``B3``: official for 2000-2026. Years 2027-2099 are projected: ANBIMA
  holidays, plus December 24, plus the last weekday of the year. See the
  packaged calendar list in :doc:`api`.
- ``Actual``: no holidays and no weekend; every day is a business day.

JSON calendar files can set their own range with the optional ``start.date``
and ``end.date`` fields (the same names R bizdays uses). Both are
``YYYY-MM-DD`` strings. Holidays outside the range are ignored.

Providers
---------

Provider calendars need an optional extra:
``pip install "bizdays[pmc]"``, ``"bizdays[xcal]"`` or ``"bizdays[work]"``.

- ``PMC/``: the weekend comes from the provider weekmask. For example
  ``PMC/TASE`` has Friday and Saturday as its weekend, and ``PMC/24/7`` has no
  weekend.
- ``XCAL/``: a business day is a session of the exchange. Every day that is
  not a session, weekends included, is a holiday, so ``weekdays`` is empty.
  An early-close session is still a business day: bizdays counts days, not
  hours. An exchange closure listed by the provider is a holiday, for example
  NYSE on 2025-01-09.
- ``WORK/``: workalendar computes holidays year by year, and some calendars
  know only some years. The range is the latest block of consecutive years in
  1991..2051 that the calendar can compute. A calendar with no such year
  raises ``ValueError``.

Errors:

- An unknown name raises ``ValueError`` with the prefix and the name.
- A provider that is not installed raises ``ImportError`` with the
  ``pip install`` command.
- Any other provider error for a known name is passed on unchanged.
- :func:`bizdays.list_calendars` never raises for a missing provider; it
  reports it as not available.

Updating the data
-----------------

The maintainer (Wilson Freitas) owns the packaged data. Each December, and
when B3 or ANBIMA publish a new calendar:

1. Compare the published year with the JSON file in ``bizdays/data/``.
2. Fix the file. Holidays stay sorted and unique.
3. Run the data tests (``tests/test_calendar_data.py``).
4. Release a patch: 2.0.x, and 1.0.x on the ``1.x`` branch while it is
   maintained.

A test fails the release when a packaged calendar ends within 10 years.
