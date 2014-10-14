
import os
import re
from datetime import datetime, date, timedelta
from itertools import izip, cycle

D1 = timedelta(1)

def datehandler(func):
    def handler(self, dt, *args):
        return func(self, Date(dt).date, *args)
    return handler


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


class DateIndex(object):
    def __init__(self, holidays, startdate, enddate, weekdays):
        self._index = {}
        self._bizdays = []
        self._years = {}
        self.startdate = Date(startdate).date
        self.enddate = Date(enddate).date
        self.weekdays = weekdays
        self.holidays = [Date(d).date for d in holidays]
        dt = self.startdate
        w = c = 1
        while dt <= self.enddate:
            is_hol = dt in self.holidays or dt.weekday() in weekdays
            self._index[dt] = (w, c, is_hol)
            c += 1
            if not is_hol:
                w += 1
                self._bizdays.append(dt)
            col = self._years.get(dt.year, [])
            col.append((dt, dt.month, dt.weekday(), is_hol, c))
            self._years[dt.year] = col
            dt = dt + D1
    
    @datehandler
    def _getpos(self, dt):
        return self._index[dt][0] - 1
        
    
    @datehandler
    def offset(self, dt, n):
        if not self._index[dt][2]:
            pos = self._getpos(dt) + n
            return self._bizdays[pos]
        else:
            raise ValueError('Cannot offset a nonworking day: ' + dt.isoformat())
    
    @datehandler
    def following(self, dt):
        if not self._index[dt][2]:
            return dt
        else:
            return self.following(dt + D1)
    
    @datehandler
    def preceding(self, dt):
        if not self._index[dt][2]:
            return dt
        else:
            return self.preceding(dt - D1)
    
    def seq(self, dt1, dt2):
        dt1 = Date(dt1).date
        dt2 = Date(dt2).date
        if self._index[dt1][2]:
            raise ValueError('Cannot start a sequence of working days with a nonworking day: ' + dt1.isoformat())
        if self._index[dt2][2]:
            raise ValueError('Cannot end a sequence of working days with a nonworking day: ' + dt2.isoformat())
        pos1 = self._getpos(dt1)
        pos2 = self._getpos(dt2) + 1
        return self._bizdays[pos1:pos2]
    
    @datehandler
    def get(self, dt):
        return self._index[dt]
    
    def getnthday(self, n, year, month=None):
        n = n - 1 if n > 0 else n
        if month:
            col = [d[0] for d in self._years[year] if d[1] == month]
            return col[n]
        else:
            return self._years[year][n][0]
    
    def getnthweekday(self, n, weekday, year, month=None):
        n = n - 1 if n > 0 else n
        weekdays = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
        if month:
            col = [d[0] for d in self._years[year] if weekdays[d[2]] == weekday and d[1] == month]
        else:
            col = [d[0] for d in self._years[year] if weekdays[d[2]] == weekday]
        return col[n]
    
    def get_closestweekday_to_nthday(self, n, weekday, year, month=None):
        n = n - 1 if n > 0 else n
        weekdays = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
        if month:
            nth_pos = [d[4] for d in self._years[year] if d[1] == month][n]
            col = [(d[0], abs(d[4]-nth_pos)) for d in self._years[year] if weekdays[d[2]] == weekday and d[1] == month]
            v, m = col[0]
            for i,j in col:
                v = i if j < m else v
                m = j if j < m else m
            return v
        else:
            nth_pos = [d[4] for d in self._years[year]][n]
            col = [(d[0], abs(d[4]-nth_pos)) for d in self._years[year] if weekdays[d[2]] == weekday]
            v, m = col[0]
            for i,j in col:
                v = i if j < m else v
                m = j if j < m else m
            return v
    
    def getnthbizday(self, n, year, month=None):
        n = n - 1 if n > 0 else n
        if month:
            col = [d[0] for d in self._years[year] if not d[3] and d[1] == month]
        else:
            col = [d[0] for d in self._years[year] if not d[3]]
        return col[n]
    
    def getnthbizweekday(self, n, weekday, year, month=None):
        n = n - 1 if n > 0 else n
        weekdays = ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')
        if month:
            col = [d[0] for d in self._years[year] if not d[3] and weekdays[d[2]] == weekday and d[1] == month]
        else:
            col = [d[0] for d in self._years[year] if not d[3] and weekdays[d[2]] == weekday]
        return col[n]
    
    # def getnth(self, ds1, prep=None, ds2=None, year, month):
    #     weekdays = ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')
    #     nth, dsp = ds1
    #     nth = int(nth[:-2])
    #     if prep:
    #         nth2, dsp2 = ds2
    #         nth2 = int(nth2[:-2])
    #         if dsp2 in weekdays:
    #             dt = self.getnthweekday(nth2, dsp2, year, month)
    #         else:
    #             dt = self.getnthday(nth2, year, month)
    #         if prep == 'after':
    #             pass
    #         else:
    #             pass
    #     else:
    #         if dsp in weekdays:
    #             return self.getnthweekday(nth, dsp, year, month)
    #         else:
    #             return self.getnthday(nth, year, month)
    
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
    
    def getnthday(self, nth, year, month=None, iso=False, adjust=None):
        dt = self._index.getnthday(nth, year, month)
        if adjust == 'next':
            dt = self.__adjust_next(dt)
        elif adjust == 'previous':
            dt = self.__adjust_previous(dt)
        else:
            dt = Date(dt)
        return dt.date if not iso else str(dt)
    
    def getnthweekday(self, nth, weekday, year, month=None, iso=False, adjust=None):
        dt = self._index.getnthweekday(nth, weekday, year, month)
        if adjust == 'next':
            dt = self.__adjust_next(dt)
        elif adjust == 'previous':
            dt = self.__adjust_previous(dt)
        else:
            dt = Date(dt)
        return dt.date if not iso else str(dt)
    
    def get_closestweekday_to_nthday(self, nth, weekday, year, month=None, iso=False, adjust=None):
        dt = self._index.get_closestweekday_to_nthday(nth, weekday, year, month)
        if adjust == 'next':
            dt = self.__adjust_next(dt)
        elif adjust == 'previous':
            dt = self.__adjust_previous(dt)
        else:
            dt = Date(dt)
        return dt.date if not iso else str(dt)
    
    def get_nth_offset_nthday(self, nth, offset, year, month=None, iso=False, adjust=None):
        dt = self._index.getnthday(nth, year, month)
        if adjust == 'next':
            dt = self.__adjust_next(dt)
        elif adjust == 'previous':
            dt = self.__adjust_previous(dt)
        else:
            dt = Date(dt)
        dt = self.offset(dt, offset)
        return dt.date if not iso else str(dt)
    
    def getnthbizday(self, nth, year, month=None, iso=False):
        dt = self._index.getnthbizday(nth, year, month)
        dt = Date(dt)
        return dt.date if not iso else str(dt)
    
    def getnthbizweekday(self, nth, weekday, year, month=None, iso=False):
        dt = self._index.getnthbizweekday(nth, weekday, year, month)
        dt = Date(dt)
        return dt.date if not iso else str(dt)
    
    @classmethod
    def load(cls, fname):
        if not os.path.exists(fname):
            raise Exception('Invalid calendar specification: \
            file not found (%s)' % fname)
        name = os.path.split(fname)[-1]
        if name.endswith('.cal'):
            name = name.replace('.cal', '')
        else:
            name = None
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
        return Calendar(_holidays, weekdays=_nonwork_weekdays, name=name)
    
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


