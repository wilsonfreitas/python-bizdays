from dataclasses import dataclass
import os
import re
from datetime import datetime, date, timedelta
from itertools import cycle
from typing import Any, Generator, Sequence, TextIO, Dict, Callable, TypeVar


PANDAS_INSTALLED: bool = False

try:
    import pandas as pd  # type: ignore[import-untyped]
    from pandas._libs.missing import NAType  # type: ignore[import-untyped]
    import numpy as np
    import numpy.typing as npt

    PANDAS_INSTALLED = True

    def isnull(x: Any) -> bool | npt.ArrayLike:
        return pd.isna(x)

    def recseq(gen: Generator, typo: str = "DatetimeIndex") -> list | npt.ArrayLike:
        g = list(gen)
        if get_option("mode") == "pandas":
            if typo == "DatetimeIndex":
                return pd.DatetimeIndex(g)
            elif typo == "array":
                return np.array(g)
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

    def return_none() -> None | NAType:
        if get_option("mode") == "pandas":
            return pd.NA
        else:
            return None

except ImportError:

    def isnull(x: Any) -> bool | npt.ArrayLike:
        return x is None

    def recseq(gen: Generator, typo: str = "DatetimeIndex") -> list | npt.ArrayLike:
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

    def return_none() -> None | NAType:
        return None


__all__ = ["get_option", "set_option", "Calendar"]


options: dict[str, str] = {"mode": "python"}


def get_option(name: str) -> str | None:
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


def set_option(name: str, val: str):
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


D1: timedelta = timedelta(1)


def isstr(d: object) -> bool:
    return isinstance(d, str)


def isseq(seq: str | Sequence) -> bool:
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


class Date:
    def __init__(self, d: str | date | datetime | None, format: str = "%Y-%m-%d"):
        # d = d if d else date.today()
        if isstr(d):
            d = datetime.strptime(d, format).date()  # type: ignore[arg-type]
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
        self.date: date | None = d

    def format(self, fmts: str = "%Y-%m-%d") -> str:
        if self.date is None:
            raise ValueError("Date is None - cannot format")
        return datetime.strftime(self.date, fmts)

    def __gt__(self, other: "Date") -> bool:
        if self.date is None or other.date is None:
            raise ValueError("Date is None - cannot format")
        return self.date > other.date

    def __ge__(self, other: "Date") -> bool:
        if self.date is None or other.date is None:
            raise ValueError("Date is None - cannot format")
        return self.date >= other.date

    def __lt__(self, other: "Date") -> bool:
        if self.date is None or other.date is None:
            raise ValueError("Date is None - cannot format")
        return self.date < other.date

    def __le__(self, other: "Date") -> bool:
        if self.date is None or other.date is None:
            raise ValueError("Date is None - cannot format")
        return self.date <= other.date

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Date):
            return self.date == other.date
        raise ValueError("Invalid comparison")

    def __repr__(self) -> str:
        return self.format()

    __str__ = __repr__


def find_date_pos(col: list[date], dt: date) -> int:
    beg: int = 0
    end: int = len(col)
    while (end - beg) > 1:
        mid: int = int((end + beg) / 2)
        if dt > col[mid]:
            beg = mid
        elif dt < col[mid]:
            end = mid
        else:
            return mid
    return beg


@dataclass
class DateIndexNode:
    workday: int
    currentday: int
    isholiday: bool
    revworkday: int = 0


@dataclass
class YearNode:
    date: date
    month: int
    weekday: int
    isholiday: bool
    currentday: int
    workday: int
    revworkday: int


def __daterangecheck(obj: "DateIndex", dt: date) -> date:
    # dt = Date(dt).date
    if dt > obj.enddate or dt < obj.startdate:
        raise DateOutOfRange("Given date out of calendar range")
    return dt


def daterangecheck(func: Callable[["DateIndex", date], date]) -> Callable[["DateIndex", date], date]:
    def handler(self: "DateIndex", dt: date) -> date:
        return func(self, __daterangecheck(self, dt))

    return handler


def daterangecheck_node(
    func: Callable[["DateIndex", date], DateIndexNode]
) -> Callable[["DateIndex", date], DateIndexNode]:
    def handler(self: "DateIndex", dt: date) -> DateIndexNode:
        return func(self, __daterangecheck(self, dt))

    return handler


