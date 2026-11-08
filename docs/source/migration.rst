Migration guide
===============

This page lists every change you may need to handle when you move from
bizdays 1.0.19 (the last 1.x release on PyPI) to bizdays 2.0.

If you use 1.0.20, read it as 1.0.19: it has the same API and only adds
projected B3 holidays.

Each entry has the same parts:

- **v1** says what 1.0.19 did, and **v2** what 2.0 does.
- **Why** gives the reason for the change.
- **Before (1.0.19)** shows old code. **After (2.0)** shows the new code and
  its output. The "After" examples are tested with every release.
- **Migration** says how much work the change needs:

  - *mechanical*: a search and replace, or a small fixed edit;
  - *manual*: you must read the code around the call and decide;
  - *no direct replacement*: the feature is gone; the entry says what to do
    instead;
  - *nothing to change*: your code still runs, but some results are
    different, so check stored results.

The "After" examples use these imports and this calendar:

.. code-block:: pycon

   >>> import datetime
   >>> import io
   >>> import json
   >>> import os
   >>> import tempfile
   >>> import warnings
   >>> import numpy as np
   >>> import pandas as pd
   >>> from bizdays import Calendar, DateOutOfRange
   >>> cal = Calendar.load(name="ANBIMA")
   >>> tmp = tempfile.mkdtemp()

Inventory
---------

.. list-table::
   :header-rows: 1
   :widths: 60 20 20

   * - Change
     - Migration
     - Entry
   * - Python 3.10 or newer; pandas 3 is supported
     - mechanical
     - :ref:`migrate-python-and-dependencies`
   * - ``pandas_market_calendars`` and other providers are optional extras
     - mechanical
     - :ref:`migrate-optional-providers`
   * - Only ``Calendar``, ``list_calendars`` and ``DateOutOfRange`` are public
     - no direct replacement
     - :ref:`migrate-removed-top-level-names`
   * - ``get_option``, ``set_option`` and the pandas and ISO modes are gone
     - manual
     - :ref:`migrate-options-and-modes`
   * - ``cal.vec`` is gone; every method takes vectors
     - mechanical
     - :ref:`migrate-vec-removed`
   * - ``DateOutOfRange`` is a ``ValueError``
     - mechanical
     - :ref:`migrate-date-out-of-range`
   * - ``Calendar(...)`` has new defaults and checks its arguments
     - mechanical
     - :ref:`migrate-constructor`
   * - ``Calendar.load`` takes keyword arguments only
     - mechanical
     - :ref:`migrate-load-keyword-only`
   * - Text ``.cal`` files are no longer read
     - manual
     - :ref:`migrate-cal-files`
   * - Load errors have specific types
     - mechanical
     - :ref:`migrate-load-errors`
   * - Date strings must be ``YYYY-MM-DD``
     - manual
     - :ref:`migrate-strict-date-strings`
   * - Sets, generators, ``range``, dicts and 2-D inputs are rejected
     - mechanical
     - :ref:`migrate-input-containers`
   * - Counts must be whole numbers
     - mechanical
     - :ref:`migrate-whole-counts`
   * - Results are NumPy values, not Python values
     - manual
     - :ref:`migrate-return-types`
   * - Missing values are ``NaN``, ``NaT`` or masked, not ``None``
     - manual
     - :ref:`migrate-missing-values`
   * - Vector lengths must match, or one must be 1
     - mechanical
     - :ref:`migrate-vector-lengths`
   * - Dates outside the calendar range raise ``DateOutOfRange``
     - manual
     - :ref:`migrate-calendar-range`
   * - ``getdate(expr, year, month)`` is now ``getdate(expr, ref)``
     - mechanical
     - :ref:`migrate-getdate-signature`
   * - ``getdate`` expressions follow R bizdays more closely
     - manual
     - :ref:`migrate-getdate-grammar`
   * - ``getdate`` with a year ref gives a different date in one case
     - nothing to change
     - :ref:`migrate-getdate-year-ref`
   * - ``getbizdays`` returns floats and checks its range
     - manual
     - :ref:`migrate-getbizdays`
   * - B3 covers more years; Actual has a wider range
     - nothing to change
     - :ref:`migrate-calendar-data`

Install and packaging
---------------------

.. _migrate-python-and-dependencies:

Python and dependency versions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**v1:** 1.0.19 needs Python 3.9 or newer, ``pandas>=2,<3`` and
``pandas-market-calendars>=4,<5``. NumPy comes in through pandas.

**v2:** 2.0 needs Python 3.10 or newer (tested on 3.10 to 3.14),
``numpy>=1.24`` and ``pandas>=2`` (pandas 2 and 3 both work).
``pandas-market-calendars`` is no longer required (see
:ref:`migrate-optional-providers`).

**Why:** Python 3.9 is no longer supported upstream, and users asked for
pandas 3. bizdays uses NumPy directly, so it names it.

Before (1.0.19):

.. code-block:: shell

   pip install "bizdays==1.0.19"   # Python 3.9+, pandas 2 only

After (2.0):

.. code-block:: shell

   pip install "bizdays>=2"        # Python 3.10+, pandas 2 or 3

**Migration:** mechanical. Move to Python 3.10 or newer. If you pinned
``pandas<3`` only for bizdays, you can drop the pin.

.. _migrate-optional-providers:

Optional calendar providers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**v1:** ``pandas_market_calendars`` was a required dependency, so
``Calendar.load("PMC/B3")`` worked after a plain install. There was no
missing-provider error; a bad ``PMC/`` name raised the provider's own
``RuntimeError``.

**v2:** each external provider is an optional extra: ``pmc`` for
``PMC/<name>`` (``pandas_market_calendars``), ``xcal`` for ``XCAL/<name>``
(``exchange_calendars``, new) and ``work`` for ``WORK/<code>``
(``workalendar``, new). Without the extra, loading such a calendar raises
``ImportError``, and the message names the extra to install.

