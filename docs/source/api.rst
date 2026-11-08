API reference
=============

.. module:: bizdays

The top-level :class:`Calendar` is the NumPy-backed public API. Scalar calls
return NumPy scalars and vectorized calls return NumPy arrays. Date results are
``datetime64[D]`` with ``NaT`` for missing values. Counts are ``float64``
(``numpy.float64`` for scalars) with ``NaN`` for missing values. ``isbizday``
vectors are masked arrays with ``fill_value=False``, and a missing scalar flag
is ``numpy.ma.masked``.

Numbers, partial strings such as ``"2024-01"``, and ``numpy.datetime64`` values
with unit ``Y``, ``M`` or ``W`` are not dates and raise ``ValueError``.
Time-zone-aware values use their wall-clock date.

Public API
----------

The public API is exactly the names in ``bizdays.__all__``, with their
documented methods, properties and exceptions:

- :class:`Calendar`
- :func:`list_calendars`
- :class:`DateOutOfRange`, raised when a date lies outside the calendar range.
  It is a subclass of ``ValueError``, so ``except ValueError`` catches it.

Every submodule (``bizdays.calendar``, ``bizdays.dateindex``, ``bizdays.utils``,
``bizdays.date``, ``bizdays.getdate_parser``, ``bizdays.calendarfile``,
``bizdays.external``) is internal and may change without notice.

.. autoexception:: DateOutOfRange

Calendar discovery
------------------

.. autofunction:: list_calendars

Example:

.. code-block:: python

   from bizdays import list_calendars

   info = list_calendars()
   info["packaged"]
   info["pandas_market_calendars"]["available"]
   info["pandas_market_calendars"]["calendars"]
   info["exchange_calendars"]["available"]
   info["exchange_calendars"]["calendars"]
   info["workalendar"]["available"]
   info["workalendar"]["calendars"]

Calendar construction
---------------------

.. autoclass:: Calendar
   :members:
   :exclude-members: bizdays, isbizday, inrange, adjust_next, following, modified_following, adjust_previous, preceding, modified_preceding, seq, offset, diff, getdate, getbizdays, load

Create a calendar in memory when you already have the holidays and nonworking
weekdays available in Python:

.. code-block:: python

   from bizdays import Calendar

   cal = Calendar(
       holidays=["2024-01-01", "2024-12-25"],
       weekdays=["Saturday", "Sunday"],
       startdate="2024-01-01",
       enddate="2024-12-31",
       name="Example",
       financial=True,
   )

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

Check input dates before a call with :meth:`Calendar.inrange`. Results cannot be
checked in advance, so catch the error and use ``positions``:

.. code-block:: python

   from bizdays import DateOutOfRange

   ok = cal.inrange(df.maturity).filled(False)   # check inputs first
   try:
       d = cal.offset(df.date, df.n)
   except DateOutOfRange as e:                     # results cannot be checked in advance
       bad_rows = df.index[e.positions]

Loading calendars
-----------------

.. automethod:: Calendar.load

Use :meth:`Calendar.load` for packaged calendars and JSON files:

.. code-block:: python

   from bizdays import Calendar

   anbima = Calendar.load(name="ANBIMA")
   b3 = Calendar.load(name="B3")
   actual = Calendar.load(name="Actual")
   custom = Calendar.load(filename="custom-calendar.json")

Packaged calendars shipped with the project:

- ``ANBIMA``: 2000-2099, ANBIMA's own holiday list.
- ``B3``: official B3 holidays for 2000-2026. Years 2027-2099 are projected:
  ANBIMA holidays, plus December 24, plus the last weekday of the year.
  Projected years are replaced when B3 publishes them.
- ``Actual``: no holidays, every day is a business day; 1970-01-01 to 2071-01-01.

Optional integration with ``pandas_market_calendars`` remains available through
the ``PMC/`` prefix, for example ``Calendar.load(name="PMC/NYSE")`` when the
optional dependency is installed.

