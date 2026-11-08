API reference
=============

.. module:: bizdays

This page documents bizdays 2.0. Every example on this page runs as a test,
so the outputs shown are the real outputs. The examples share one session that
starts here:

.. code-block:: pycon

   >>> import numpy as np
   >>> import pandas as pd
   >>> import bizdays
   >>> from bizdays import Calendar, DateOutOfRange, list_calendars
   >>> cal = Calendar.load(name="ANBIMA")

Numbers, partial strings such as ``"2024-01"``, and ``numpy.datetime64`` values
with unit ``Y``, ``M`` or ``W`` are not dates and raise ``ValueError``.
Time-zone-aware values use their wall-clock date.

See also:

- :doc:`migration`, for code written for bizdays 1.x.
- The release notes:
  `CHANGELOG.md <https://github.com/wilsonfreitas/python-bizdays/blob/main/CHANGELOG.md>`_.

Public API
----------

The public API is exactly the names in ``bizdays.__all__``, with their
documented methods, properties and exceptions:

.. code-block:: pycon

   >>> bizdays.__all__
   ['Calendar', 'list_calendars', 'DateOutOfRange']

- :class:`Calendar`
- :func:`list_calendars`
- :class:`DateOutOfRange`, raised when a date lies outside the calendar range.
  It is a subclass of ``ValueError``, so ``except ValueError`` catches it.

Every submodule (``bizdays.calendar``, ``bizdays.dateindex``, ``bizdays.utils``,
``bizdays.date``, ``bizdays.getdate_parser``, ``bizdays.calendarfile``,
``bizdays.external``) is internal and may change without notice.

.. autoexception:: DateOutOfRange

Output types
------------

Methods return NumPy values, never pandas objects or Python dates. When every
argument is a single value, the result is a NumPy scalar. When any argument is
a vector, the result is a 1-D NumPy array.

.. list-table::
   :header-rows: 1

   * - Result
     - Methods
     - Type
     - Missing value
   * - Dates
     - ``offset``, ``following``, ``preceding``, ``modified_*``,
       ``adjust_*``, ``seq``, ``getdate``
     - ``numpy.datetime64`` with unit ``D``, or an array of ``datetime64[D]``
     - ``NaT`` ("not a time")
   * - Counts
     - ``bizdays``, ``diff``, ``getbizdays``
     - ``numpy.float64``, or an array of ``float64``
     - ``NaN`` ("not a number")
   * - Flags
     - ``isbizday``, ``inrange``
     - ``numpy.bool_``; a vector is always a ``numpy.ma.MaskedArray`` with
       ``fill_value=False``
     - ``numpy.ma.masked`` for a scalar, a masked element in a vector
   * - Properties
     - ``startdate``, ``enddate``, ``holidays``, ``weekdays``, ``name``,
       ``financial``
     - Python types: ``datetime.date``, ``list``, ``tuple``, ``str``, ``bool``
     - none

A masked array is a NumPy array with a second array, the mask, that marks the
missing elements.

Counts are ``float64`` even when nothing is missing, because NumPy has no
integer type with a missing value. Use ``.item()`` for a Python number:

.. code-block:: pycon

   >>> cal.bizdays("2024-01-02", "2024-01-05")
   np.float64(3.0)
   >>> cal.bizdays("2024-01-02", "2024-01-05").item()
   3.0
   >>> x = cal.bizdays(["2024-01-02", None], "2024-01-05")
   >>> x
   array([ 3., nan])

``NaN`` compares ``False`` with any number, so a missing count is never
``> 0``. Drop the ``NaN`` values before you turn counts into integers:

.. code-block:: pycon

   >>> x > 0
   array([ True, False])
   >>> x[~np.isnan(x)].astype(int)
   array([3])

Properties keep Python types:

.. code-block:: pycon

   >>> cal.startdate
   datetime.date(2000, 1, 1)

Results are positional: a pandas Series in gives a NumPy array out, and the
Series index is not kept. Assign a result straight to a column. Never wrap it
in ``pd.Series(result)`` without ``index=``:

.. code-block:: pycon

   >>> df = pd.DataFrame({"start": ["2024-01-02", "2024-01-03"]}, index=[10, 20])
   >>> df["du"] = cal.bizdays(df.start, "2024-01-05")
   >>> df
            start   du
   10  2024-01-02  3.0
   20  2024-01-03  2.0
   >>> pd.Series(cal.bizdays(df.start, "2024-01-05"), index=df.index)
   10    3.0
   20    2.0
   dtype: float64