**Why:** most users only need the packaged calendars. Big optional packages
should not be installed for everyone.

Before (1.0.19):

.. code-block:: python

   # pip install bizdays
   from bizdays import Calendar

   cal = Calendar.load("PMC/B3")

After (2.0):

.. code-block:: python

   # pip install "bizdays[pmc]"   (or bizdays[xcal], bizdays[work])
   from bizdays import Calendar

   cal = Calendar.load(name="PMC/B3")
   # Without the extra: ImportError ... pip install "bizdays[pmc]"

**Migration:** mechanical. Add the extra to your requirements, for example
``bizdays[pmc]``.

Public names
------------

.. _migrate-removed-top-level-names:

Removed top-level names
~~~~~~~~~~~~~~~~~~~~~~~

**v1:** ``bizdays`` exported many helpers at the top level, such as
``load_holidays``, ``Date``, ``DateIndex``, ``VectorizedOps``, ``isseq``,
``isstr`` and ``options``.

**v2:** the public names are only ``Calendar``, ``list_calendars`` and
``DateOutOfRange`` (the ``__all__`` list). Submodules such as
``bizdays.utils`` or ``bizdays.dateindex`` are internal: they can change in
any release.

**Why:** a small public surface can be kept stable. The helpers were
internal tools, not part of a designed API.

Before (1.0.19):

.. code-block:: python

   from bizdays import Date, load_holidays

   holidays = load_holidays("ANBIMA.cal")
   d = Date("2024-01-02")

After (2.0):

.. code-block:: pycon

   >>> import bizdays
   >>> print(bizdays.__all__)
   ['Calendar', 'list_calendars', 'DateOutOfRange']
   >>> from bizdays import Date
   Traceback (most recent call last):
   ...
   ImportError: cannot import name 'Date' from 'bizdays'

**Migration:** no direct replacement. Pass dates as strings, Python dates,
NumPy or pandas values. To read a holiday list from a file, see
:ref:`migrate-cal-files`.

.. _migrate-options-and-modes:

Options and modes
~~~~~~~~~~~~~~~~~

**v1:** ``get_option`` and ``set_option`` changed the results of every
calendar. ``set_option("mode", "pandas")`` made ``seq`` return a pandas
``DatetimeIndex`` and made counts object arrays with ``pd.NA``.
``set_option("mode.datetype", "iso")`` made dates come back as strings such
as ``'2015-12-28'``.

**v2:** both functions are gone. Results are always NumPy values (see
:ref:`migrate-return-types`). pandas inputs are still accepted.

**Why:** a global switch made the same call return different types in
different parts of a program.

Before (1.0.19):

.. code-block:: python

   from bizdays import set_option

   set_option("mode", "pandas")
   cal.seq("2014-01-02", "2014-01-07")      # DatetimeIndex
   set_option("mode.datetype", "iso")
   cal.following("2015-12-25")              # '2015-12-28'

After (2.0):

.. code-block:: pycon

   >>> from bizdays import set_option
   Traceback (most recent call last):
   ...
   ImportError: cannot import name 'set_option' from 'bizdays'
   >>> s = pd.Series(["2024-01-02", "2024-03-01"], index=["a", "b"])
   >>> counts = pd.Series(cal.bizdays(s, "2024-06-14"), index=s.index)
   >>> print(counts.to_dict())
   {'a': 113.0, 'b': 72.0}
   >>> print(np.datetime_as_string(cal.following("2015-12-25")))
   2015-12-28
   >>> print(cal.following(["2015-12-25"]).astype(str))
   ['2015-12-28']
   >>> idx = pd.DatetimeIndex(cal.seq("2014-01-02", "2014-01-07"))
   >>> print(list(idx.strftime("%Y-%m-%d")))
   ['2014-01-02', '2014-01-03', '2014-01-06', '2014-01-07']

**Migration:** manual. Remove the ``set_option`` calls. Where you need
pandas objects, wrap the result yourself and pass ``index=`` to keep your
index. Where you need ISO strings, use ``np.datetime_as_string(result)`` or
``result.astype(str)``.

.. _migrate-vec-removed:

``cal.vec`` is gone
~~~~~~~~~~~~~~~~~~~

**v1:** vector calls went through ``cal.vec``, for example
``cal.vec.adjust_next(dates)``.

**v2:** ``cal.vec`` is gone. Every method takes a single value or a vector.

**Why:** two ways to make the same call were not needed.

Before (1.0.19):

.. code-block:: python

   list(cal.vec.adjust_next(["2015-12-25"]))

After (2.0):

.. code-block:: pycon

   >>> print(cal.following(["2015-12-25"]))
   ['2015-12-28']
   >>> print(cal.adjust_next(["2015-12-25"]))
   ['2015-12-28']

**Migration:** mechanical. Replace ``.vec.`` with ``.``.

.. _migrate-date-out-of-range:

``DateOutOfRange`` is a ``ValueError``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**v1:** ``from bizdays import DateOutOfRange`` worked, and the class was a
direct subclass of ``Exception``.

**v2:** the class is a subclass of ``ValueError``, and it is still exported
at the top level.

**Why:** a date outside the calendar range is a bad input value, so
``ValueError`` is the expected base class.

Before (1.0.19):

.. code-block:: python

   from bizdays import DateOutOfRange

   try:
       cal.bizdays("1999-01-01", "2024-01-02")
   except ValueError:
       ...                     # not reached in 1.0.19
   except DateOutOfRange:
       ...                     # reached

After (2.0):

.. code-block:: pycon

   >>> issubclass(DateOutOfRange, ValueError)
   True
   >>> try:
   ...     cal.bizdays("1999-01-01", "2024-01-02")
   ... except DateOutOfRange:
   ...     print("out of range")
   ... except ValueError:
   ...     print("bad input")
   out of range

**Migration:** mechanical. If you catch both, put ``except DateOutOfRange`` before ``except ValueError``; otherwise the
``ValueError`` branch also catches range errors.

