#!/usr/bin/env python

from distutils.core import setup

setup(name="bizdays",
      version="0.1.1",
      py_modules=['bizdays'],
      author='Wilson Freitas',
      author_email='wilson.freitas@gmail.com',
      description='A quick and dirty implementation for business days calculations.',
      url='https://github.com/wilsonfreitas/bizdays',
      license='MIT',
      long_description='''\
In several countries and markets, to account the value of financial
instruments, mainly bonds and derivatives, it is necessary the use of different
rules to compute the way the days go by. Those rules are related to holidays
which are intrinsically related to counties and local markets. Usually you have
a list with the holidays and all you want is to find out the number of business
days between two dates, nothing more. It is necessary for pricing properly the
financial instrument. bizdays was implemented to do that, compute business days
between two dates and other collateral effects like adjust a given date for the
next or previous business day, and so forth. bizdays is a module without
dependencies, what makes it appropriate for simple implementations.
''', )

