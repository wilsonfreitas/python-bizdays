
import os
import re
from datetime import datetime, date, timedelta
from itertools import izip, cycle

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
    _weekdays = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
    def __init__(self, holidays=[], weekdays=[], startdate='1970-01-01', enddate='2071-01-01', name=None,
                       adjust_from='next', adjust_to='previous'):
        self.name = name
        self._holidays = [Date(d) for d in holidays]
        self._nonwork_weekdays = [[w.lower() for w in self._weekdays].index(wd.lower()) for wd in weekdays]
        if len(self._holidays):
            self._startdate = min(self._holidays)
            self._enddate = max(self._holidays)
        else:
            self._startdate = Date(startdate)
            self._enddate = Date(enddate)
        self._index = DateIndex(self._holidays, self._startdate, self._enddate, self._nonwork_weekdays)
        self.vec = VectorizedOps(self)
        self.__adjust_from = self.__adjust_next if adjust_from == 'next' else self.__adjust_previous
        self.__adjust_to = self.__adjust_previous if adjust_to == 'previous' else self.__adjust_next
    
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
        d1 = self.__adjust_from(date_from)
        d2 = self.__adjust_to(date_to)
        if d1 > d2:
            raise ValueError("The first date must be before the second.")
        return self._index[d2][0] - self._index[d1][0]
    
    def isbizday(self, dt):
        return not self._index[dt][2]
    
    def __adjust_next(self, dt):
        d1 = timedelta(1)
        dt = Date(dt).date
        while self._index[dt][2]:
            dt = dt + d1
        return Date(dt)
        
    def adjust_next(self, dt, iso=False):
        dt = self.__adjust_next(dt)
        return dt.date if not iso else str(dt)
    
    def __adjust_previous(self, dt):
        d1 = timedelta(1)
        dt = Date(dt).date
        while self._index[dt][2]:
            dt = dt - d1
        return Date(dt)
    
    def adjust_previous(self, dt, iso=False):
        dt = self.__adjust_previous(dt)
        return dt.date if not iso else str(dt)
    
    def seq(self, date_from, date_to, iso=False):
        _from = self.__adjust_from(date_from)
        _to = self.__adjust_to(date_to)
        if _from > _to:
            raise ValueError("The first date must be before the second.")
        d1 = timedelta(1)
        while _from <= _to:
            yield _from.date if not iso else str(_from)
            _from = self.__adjust_next(_from.date + d1)
    
    def offset(self, dt, n, iso=False):
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
        return dt.date if not iso else str(dt)
    
    @classmethod
    def load(cls, fname):
        if not os.path.exists(fname):
            raise Exception('Invalid calendar specification: \
            file not found (%s)' % fname)
        w = '|'.join( w.lower() for w in cls._weekdays )
        wre = '^%s$' % w
        _holidays = []
        _nonwork_weekdays = []
        with open(fname) as fcal:
            for cal_reg in fcal:
                cal_reg = cal_reg.strip()
                if cal_reg is '': continue
                if re.match(wre, cal_reg.lower()):
                    _nonwork_weekdays.append(cal_reg)
                elif re.match(r'^\d\d\d\d-\d\d-\d\d$', cal_reg):
                    _holidays.append(Date(cal_reg))
        return Calendar(_holidays, weekdays=_nonwork_weekdays)

    @staticmethod
    def load_holidays(fname, format='%Y-%m-%d'):
        if not os.path.exists(fname):
            raise Exception('Invalid calendar specification: \
            file not found (%s)' % fname)
        _holidays = []
        with open(fname) as fcal:
            for cal_reg in fcal:
                cal_reg = cal_reg.strip()
                if cal_reg is '': continue
                _holidays.append(Date(cal_reg, format=format).date)
        return _holidays
    
    def __eq__(self, other):
        return self.startdate == other.startdate and \
            self.enddate == other.enddate and \
            self._cal_spec == other._cal_spec
    
    def __str__(self):
        return '''Calendar: {0}
Start: {1}
End: {2}
Holidays: {3}'''.format(self.name, self.startdate, self.enddate, len(self._holidays))
    
    __repr__ = __str__


class VectorizedOps(object):
    def __init__(self, calendar):
        self.cal = calendar
    
    def isbizday(self, dates):
        return (self.cal.isbizday(dt) for dt in dates)
    
    def bizdays(self, dates_from, dates_to):
        if type(dates_from) in (str, unicode):
            dates_from = [dates_from]
        if type(dates_to) in (str, unicode):
            dates_to = [dates_to]
        if len(dates_from) < len(dates_to):
            dates_from = cycle(dates_from)
        else:
            dates_to = cycle(dates_to)
        return (self.cal.bizdays(_from, _to) for _from, _to in izip(dates_from, dates_to))
    
    def adjust_next(self, dates, iso=False):
        return ( self.cal.adjust_next(dt, iso=iso) for dt in dates )
    
    def adjust_previous(self, dates, iso=False):
        return ( self.cal.adjust_previous(dt, iso=iso) for dt in dates )
    
    def offset(self, dates, ns, iso=False):
        if type(dates) in (str, unicode):
            dates = [dates]
        if type(ns) in (int, long):
            ns = [ns]
        if len(dates) < len(ns):
            dates = cycle(dates)
        else:
            ns = cycle(ns)
        return (self.cal.offset(dt, n, iso=iso) for dt, n in izip(dates, ns))