Building and loading calendars
------------------------------

.. _migrate-constructor:

``Calendar(...)`` defaults and checks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**v1:**

- ``Calendar().name`` was ``None``, so ``str(Calendar())`` showed ``None``.
- ``Calendar(holidays=[...])`` without ``weekdays`` gave no warning.
- A calendar built from one holiday and no range worked, with the range
  2024-01-01..2024-01-01.
- ``startdate`` after ``enddate`` raised ``KeyError``.
- Unknown weekday names raised a ``ValueError`` about a list index; numbers
  such as ``[5, 6]`` raised ``TypeError``.
- A calendar with every weekday off was built, and its counts were 0.
- Duplicate weekdays were kept.
- Holidays outside an explicit ``startdate..enddate`` were kept.

**v2:**

- ``Calendar().name`` is ``""``. Passing ``name=None`` still works and
  also gives ``""``.
- ``Calendar(holidays=[...])`` without ``weekdays`` emits a ``UserWarning``
  (as R bizdays does). Pass ``weekdays=[]`` for a calendar without weekend.
- A calendar without any business day in its range raises ``ValueError``,
  for example one holiday and no range, or every weekday off.
- ``startdate`` after ``enddate`` raises ``ValueError``.
- Weekday names must be English, full (``"Saturday"``) or 3-letter
  (``"sat"``), in any case. Other words and numbers raise ``ValueError``.
- Duplicate weekdays are removed.
- Holidays outside an explicit ``startdate..enddate`` are dropped.

**Why:** these setups were mistakes that gave wrong counts later, far from
the cause. Failing early shows the cause.

Before (1.0.19):

.. code-block:: python

   Calendar().name                                   # None
   Calendar(holidays=["2024-01-01"])                 # range 2024-01-01..2024-01-01
   Calendar(startdate="2024-01-10", enddate="2024-01-01")   # KeyError
   Calendar(weekdays=["Sabado"])                     # ValueError: ... not in list
   Calendar(weekdays=[5, 6])                         # TypeError
   Calendar(weekdays=["Saturday", "saturday"]).weekdays     # both kept

After (2.0):

.. code-block:: pycon

   >>> print(repr(Calendar().name))
   ''
   >>> with warnings.catch_warnings(record=True) as caught:
   ...     warnings.simplefilter("always")
   ...     two = Calendar(holidays=["2024-01-01", "2024-12-25"])
   >>> print(caught[0].message)
   You provided holidays without set weekdays.
   That setup leads to inconsistencies!
   >>> with warnings.catch_warnings(record=True) as caught:
   ...     warnings.simplefilter("always")
   ...     two = Calendar(holidays=["2024-01-01", "2024-12-25"], weekdays=[])
   >>> len(caught)
   0
   >>> Calendar(holidays=["2024-01-01"], weekdays=[])
   Traceback (most recent call last):
   ...
   ValueError: The calendar has no business days in 2024-01-01..2024-01-01
   >>> Calendar(startdate="2024-01-10", enddate="2024-01-01")
   Traceback (most recent call last):
   ...
   ValueError: startdate 2024-01-10 is after enddate 2024-01-01
   >>> Calendar(weekdays=["Sabado"])
   Traceback (most recent call last):
   ...
   ValueError: Invalid weekday 'Sabado'; use English names such as 'Saturday' or 'sat'
   >>> Calendar(weekdays=[5, 6])
   Traceback (most recent call last):
   ...
   ValueError: Invalid weekday 5; use English names such as 'Saturday' or 'sat'
   >>> week = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
   >>> Calendar(weekdays=week, startdate="2024-01-01", enddate="2024-01-10")
   Traceback (most recent call last):
   ...
   ValueError: The calendar has no business days in 2024-01-01..2024-01-10
   >>> print(Calendar(weekdays=["Saturday", "saturday"]).weekdays)
   ('Saturday',)
   >>> inside = Calendar(
   ...     holidays=["2023-01-01", "2024-01-01"], weekdays=[],
   ...     startdate="2023-06-01", enddate="2024-12-31",
   ... )
   >>> len(inside.holidays)
   1

**Migration:** mechanical. Use English weekday names, pass ``weekdays=[]``
when you mean "no weekend", and check that ``startdate`` comes before
``enddate``. Code that tests ``cal.name is None`` should test
``not cal.name``.

.. _migrate-load-keyword-only:

``Calendar.load`` takes keywords only
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**v1:** ``Calendar.load("ANBIMA")`` worked by position, because the first
parameter was ``name``. A file needed ``filename=``: a file path passed by
position raised ``Exception: Invalid calendar``. If both ``name`` and
``filename`` were given, ``filename`` won.

**v2:** use ``Calendar.load(name=...)`` for packaged and provider calendars,
and ``Calendar.load(filename=...)`` for your own JSON files. A positional
argument raises ``TypeError``. Exactly one of the two keywords must be
given; both, or neither, raise ``ValueError``.

**Why:** keywords make the call clear, and each call names exactly one
source, so no argument is silently ignored.

Before (1.0.19):

.. code-block:: python

   Calendar.load("ANBIMA")
   Calendar.load(filename="custom-calendar.json")
   Calendar.load(name="B3", filename="x.json")   # loads x.json

After (2.0):

.. code-block:: pycon

   >>> print(Calendar.load(name="ANBIMA").name)
   ANBIMA
   >>> Calendar.load("ANBIMA")
   Traceback (most recent call last):
   ...
   TypeError: Calendar.load() takes 1 positional argument but 2 were given
   >>> Calendar.load(name="B3", filename="x.json")
   Traceback (most recent call last):
   ...
   ValueError: Provide exactly one of 'name' or 'filename'

**Migration:** mechanical. Write ``name=`` before a calendar name and
``filename=`` before a file path.

.. _migrate-cal-files:

Text ``.cal`` files
~~~~~~~~~~~~~~~~~~~

