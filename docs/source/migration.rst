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
- scalar counters such as ``bizdays`` return ``numpy.int_``
- vectorized calls return ``numpy.ndarray`` values
- missing date-like results use ``NaT``; missing numeric and boolean results use
  masked arrays

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

Older docs sometimes implied that switching a global runtime mode would change
the return types of the top-level calendar API. The current NumPy-backed
``Calendar`` accepts pandas inputs directly, but still returns NumPy-native
results.

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
- ``Calendar.getbizdays`` is not part of the NumPy-backed top-level API.

If older material uses ``getbizdays``, rewrite it in terms of explicit date
ranges or the operations you actually need to perform. For example:

Before:

.. code-block:: python

   cal.getbizdays(2021, 12)

After:

.. code-block:: python

   start = "2021-12-01"
   end = "2022-01-01"
   cal.bizdays(start, end)

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
