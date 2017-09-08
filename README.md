[![Downloads](https://img.shields.io/pypi/dm/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)
[![Latest Version](https://img.shields.io/pypi/v/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)
[![Development Status](https://img.shields.io/pypi/status/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)

# [python-bizdays](http://wilsonfreitas.github.io/python-bizdays/)

In several countries and markets, the accountability of the price of a financial
instrument, mainly bonds and derivatives, involves the use of different
rules to compute the way the days go by.
In some countries, like in Brazil, several financial instrument only pay interest for business days along their life cycle.
Therefore, having a way to compute the number of business days between 2 dates is quite useful to price the financial instruments properly.
It is necessary the holidays which occur between the 2 dates, to compute the business days and they are intrinsically related to counties and local markets.
In Brazil, [ANBIMA](http://portal.anbima.com.br/Pages/home.aspx) prepares a file with a list of holidays up to the year of 2078 which is largely used by market practioners for pricing financial instruments.
<!-- Usually you have a list with the holidays and all you want
is to find out the number of business days between two dates, nothing more. 
It is necessary for pricing properly the financial instrument. -->
Several financial libraries compute the holidays, giving no option to users set it by their own.
Furtherly, the financial calendar is usually a small feature of a huge library, as [quantlib](http://quantlib.org/index.shtml), for example, and some users, including myself, don't want to put a hand in such a huge library only to use the financial calendar.

**bizdays** is a pure Python module relying on its simplicity and the power of Python's batteries.
bizdays computes business days between two dates and other collateral effects, like adjust a given date for the next or previous business day, check whether a date is a business day, creates generators of business days sequences, and so forth.
bizdays is a module without further dependencies, what makes it appropriated for small implementations.