**v1:** ``Calendar.load(filename="my.cal")`` read a text file with one
holiday (``YYYY-MM-DD``) or one English weekday name per line. Blank lines
were skipped.

**v2:** only JSON calendar files are read. A ``.cal`` file raises
``ValueError`` with the text "a JSON calendar is expected" and a link to
this page.

**Why:** one file format, the same as R bizdays, is easier to keep correct.
JSON can also hold the name, the range and the ``financial`` flag.

Before (1.0.19):

.. code-block:: python

   # my.cal:
   #   2001-01-01
   #   2001-02-26
   #   Saturday
   #   Sunday
   cal = Calendar.load(filename="my.cal")

After (2.0): a ``.cal`` file raises an error.

.. code-block:: pycon

   >>> path = os.path.join(tmp, "old.cal")
   >>> with open(path, "w") as f:
   ...     _ = f.write("2001-01-01\nSaturday\n")
   >>> Calendar.load(filename=path)
   Traceback (most recent call last):
   ...
   ValueError: Invalid calendar file ...: a JSON calendar is expected. ...

Read the ``.cal`` lines yourself: lines that start with a letter are
weekdays, the other lines are holidays.

.. code-block:: pycon

   >>> lines = io.StringIO("2001-01-01\n2001-02-26\nSaturday\nSunday\n")
   >>> rows = [line.strip() for line in lines if line.strip()]
   >>> old_weekdays = [row for row in rows if row[0].isalpha()]
   >>> old_holidays = [row for row in rows if not row[0].isalpha()]
   >>> old = Calendar(holidays=old_holidays, weekdays=old_weekdays, name="old")
   >>> print(old.weekdays)
   ('Saturday', 'Sunday')
   >>> len(old.holidays)
   2

To keep a file, write the same lists to a JSON file once, and load it with
``filename=``:

.. code-block:: pycon

   >>> data = {"name": "old", "weekdays": old_weekdays, "holidays": old_holidays}
   >>> json_path = os.path.join(tmp, "old.json")
   >>> with open(json_path, "w") as f:
   ...     json.dump(data, f)
   >>> print(Calendar.load(filename=json_path).weekdays)
   ('Saturday', 'Sunday')

JSON calendar files use these top-level fields:

- ``name``: string
- ``weekdays``: list of English weekday names
- ``holidays``: list of ``YYYY-MM-DD`` strings
- ``financial``: boolean (default ``true``)
- ``start.date`` and ``end.date``: optional ``YYYY-MM-DD`` strings for the
  range
- ``adjust.from`` and ``adjust.to``: optional, accepted for compatibility
  with R bizdays (see :ref:`migrate-load-errors`)

Minimal example:

.. code-block:: json

   {
     "name": "Custom",
     "weekdays": ["saturday", "sunday"],
     "holidays": ["2024-01-01", "2024-12-25"],
     "financial": true
   }

**Migration:** manual. Convert each ``.cal`` file to JSON once, with the
recipe above, or build the calendar in Python from your own data.

.. _migrate-load-errors:

Load errors
~~~~~~~~~~~

**v1:** an unknown calendar name and a missing file both raised a plain
``Exception: Invalid calendar: ...``.

**v2:**

- an unknown name raises ``ValueError``, and the message lists the packaged
  calendars;
- a missing file raises ``FileNotFoundError``;
- a JSON file with ``adjust.from`` other than ``"following"``, or
  ``adjust.to`` other than ``"preceding"``, raises ``ValueError``, because
  bizdays always uses these two rules.

**Why:** specific error types can be caught on their own.

Before (1.0.19):

.. code-block:: python

   try:
       Calendar.load("B1")
   except Exception:
       ...

After (2.0):

.. code-block:: pycon

   >>> Calendar.load(name="B1")
   Traceback (most recent call last):
   ...
   ValueError: Unknown calendar: 'B1'; packaged calendars are ANBIMA, B3, Actual
   >>> Calendar.load(filename=os.path.join(tmp, "missing.json"))
   Traceback (most recent call last):
   ...
   FileNotFoundError: Calendar file not found: ...
   >>> adjust_path = os.path.join(tmp, "adjust.json")
   >>> with open(adjust_path, "w") as f:
   ...     json.dump({"name": "X", "weekdays": [], "holidays": [],
   ...                "adjust.to": "following"}, f)
   >>> Calendar.load(filename=adjust_path)
   Traceback (most recent call last):
   ...
   ValueError: Invalid calendar JSON: 'adjust.to' must be 'preceding', got 'following'

**Migration:** mechanical. Catch ``ValueError`` or ``FileNotFoundError``
instead of ``Exception``.

Inputs
------

.. _migrate-strict-date-strings:

Strict date strings
~~~~~~~~~~~~~~~~~~~

**v1:** date strings without zero padding, such as ``"2024-1-2"``, worked.

**v2:** a date string must be ``YYYY-MM-DD``. Other strings raise
``ValueError``, including ``""`` and ``"NaT"``. A ``numpy.datetime64`` with
unit ``Y``, ``M`` or ``W`` is not a date and raises ``ValueError``. A
string such as ``"2024-01"`` was already an error for dates; now it is only
accepted as a month ref in ``getdate``.

**Why:** a loose parser can read a wrong value as a valid date without any
error.

Before (1.0.19):

.. code-block:: python

   cal.isbizday("2024-1-2")   # True

After (2.0):

.. code-block:: pycon

   >>> cal.isbizday("2024-1-2")
   Traceback (most recent call last):
   ...
   ValueError: dt: invalid date string np.str_('2024-1-2'); expected YYYY-MM-DD
   >>> cal.isbizday("")
   Traceback (most recent call last):
   ...
   ValueError: dt: invalid date string np.str_(''); expected YYYY-MM-DD
   >>> cal.isbizday(np.datetime64("2024-01"))
   Traceback (most recent call last):
   ...
   ValueError: dt: numpy.datetime64 with unit 'M' is not a date; use unit 'D' or finer
   >>> values = ["2024-1-2", "2024-1-6"]
   >>> print(cal.isbizday(pd.to_datetime(values)))
   [True False]
   >>> print(cal.isbizday(pd.to_datetime(values).strftime("%Y-%m-%d")))
   [True False]

