bizdays documentation
=====================

``bizdays`` provides business-day calculations around a NumPy-backed
``Calendar`` API. The top-level ``bizdays.Calendar`` accepts scalar dates,
Python sequences, NumPy arrays, and pandas date-like inputs, while returning
NumPy scalars or arrays for consistent vectorized behavior.

This site documents bizdays 2.0:

- build calendars directly with :class:`bizdays.Calendar`
- load packaged calendars with ``Calendar.load(name=...)``
- load custom JSON calendar files with ``Calendar.load(filename=...)``
- work with Python, NumPy, and pandas date-like inputs using the same API

Install
-------

.. code-block:: shell

   pip install bizdays

bizdays 2.0 runs on Python 3.10 to 3.14. Each optional calendar provider is an
extra:

.. code-block:: shell

   pip install "bizdays[pmc]"    # pandas_market_calendars, names with the PMC/ prefix
   pip install "bizdays[xcal]"   # exchange_calendars, names with the XCAL/ prefix
   pip install "bizdays[work]"   # workalendar, names with the WORK/ prefix

The notebooks under ``docs/source/`` are the canonical documentation examples
and are executed during the Sphinx build.

Documentation map
-----------------

- :doc:`quick` introduces the core workflow.
- :doc:`calendars` shows packaged calendars, constructor-based calendars, and
  JSON calendar files.
- :doc:`calendar-data` lists every calendar source, its range and how the data is updated.
- :doc:`pandas` focuses on pandas inputs and NumPy-backed outputs.
- :doc:`getdate` documents date-expression lookups.
- :doc:`api` is the method-by-method reference.
- :doc:`migration` is the only page that discusses older documentation patterns.
- Release notes:
  `CHANGELOG.md <https://github.com/wilsonfreitas/python-bizdays/blob/main/CHANGELOG.md>`_.

Contents
--------

.. toctree::
   :maxdepth: 2

   quick
   pandas
   calendars
   calendar-data
   getdate
   migration
   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
