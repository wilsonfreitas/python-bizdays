from io import StringIO
import os
import re
from datetime import datetime, date, timedelta
from itertools import cycle
from typing import TextIO, Dict

PANDAS_INSTALLED = False

try:
    import pandas as pd
    import numpy as np

    PANDAS_INSTALLED = True

    def isnull(x):
        return pd.isna(x)

    def recseq(gen, typo="DatetimeIndex"):
        g = list(gen)
        if get_option("mode") == "pandas":
            if typo == "DatetimeIndex":
                return pd.DatetimeIndex(g)
            elif typo == "array":
                return np.array(g)
        else:
            return g

    def retdate(dt):
        if get_option("mode.datetype") == "datetime":
            return datetime(dt.year, dt.month, dt.day)
        elif get_option("mode.datetype") == "date":
            return dt
        elif get_option("mode.datetype") == "iso":
            return dt.isoformat()
        elif get_option("mode") == "pandas":
            return pd.to_datetime(dt)
        else:
            return dt

    def return_none():
        if get_option("mode") == "pandas":
            return pd.NA
        else:
            return None

except ImportError:

    def isnull(x):
        return x is None

    def recseq(gen, typo=None):
        return list(gen)

    def retdate(dt):
        if get_option("mode.datetype") == "datetime":
            return datetime(dt.year, dt.month, dt.day)
        elif get_option("mode.datetype") == "date":
            return dt
        elif get_option("mode.datetype") == "iso":
            return dt.isoformat()
        else:
            return dt

    def return_none():
        return None


__all__ = ["get_option", "set_option", "Calendar"]


options = {"mode": "python"}


def get_option(name):
    """gets option value

    Parameters
    ----------
    name : str
        option name

    Returns
    -------
    val : str
        option value
    """
    return options.get(name)


def set_option(name, val):
    """sets option value

    Parameters
    ----------
    name : str
        option name
    val : str
        option value

    Returns
    -------
        No return
    """
    if name == "pandas" and not PANDAS_INSTALLED:
        raise Exception("Cannot set mode pandas: pandas not installed")
    options[name] = val


D1 = timedelta(1)


def isstr(d):
    return isinstance(d, str)


def isseq(seq):
    if isstr(seq):
        return False
    try:
        iter(seq)
    except TypeError:
        return False
    else:
        return True


class DateOutOfRange(Exception):
    pass


def find_date_pos(col, dt):
    beg = 0
    end = len(col)
    while (end - beg) > 1:
        mid = int((end + beg) / 2)
        if dt > col[mid]:
            beg = mid
        elif dt < col[mid]:
            end = mid
        else:
            return mid
    return beg


def __daterangecheck(obj, dt):
    dt = Date(dt).date
    if dt > obj.enddate or dt < obj.startdate:
        raise DateOutOfRange("Given date out of calendar range")
    return dt


def daterangecheck(func):
    def handler(self, dt, *args):
        dt = __daterangecheck(self, dt)
        return func(self, dt, *args)

    return handler


def daterangecheck2(func):
    def handler(self, dt1, dt2, *args):
        dt1 = __daterangecheck(self, dt1)
        dt2 = __daterangecheck(self, dt2)
        return func(self, dt1, dt2, *args)

    return handler


def load_holidays(fname, format="%Y-%m-%d"):
    if not os.path.exists(fname):
        raise Exception(
            "Invalid calendar specification: \
        file not found (%s)"
            % fname
        )
    _holidays = []
    with open(fname) as fcal:
        for cal_reg in fcal:
            cal_reg = cal_reg.strip()
            if cal_reg == "":
                continue
            _holidays.append(Date(cal_reg, format=format).date)
    return _holidays