Missing values
--------------

A missing value is anything ``pandas.isna`` reports as missing (``None``,
``NaN``, ``NaT``, ``pd.NA``), plus a masked element. Missing in gives missing
out, element by element:

.. code-block:: pycon

   >>> cal.isbizday(["2024-01-01", None, "2024-01-02"])
   masked_array(data=[False, --, True],
                mask=[False,  True, False],
          fill_value=False)
   >>> cal.isbizday(None)
   masked
   >>> cal.bizdays(None, "2024-01-05")
   np.float64(nan)
   >>> cal.offset(["2024-01-02", None], 1)
   array(['2024-01-03', 'NaT'], dtype='datetime64[D]')
   >>> cal.diff(["2024-01-02", "2024-01-05", None, "2024-01-10"])
   array([ 3., nan, nan])

``seq`` is the exception: a missing end raises ``ValueError``. An empty
string is not missing; it is an invalid date and raises ``ValueError``.
Missing values are never out of range.

Vector arguments
----------------

These rules apply to the methods with two arguments that can be vectors:
``bizdays``, ``offset``, ``getdate`` and ``getbizdays``. A single value (a
scalar, or a vector of length 1) is used for every element. Equal lengths pair
element by element:

.. code-block:: pycon

   >>> cal.offset("2024-01-05", [1, 2])
   array(['2024-01-08', '2024-01-09'], dtype='datetime64[D]')

Any other pair of lengths raises ``ValueError``:

.. code-block:: pycon

   >>> cal.bizdays(["2024-01-02", "2024-01-03"], ["2024-01-04", "2024-01-05", "2024-01-08"])
   Traceback (most recent call last):
   ...
   ValueError: date_from has length 2 and date_to has length 3; ...

To repeat the shorter input on purpose, use ``np.tile`` or ``np.repeat``.

Errors
------

.. list-table::
   :header-rows: 1

   * - Situation
     - Error
   * - A date (input or result) outside the calendar range; a ``getbizdays``
       period not fully inside it
     - :class:`DateOutOfRange`, a subclass of ``ValueError``, with
       ``positions``
   * - Invalid date string, number given as a date, ``numpy.datetime64`` with
       unit ``Y``/``M``/``W`` given as a date, 2-D input, invalid count, year
       or month, invalid ``getdate`` expression or ref, a ``getdate`` date that
       does not exist in its period, ``seq`` with a vector or a missing end,
       bad constructor arguments, unknown packaged or provider calendar, a
       ``.cal`` file, a value other than the default for ``adjust.from`` or
       ``adjust.to`` in a JSON file
     - ``ValueError``
   * - Vector lengths that differ, when neither is 1
     - ``ValueError``
   * - Calendar file not found
     - ``FileNotFoundError``
   * - Optional provider not installed
     - ``ImportError``, which names the extra to install

So ``except ValueError`` catches every bad-input problem, including dates out
of range. Values of the wrong type also raise ``ValueError``, not
``TypeError``. Python's own errors for a wrong call, such as a missing
argument, are not covered by this table.

Calendar discovery
------------------

.. autofunction:: list_calendars

Example:

.. code-block:: pycon

   >>> info = list_calendars()
   >>> info["packaged"]
   ['ANBIMA', 'B3', 'Actual']
   >>> sorted(info["pandas_market_calendars"])
   ['available', 'calendars', 'prefix']
   >>> info["workalendar"]["prefix"]
   'WORK/'

For each provider (``pandas_market_calendars``, ``exchange_calendars``,
``workalendar``), ``available`` says whether it is installed and
``calendars`` lists the names you can load with its prefix.

Calendar construction
---------------------

.. autoclass:: Calendar
   :members:
   :exclude-members: bizdays, isbizday, inrange, adjust_next, following, modified_following, adjust_previous, preceding, modified_preceding, seq, offset, diff, getdate, getbizdays, load

Create a calendar in memory when you already have the holidays and nonworking
weekdays available in Python:

