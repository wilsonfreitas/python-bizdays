bizdays documentation
=====================

``bizdays`` provides business-day calculations around a NumPy-backed
``Calendar`` API. The top-level ``bizdays.Calendar`` accepts scalar dates,
Python sequences, NumPy arrays, and pandas date-like inputs, while returning
NumPy scalars or arrays for consistent vectorized behavior.

This documentation is intentionally focused on the current public API:

- build calendars directly with :class:`bizdays.Calendar`
- load packaged calendars with ``Calendar.load(name=...)``
- load custom JSON calendar files with ``Calendar.load(filename=...)``
- work with Python, NumPy, and pandas date-like inputs using the same API

Install
-------

.. code-block:: shell

   pip install bizdays

Use ``pip install "bizdays[pmc]"`` when you want to load
``pandas_market_calendars`` calendars through the ``PMC/`` prefix.

The notebooks under ``docs/source/`` are the canonical documentation examples
and are executed during the Sphinx build.

Documentation map
-----------------

- :doc:`quick` introduces the core workflow.
- :doc:`calendars` shows packaged calendars, constructor-based calendars, and
  JSON calendar files.
- :doc:`pandas` focuses on pandas inputs and NumPy-backed outputs.
- :doc:`getdate` documents date-expression lookups.
- :doc:`api` is the method-by-method reference.
- :doc:`migration` is the only page that discusses older documentation patterns.

Contents
--------

.. toctree::
   :maxdepth: 2

   quick
   pandas
   calendars
   getdate
   migration
   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
