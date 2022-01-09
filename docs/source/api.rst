API
===

.. module:: bizdays

:class:`Calendar`
-----------------

.. autoclass:: Calendar
   :members: bizdays, isbizday, offset, seq, getdate, getbizdays, following, preceding, modified_following, modified_preceding, load
   :undoc-members:

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