def isseq(seq):
    if type(seq) in (str, unicode):
        return False
    try:
        iter(seq)
    except:
        return False
    else:
        return True

class VectorizedOps(object):
    def __init__(self, calendar):
        self.cal = calendar
    
    def isbizday(self, dates):
        return (self.cal.isbizday(dt) for dt in dates)
    
    def bizdays(self, dates_from, dates_to):
        if not isseq(dates_from):
            dates_from = [dates_from]
        if not isseq(dates_to):
            dates_to = [dates_to]
        if len(dates_from) < len(dates_to):
            dates_from = cycle(dates_from)
        else:
            dates_to = cycle(dates_to)
        return (self.cal.bizdays(_from, _to) for _from, _to in izip(dates_from, dates_to))
    
    def adjust_next(self, dates, iso=False):
        if not isseq(dates):
            dates = [dates]
        return ( self.cal.adjust_next(dt, iso=iso) for dt in dates )
    
    def adjust_previous(self, dates, iso=False):
        if not isseq(dates):
            dates = [dates]
        return ( self.cal.adjust_previous(dt, iso=iso) for dt in dates )
    
    def offset(self, dates, ns, iso=False):
        if not isseq(dates):
            dates = [dates]
        if not isseq(ns):
            ns = [ns]
        if len(dates) < len(ns):
            dates = cycle(dates)
        else:
            ns = cycle(ns)
        return (self.cal.offset(dt, n, iso=iso) for dt, n in izip(dates, ns))