**Migration:** manual. Find where your date strings come from. Parse loose
strings with ``pd.to_datetime`` and pass the result directly, or format them
with ``.strftime("%Y-%m-%d")``.

.. _migrate-input-containers:

Input containers
~~~~~~~~~~~~~~~~

**v1:** any iterable worked as a vector: ``cal.isbizday({"2024-01-02"})``
gave ``[True]``, and generators worked too.

**v2:** vectors are lists, tuples, NumPy arrays and pandas ``Series`` or
``Index`` objects. Sets, generators, ``range`` and dicts raise
``ValueError``. 2-D input, such as a ``DataFrame`` or a list of lists, also
raises ``ValueError``.

**Why:** sets and dicts have no fixed order, and a generator can be read
only once, so results could not be matched to inputs.

Before (1.0.19):

.. code-block:: python

   cal.isbizday({"2024-01-02"})                # [True]
   cal.isbizday(d for d in ["2024-01-02"])     # [True]

After (2.0):

.. code-block:: pycon

   >>> cal.isbizday({"2024-01-02"})
   Traceback (most recent call last):
   ...
   ValueError: dt: set is not a supported sequence; use a list, tuple, NumPy array or pandas Series/Index
   >>> cal.isbizday(d for d in ["2024-01-02"])
   Traceback (most recent call last):
   ...
   ValueError: dt: generator is not a supported sequence; ...
   >>> df = pd.DataFrame({"day": ["2024-01-02", "2024-01-06"]})
   >>> cal.isbizday(df)
   Traceback (most recent call last):
   ...
   ValueError: dt must be 1-D, got a DataFrame
   >>> print(cal.isbizday(list(d for d in ["2024-01-02"])))
   [True]
   >>> print(cal.isbizday(df["day"]))
   [True False]

**Migration:** mechanical. Wrap the input in ``list(...)``, or pass one
column (``df["col"]``) instead of a ``DataFrame``.

.. _migrate-whole-counts:

Whole-number counts
~~~~~~~~~~~~~~~~~~~

**v1:** ``cal.offset("2013-01-02", True)`` was read as ``offset(..., 1)``
and gave 2013-01-03. ``cal.offset("2013-01-02", 1.5)`` raised
``TypeError``.

**v2:** the count must be a whole number. ``True``, ``False`` and ``1.5``
raise ``ValueError``. Whole floats such as ``3.0`` now work.

**Why:** a ``bool`` count is almost always a bug, and whole floats are
common when counts come from pandas.

Before (1.0.19):

.. code-block:: python

   cal.offset("2013-01-02", True)   # datetime.date(2013, 1, 3)
   cal.offset("2013-01-02", 1.5)    # TypeError

After (2.0):

.. code-block:: pycon

   >>> cal.offset("2013-01-02", True)
   Traceback (most recent call last):
   ...
   ValueError: n must be whole numbers or missing (got True)
   >>> cal.offset("2013-01-02", 1.5)
   Traceback (most recent call last):
   ...
   ValueError: n must be whole numbers or missing (got 1.5)
   >>> print(cal.offset("2013-01-02", 3.0))
   2013-01-07

**Migration:** mechanical. Pass ``int(n)``.

Outputs and missing values
--------------------------

.. _migrate-return-types:

Return types
~~~~~~~~~~~~

**v1:** results were Python values: ``datetime.date`` for dates, ``int``
for counts, ``bool`` for flags, and lists for vectors.

**v2:** results are NumPy values:

- dates are ``numpy.datetime64`` (unit ``D``);
- counts are ``numpy.float64``, even when the value is whole;
- flags are ``numpy.bool_``, so ``cal.isbizday(d) is True`` is ``False``;
- vectors are ``numpy.ndarray`` (and masked arrays for ``isbizday``, see
  :ref:`migrate-missing-values`);
- a ``numpy.datetime64`` is not found in a ``set`` or ``dict`` of
  ``datetime.date`` values;
- a pandas ``Series`` input does not keep its index in the result.

**Why:** NumPy values make vector calls fast, and the same call returns the
same type for one value and for many.

Before (1.0.19):

.. code-block:: python

   cal.following("2015-12-25")                 # datetime.date(2015, 12, 28)
   cal.bizdays("2024-01-02", "2024-06-14")     # 113
   cal.isbizday("2024-01-02") is True          # True
   cal.seq("2014-01-02", "2014-01-07")         # list of datetime.date

After (2.0):

.. code-block:: pycon

   >>> type(cal.following("2015-12-25")).__name__
   'datetime64'
   >>> print(cal.bizdays("2024-01-02", "2024-06-14"))
   113.0
   >>> cal.isbizday("2024-01-02") is True
   False
   >>> bool(cal.isbizday("2024-01-02"))
   True
   >>> cal.following("2015-12-25") in {datetime.date(2015, 12, 28)}
   False
   >>> cal.following("2015-12-25").item()
   datetime.date(2015, 12, 28)
   >>> cal.seq("2014-01-02", "2014-01-07").tolist()
   [datetime.date(2014, 1, 2), datetime.date(2014, 1, 3), datetime.date(2014, 1, 6), datetime.date(2014, 1, 7)]
   >>> df = pd.DataFrame({"day": ["2024-01-02", "2024-03-01"]}, index=[10, 20])
   >>> df["count"] = cal.bizdays(df["day"], "2024-06-14")
   >>> print(df["count"].to_dict())
   {10: 113.0, 20: 72.0}

