API reference
=============

.. module:: bizdays

The top-level :class:`Calendar` is the NumPy-backed public API. Scalar calls
return NumPy scalars, vectorized calls return ``numpy.ndarray`` values, missing
date-like results use ``NaT``, and missing numeric or boolean results use masked
arrays.

Calendar construction
---------------------

.. autoclass:: Calendar
   :members:
   :exclude-members: bizdays, isbizday, adjust_next, following, modified_following, adjust_previous, preceding, modified_preceding, seq, offset, diff, getdate, load

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

- ``ANBIMA``
- ``B3``
- ``Actual``

Optional integration with ``pandas_market_calendars`` remains available through
the ``PMC/`` prefix, for example ``Calendar.load(name="PMC/NYSE")`` when the
optional dependency is installed.

Core business-day calculations
------------------------------

bizdays
^^^^^^^

.. automethod:: Calendar.bizdays

Examples:

.. code-block:: python

   cal.bizdays("2013-01-02", "2013-01-31")
   cal.bizdays(["2013-01-02", "2013-01-02"], ["2013-01-31", "2013-02-28"])
   cal.bizdays(None, "2024-01-05")  # masked scalar result

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
- date references such as ``"2021-02-10"`` for relative weekday expressions

The ``expr`` grammar accepted by the current parser has three forms.

Simple expressions
""""""""""""""""""

Format:

.. code-block:: text

   <ordinal> <target>

Examples:

.. code-block:: text

   first day
   15th day
   last bizday
   third tue

Composite expressions
"""""""""""""""""""""

Format:

.. code-block:: text

   <ordinal> <target> <before|after> <ordinal> <target>

Examples:

.. code-block:: text

   first day before 15th day
   second bizday after 15th day
   1st bizday before 2nd fri
   last mon before 30th day

Date-relative expressions
"""""""""""""""""""""""""

Format:

.. code-block:: text

   <next|previous> <weekday>

Examples:

.. code-block:: text

   next wed
   previous mon

Valid ``ordinal`` tokens:

- named ordinals: ``first``, ``second``, ``third``, ``last``
- numeric ordinals: ``1st``, ``2nd``, ``3rd``, ``4th``, ``15th``, and so on

Valid ``target`` tokens:

- ``day``
- ``bizday``
- weekday names matched by their first three letters, such as ``mon``, ``tue``,
  ``wed``, ``thu``, ``fri``, ``sat``, ``sun``

Reference-specific rules:

- month refs (``YYYY-MM``) support simple and composite expressions
- year refs (``YYYY`` or ``int``) support simple and composite expressions
- date refs (``YYYY-MM-DD`` and date-like values) support only weekday-based
  expressions, especially ``next <weekday>`` and ``previous <weekday>``

Parser notes:

- ``next`` and ``previous`` require a weekday target, not ``day`` or ``bizday``
- composite expressions only accept the operators ``before`` and ``after``
- expressions are whitespace-tokenized, so the supported forms are strictly the
  2-token, 5-token, and ``next|previous`` 2-token patterns above

Examples:

.. code-block:: python

   cal.getdate("15th day", "2002-05")
   cal.getdate(["last day", "last bizday"], "2006")
   cal.getdate("next wed", "2021-02-10")
   cal.getdate("first bizday", ["2002-01", "2002-02"])