.. code-block:: pycon

   >>> custom = Calendar(
   ...     holidays=["2024-01-01", "2024-12-25"],
   ...     weekdays=["Saturday", "Sunday"],
   ...     startdate="2024-01-01",
   ...     enddate="2024-12-31",
   ...     name="Example",
   ...     financial=True,
   ... )
   >>> custom.weekdays
   ('Saturday', 'Sunday')
   >>> custom.enddate
   datetime.date(2024, 12, 31)

Constructor notes:

- ``holidays`` accepts ISO strings, ``datetime.date``, ``datetime.datetime``,
  ``numpy.datetime64``, and pandas timestamps
- ``weekdays`` lists the nonworking weekdays
- when ``startdate`` and ``enddate`` are omitted, they are inferred from the
  holiday range
- calendars without holidays default to a broad built-in date range
- holidays outside an explicit ``startdate..enddate`` are ignored
- ``ValueError`` for ``startdate`` after ``enddate``, a calendar without
  business days, or an invalid weekday name
- holidays with ``weekdays=None`` emit a ``UserWarning``; pass ``weekdays=[]``
  for a calendar without nonworking weekdays

Calendar range
--------------

A calendar covers ``startdate..enddate``, both ends included. Any input date
outside that range, or any result that would fall outside it, raises
:class:`DateOutOfRange`. One bad element fails the whole call: there are no
partial results, and dates are never clamped or wrapped. ``offset`` past either
end, ``following`` past the end and ``preceding`` before the start all raise.
Missing values are never out of range.

The error message names the first bad element by its inputs and says how many
elements are bad. ``DateOutOfRange.positions`` is a sorted ``int64`` array with
the index of every bad element in the result (after the length rules); a call
with only scalars gives ``[0]``.

.. automethod:: Calendar.inrange

.. code-block:: pycon

   >>> cal.inrange("2100-01-01")
   np.False_
   >>> cal.inrange(["1999-12-31", "2024-01-02", None])
   masked_array(data=[False, True, --],
                mask=[False, False,  True],
          fill_value=False)

Range recipes
^^^^^^^^^^^^^

Check input dates before a call with :meth:`Calendar.inrange`, and compute only
the rows that are inside the range. ``filled(False)`` turns missing flags into
``False``:

.. code-block:: pycon

   >>> df = pd.DataFrame({"start": ["2024-01-02", "2024-01-03"], "maturity": ["2024-06-15", "2100-01-03"]})
   >>> ok = cal.inrange(df.maturity).filled(False)
   >>> df.loc[ok, "du"] = cal.bizdays(df.start[ok], df.maturity[ok])
   >>> df
           start    maturity     du
   0  2024-01-02  2024-06-15  113.0
   1  2024-01-03  2100-01-03    NaN

Results cannot be checked in advance, so catch the error and use
``positions``:

.. code-block:: pycon

   >>> try:
   ...     cal.offset(["2024-01-02", "2099-12-20", "2099-12-22"], [1, 5, 10])
   ... except DateOutOfRange as e:
   ...     print(e.positions)
   [1 2]

Loading calendars
-----------------

.. automethod:: Calendar.load

Use :meth:`Calendar.load` for packaged calendars and JSON files:

.. code-block:: pycon

   >>> b3 = Calendar.load(name="B3")
   >>> b3.enddate
   datetime.date(2099, 12, 31)
   >>> Calendar.load(name="Actual").startdate
   datetime.date(1900, 1, 1)

A JSON calendar file is loaded with ``filename=``:

.. code-block:: python

   custom = Calendar.load(filename="custom-calendar.json")

Packaged calendars shipped with the project:

- ``ANBIMA``: 2000-01-01 to 2099-12-25. Official ANBIMA holidays up to 2079;
  later years are projected with the national holiday rule.
- ``B3``: official B3 holidays for 2000-2026. Years 2027-2099 are projected:
  ANBIMA holidays, plus December 24, plus the last weekday of the year.
  Projected years are replaced when B3 publishes them.
- ``Actual``: no holidays, every day is a business day; 1900-01-01 to 2199-12-31.

Ranges, official and projected years, and how the data is updated:
:doc:`calendar-data`.

Calendars from optional providers use a name prefix. Each provider is an
optional extra; without it, ``Calendar.load`` raises ``ImportError``:

.. code-block:: python

   Calendar.load(name="PMC/NYSE")   # pandas_market_calendars: pip install "bizdays[pmc]"
   Calendar.load(name="XCAL/XNYS")  # exchange_calendars: pip install "bizdays[xcal]"
   Calendar.load(name="WORK/FR")    # workalendar: pip install "bizdays[work]"