**Migration:** manual. Use ``bool(...)`` or ``==`` instead of ``is True``.
Use ``.item()`` for one Python value and ``.tolist()`` for a list. Use
``int(...)`` or ``.astype(int)`` where you need integers (drop ``NaN``
first). Assign results to a ``DataFrame`` column, or build a ``Series`` with
``index=``; never ``pd.Series(result)`` alone, which gets a new index.

.. _migrate-missing-values:

Missing values
~~~~~~~~~~~~~~

**v1:** a missing input (``None``) gave ``None`` inside the result list,
for example ``cal.bizdays(["2024-01-02", None], "2024-06-14")`` gave
``[113, None]``. In pandas mode it gave ``pd.NA``. ``cal.seq(None, ...)``
raised ``TypeError``.

**v2:**

- counts use ``NaN``;
- dates use ``NaT`` (not a time);
- ``isbizday`` with a vector always returns a ``numpy.ma.MaskedArray``,
  with missing entries masked; a missing scalar gives ``numpy.ma.masked``;
- ``diff`` gives ``NaN`` for each step that touches a missing date;
- ``seq`` with a missing end raises ``ValueError``.

**Why:** ``None`` inside a list forces Python objects; ``NaN``, ``NaT`` and
masks keep NumPy arrays fast and typed.

Before (1.0.19):

.. code-block:: python

   cal.bizdays(["2024-01-02", None], "2024-06-14")   # [113, None]
   cal.isbizday(["2024-01-02", None])                # [True, None]
   cal.seq(None, "2014-01-07")                       # TypeError

After (2.0):

.. code-block:: pycon

   >>> counts = cal.bizdays(["2024-01-02", None], "2024-06-14")
   >>> print(counts)
   [113.  nan]
   >>> print(np.isnan(counts))
   [False  True]
   >>> print(counts[~np.isnan(counts)].astype(int))
   [113]
   >>> flags = cal.isbizday(["2024-01-02", None])
   >>> print(flags)
   [True --]
   >>> type(flags).__name__
   'MaskedArray'
   >>> print(flags.mask)
   [False  True]
   >>> print(flags.filled(False))
   [ True False]
   >>> print(np.isnat(cal.following(["2015-12-25", None])))
   [False  True]
   >>> print(cal.diff(["2014-01-02", None, "2014-01-10"]))
   [nan nan]
   >>> cal.seq(None, "2014-01-07")
   Traceback (most recent call last):
   ...
   ValueError: seq endpoints cannot be missing

**Migration:** manual. Replace ``x is None`` checks with ``np.isnan`` for
counts, ``np.isnat`` for dates and ``.mask`` for flags. Use
``.filled(False)`` to turn a masked flag array into a plain ``bool`` array.
Drop ``NaN`` before ``.astype(int)``.

Vectors and calendar range
--------------------------

.. _migrate-vector-lengths:

Vector lengths
~~~~~~~~~~~~~~

**v1:** ``bizdays`` recycled a shorter vector when its length divided the
longer one (lengths 2 and 4 gave 4 results), and raised a plain
``Exception`` otherwise (lengths 2 and 3). ``offset``, ``getdate`` and
``getbizdays`` recycled any lengths silently (lengths 3 and 2 gave 3
results). An empty vector raised ``ZeroDivisionError``.

**v2:** two vector arguments must have equal lengths, or one of them must
have length 1. Any other combination raises ``ValueError``. An empty
argument gives an empty array when the other argument is empty or has
length 1.

**Why:** silent recycling hid bugs where two columns were not aligned.

Before (1.0.19):

.. code-block:: python

   cal.bizdays(["2024-01-02", "2024-01-03"], ["2024-02-01"] * 4)  # [22, 21, 22, 21]
   cal.bizdays(["2024-01-02", "2024-01-03"], ["2024-02-01"] * 3)  # Exception
   cal.bizdays([], "2024-01-02")                                   # ZeroDivisionError

After (2.0):

.. code-block:: pycon

   >>> cal.bizdays(["2024-01-02", "2024-01-03"], ["2024-02-01"] * 4)
   Traceback (most recent call last):
   ...
   ValueError: date_from has length 2 and date_to has length 4; ...
   >>> print(cal.bizdays(np.tile(["2024-01-02", "2024-01-03"], 2), ["2024-02-01"] * 4))
   [22. 21. 22. 21.]
   >>> print(cal.bizdays([], "2024-01-02"))
   []

**Migration:** mechanical. Pass equal lengths, or repeat the shorter input
with ``np.tile`` or ``np.repeat``.

.. _migrate-calendar-range:

Calendar range
~~~~~~~~~~~~~~

**v1:** some calls past the calendar ends wrapped around. On ANBIMA (range
2000-01-01..2099-12-25), ``offset("2000-01-03", -3)`` returned 2099-12-22.

**v2:** any input or result outside ``startdate..enddate`` raises
:class:`bizdays.DateOutOfRange`. There are no partial results: one bad
element fails the whole call, and the error's ``positions`` attribute lists
every bad element. For ``getdate`` and ``getbizdays`` the whole period
(month or year) must be inside the range, so
``getdate("last bizday", "2099-12")`` on ANBIMA raises. Use
:meth:`bizdays.Calendar.inrange` to check input dates before a call.

**Why:** a wrapped date is a wrong answer that looks right.

Before (1.0.19):

.. code-block:: python

   cal.offset("2000-01-03", -3)   # datetime.date(2099, 12, 22)

After (2.0):

.. code-block:: pycon

   >>> cal.offset("2000-01-03", -3)
   Traceback (most recent call last):
   ...
   DateOutOfRange: 1 of 1 elements out of calendar range 2000-01-01..2099-12-25; ...
   >>> try:
   ...     cal.offset(["2024-01-02", "2099-12-24"], 5)
   ... except DateOutOfRange as err:
   ...     print(err.positions)
   [1]
   >>> print(cal.inrange(["1999-01-01", "2024-01-02"]))
   [False True]
   >>> cal.getdate("last bizday", "2099-12")
   Traceback (most recent call last):
   ...
   DateOutOfRange: 1 of 1 elements out of calendar range 2000-01-01..2099-12-25; ...

