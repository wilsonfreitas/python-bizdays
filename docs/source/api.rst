API
===

.. module:: bizdays

:class:`Calendar`
-----------------

.. autoclass:: Calendar
   :members: bizdays, isbizday, offset, seq, getdate, getbizdays, following, preceding, modified_following, modified_preceding, load, diff
   :undoc-members:

getdate
-------

``Calendar.getdate(expr, ref)`` resolves date expressions against three kinds of
references:

- month references such as ``"2002-05"``
- year references such as ``2006`` or ``"2006"``
- date references such as ``"2021-02-10"`` for relative weekday expressions

Examples:

.. code-block:: python

   cal.getdate("15th day", "2002-05")
   cal.getdate("last mon before 30th day", "2006-07")
   cal.getdate("next wed", "2021-02-10")
   cal.getdate("second fri", "2026-04-20")

options
-------

.. autofunction:: set_option

Options:

- `mode`: accepts `pandas` and `python` (default).
  Pandas mode enable integration with pandas,
  check out :doc:`pandas` for more information.
- `mode.datetype`: specify the date type returned by
  Calendar's methods that return dates (`seq`, `following`, `preceding`, ...).
  Accepts `date` (default), `datetime` and `iso` for ISO formated strings.
  In pandas mode this option is ignored.

.. code-block:: python

   from bizdays import set_option
   set_option('mode', 'pandas')

.. autofunction:: get_option

.. code-block:: python

   from bizdays import get_option
   get_option('mode')