The ``WORK/`` names use workalendar registry codes.

Core business-day calculations
------------------------------

bizdays
^^^^^^^

.. automethod:: Calendar.bizdays

Examples:

.. code-block:: pycon

   >>> cal.bizdays("2013-01-02", "2013-01-31")
   np.float64(21.0)
   >>> cal.bizdays(["2013-01-02", "2013-01-02"], ["2013-01-31", "2013-02-28"])
   array([21., 39.])
   >>> cal.bizdays(None, "2024-01-05")
   np.float64(nan)

Adjust maturities first
"""""""""""""""""""""""

An end date that is not a business day moves to the preceding business day,
and a start date that is not a business day moves to the following one. So
2024-06-15, a Saturday, counts like Friday 2024-06-14. A payment due on
2024-06-15 is made on Monday 2024-06-17, so adjust maturities with
``following`` first:

.. code-block:: pycon

   >>> cal.bizdays("2024-01-02", "2024-06-15")
   np.float64(113.0)
   >>> cal.following("2024-06-15")
   np.datetime64('2024-06-17')
   >>> cal.bizdays("2024-01-02", cal.following("2024-06-15"))
   np.float64(114.0)

isbizday
^^^^^^^^

.. automethod:: Calendar.isbizday

Examples:

.. code-block:: pycon

   >>> cal.isbizday("2013-01-02")
   np.True_
   >>> cal.isbizday(["2013-01-01", "2013-01-02"])
   masked_array(data=[False, True],
                mask=[False, False],
          fill_value=False)
   >>> cal.isbizday([None, "2024-01-02"])
   masked_array(data=[--, True],
                mask=[ True, False],
          fill_value=False)

offset
^^^^^^

.. automethod:: Calendar.offset

Examples:

.. code-block:: pycon

   >>> cal.offset("2013-01-02", 5)
   np.datetime64('2013-01-09')
   >>> cal.offset(["2013-01-02", "2013-01-03"], [1, -1])
   array(['2013-01-03', '2013-01-02'], dtype='datetime64[D]')
   >>> cal.offset("2024-01-05", [1, 2])
   array(['2024-01-08', '2024-01-09'], dtype='datetime64[D]')

From a day that is not a business day, ``n=1`` is the next business day and
``n=-1`` the previous one (2013-01-01 is a holiday):

.. code-block:: pycon

   >>> cal.offset("2013-01-01", [1, 2, -1, -2])
   array(['2013-01-02', '2013-01-03', '2012-12-31', '2012-12-28'],
         dtype='datetime64[D]')

seq
^^^

.. automethod:: Calendar.seq

Examples:

.. code-block:: pycon

   >>> cal.seq("2014-01-02", "2014-01-07")
   array(['2014-01-02', '2014-01-03', '2014-01-06', '2014-01-07'],
         dtype='datetime64[D]')
   >>> cal.seq("2014-01-07", "2014-01-02")  # reverse order is kept
   array(['2014-01-07', '2014-01-06', '2014-01-03', '2014-01-02'],
         dtype='datetime64[D]')

diff
^^^^

.. automethod:: Calendar.diff

Examples:

.. code-block:: pycon

   >>> cal.diff(["2013-01-02", "2013-01-03", "2013-01-04"])
   array([1., 1.])
   >>> cal.diff(["2013-01-02"])
   array([], dtype=float64)

Date adjustment methods
-----------------------

adjust_next
^^^^^^^^^^^

.. automethod:: Calendar.adjust_next

Example:

.. code-block:: pycon

   >>> cal.adjust_next("2013-01-01")
   np.datetime64('2013-01-02')

following
^^^^^^^^^

.. automethod:: Calendar.following

Example:

.. code-block:: pycon

   >>> cal.following("2015-12-25")
   np.datetime64('2015-12-28')

modified_following
^^^^^^^^^^^^^^^^^^

.. automethod:: Calendar.modified_following

Example:

.. code-block:: pycon

   >>> cal.modified_following("2022-04-30")
   np.datetime64('2022-04-29')

adjust_previous
^^^^^^^^^^^^^^^

.. automethod:: Calendar.adjust_previous

Example:

.. code-block:: pycon

   >>> cal.adjust_previous("2013-01-01")
   np.datetime64('2012-12-31')

preceding
^^^^^^^^^

.. automethod:: Calendar.preceding

Example:

.. code-block:: pycon

   >>> cal.preceding("2014-01-01")
   np.datetime64('2013-12-31')

modified_preceding
^^^^^^^^^^^^^^^^^^

.. automethod:: Calendar.modified_preceding

Example:

.. code-block:: pycon

   >>> cal.modified_preceding("2015-03-01")
   np.datetime64('2015-03-02')

Date expression lookup
----------------------

getdate
^^^^^^^

.. automethod:: Calendar.getdate

``Calendar.getdate(expr, ref)`` resolves expressions against three kinds of
references:

- month references such as ``"2002-05"``
- year references such as ``2006`` or ``"2006"``
- date references such as ``"2021-02-10"``

All refs in one call must be of one kind (year, month or date); missing refs do
not count. Mixing kinds, as in ``["2002-01", "2021-02-10"]``, raises
``ValueError``.

Expressions
"""""""""""