**Migration:** manual. Filter inputs with ``inrange`` before the call, or
catch ``DateOutOfRange`` and use ``positions``. Code that needs partial
results has no direct replacement yet; ``errors="coerce"`` is planned for
2.1.

getdate
-------

.. _migrate-getdate-signature:

``getdate(expr, ref)``
~~~~~~~~~~~~~~~~~~~~~~

**v1:** ``getdate(expr, year, month=None)``, for example
``cal.getdate("last bizday", 2024, 2)`` gave 2024-02-29.

**v2:** ``getdate(expr, ref)``. The ref is a year (``2024``), a month
(``"2024-02"`` or a ``numpy.datetime64`` with unit ``M``) or a date. The
old call with three arguments raises ``TypeError``.

**Why:** one ref argument, as in R bizdays, also allows date refs and
vectors of refs.

**Day refs are not month refs.** A ``pd.Timestamp``, a ``datetime.date`` or
a ``"YYYY-MM-DD"`` string is a date ref, even on the first day of a month.
``"last bizday"`` with a date ref is the business day before that date. To
get the last business day of a month from dates, convert them to months
with ``.astype("datetime64[M]")``.

Before (1.0.19):

.. code-block:: python

   cal.getdate("last bizday", 2024, 2)    # datetime.date(2024, 2, 29)

After (2.0):

.. code-block:: pycon

   >>> year, month = 2024, 2
   >>> print(cal.getdate("last bizday", f"{year}-{month:02d}"))
   2024-02-29
   >>> cal.getdate("last bizday", 2024, 2)
   Traceback (most recent call last):
   ...
   TypeError: Calendar.getdate() takes 3 positional arguments but 4 were given
   >>> print(cal.getdate("last bizday", pd.Timestamp("2024-02-01")))
   2024-01-31
   >>> print(cal.getdate("last bizday", np.datetime64("2024-02")))
   2024-02-29
   >>> days = pd.to_datetime(["2024-02-01", "2024-03-15"]).values
   >>> print(cal.getdate("last bizday", days.astype("datetime64[M]")))
   ['2024-02-29' '2024-03-28']

**Migration:** mechanical. Replace ``year, month`` with
``f"{year}-{month:02d}"``, and ``year`` alone with ``year``. If your refs are
dates, convert them with ``.astype("datetime64[M]")`` when you mean the
month.

.. _migrate-getdate-grammar:

``getdate`` expressions
~~~~~~~~~~~~~~~~~~~~~~~

**v1:**

- ordinals with a wrong suffix worked: ``"2st bizday"`` was the 2nd
  business day;
- ``previous`` was not supported: every ``previous ...`` expression raised
  ``ValueError``;
- ``next <weekday>`` with a year or month ref raised ``ValueError``;
- only year and month refs existed;
- all refs in one vector call could mix any kind.

**v2:**

- ordinals need the right English suffix: ``1st``, ``2nd``, ``3rd``,
  ``4th``, ``11th``, ``21st``; ``2st`` raises ``ValueError``;
- ``previous <weekday>`` is new and needs a date ref; ``previous bizday``
  and ``previous day`` still raise ``ValueError``;
- ``next <weekday>`` (and ``next day``, ``next bizday``) with a year or
  month ref is the first one in the period;
- date refs accept the forms of R bizdays: ``<n> day`` is the date plus
  ``n`` days, ``last day`` the day before, ``<n> bizday`` is
  ``offset(date, n)``, ``last bizday`` is ``offset(date, -1)``, and
  ``next``/``last <weekday>`` the next or previous one;
- expressions with ``before`` or ``after`` need a year or month ref;
- all refs in one call must be of one kind (year, month or date).
- weekday words must be full or 3-letter English names (``tues`` raises
  ``ValueError``, as in 1.0.19).

**Why:** the grammar now follows R bizdays, the reference implementation.

Before (1.0.19):

.. code-block:: python

   cal.getdate("2st bizday", 2024, 1)    # datetime.date(2024, 1, 3)
   cal.getdate("next wed", 2002, 1)      # ValueError

After (2.0):

.. code-block:: pycon

   >>> cal.getdate("2st bizday", "2024-01")
   Traceback (most recent call last):
   ...
   ValueError: Invalid ordinal in getdate expression: 2st (use 2nd)
   >>> print(cal.getdate("2nd bizday", "2024-01"))
   2024-01-03
   >>> cal.getdate("first tues", "2024-01")
   Traceback (most recent call last):
   ...
   ValueError: Invalid day token in getdate expression: tues
   >>> cal.getdate("previous bizday", "2024-01")
   Traceback (most recent call last):
   ...
   ValueError: previous expressions require a weekday target
   >>> print(cal.getdate("next wed", "2002-01"))
   2002-01-02
   >>> print(cal.getdate("next bizday", "2022-06-18"))
   2022-06-20
   >>> cal.getdate("first bizday before first day", "2024-01-10")
   Traceback (most recent call last):
   ...
   ValueError: Composite getdate expressions need a year or month ref, ...
   >>> cal.getdate(["first day", "next wed"], ["2002-01", "2021-02-10"])
   Traceback (most recent call last):
   ...
   ValueError: getdate refs must all be of one kind (year, month or date); found: date, month
   >>> print(cal.getdate(["first bizday", "last bizday"], ["2024-01", "2024-02"]))
   ['2024-01-02' '2024-02-29']

**Migration:** manual. Fix ordinal suffixes and split calls that mix ref
kinds.

.. _migrate-getdate-year-ref:

``getdate`` with a year ref
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**v1:** ``cal.getdate("first bizday before first day", 2024)`` gave
2024-01-02. This was a bug: the business day before 1 January is in the
year before.

**v2:** the same call gives 2023-12-29, the business day before
1 January.

**Why:** the old result was wrong.

