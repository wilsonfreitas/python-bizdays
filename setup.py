#!/usr/bin/env python

from setuptools import setup

with open('SITE.md', 'r') as fh:
    long_description = fh.read()

setup(name='bizdays',
      version='0.3.0',
      py_modules=['bizdays'],
      author='Wilson Freitas',
      author_email='wilson.freitas@gmail.com',
      description='Functions to handle business days calculations',
      url='https://github.com/wilsonfreitas/bizdays',
      keywords='business days, finance, calendar, bizdays',
      long_description=long_description,
      long_description_content_type='text/markdown',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Topic :: Utilities',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
          'Operating System :: OS Independent'
      ],
      python_requires='>=2.7'
      )
