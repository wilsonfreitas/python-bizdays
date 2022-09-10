[![Downloads](https://img.shields.io/pypi/dm/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)
[![Latest Version](https://img.shields.io/pypi/v/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/bizdays.svg)](https://pypi.python.org/pypi/bizdays/)

# [python-bizdays](http://wilsonfreitas.github.io/python-bizdays/)

In several countries and markets, the accountability of the price of a financial
instrument, mainly bonds and derivatives, involves the use of different rules to
compute the way the days go by.
In Brazil, several financial instruments pay interest according to the business
days along their life cycle.
So, having a way to compute the number of business days between 2 dates is
fairly useful to price financial instruments.
**bizdays** was created to make it easier.

**bizdays** computes business days between two dates based on the definition of
nonworking days (usually holidays and weekends).
It also computes other collateral effects like adjust dates for the next or
previous business day, check whether a date is a business day, create sequences
of business days, and much more.

Several financial libraries compute the holidays, giving no option to users set
it by their own.
Furtherly, the financial calendar is usually a small feature of a huge library,
as quantlib, for example, and some users, including myself, don't want to put a
hand in such a huge library only to use the financial calendar.

**bizdays** is a pure Python module without strong dependencies,
what makes it appropriated for small projects.

