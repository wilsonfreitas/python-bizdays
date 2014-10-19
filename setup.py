#!/usr/bin/env python

from distutils.core import setup

setup(name="bizdays",
      version="v0.2.0",
      py_modules=['bizdays'],
      author='Wilson Freitas',
      author_email='wilson.freitas@gmail.com',
      description='Functions to handle business days calculations',
      url='https://github.com/wilsonfreitas/bizdays',
      license='MIT',
      keywords='business days, finance, calendar, bizdays',
      long_description='''\
      
**That version has been completely rewritten and many functions have been redesigned to signature differen from the
earlier version.**

In several countries and markets, to account the value of financial instruments, mainly bonds and derivatives, it is
necessary the use of different rules to compute the way the days go by. Those rules are related to holidays which are
intrinsically related to counties and local markets. Usually you have a list with the holidays and all you want is to
find out the number of business days between two dates, nothing more. It is necessary for pricing properly the
financial instrument. bizdays was implemented to do that, compute business days between two dates and other collateral
effects like adjust a given date for the next or previous business day, and so forth. bizdays is a module without
dependencies, what makes it appropriate for simple implementations.

bizdays is a small set of functions to help with calculations which make use of business days. It works based on a list
of holidays which is passed as an argument. Its interface is simple and flexible operating on vector of dates. bizdays
can be fairly used for fixed income calculations. Many countries make intense use of business days to price financial
instruments, like bonds and derivatives.

Examples::

    >>> from bizdays import Calendar, load_holidays
    >>> holidays = load_holidays('Brazil.txt') # Brazilian financial market holidays 
    >>> cal = Calendar(holidays, ['Sunday', 'Saturday'], name='Brazil')
    >>> cal
    Calendar: Brazil
    Start: 2000-01-01
    End: 2078-12-25
    Holidays: 948
    
    >>> cal.isbizday('2014-01-12')
    False
    
    >>> cal.isbizday('2014-01-13')
    True
    
    >>> cal.bizdays('2014-01-13', '2015-01-13')
    253
    
    >>> cal.adjust_next('2015-12-25')
    datetime.date(2015, 12, 28)
    
    >>> cal.adjust_next('2015-12-28')
    datetime.date(2015, 12, 28)
    
    >>> cal.adjust_previous('2014-01-01')
    datetime.date(2013, 12, 31)
    
    >>> cal.adjust_previous('2014-01-02')
    datetime.date(2014, 1, 2)
    
    >>> cal.seq('2014-01-02', '2014-01-07')
    <generator object seq at 0x1092b02d0>
    
    >>> list(cal.seq('2014-01-02', '2014-01-07'))
    [datetime.date(2014, 1, 2),
     datetime.date(2014, 1, 3),
     datetime.date(2014, 1, 6),
     datetime.date(2014, 1, 7)]
    
    >>> cal.offset('2014-01-02', 5)
    datetime.date(2014, 1, 9)
    
    >>> cal.getdate('15th day', 2002, 5)
    datetime.date(2002, 5, 15)
    
    >>> cal.getdate('15th bizday', 2002, 5)
    datetime.date(2002, 5, 22)
    
    >>> cal.getdate('last wed', 2002, 5)
    datetime.date(2002, 5, 29)
    
    >>> cal.getdate('first fri before last day ', 2002, 5)
    datetime.date(2002, 5, 24)


''',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Utilities",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Operating System :: OS Independent"
    ],
)

