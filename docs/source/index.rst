.. bizdays documentation master file, created by
   sphinx-quickstart on Wed Dec 29 12:03:45 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to bizdays's documentation!
===================================

**bizdays** computes business days between two dates based on the definition of
nonworking days (usually holidays and nonworking weekdays). It also computes
other collateral effects like adjust dates for the next or previous business
day, check whether a date is a business day, create generators of business
days sequences, and so forth.

Install
-------

**bizdays** is avalilable at PyPI, so it is pip instalable:

.. code-block:: shell

   pip install bizdays


Check out the :doc:`quick` section for further information.


Contents
--------

.. toctree::
   :maxdepth: 2

   quick
   pandas
   calendars
   getdate
   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`