class DateIndex(object):
    WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

    def __init__(self, holidays, startdate, enddate, weekdays):
        self._index = {}
        self._bizdays = []
        self._days = []
        self._years = {}
        self._weekdays = {}
        self.startdate = Date(startdate).date
        self.enddate = Date(enddate).date
        self.weekdays = weekdays
        self.holidays = [Date(d).date for d in holidays]

        dts = []
        dt = self.startdate
        while dt <= self.enddate:
            dts.append(dt)
            dt = dt + D1

        w = 0
        c = 1
        for dt in dts:
            is_hol = dt in self.holidays or dt.weekday() in weekdays
            if not is_hol:
                w += 1
                self._bizdays.append(dt)
            self._index[dt] = [w, c, is_hol, None]
            c += 1

        max_w = self._index[self.enddate][0]
        w = max_w + 1
        for dt in reversed(dts):
            is_hol = self._index[dt][2]
            if not is_hol:
                w -= 1
            self._index[dt][3] = w

        for dt in dts:
            # ----
            ix = self._index[dt]
            col = self._years.get(dt.year, [])
            _ = (dt, dt.month, dt.weekday(), ix[2], ix[1], ix[0], ix[3])
            col.append(_)
            # col.append((dt, dt.month, dt.weekday(), is_hol, c, w))
            self._years[dt.year] = col
            col = self._weekdays.get(dt.weekday(), [])
            col.append(dt)
            self._weekdays[dt.weekday()] = col
            self._days.append(dt)
            # ----

    @daterangecheck
    def offset(self, dt, n):
        if n > 0:
            pos = self._index[dt][0] - 1 + n
        elif n < 0:
            pos = self._index[dt][3] - 1 + n
        else:
            return dt
        return self._bizdays[pos]

    @daterangecheck
    def following(self, dt):
        if not self._index[dt][2]:
            return dt
        else:
            return self.following(dt + D1)

    @daterangecheck
    def modified_following(self, dt):
        dtx = self.following(dt)
        if dtx.month != dt.month:
            dtx = self.preceding(dt)
        return dtx

    @daterangecheck
    def preceding(self, dt):
        if not self._index[dt][2]:
            return dt
        else:
            return self.preceding(dt - D1)

    @daterangecheck
    def modified_preceding(self, dt):
        dtx = self.preceding(dt)
        if dtx.month != dt.month:
            dtx = self.following(dt)
        return dtx

    @daterangecheck2
    def seq(self, dt1, dt2):
        pos1 = max(self._index[dt1][0], self._index[dt1][3]) - 1
        pos2 = min(self._index[dt2][0], self._index[dt2][3])
        return self._bizdays[pos1:pos2]

    @daterangecheck
    def get(self, dt):
        return self._index[dt]

    def getbizdays(self, year, month=None):
        if month:
            return sum(not d[3] for d in self._years[year] if d[1] == month)
        else:
            return sum(not d[3] for d in self._years[year])

    def getdate(self, expr, year, month=None):
        tok = expr.split()
        if len(tok) == 2:
            n = self._getnth(tok[0])
            if tok[1] == "day":
                return self._getnthday(n, year, month)
            elif tok[1] == "bizday":
                return self._getnthbizday(n, year, month)
            elif tok[1] in self.WEEKDAYS:
                return self._getnthweekday(n, tok[1], year, month)
            else:
                raise ValueError("Invalid day:", tok[1])
        elif len(tok) == 5:
            n = self._getnth(tok[3])
            if tok[4] == "day":
                pos = self._getnthdaypos(n, year, month)
            elif tok[4] == "bizday":
                pos = self._getnthbizdaypos(n, year, month)
            else:
                raise ValueError("Invalid reference day:", tok[4])
            m = {"before": -1, "after": 1}.get(tok[2], 0)
            if not m:
                raise ValueError("Invalid operator:", tok[2])
            n = self._getnthpos(tok[0]) * m
            if tok[1] == "day":
                return self._getnthday_beforeafter(n, pos)
            elif tok[1] == "bizday":
                return self._getnthbizday_beforeafter(n, pos)
            elif tok[1] in self.WEEKDAYS:
                return self._getnthweekday_beforeafter(n, tok[1], pos)
            else:
                raise ValueError("Invalid day:", tok[1])

    def _getnthpos(self, nth):
        if nth == "first":
            return 1
        elif nth == "second":
            return 2
        elif nth == "third":
            return 3
        elif nth == "last":
            return 1
        elif nth[-2:] in ("th", "st", "nd", "rd"):
            return int(nth[:-2])
        else:
            raise ValueError("invalid nth:", nth)

    def _getnth(self, nth):
        if nth == "first":
            return 1
        elif nth == "second":
            return 2
        elif nth == "third":
            return 3
        elif nth == "last":
            return -1
        elif nth[-2:] in ("th", "st", "nd", "rd"):
            return int(nth[:-2])
        else:
            raise ValueError("invalid nth:", nth)

    def _getnthdaypos(self, n, year, month=None):
        n = n - 1 if n > 0 else n
        if month:
            pos = [
                (d[4] - 1, d[5] - 1, d[0], d[6] - 1)
                for d in self._years[year]
                if d[1] == month
            ]
            return pos[n]
        else:
            return (
                self._years[year][n][4] - 1,
                self._years[year][n][5] - 1,
                self._years[year][n][0],
                self._years[year][n][6],
            )

    def _getnthbizdaypos(self, n, year, month=None):
        n = n - 1 if n > 0 else n
        if month:
            col = [
                (d[4] - 1, d[5] - 1, d[0], d[6] - 1)
                for d in self._years[year]
                if not d[3] and d[1] == month
            ]
        else:
            col = [
                (d[4] - 1, d[5] - 1, d[0], d[6] - 1)
                for d in self._years[year]
                if not d[3]
            ]
        return col[n]

    def _getnthweekdaypos(self, n, weekday, year, month=None):
        n = n - 1 if n > 0 else n
        if month:
            col = [
                (d[4] - 1, d[5] - 1, d[0], d[6] - 1)
                for d in self._years[year]
                if self.WEEKDAYS[d[2]] == weekday and d[1] == month
            ]
        else:
            col = [
                (d[4] - 1, d[5] - 1, d[0], d[6] - 1)
                for d in self._years[year]
                if self.WEEKDAYS[d[2]] == weekday
            ]
        return col[n]

    def _getnthday_beforeafter(self, n1, pos):
        pos = pos[0] + n1
        return self._days[pos]

    def _getnthbizday_beforeafter(self, n1, pos):
        if n1 > 0:
            pos = pos[1] + n1
        else:
            pos = pos[3] + n1
        return self._bizdays[pos]

    def _getnthweekday_beforeafter(self, n1, weekday, pos):
        dt = pos[2]
        wday = self.WEEKDAYS.index(weekday)
        pos = find_date_pos(self._weekdays[wday], dt)
        if dt.weekday() != wday:
            n1 = n1 + 1 if n1 < 0 else n1
        return self._weekdays[wday][pos + n1]

    def _getnthday(self, n, year, month=None):
        pos = self._getnthdaypos(n, year, month)[0]
        return self._days[pos]

    def _getnthbizday(self, n, year, month=None):
        pos = self._getnthbizdaypos(n, year, month)[1]
        return self._bizdays[pos]

    def _getnthweekday(self, n, weekday, year, month=None):
        n = n - 1 if n > 0 else n
        if month:
            col = [
                d[0]
                for d in self._years[year]
                if self.WEEKDAYS[d[2]] == weekday and d[1] == month
            ]
        else:
            col = [d[0] for d in self._years[year] if self.WEEKDAYS[d[2]] == weekday]
        return col[n]

    def __getitem__(self, dt):
        return self.get(dt)


