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
'''

import os
from datetime import datetime, date, timedelta
import re

class Calendar(object):
	''' Calendar class to compute business days accordingly a given
	calendar specification. The specification has the weekdays which aren't
	business days and a list of holidays (or non-business days).
	'''
	_weekdays = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
		 'Saturday', 'Sunday')
	def __init__(self, cal):
		self._read_cal(cal)
		self._startdate = date(self._holidays[0].year, 1, 1)
		self._enddate = date(self._holidays[-1].year, 12, 31)
		
		self._index = {}
		d1 = timedelta(1)
		dt = self._startdate
		w = c = 1
		while dt <= self._enddate:
			is_hol = dt in self._holidays or dt.weekday() in \
				self._nonwork_weekdays
			self._index[dt] = (w, c, is_hol)
			c += 1
			if not is_hol:
				w += 1
			dt += d1
	
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
	
	def __eq__(self, other):
		return self.startdate == other.startdate and \
			self.enddate == other.enddate and \
			self._cal_spec == other._cal_spec
	
	def _read_cal(self, cal):
		fname = cal + '.cal'
		if not os.path.exists(fname):
			raise Exception('Invalid calendar specification: \
			file not found (%s)' % fname)
		self._cal_spec = cal
		fcal = open(fname)
		w = '|'.join(self._weekdays)
		self._holidays = []
		self._nonwork_weekdays = []
		for cal_reg in fcal:
			cal_reg = cal_reg.strip()
			if cal_reg is '': continue
			m = re.match('^%s$' % w, cal_reg)
			if m:
				self._nonwork_weekdays.append(self._weekdays.index(cal_reg))
			else:
				dt = datetime.strptime(cal_reg, '%Y-%m-%d').date()
				self._holidays.append(dt)
		fcal.close()
	
	def bizdays(self, dates):
		d1, d2 = dates
		d1 = datetime.strptime(d1, '%Y-%m-%d').date()
		d1 = self.__next_bizday(d1)
		d2 = datetime.strptime(d2, '%Y-%m-%d').date()
		d2 = self.__previous_bizday(d2)
		return self._index[d2][0] - self._index[d1][0]
	
	def currentdays(self, dates):
		d1, d2 = dates
		d1 = datetime.strptime(d1, '%Y-%m-%d').date()
		d2 = datetime.strptime(d2, '%Y-%m-%d').date()
		return (d2 - d1).days
	
	def isbizday(self, dt):
		dt = datetime.strptime(dt, '%Y-%m-%d').date()
		return not self._index[dt][2]
	
	def __next_bizday(self, dt):
		d1 = timedelta(1)
		while self._index[dt][2]:
			dt += d1
		return dt
		
	def adjust_next(self, dt):
		"""Returns the next business day whether the passed date isn't a
		business day or returns the given date"""
		dt = datetime.strptime(dt, '%Y-%m-%d').date()
		return self.__next_bizday(dt).isoformat()
	
	def __previous_bizday(self, dt):
		d1 = timedelta(1)
		while self._index[dt][2]:
			dt -= d1
		return dt
	
	def adjust_previous(self, dt):
		"""Returns the first business day before the passed date whether
		the given date isn't a business day or returns the given date"""
		dt = datetime.strptime(dt, '%Y-%m-%d').date()
		return self.__previous_bizday(dt).isoformat()
	
	def seq(self, _from, _to):
		d1 = timedelta(1)
		_from = self.__next_bizday(datetime.strptime(_from, '%Y-%m-%d').date())
		_to = datetime.strptime(_to, '%Y-%m-%d').date()
		while _from <= _to:
			yield _from.isoformat()
			_from = self.__next_bizday(_from + d1)


