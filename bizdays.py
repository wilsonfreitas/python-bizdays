'''Business days calculations and utilities for a given calendar specification.
The calendar specification is a .cal file containing the weekdays to be 
considered as non-business days and a iso-formated list of dates representing
holidays. It follows an example::

	Saturday
	Sunday
	2001-01-01
	2002-01-01
	2013-01-01

Classes:
	Calendar
	CalendarSpec
Functions:
	create_date_index
'''

import os
from datetime import datetime, date, timedelta
import re

def create_date_index(holidays, startdate, enddate, weekdays):
	""" This function returns the date index.
	The date index accumulates the amount of business days.
	This can be used to speed up the amount of business days between 2 dates.
	Once each date is index the amount of business days between 2 dates is
	fairly obtained by the subtraction of the respective index value for 
	each date."""
	_index = {}
	d1 = timedelta(1)
	dt = startdate
	w = c = 1
	while dt <= enddate:
		is_hol = dt in holidays or dt.weekday() in weekdays
		_index[dt] = (w, c, is_hol)
		c += 1
		if not is_hol:
			w += 1
		dt += d1
	return _index


class Calendar(object):
	''' Calendar class to compute business days accordingly a list of holidays.
	'''
	_weekdays = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
		 'Saturday', 'Sunday')
	def __init__(self, holidays=None, startdate=None, enddate=None, weekdays=('Saturday', 'Sunday')):
		self._holidays = holidays or []
		self._nonwork_weekdays = [self._weekdays.index(wd) for wd in weekdays]
		if startdate:
			self._startdate = datetime.strptime(startdate, '%Y-%m-%d').date()
		else:
			self._startdate = date(self._holidays[0].year, 1, 1)
		if enddate:
			self._enddate = datetime.strptime(enddate, '%Y-%m-%d').date()
		else:
			self._enddate = date(self._holidays[-1].year, 12, 31)
		
		self._index = create_date_index(self._holidays, self._startdate, 
			self._enddate, self._nonwork_weekdays)
	
	def __get_weekdays(self):
		return tuple( self._weekdays[nwd] for nwd in self._nonwork_weekdays )
	weekdays = property(__get_weekdays)
	
	def __get_startdate(self):
		return self._startdate
	startdate = property(__get_startdate)
	
	def __get_enddate(self):
		return self._enddate
	enddate = property(__get_enddate)
	
	def __get_holidays(self):
		return self._holidays
	holidays = property(__get_holidays)
	
	def __get_index(self):
		return self._index
	index = property(__get_index)
	
	def bizdays(self, dates):
		'''Returns the number of business days between 2 dates. 
		dates is a tuple with 2 strings ISO-formated dates (%%Y-%%m-%%d).'''
		d1, d2 = dates
		d1 = datetime.strptime(d1, '%Y-%m-%d').date()
		d1 = self.__adjust_next(d1)
		d2 = datetime.strptime(d2, '%Y-%m-%d').date()
		d2 = self.__adjust_previous(d2)
		if d1 > d2:
			raise ValueError("The first date must be before the second.")
		return self._index[d2][0] - self._index[d1][0]
	
	def currentdays(self, dates):
		'''Returns the number of current days between 2 dates.
		It simply subtracts dates and return the amount of days in timedelta.
		dates is a tuple with 2 strings ISO-formated dates (%%Y-%%m-%%d).
		'''
		d1, d2 = dates
		d1 = datetime.strptime(d1, '%Y-%m-%d').date()
		d2 = datetime.strptime(d2, '%Y-%m-%d').date()
		if d1 > d2:
			raise ValueError("The first date must be before the second.")
		return (d2 - d1).days
	
	def isbizday(self, dt):
		'''Returns True whether dt is a business day or False otherwise.
		dt is a string ISO-formated date (%%Y-%%m-%%d).'''
		dt = datetime.strptime(dt, '%Y-%m-%d').date()
		return not self._index[dt][2]
	
	def __adjust_next(self, dt):
		d1 = timedelta(1)
		while self._index[dt][2]:
			dt += d1
		return dt
		
	def adjust_next(self, dt):
		"""Returns the next business day whether the passed date isn't a
		business day or returns the given date.
		dt is a string ISO-formated date (%%Y-%%m-%%d).
		"""
		dt = datetime.strptime(dt, '%Y-%m-%d').date()
		return self.__adjust_next(dt).isoformat()
	
	def __adjust_previous(self, dt):
		d1 = timedelta(1)
		while self._index[dt][2]:
			dt -= d1
		return dt
	
	def adjust_previous(self, dt):
		"""Returns the first business day before the passed date whether
		the given date isn't a business day or returns the given date.
		dt is a string ISO-formated date (%%Y-%%m-%%d).
		"""
		dt = datetime.strptime(dt, '%Y-%m-%d').date()
		return self.__adjust_previous(dt).isoformat()
	
	def seq(self, dates):
		'''Returns a sequence generator which generates business days between
		the 2 given dates.
		dates is a tuple with 2 strings ISO-formated dates (%%Y-%%m-%%d).
		'''
		_from, _to = dates
		d1 = timedelta(1)
		_from = datetime.strptime(_from, '%Y-%m-%d').date()
		_to = datetime.strptime(_to, '%Y-%m-%d').date()
		if _from > _to:
			raise ValueError("The first date must be before the second.")
		_from = self.__adjust_next(_from)
		while _from <= _to:
			yield _from.isoformat()
			_from = self.__adjust_next(_from + d1)

	def offset(self, dt, n):	
		"""
		Offsets the given date by n days
		"""
		if n >= 0:
			d1 = timedelta(1)
			adjust = lambda d: self.__adjust_next(d)
			dt = adjust(datetime.strptime(dt, '%Y-%m-%d').date())
		else:
			d1 = timedelta(-1)
			adjust = lambda d: self.__adjust_previous(d)
			dt = adjust(datetime.strptime(dt, '%Y-%m-%d').date())
			n = abs(n)
		i = 0
		while i < n:
			dt += d1
			dt = adjust(dt)
			i += 1
		return dt.isoformat()

class CalendarSpec(Calendar):
	''' CalendarSpec class to compute business days accordingly a given
	calendar's specification. The specification has the weekdays which aren't
	business days (usually known as weekend) and a list of holidays
	(or non-business days).
	'''
	def __init__(self, cal, startdate=None, enddate=None):
		fname = cal + '.cal'
		if not os.path.exists(fname):
			raise Exception('Invalid calendar specification: \
			file not found (%s)' % fname)
		self._cal_spec = cal
		fcal = open(fname)
		w = '|'.join(self._weekdays)
		_holidays = []
		_nonwork_weekdays = []
		for cal_reg in fcal:
			cal_reg = cal_reg.strip()
			if cal_reg is '': continue
			m = re.match('^%s$' % w, cal_reg)
			if m:
				_nonwork_weekdays.append(cal_reg)
				# _nonwork_weekdays.append(self._weekdays.index(cal_reg))
			else:
				dt = datetime.strptime(cal_reg, '%Y-%m-%d').date()
				_holidays.append(dt)
		fcal.close()
		super(CalendarSpec, self).__init__(_holidays, startdate, enddate, _nonwork_weekdays)
	
	def __eq__(self, other):
		return self.startdate == other.startdate and \
			self.enddate == other.enddate and \
			self._cal_spec == other._cal_spec
	
	def __get_name(self):
		return self._cal_spec
	name = property(__get_name)
	