Before (1.0.19):

.. code-block:: python

   cal.getdate("first bizday before first day", 2024)   # datetime.date(2024, 1, 2)

After (2.0):

.. code-block:: pycon

   >>> print(cal.getdate("first bizday before first day", 2024))
   2023-12-29

**Migration:** nothing to change. The call still runs, but check results
that you stored with 1.0.19.

getbizdays
----------

.. _migrate-getbizdays:

``getbizdays``
~~~~~~~~~~~~~~

**v1:** ``getbizdays(year, month=None)`` returned an ``int`` (or a list of
``int``). A period that went past the calendar end gave a partial count: on
ANBIMA, ``getbizdays(2099)`` gave 245. ``getbizdays(year, 0)`` meant the
whole year.

**v2:**

- results are ``float64`` (``NaN`` where ``year`` or ``month`` is missing);
- the whole period must lie inside the calendar range, or
  ``DateOutOfRange`` is raised;
- ``month`` must be between 1 and 12; ``0`` raises ``ValueError`` (leave
  ``month`` out, or pass ``month=None``, for the whole year);
- vectors follow the length rules of :ref:`migrate-vector-lengths`.

**Why:** a partial count looks like a full one, and ``0`` is not a month.

Before (1.0.19):

.. code-block:: python

   cal.getbizdays(2024)            # 253
   cal.getbizdays(2099)            # 245 (partial)
   cal.getbizdays(2024, 0)         # 253
   cal.getbizdays([2023, 2024])    # [249, 253]

After (2.0):

.. code-block:: pycon

   >>> print(cal.getbizdays(2024))
   253.0
   >>> print(cal.getbizdays(2024, 12))
   21.0
   >>> cal.getbizdays(2099)
   Traceback (most recent call last):
   ...
   DateOutOfRange: 1 of 1 elements out of calendar range 2000-01-01..2099-12-25; ...
   >>> cal.getbizdays(2024, 0)
   Traceback (most recent call last):
   ...
   ValueError: month must be between 1 and 12 (got 0)
   >>> print(cal.getbizdays([2023, 2024]))
   [249. 253.]

**Migration:** manual. Replace ``month=0`` with no month, use ``int(...)``
where you need integers, and check periods near the calendar ends.

Calendar data
-------------

.. _migrate-calendar-data:

Calendar data
~~~~~~~~~~~~~

**v1:** the B3 calendar ended on 2026-12-31, so
``Calendar.load("B3").bizdays("2026-12-01", "2027-01-10")`` raised
``DateOutOfRange``. The Actual calendar covered 1970-01-01..2071-01-01.

**v2:** B3 is official for 2000-2026. Years 2027-2099 are projected: ANBIMA
holidays, plus December 24, plus the last weekday of the year. Actual
covers 1900-01-01..2199-12-31. The range of ``Calendar()`` without holidays
or dates does not change (1970-01-01..2071-01-01). See :doc:`calendar-data`
for every range and the update policy.

**Why:** a B3 calendar that ends next year breaks long-dated contracts.

Before (1.0.19):

.. code-block:: python

   b3 = Calendar.load("B3")
   b3.enddate                                  # datetime.date(2026, 12, 31)
   b3.bizdays("2026-12-01", "2027-01-10")      # DateOutOfRange

After (2.0):

.. code-block:: pycon

   >>> b3 = Calendar.load(name="B3")
   >>> print(b3.enddate)
   2099-12-31
   >>> print(b3.bizdays("2026-12-01", "2027-01-10"))
   24.0
   >>> actual = Calendar.load(name="Actual")
   >>> print(actual.startdate, actual.enddate)
   1900-01-01 2199-12-31
   >>> print(Calendar().startdate, Calendar().enddate)
   1970-01-01 2071-01-01

**Migration:** nothing to change. Calls that raised ``DateOutOfRange`` now
work. Projected B3 years can change when B3 publishes its official
calendar.

New in 2.0
----------

These are new features, not breaking changes. See :doc:`api` for details.

- :func:`bizdays.list_calendars` lists the packaged and provider calendars.
- :meth:`bizdays.Calendar.inrange` tells which dates are inside the
  calendar range.
- :class:`bizdays.DateOutOfRange` has a ``positions`` attribute.
- ``numpy.datetime64`` values and pandas ``Timestamp``, ``Series`` and
  ``DatetimeIndex`` inputs work everywhere (1.0.19 rejected
  ``numpy.datetime64`` with a ``ValueError``).
- ``XCAL/<name>`` and ``WORK/<code>`` calendar providers.
- ``getdate`` date refs and vectors of expressions and refs.
- ``getdate`` ``previous <weekday>`` with a date ref.
- Empty inputs give empty results (1.0.19 raised ``ZeroDivisionError``).

What did not change
-------------------

- Method names, and both alias pairs: ``following`` / ``adjust_next`` and
  ``preceding`` / ``adjust_previous``.
- Property types: ``holidays``, ``startdate`` and ``enddate`` are still
  Python ``datetime.date`` values.
- Counting rules, including ends that are not business days
  (``bizdays(a, b) == bizdays(following(a), preceding(b))``) and
  ``financial=False``.
- ``offset(d, 0)`` returns ``d`` unchanged, even when ``d`` is a holiday.
- ``seq`` with the start after the end gives a descending sequence.
- Time-zone-aware values use the wall-clock date: 2024-01-06 23:00 at
  -03:00 is 2024-01-06.
- ``seq`` with a vector raises ``ValueError``.
- ``getdate`` with an unknown weekday word, such as ``tues``, ``wedn`` or
  ``monkey``, raises ``ValueError``.
- ANBIMA and B3 holidays up to 2026 are the same.

.. code-block:: pycon

   >>> print(cal.bizdays("2024-01-02", "2024-06-15"),
   ...       cal.bizdays(cal.following("2024-01-02"), cal.preceding("2024-06-15")))
   113.0 113.0