Optional integration with ``exchange_calendars`` is available through the
``XCAL/`` prefix, for example ``Calendar.load(name="XCAL/XNYS")`` when the
optional dependency is installed.

Optional integration with ``workalendar`` is available through the ``WORK/``
prefix, for example ``Calendar.load(name="WORK/FR")`` when the optional
dependency is installed. The ``WORK/`` names use workalendar registry codes.

Core business-day calculations
------------------------------

bizdays
^^^^^^^

.. automethod:: Calendar.bizdays

Examples:

.. code-block:: python

   cal.bizdays("2013-01-02", "2013-01-31")
   cal.bizdays(["2013-01-02", "2013-01-02"], ["2013-01-31", "2013-02-28"])
   cal.bizdays(None, "2024-01-05")  # nan

isbizday
^^^^^^^^

.. automethod:: Calendar.isbizday

Examples:

.. code-block:: python

   cal.isbizday("2013-01-02")
   cal.isbizday(["2013-01-01", "2013-01-02"])
   cal.isbizday([None, "2024-01-02"])  # masked array result

offset
^^^^^^

.. automethod:: Calendar.offset

Examples:

.. code-block:: python

   cal.offset("2013-01-02", 5)
   cal.offset(["2013-01-02", "2013-01-03"], [1, -1])
   cal.offset("2024-01-05", [1, 2])

seq
^^^

.. automethod:: Calendar.seq

Examples:

.. code-block:: python

   cal.seq("2014-01-02", "2014-01-07")
   cal.seq("2014-01-07", "2014-01-02")  # reverse order is preserved

diff
^^^^

.. automethod:: Calendar.diff

Examples:

.. code-block:: python

   cal.diff(["2013-01-02", "2013-01-03", "2013-01-04"])
   cal.diff(["2013-01-02"])  # returns an empty array

Date adjustment methods
-----------------------

adjust_next
^^^^^^^^^^^

.. automethod:: Calendar.adjust_next

Example:

.. code-block:: python

   cal.adjust_next("2013-01-01")

following
^^^^^^^^^

.. automethod:: Calendar.following

Example:

.. code-block:: python

   cal.following("2015-12-25")

modified_following
^^^^^^^^^^^^^^^^^^

.. automethod:: Calendar.modified_following

Example:

.. code-block:: python

   cal.modified_following("2022-04-30")

adjust_previous
^^^^^^^^^^^^^^^

.. automethod:: Calendar.adjust_previous

Example:

.. code-block:: python

   cal.adjust_previous("2013-01-01")

preceding
^^^^^^^^^

.. automethod:: Calendar.preceding

Example:

.. code-block:: python

   cal.preceding("2014-01-01")

modified_preceding
^^^^^^^^^^^^^^^^^^

.. automethod:: Calendar.modified_preceding

Example:

.. code-block:: python

   cal.modified_preceding("2015-03-01")

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

.. code-block:: python

   cal.getdate("15th day", "2002-05")
   cal.getdate(["last day", "last bizday"], "2006")
   cal.getdate("next wed", "2002-01")         # 2002-01-02, the first Wednesday
   cal.getdate("next wed", "2021-02-10")      # 2021-02-17
   cal.getdate("next bizday", "2022-06-18")   # 2022-06-20
   cal.getdate("last mon", "2022-06-20")      # 2022-06-13
   cal.getdate("first bizday", ["2002-01", "2002-02"])

Business days in a period
-------------------------

getbizdays
^^^^^^^^^^

.. automethod:: Calendar.getbizdays

Example:

.. code-block:: python

   cal = Calendar.load(name="ANBIMA")
   cal.getbizdays(2024)                     # 253.0, the whole year
   cal.getbizdays(2024, 2)                  # 19.0
   cal.getbizdays([2024, 2024], [1, 2])     # array([22., 19.])
