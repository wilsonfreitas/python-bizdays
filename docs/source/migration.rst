Migration guide
===============

The current top-level ``bizdays.Calendar`` is the NumPy-backed implementation.
This guide explains how to update older examples and habits to the current
documentation and API surface.

What changed in the docs
------------------------

Normal user-facing documentation now focuses only on the current public API:

- :class:`bizdays.Calendar`
- :meth:`bizdays.Calendar.load`
- packaged JSON calendars
- constructor-based calendars
- pandas inputs with NumPy-backed outputs

Older topics are no longer part of normal docs and are mentioned here only to
help migrate existing examples.

1. Loading calendars
--------------------

Use keyword arguments with :meth:`bizdays.Calendar.load`.

.. code-block:: python

   from bizdays import Calendar

   Calendar.load(name="ANBIMA")
   Calendar.load(filename="custom-calendar.json")

Older positional calls such as ``Calendar.load("ANBIMA")`` are no longer
accepted.

Before:

.. code-block:: python

   Calendar.load("ANBIMA")

After:

.. code-block:: python

   Calendar.load(name="ANBIMA")

2. Packaged calendars vs custom files
-------------------------------------

Packaged calendars ship with the project and should be loaded by name:

.. code-block:: python

   Calendar.load(name="ANBIMA")
   Calendar.load(name="B3")
   Calendar.load(name="Actual")

Use ``filename=...`` only for your own JSON calendar files.

Before:

.. code-block:: python

   Calendar.load(filename="ANBIMA.cal")

After:

.. code-block:: python

   Calendar.load(name="ANBIMA")

3. Constructor-based calendars
------------------------------

Older examples often focused on loading calendars from files even when the data
already existed in Python objects. The current docs also show direct
construction:

.. code-block:: python

   from bizdays import Calendar

   cal = Calendar(
       holidays=["2024-01-01", "2024-12-25"],
       weekdays=["Saturday", "Sunday"],
       startdate="2024-01-01",
       enddate="2024-12-31",
       name="Example",
   )

Use this approach when your application already owns the holiday list.

4. Return types
---------------

The NumPy-backed API returns NumPy-native values:

- scalar date results such as ``following`` and ``getdate`` return
  ``numpy.datetime64``
- scalar counters such as ``bizdays`` return ``numpy.float64``
- vectorized calls return ``numpy.ndarray`` values
- counts are ``float64`` with ``NaN`` for missing values; missing date-like
  results use ``NaT``; ``isbizday`` vectors are masked arrays with
  ``fill_value=False``, and a missing scalar flag is ``numpy.ma.masked``

Before:

.. code-block:: python

   cal.following("2015-12-25")   # expected datetime.date in old examples
   cal.seq("2014-01-02", "2014-01-07")  # expected list of dates

After:

.. code-block:: python

   cal.following("2015-12-25")   # numpy.datetime64
   cal.seq("2014-01-02", "2014-01-07")  # numpy.ndarray

5. pandas usage
---------------

``get_option`` and ``set_option`` were removed in 2.0.0, together with the
global runtime mode they controlled. The NumPy-backed ``Calendar`` accepts
pandas inputs directly, and always returns NumPy-native results.

Before:

.. code-block:: python

   from bizdays import set_option

   set_option("mode", "pandas")

Current pattern:

.. code-block:: python

   import pandas as pd

   dates = pd.to_datetime(["2014-01-12", "2014-01-13", None])
   cal.isbizday(dates)

6. Date expression lookup
-------------------------

- ``Calendar.getdate`` is still supported on the top-level API.
- ``Calendar.getbizdays(year, month=None)`` is back, with these changes:

  - Results are ``float64`` (``NaN`` where ``year`` or ``month`` is missing).
  - The whole period must lie inside the calendar range. v1 returned a partial
    count: on ANBIMA, which ends on 2099-12-25, v1 ``getbizdays(2099)`` gave
    245; v2 raises ``DateOutOfRange``.
  - v1 ``getbizdays(year, 0)`` meant the whole year; v2 raises ``ValueError``.
    Leave ``month`` out (or pass ``month=None``) instead.
  - Vectors follow the length rules: equal lengths, or one of length 1.

.. code-block:: python

   cal.getbizdays(2021)          # whole year
   cal.getbizdays(2021, 12)      # December

7. JSON calendar files
----------------------

Current JSON calendar files use these top-level fields:

- ``name``: string
- ``weekdays``: list of strings
- ``holidays``: list of ISO date strings
- ``financial``: boolean
- ``adjust.from`` and ``adjust.to``: optional strings accepted for schema
  compatibility

Minimal example:

.. code-block:: json

   {
     "name": "Custom",
     "weekdays": ["saturday", "sunday"],
     "holidays": ["2024-01-01", "2024-12-25"],
     "financial": true
   }

If you are updating older custom-file examples, keep the file-based workflow but
move the content to JSON and load it with ``Calendar.load(filename=...)``.

8. Vector lengths
-----------------

In v1, ``bizdays`` recycled a shorter vector when its length divided the longer
one, and raised a plain ``Exception`` otherwise; ``offset``, ``getdate`` and
``getbizdays`` recycled any lengths silently.

In v2, two vector arguments must have equal lengths, or one of them must have
length 1. Any other combination raises ``ValueError``. An empty argument gives
an empty array when the other argument is empty or has length 1.

The fix is mechanical: pass equal lengths, or repeat the shorter input with
``np.tile`` or ``np.repeat``:

.. code-block:: python

   cal.bizdays(["2024-01-02", "2024-01-03"], ["2024-02-01"] * 4)  # v1: 4 numbers; v2: ValueError
   cal.bizdays(np.tile(["2024-01-02", "2024-01-03"], 2), ["2024-02-01"] * 4)  # explicit repeat

9. Calendar range and construction
----------------------------------

In v1, some calls past the calendar ends wrapped around. On ANBIMA (range
2000-01-01..2099-12-25), ``offset("2000-01-03", -3)`` returned 2099-12-22. In
v2, any input or result outside ``startdate..enddate`` raises
:class:`bizdays.DateOutOfRange`, a subclass of ``ValueError``. There are no
partial results: one bad element fails the whole call, and the error's
``positions`` attribute lists every bad element. Use
:meth:`bizdays.Calendar.inrange` to check input dates before a call.

``Calendar(...)`` now checks its arguments:

- ``startdate`` after ``enddate`` raises ``ValueError``
- a calendar without business days in its whole range raises ``ValueError``
- weekday names must be English, full or 3-letter, in any case; numbers and
  other words raise ``ValueError``, and duplicates are removed
- holidays given with ``weekdays=None`` emit a ``UserWarning`` (as in R
  bizdays); pass ``weekdays=[]`` for no nonworking weekdays
- holidays outside an explicit ``startdate..enddate`` are dropped