class Date(object):
    def __init__(self, d=None, format="%Y-%m-%d"):
        # d = d if d else date.today()
        if isstr(d):
            d = datetime.strptime(d, format).date()
        elif isinstance(d, datetime):
            d = d.date()
        elif isinstance(d, Date):
            d = d.date
        elif isinstance(d, date):
            pass
        elif d is None:
            pass
        else:
            raise ValueError()
        self.date = d

    def format(self, fmts="%Y-%m-%d"):
        return datetime.strftime(self.date, fmts)

    def __gt__(self, other):
        return self.date > other.date

    def __ge__(self, other):
        return self.date >= other.date

    def __lt__(self, other):
        return self.date < other.date

    def __le__(self, other):
        return self.date <= other.date

    def __eq__(self, other):
        return self.date == other.date

    def __repr__(self):
        return self.format()

    __str__ = __repr__


class Calendar(object):
    """
    Calendar class

    Calendar representation where holidays and nonworking weekdays are
    defined.

    Attributes
    ----------

    name : str

    holidays : list of dates

    enddate : date

    startdate : date

    weekdays : list of str

    financial : bool


    Parameters
    ----------
    holidays : list with dates
        Dates can be ISO formated string, datetime.date or datetime.datetime.

    weekdays : list
        A list with weekdays representing nonworking days.

        Accepts: 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                 'Saturday', 'Sunday'

    startdate : str or datetime.date
        Calendar's start date

    enddate : str or datetime.date
        Calendar's end date

    name : str
        Calendar's name

    financial : bool
        Defines a financial calendar
    """

    _weekdays = (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    )

    def __init__(
        self,
        holidays=[],
        weekdays=[],
        startdate=None,
        enddate=None,
        name=None,
        financial=True,
    ):
        self.financial = financial
        self.name = name
        self._holidays = [Date(d) for d in holidays]
        self._nonwork_weekdays = [
            [w[:3].lower() for w in self._weekdays].index(wd[:3].lower())
            for wd in weekdays
        ]
        if len(self._holidays):
            if startdate:
                self._startdate = Date(startdate)
            else:
                self._startdate = min(self._holidays)
            if enddate:
                self._enddate = Date(enddate)
            else:
                self._enddate = max(self._holidays)
        else:
            if startdate:
                self._startdate = Date(startdate)
            else:
                self._startdate = Date("1970-01-01")
            if enddate:
                self._enddate = Date(enddate)
            else:
                self._enddate = Date("2071-01-01")
        self._index = DateIndex(
            self._holidays, self._startdate, self._enddate, self._nonwork_weekdays
        )
        self.vec = VectorizedOps(self)

    def __get_weekdays(self):
        return tuple(self._weekdays[nwd] for nwd in self._nonwork_weekdays)

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

    def bizdays(self, date_from, date_to):
        """
        Calculate the amount of business days between two dates

        Parameters
        ----------

        date_from : datetime.date, datetime.datetime, pandas.Timestamp, str
            Start date

        date_to : datetime.date, datetime.datetime, pandas.Timestamp, str
            End date

        Returns
        -------
        int, list, numpy.ndarray
            The number of business days between date_from and date_to
        """
        if isseq(date_from) or isseq(date_to):
            return recseq(self.vec.bizdays(date_from, date_to), "array")
        else:
            if isnull(date_from) or isnull(date_to):
                return return_none()
            date_from = Date(date_from).date
            date_to = Date(date_to).date
            if date_from > date_to:
                d1, d2 = date_to, date_from
            else:
                d1, d2 = date_from, date_to
            t1 = (self._index[d1][0], self._index[d1][3])
            t2 = (self._index[d2][0], self._index[d2][3])
            i1 = t2[0] - t1[0]
            i2 = t2[1] - t1[1]
            bdays = min(i1, i2)
            adj_vec = int(self._index[d1][2] and self._index[d2][2])
            date_reverse = date_from > date_to
            if date_reverse:
                adj_vec = -adj_vec
                bdays = -bdays
            bdays -= adj_vec
            if self.financial:
                if self._index[d1][2] and self._index[d2][2] and abs(bdays) == 1:
                    return 0
                else:
                    return bdays
            else:
                if date_reverse:
                    return bdays - 1
                else:
                    return bdays + 1

    def isbizday(self, dt):
        """
        Checks if the given dates are business days.

        Parameters
        ----------

        dt : datetime.date, datetime.datetime, pandas.Timestamp, str
            Dates to be checked

        Returns
        -------

        bool, list of bool, array of bool
            Returns True if the given date is a business day and False
            otherwise.
        """
        if isseq(dt):
            return recseq(self.vec.isbizday(dt), "array")
        else:
            if isnull(dt):
                return dt
            else:
                return not self._index[dt][2]

    def __adjust_next(self, dt):
        return Date(self._index.following(dt)).date

    def adjust_next(self, dt):
        """
        Adjusts the given dates to the next business day

        Rolls the given date to the next business day,
        unless it is a business day.

        Parameters
        ----------

        dt : datetime.date, datetime.datetime, pandas.Timestamp, str
            Dates to be adjusted

        Returns
        -------

        datetime.date, datetime.datetime, pandas.Timestamp, str
            return the next business day if the given date is
            not a business day.

        """
        if isseq(dt):
            return recseq(self.vec.adjust_next(dt))
        else:
            if isnull(dt):
                return dt
            return retdate(self.__adjust_next(dt))

    following = adjust_next

    def modified_following(self, dt):
        """
        Adjusts the given dates to the next business day with a small
        difference.

        Rolls the given date to the next business day,
        unless it happens in the next month, in this case
        it returns the previous business day.

        Parameters
        ----------

        dt : datetime.date, datetime.datetime, pandas.Timestamp, str
            Dates to be adjusted

        Returns
        -------

        datetime.date, datetime.datetime, pandas.Timestamp, str
            return the next business day if the given date is
            not a business day.

        """
        if isseq(dt):
            return recseq(self.vec.modified_following(dt))
        else:
            if isnull(dt):
                return dt
            dtx = self._index.modified_following(dt)
            return retdate(dtx)

    def __adjust_previous(self, dt):
        return Date(self._index.preceding(dt)).date

    def adjust_previous(self, dt):
        """
        Adjusts the given dates to the previous business day

        Rolls the given date to the previous business day,
        unless it is a business day.

        Parameters
        ----------

        dt : datetime.date, datetime.datetime, pandas.Timestamp, str
            Dates to be adjusted

        Returns
        -------

        datetime.date, datetime.datetime, pandas.Timestamp, str
            return the previous business day if the given date is
            not a business day.

        """
        if isseq(dt):
            return recseq(self.vec.adjust_previous(dt))
        else:
            if isnull(dt):
                return dt
            dt = self.__adjust_previous(dt)
            return retdate(dt)

    preceding = adjust_previous

    def modified_preceding(self, dt):
        """
        Adjusts the given dates to the previous business day with a small
        difference.

        Rolls the given date to the previous business day,
        unless it happens in the previous month, in this case
        it returns the previous business day.

        Parameters
        ----------

        dt : datetime.date, datetime.datetime, pandas.Timestamp, str
            Dates to be adjusted

        Returns
        -------

        datetime.date, datetime.datetime, pandas.Timestamp, str
            return the previous business day if the given date is
            not a business day.

        """
        if isseq(dt):
            return recseq(self.vec.modified_preceding(dt))
        else:
            if isnull(dt):
                return dt
            dtx = self._index.modified_preceding(dt)
            return retdate(dtx)

    def seq(self, date_from, date_to):
        """
        Sequence of business days.

        Parameters
        ----------

        date_from : datetime.date, datetime.datetime, pandas.Timestamp, str
            Start date

        date_to : datetime.date, datetime.datetime, pandas.Timestamp, str
            End date

        Returns
        -------
        list of dates, pandas.DatetimeIndex
            Returns a sequence of dates with business days only.
        """
        _from = Date(date_from).date
        _to = Date(date_to).date
        reverse = False
        if _from > _to:
            _from, _to = _to, _from
            reverse = True
        _seq = recseq(retdate(dt) for dt in self._index.seq(_from, _to))
        if reverse:
            _seq.reverse()
        return _seq

    def offset(self, dt, n):
        """
        Offsets the given dates by n business days.

        Parameters
        ----------

        dt : datetime.date, datetime.datetime, pandas.Timestamp, str
            Dates to be offset

        n : int, list of int
            the amount of business days to offset

        Returns
        -------
        date, list of dates, pandas.DatetimeIndex
            Returns the given dates offset by the given amount of n business
            days.

        """
        if isseq(dt) or isseq(n):
            return recseq(self.vec.offset(dt, n))
        else:
            if isnull(dt):
                return dt
            elif isnull(n):
                return n
            return retdate(self._index.offset(dt, n))

    def diff(self, dts):
        """
        Compute the number of business days between dates in a given vector
        of dates.

        Parameters
        ----------

        dts : list of date
            Sequence containing the dates to be differenced.

        Returns
        -------

        list of int
            The number of business days between given dates.
        """
        if len(dts) <= 1:
            return recseq([], "array")
        return self.bizdays(dts[:-1], dts[1:])

    def getdate(self, expr, year, month=None):
        """
        Get dates using other dates (or month or year) as reference.

        Imagine you have one date and want the first or last day of this
        date's month. For example, you have the date 2018-02-01 and want
        the last day of its month. You have to check whether or not its year
        is a leap year, and this sounds a tough task. getdate helps with
        returning specific dates according to a reference than can be another
        date, a month or an year.

        Parameters
        ----------

        expr : str, list of str
            String specifying the date to be returned.

            See :doc:`getdate` for more information.

        year : int, list of int
            Year

        month : int, list of int
            Month

        Returns
        -------
        date, list of dates, pandas.DatetimeIndex
            Returns dates according to a reference that can be a month or an
            year.

        """
        if any([isseq(expr), isseq(year), isseq(month)]):
            return recseq(self.vec.getdate(expr, year, month))
        else:
            dt = self._index.getdate(expr, year, month)
            return retdate(Date(dt).date)

    def getbizdays(self, year, month=None):
        """
        Business days in a specific year or month.

        Parameters
        ----------

        year : int, list of int
            Year

        month : int, list of int
            Month

        Returns
        -------
        int, list of int
            Returns the number of business days in the given time span.

        """
        if any([isseq(year), isseq(month)]):
            return recseq(self.vec.getbizdays(year, month), "array")
        else:
            return self._index.getbizdays(year, month)

    @classmethod
    def load(cls, name=None, filename=None):
        """
        Load calendars from a file.

        Parameters
        ----------

        name : str
            Name of the calendar.
            The calendar is loaded from a file delivered with the package.
            The calendars:

            * B3
            * ANBIMA
            * Actual
            * calendars from pandas_market_calendars - use the prefix "PMC/<calendar name>" to name the calendar

            are delivered with the package.

        filename : str
            Text file with holidays  and weekdays.

        Returns
        -------
        Calendar
            A Calendar object.

        """
        if filename:
            res = _checkfile(filename)
            return cls._load_calendar_from_file(res)
        elif name:
            if name.startswith("PMC/"):
                try:
                    import pandas_market_calendars as mcal
                except ImportError:
                    raise Exception("pandas_market_calendars must be installed to use PMC calendars")
                cal = mcal.get_calendar(name[4:])
                hol = cal.holidays()
                return Calendar((d.item() for d in hol.holidays), weekdays=("Saturday", "Sunday"), name=name)
            else:
                res = _checklocalfile(name)
                return cls._load_calendar_from_file(res)

    @classmethod
    def _load_calendar_from_file(cls, res: Dict[str, TextIO]) -> "Calendar":
        w = "|".join(w.lower() for w in cls._weekdays)
        wre = "^%s$" % w
        _holidays = []
        _nonwork_weekdays = []
        with res["iter"] as fcal:
            for cal_reg in fcal:
                cal_reg = cal_reg.strip()
                if cal_reg == "":
                    continue
                if re.match(wre, cal_reg.lower()):
                    _nonwork_weekdays.append(cal_reg)
                elif re.match(r"^\d\d\d\d-\d\d-\d\d$", cal_reg):
                    _holidays.append(Date(cal_reg))
        return Calendar(_holidays, weekdays=_nonwork_weekdays, name=res["name"])

    def __str__(self):
        return """Calendar: {0}
Start: {1}
End: {2}
Weekdays: {5}
Holidays: {3}
Financial: {4}""".format(
            self.name,
            self.startdate,
            self.enddate,
            len(self._holidays),
            self.financial,
            ", ".join(self.weekdays) if self.weekdays else "",
        )

    __repr__ = __str__


