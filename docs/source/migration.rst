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
   * - ``DateOutOfRange`` is exported and is a ``ValueError``
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
``Calendar.load("PMC/B3")`` worked after a plain install.

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

**v1:** ``DateOutOfRange`` was a subclass of ``Exception`` and was not
exported at the top level.

**v2:** ``from bizdays import DateOutOfRange`` works, and the class is a
subclass of ``ValueError``.

**Why:** a date outside the calendar range is a bad input value, so
``ValueError`` is the expected base class.

Before (1.0.19):

.. code-block:: python

   from bizdays.utils import DateOutOfRange

   try:
       cal.offset("2099-12-20", 10)
   except ValueError:
       ...                     # never reached in 1.0.19
   except DateOutOfRange:
       ...

After (2.0):

.. code-block:: pycon

   >>> issubclass(DateOutOfRange, ValueError)
   True
   >>> try:
   ...     cal.offset("2099-12-20", 10)
   ... except DateOutOfRange:
   ...     print("out of range")
   ... except ValueError:
   ...     print("bad input")
   out of range

**Migration:** mechanical. Import it from ``bizdays``. If you catch both,
put ``except DateOutOfRange`` before ``except ValueError``; otherwise the
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
- Unknown weekday names raised ``ValueError: 'sab' is not in list``; numbers
  such as ``[5, 6]`` raised ``TypeError``.
- A calendar with every weekday off was built, and its counts were 0.
- Duplicate weekdays were kept.
- Holidays outside an explicit ``startdate..enddate`` were kept.

**v2:**

- ``Calendar().name`` is ``""``.
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
   Calendar(weekdays=["Sabado"])                     # ValueError: 'sab' is not in list
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

**v1:** ``Calendar.load("ANBIMA")`` worked, and the same argument could be
a calendar name or a file name. If both ``name`` and ``filename`` were
given, ``filename`` won.

**v2:** use ``Calendar.load(name=...)`` for packaged and provider calendars,
and ``Calendar.load(filename=...)`` for your own JSON files. A positional
argument raises ``TypeError``. Exactly one of the two keywords must be
given; both, or neither, raise ``ValueError``.

**Why:** one argument with two meanings made it unclear whether a name or a
file was loaded.

Before (1.0.19):

.. code-block:: python

   Calendar.load("ANBIMA")
   Calendar.load("custom-calendar.json")
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

New in 2.0
----------

What did not change
-------------------