Format:

.. code-block:: text

   <position> <day>
   <position> <day> <before|after> <position> <day>
   previous <weekday>

Positions:

- ``next``, ``first``/``1st``, ``second``/``2nd``, ``third``/``3rd``, ``last``
- ``<n>`` with the right English suffix: ``4th``, ``11th``, ``21st``, ``22nd``,
  ``23rd``. A wrong suffix, such as ``2st``, raises ``ValueError``; so does
  ``0th``.

Days:

- ``day``, ``bizday``
- weekdays, as 3-letter or full English names: ``mon``/``monday`` ...
  ``sun``/``sunday``

Words are case-insensitive. Any other word raises ``ValueError``.

Year or month refs
""""""""""""""""""

- ``<n> <day>`` is the n-th day, business day or weekday inside the period;
  ``last`` is the last one, and ``next`` means the first.
- Composite expressions (``first day before 15th day``, ``1st bizday before 2nd
  fri``) work with period refs only. In their first slot, ``last`` and ``next``
  mean ``1st``. The result may leave the ref period, but not the calendar range.
- A date that does not exist in its period, such as ``5th fri`` in a month with
  four Fridays, raises ``ValueError``.

Date refs
"""""""""

- ``<n> day`` is the date plus n days; ``last day`` is the day before.
- ``<n> bizday`` is ``offset(date, n)``; ``last bizday`` is ``offset(date, -1)``.
- ``<n> <weekday>`` is the n-th such weekday strictly after the date;
  ``last <weekday>`` and ``previous <weekday>`` are the one strictly before.
- ``previous`` works with weekdays and date refs only.

Examples:

.. code-block:: pycon

   >>> cal.getdate("15th day", "2002-05")
   np.datetime64('2002-05-15')
   >>> cal.getdate(["last day", "last bizday"], "2006")
   array(['2006-12-31', '2006-12-29'], dtype='datetime64[D]')
   >>> cal.getdate("next wed", "2002-01")  # the first Wednesday
   np.datetime64('2002-01-02')
   >>> cal.getdate("next wed", "2021-02-10")
   np.datetime64('2021-02-17')
   >>> cal.getdate("next bizday", "2022-06-18")
   np.datetime64('2022-06-20')
   >>> cal.getdate("last mon", "2022-06-20")
   np.datetime64('2022-06-13')
   >>> cal.getdate("first bizday", ["2002-01", "2002-02"])
   array(['2002-01-02', '2002-02-01'], dtype='datetime64[D]')

Business days in a period
-------------------------

getbizdays
^^^^^^^^^^

.. automethod:: Calendar.getbizdays

Examples:

.. code-block:: pycon

   >>> cal.getbizdays(2024)  # the whole year
   np.float64(253.0)
   >>> cal.getbizdays(2024, 2)
   np.float64(19.0)
   >>> cal.getbizdays([2024, 2024], [1, 2])
   array([22., 19.])
   >>> cal.getbizdays(2024, [1, None])
   array([22., nan])

The whole period must lie inside the calendar range. ANBIMA ends on
2099-12-25, so November 2099 works and the year 2099 does not:

.. code-block:: pycon

   >>> cal.getbizdays(2099, 11)
   np.float64(19.0)
   >>> try:
   ...     cal.getbizdays(2099)
   ... except DateOutOfRange as e:
   ...     print(e.positions)
   [0]