def _checkfile(fname: str) -> Dict[str, TextIO]:
    if not os.path.exists(fname):
        raise Exception(f"Invalid calendar: {fname}")
    name = os.path.split(fname)[-1]
    if name.endswith(".cal"):
        name = name.replace(".cal", "")
    else:
        name = None
    return {"name": name, "iter": open(fname)}


def _checklocalfile(name: str) -> Dict[str, TextIO]:
    dir = os.path.dirname(__file__)
    fname = f"{dir}/{name}.cal"
    if not os.path.exists(fname):
        raise Exception(f"Invalid calendar: {name}")
    name = os.path.split(fname)[-1]
    if name.endswith(".cal"):
        name = name.replace(".cal", "")
    else:
        name = None
    return {"name": name, "iter": open(fname)}


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
        lengths = [len(dates_from), len(dates_to)]
        if max(lengths) % min(lengths) != 0:
            raise Exception(
                "from length must be multiple of to length and " "vice-versa"
            )
        if len(dates_from) < len(dates_to):
            dates_from = cycle(dates_from)
        else:
            dates_to = cycle(dates_to)
        return (
            self.cal.bizdays(_from, _to) for _from, _to in zip(dates_from, dates_to)
        )

    def adjust_next(self, dates):
        if not isseq(dates):
            dates = [dates]
        return (self.cal.adjust_next(dt) for dt in dates)

    def modified_following(self, dates):
        if not isseq(dates):
            dates = [dates]
        return (self.cal.modified_following(dt) for dt in dates)

    def adjust_previous(self, dates):
        if not isseq(dates):
            dates = [dates]
        return (self.cal.adjust_previous(dt) for dt in dates)

    def modified_preceding(self, dates):
        if not isseq(dates):
            dates = [dates]
        return (self.cal.modified_preceding(dt) for dt in dates)

    def offset(self, dates, ns):
        if not isseq(dates):
            dates = [dates]
        if not isseq(ns):
            ns = [ns]
        if len(dates) < len(ns):
            dates = cycle(dates)
        else:
            ns = cycle(ns)
        return (self.cal.offset(dt, n) for dt, n in zip(dates, ns))

    def getdate(self, expr, year, month):
        if not isseq(expr):
            expr = [expr]
        if not isseq(year):
            year = [year]
        if not isseq(month):
            month = [month]
        if len(expr) >= len(year) and len(expr) >= len(month):
            year = cycle(year)
            month = cycle(month)
        elif len(year) >= len(expr) and len(year) >= len(month):
            expr = cycle(expr)
            month = cycle(month)
        elif len(month) >= len(expr) and len(month) >= len(year):
            expr = cycle(expr)
            year = cycle(year)
        return (self.cal.getdate(ex, ye, mo) for ex, ye, mo in zip(expr, year, month))

    def getbizdays(self, year, month):
        if not isseq(year):
            year = [year]
        if not isseq(month):
            month = [month]
        if len(year) > len(month):
            month = cycle(month)
        else:
            year = cycle(year)
        return (self.cal.getbizdays(ye, mo) for ye, mo in zip(year, month))