def daterangecheck_with_n(func: Callable[["DateIndex", date, int], date]) -> Callable[["DateIndex", date, int], date]:
    def handler(self: "DateIndex", dt: date, n: int) -> date:
        return func(self, __daterangecheck(self, dt), n)

    return handler


def daterangecheck2(
    func: Callable[["DateIndex", date, date], list[date]]
) -> Callable[["DateIndex", date, date], list[date]]:
    def handler(self, dt1, dt2):
        return func(self, __daterangecheck(self, dt1), __daterangecheck(self, dt2))

    return handler


def load_holidays(fname: str, format: str = "%Y-%m-%d") -> list[date | None]:
    if not os.path.exists(fname):
        raise Exception(
            "Invalid calendar specification: \
        file not found (%s)"
            % fname
        )
    _holidays: list[date | None] = []
    with open(fname) as fcal:
        for cal_reg in fcal:
            cal_reg = cal_reg.strip()
            if cal_reg == "":
                continue
            _holidays.append(Date(cal_reg, format=format).date)
    return _holidays


class DateIndex(object):
    WEEKDAYS: tuple[str, str, str, str, str, str, str] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

    def __init__(self, holidays: list[Date], startdate: date, enddate: date, weekdays: list[int]):
        self._index: dict[date, DateIndexNode] = {}
        self._bizdays: list[date] = []
        self._days: list[date] = []
        self._years: dict[int, list[YearNode]] = {}
        self._weekdays: dict[int, list[date]] = {}
        self.weekdays: list[int] = weekdays
        self.holidays = [d.date for d in holidays]
        self.startdate: date = startdate
        self.enddate: date = enddate

        dts: list[date] = []
        dt: date = self.startdate
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
            self._index[dt] = DateIndexNode(workday=w, currentday=c, isholiday=is_hol)
            c += 1

        max_w: int = self._index[self.enddate].workday
        w = max_w + 1
        for dt in reversed(dts):
            is_hol = self._index[dt].isholiday
            if not is_hol:
                w -= 1
            self._index[dt].revworkday = w

        for dt in dts:
            # ----
            ix = self._index[dt]
            col: list = self._years.get(dt.year, [])
            col.append(YearNode(dt, dt.month, dt.weekday(), ix.isholiday, ix.currentday, ix.workday, ix.revworkday))
            self._years[dt.year] = col
            col = self._weekdays.get(dt.weekday(), [])
            col.append(dt)
            self._weekdays[dt.weekday()] = col
            self._days.append(dt)
            # ----

    @daterangecheck_with_n
    def offset(self, dt: date, n: int) -> date:
        if n > 0:
            pos = self._index[dt].workday - 1 + n
        elif n < 0:
            pos = self._index[dt].revworkday - 1 + n
        else:
            return dt
        return self._bizdays[pos]

    @daterangecheck
    def following(self, dt: date) -> date:
        if not self._index[dt].isholiday:
            return dt
        else:
            return self.following(dt + D1)

    @daterangecheck
    def modified_following(self, dt: date) -> date:
        dtx = self.following(dt)
        if dtx.month != dt.month:
            dtx = self.preceding(dt)
        return dtx

    @daterangecheck
    def preceding(self, dt: date) -> date:
        if not self._index[dt].isholiday:
            return dt
        else:
            return self.preceding(dt - D1)

    @daterangecheck
    def modified_preceding(self, dt: date) -> date:
        dtx = self.preceding(dt)
        if dtx.month != dt.month:
            dtx = self.following(dt)
        return dtx

    @daterangecheck2
    def seq(self, dt1: date, dt2: date) -> list[date]:
        pos1 = max(self._index[dt1].workday, self._index[dt1].revworkday) - 1
        pos2 = min(self._index[dt2].workday, self._index[dt2].revworkday)
        return self._bizdays[pos1:pos2]

    @daterangecheck_node
    def get(self, dt: date) -> DateIndexNode:
        return self._index[dt]

    def getbizdays(self, year: int, month: int = 0) -> int:
        if month:
            return sum(not d.isholiday for d in self._years[year] if d.month == month)
        else:
            return sum(not d.isholiday for d in self._years[year])

    def getdate(self, expr: str, year: int, month: int = 0) -> date:
        tok = expr.split()
        if len(tok) == 2:
            n = self._getnth(tok[0])
            if tok[1] == "day":
                _dt = self._getnthday(n, year, month)
            elif tok[1] == "bizday":
                _dt = self._getnthbizday(n, year, month)
            elif tok[1] in self.WEEKDAYS:
                _dt = self._getnthweekday(n, tok[1], year, month)
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
                _dt = self._getnthday_beforeafter(n, pos)
            elif tok[1] == "bizday":
                _dt = self._getnthbizday_beforeafter(n, pos)
            elif tok[1] in self.WEEKDAYS:
                _dt = self._getnthweekday_beforeafter(n, tok[1], pos)
            else:
                raise ValueError("Invalid day:", tok[1])
        return _dt

    def _getnthpos(self, nth: str) -> int:
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

    def _getnth(self, nth: str) -> int:
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

    def _getnthdaypos(self, n: int, year: int, month: int = 0) -> tuple[int, int, date, int]:
        n = n - 1 if n > 0 else n
        if month:
            pos = [
                (d.currentday - 1, d.workday - 1, d.date, d.revworkday - 1)
                for d in self._years[year]
                if d.month == month
            ]
            return pos[n]
        else:
            return (
                self._years[year][n].currentday - 1,
                self._years[year][n].workday - 1,
                self._years[year][n].date,
                self._years[year][n].revworkday,
            )

    def _getnthbizdaypos(self, n: int, year: int, month: int = 0) -> tuple[int, int, date, int]:
        n = n - 1 if n > 0 else n
        if month:
            col = [
                (d.currentday - 1, d.workday - 1, d.date, d.revworkday - 1)
                for d in self._years[year]
                if not d.isholiday and d.month == month
            ]
        else:
            col = [
                (d.currentday - 1, d.workday - 1, d.date, d.revworkday - 1)
                for d in self._years[year]
                if not d.isholiday
            ]
        return col[n]

    def _getnthweekdaypos(self, n: int, weekday: int, year: int, month: int = 0) -> tuple[int, int, date, int]:
        n = n - 1 if n > 0 else n
        if month:
            col = [
                (d.currentday - 1, d.workday - 1, d.date, d.revworkday - 1)
                for d in self._years[year]
                if self.WEEKDAYS[d.weekday] == weekday and d.month == month
            ]
        else:
            col = [
                (d.currentday - 1, d.workday - 1, d.date, d.revworkday - 1)
                for d in self._years[year]
                if self.WEEKDAYS[d.weekday] == weekday
            ]
        return col[n]

    def _getnthday_beforeafter(self, n1: int, pos: tuple[int, int, date, int]) -> date:
        return self._days[pos[0] + n1]

    def _getnthbizday_beforeafter(self, n1: int, pos: tuple[int, int, date, int]) -> date:
        if n1 > 0:
            _pos = pos[1] + n1
        else:
            _pos = pos[3] + n1
        return self._bizdays[_pos]

    def _getnthweekday_beforeafter(self, n1: int, weekday: str, pos: tuple[int, int, date, int]) -> date:
        dt: date = pos[2]
        wday: int = self.WEEKDAYS.index(weekday)
        _pos = find_date_pos(self._weekdays[wday], dt)
        if dt.weekday() != wday:
            n1 = n1 + 1 if n1 < 0 else n1
        return self._weekdays[wday][_pos + n1]

    def _getnthday(self, n: int, year: int, month: int = 0) -> date:
        pos = self._getnthdaypos(n, year, month)[0]
        return self._days[pos]

    def _getnthbizday(self, n: int, year: int, month: int = 0) -> date:
        pos = self._getnthbizdaypos(n, year, month)[1]
        return self._bizdays[pos]

    def _getnthweekday(self, n: int, weekday: str, year: int, month: int = 0) -> date:
        n = n - 1 if n > 0 else n
        if month:
            col = [d.date for d in self._years[year] if self.WEEKDAYS[d.weekday] == weekday and d.month == month]
        else:
            col = [d.date for d in self._years[year] if self.WEEKDAYS[d.weekday] == weekday]
        return col[n]

    def __getitem__(self, dt: date) -> DateIndexNode:
        return self.get(dt)


