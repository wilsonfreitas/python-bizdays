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
    Date
    DateIndex
'''

import os
from datetime import datetime, date, timedelta
import re

class DateIndex(object):
    def __init__(self, holidays, startdate, enddate, weekdays):
        self._index = {}
        self.startdate = Date(startdate).date
        self.enddate = Date(enddate).date
        self.weekdays = weekdays
        self.holidays = [d.date for d in holidays]
        d1 = timedelta(1)
        dt = self.startdate
        w = c = 1
        while dt <= self.enddate:
            is_hol = dt in self.holidays or dt.weekday() in weekdays
            self._index[dt] = (w, c, is_hol)
            c += 1
            if not is_hol:
                w += 1
            dt = dt + d1
    
    def get(self, dt):
        dt = Date(dt)
        return self._index[dt.date]
    
    def __getitem__(self, dt):
        return self.get(dt)


class Date(object):
    def __init__(self, d=None, format='%Y-%m-%d'):
        d = d if d else date.today()
        if type(d) in (str, unicode):
            d = datetime.strptime(d, format).date()
        elif type(d) is datetime:
            d = d.date()
        elif type(d) is Date:
            d = d.date
        elif type(d) is date:
            pass
        else:
            raise ValueError()
        self.date = d
    
    def format(self, fmts='%Y-%m-%d'):
        return datetime.strftime(self.date, fmts)
    
    def __cmp__(self, other):
        return cmp(self.date, other.date)
    
    def __eq__(self, other):
        return self.date == other.date
    
    def __repr__(self):
        return self.format()
    
    __str__ = __repr__


class Calendar(object):
    ''' Calendar class to compute business days accordingly a list of holidays.
    '''
    _weekdays = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
    def __init__(self, holidays=[], weekdays=[], startdate='1970-01-01', enddate='2071-01-01', name=None,
                       adjust_from='next', adjust_to='previous'):
        self.name = name
        self._holidays = [Date(d) for d in holidays]
        self._nonwork_weekdays = [self._weekdays.index(wd) for wd in weekdays]
        if len(self._holidays):
            self._startdate = min(self._holidays)
            self._enddate = max(self._holidays)
        else:
            self._startdate = Date(startdate)
            self._enddate = Date(enddate)
        self._index = DateIndex(self._holidays, self._startdate, self._enddate, self._nonwork_weekdays)
    
    def __get_weekdays(self):
        return tuple( self._weekdays[nwd] for nwd in self._nonwork_weekdays )
    weekdays = property(__get_weekdays)
    
    def __get_startdate(self):
        return self._startdate.date
    startdate = property(__get_startdate)
    
    def __get_enddate(self):
        return self._enddate.date
    enddate = property(__get_enddate)
    
    def __get_holidays(self):
        return [d.date for d in self._holidays]
    holidays = property(__get_holidays)
    
    def __get_index(self):
        return self._index
    index = property(__get_index)
    
    def bizdays(self, date_from, date_to):
        '''Returns the number of business days between 2 dates. 
        dates is a tuple with 2 strings ISO-formated dates (%%Y-%%m-%%d).'''
        d1 = self.__adjust_next(date_from)
        d2 = self.__adjust_previous(date_to)
        if d1 > d2:
            raise ValueError("The first date must be before the second.")
        return self._index[d2][0] - self._index[d1][0]
    
    def isbizday(self, dt):
        '''Returns True whether dt is a business day or False otherwise.
        dt is a string ISO-formated date (%%Y-%%m-%%d).'''
        return not self._index[dt][2]
    
    def __adjust_next(self, dt):
        d1 = timedelta(1)
        dt = Date(dt).date
        while self._index[dt][2]:
            dt = dt + d1
        return Date(dt)
        
    def adjust_next(self, dt):
        """Returns the next business day whether the passed date isn't a
        business day or returns the given date.
        dt is a string ISO-formated date (%%Y-%%m-%%d).
        """
        return self.__adjust_next(dt).date
    
    def __adjust_previous(self, dt):
        d1 = timedelta(1)
        dt = Date(dt).date
        while self._index[dt][2]:
            dt = dt - d1
        return Date(dt)
    
    def adjust_previous(self, dt):
        """Returns the first business day before the passed date whether
        the given date isn't a business day or returns the given date.
        dt is a string ISO-formated date (%%Y-%%m-%%d).
        """
        return self.__adjust_previous(dt).date
    
    def seq(self, date_from, date_to):
        '''Returns a sequence generator which generates business days between
        the 2 given dates.
        dates is a tuple with 2 strings ISO-formated dates (%%Y-%%m-%%d).
        '''
        _from, _to = Date(date_from), Date(date_to)
        d1 = timedelta(1)
        if _from > _to:
            raise ValueError("The first date must be before the second.")
        _from = self.__adjust_next(_from)
        while _from <= _to:
            yield _from.date
            _from = self.__adjust_next(_from.date + d1)
    
    def offset(self, dt, n):    
        """
        Offsets the given date by n days
        """
        dt = Date(dt)
        if n >= 0:
            d1 = timedelta(1)
            adjust = lambda d: self.__adjust_next(d)
            dt = adjust(dt)
        else:
            d1 = timedelta(-1)
            adjust = lambda d: self.__adjust_previous(d)
            dt = adjust(dt)
            n = abs(n)
        i = 0
        while i < n:
            dt.date += d1
            dt = adjust(dt)
            i += 1
        return dt.date
    
    @classmethod
    def load(cls, fname):
        if not os.path.exists(fname):
            raise Exception('Invalid calendar specification: \
            file not found (%s)' % fname)
        w = '|'.join(cls._weekdays)
        _holidays = []
        _nonwork_weekdays = []
        with open(fname) as fcal:
            for cal_reg in fcal:
                cal_reg = cal_reg.strip()
                if cal_reg is '': continue
                if re.match('^%s$' % w, cal_reg):
                    _nonwork_weekdays.append(cal_reg)
                else:
                    _holidays.append(Date(cal_reg))
        return Calendar(_holidays, weekdays=_nonwork_weekdays)

    @staticmethod
    def load_holidays(fname):
        if not os.path.exists(fname):
            raise Exception('Invalid calendar specification: \
            file not found (%s)' % fname)
        _holidays = []
        with open(fname) as fcal:
            for cal_reg in fcal:
                cal_reg = cal_reg.strip()
                if cal_reg is '': continue
                _holidays.append(Date(cal_reg).date)
        return _holidays
    
    def __eq__(self, other):
        return self.startdate == other.startdate and \
            self.enddate == other.enddate and \
            self._cal_spec == other._cal_spec