date_types = TypeVar("date_types", str, date, datetime, pd.Timestamp, np.datetime64)


class Calendar:
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

    _weekdays: tuple[str, str, str, str, str, str, str] = (
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
        holidays: list[date | datetime | str] = [],
        weekdays: list[str] = [],
        startdate: date | datetime | str = "",
        enddate: date | datetime | str = "",
        name: str = "",
        financial: bool = True,
    ):
        self.financial: bool = financial
        self.name: str = name
        self._holidays: list[Date] = [Date(d) for d in holidays]
        self._nonwork_weekdays: list[int] = [
            [w[:3].lower() for w in self._weekdays].index(wd[:3].lower()) for wd in weekdays
        ]
        self._startdate: Date
        self._enddate: Date
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
        self._index: DateIndex = DateIndex(
            self._holidays, self._startdate.date, self._enddate.date, self._nonwork_weekdays
        )
        self.vec = VectorizedOps(self)

    def __get_weekdays(self) -> tuple[str, ...]:
        return tuple(self._weekdays[nwd] for nwd in self._nonwork_weekdays)

    weekdays = property(__get_weekdays)

    def __get_startdate(self) -> date:
        return self._startdate.date

    startdate = property(__get_startdate)

    def __get_enddate(self) -> date:
        return self._enddate.date

    enddate = property(__get_enddate)

    def __get_holidays(self) -> list[date]:
        return [d.date for d in self._holidays]

    holidays = property(__get_holidays)

    def bizdays(
        self,
        date_from: date_types | list[date_types] | pd.DatetimeIndex | np.ndarray,
        date_to: date_types | list[date_types] | pd.DatetimeIndex | np.ndarray,
    ) -> int | list[int] | np.ndarray:
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
            t1 = (self._index[d1].workday, self._index[d1].revworkday)
            t2 = (self._index[d2].workday, self._index[d2].revworkday)
            i1 = t2[0] - t1[0]
            i2 = t2[1] - t1[1]
            bdays = min(i1, i2)
            adj_vec = int(self._index[d1].isholiday and self._index[d2].isholiday)
            date_reverse = date_from > date_to
            if date_reverse:
                adj_vec = -adj_vec
                bdays = -bdays
            bdays -= adj_vec
            if self.financial:
                if self._index[d1].isholiday and self._index[d2].isholiday and abs(bdays) == 1:
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
                dt = Date(dt).date
                return not self._index[dt].isholiday

    def __adjust_next(self, dt):
        dt = Date(dt).date
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
            dt = Date(dt).date
            dtx = self._index.modified_following(dt)
            return retdate(dtx)

    def __adjust_previous(self, dt):
        dt = Date(dt).date
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
            dt = Date(dt).date
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
            dt = Date(dt).date
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
                    import pandas_market_calendars as mcal  # type: ignore[import-untyped]
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


def _checkfile(fname: str) -> dict[str, TextIO | str]:
    if not os.path.exists(fname):
        raise Exception(f"Invalid calendar: {fname}")
    name: str = os.path.split(fname)[-1]
    if name.endswith(".cal"):
        name = name.replace(".cal", "")
    else:
        name = "None"
    return {"name": name, "iter": open(fname)}


def _checklocalfile(name: str) -> dict[str, TextIO | str]:
    dir = os.path.dirname(__file__)
    fname = f"{dir}/{name}.cal"
    if not os.path.exists(fname):
        raise Exception(f"Invalid calendar: {name}")
    name = os.path.split(fname)[-1]
    if name.endswith(".cal"):
        name = name.replace(".cal", "")
    else:
        name = "None"
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
            raise Exception("from length must be multiple of to length and " "vice-versa")
        if len(dates_from) < len(dates_to):
            dates_from = cycle(dates_from)
        else:
            dates_to = cycle(dates_to)
        return (self.cal.bizdays(_from, _to) for _from, _to in zip(dates_from, dates_to))

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
