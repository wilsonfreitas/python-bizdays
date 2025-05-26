import os
import re
from datetime import date, datetime
from typing import Any, Optional, TextIO, TypeVar

import numpy as np
import numpy.typing as npt
import pandas as pd

from bizdays.date import Date
from bizdays.dateindex import DateIndex
from bizdays.utils import isseq, recycle_arrays

date_types = TypeVar("date_types", str, date, datetime, pd.Timestamp, np.datetime64)
date_list_types = TypeVar("date_list_types", list[str], list[date], list[datetime])


def _checkfile(fname: str) -> tuple[str, TextIO]:
    if not os.path.exists(fname):
        raise Exception(f"Invalid calendar: {fname}")
    name: str = os.path.split(fname)[-1]
    if name.endswith(".cal"):
        name = name.replace(".cal", "")
    else:
        name = "None"
    return (name, open(fname))


def _checklocalfile(name: str) -> tuple[str, TextIO]:
    dir = os.path.dirname(__file__)
    fname = f"{dir}/{name}.cal"
    if not os.path.exists(fname):
        raise Exception(f"Invalid calendar: {name}")
    name = os.path.split(fname)[-1]
    if name.endswith(".cal"):
        name = name.replace(".cal", "")
    else:
        name = "None"
    return (name, open(fname))


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
        holidays: date_list_types = [],
        weekdays: list[str] = [],
        startdate: date | datetime | str = "",
        enddate: date | datetime | str = "",
        name: str = "",
        financial: bool = True,
    ):
        self.financial: bool = financial
        self.name: str = name
        self._holidays: npt.NDArray[np.datetime64] = np.array(
            [Date(d).format() for d in holidays], dtype="datetime64[D]"
        )
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
            self._holidays,
            np.datetime64(self._startdate.date),
            np.datetime64(self._enddate.date),
            self._nonwork_weekdays,
        )

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
        date_from: date_types | list[date_types] | pd.DatetimeIndex | npt.NDArray[np.datetime64],
        date_to: date_types | list[date_types] | pd.DatetimeIndex | npt.NDArray[np.datetime64],
    ) -> int | npt.NDArray[np.int_]:
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
        single_value = not (isseq(date_from) or isseq(date_to))
        _date_from: npt.NDArray[np.datetime64] = np.atleast_1d(np.asarray(date_from, dtype="datetime64[D]"))
        _date_to: npt.NDArray[np.datetime64] = np.atleast_1d(np.asarray(date_to, dtype="datetime64[D]"))
        _date_from, _date_to = recycle_arrays(_date_from, _date_to)
        bdays = self._index.bizdays(_date_from, _date_to)
        if not self.financial:
            date_reverse = _date_from > _date_to
            adjust = np.where(date_reverse, -1, 1)
            bdays = bdays + adjust
        return bdays[0] if single_value else bdays

    def isbizday(
        self, dt: date_types | list[date_types] | pd.DatetimeIndex | npt.NDArray[np.datetime64]
    ) -> bool | npt.NDArray[np.bool_]:
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
        single_value = not isseq(dt)
        _dt: npt.NDArray[np.datetime64] = np.atleast_1d(np.asarray(dt, dtype="datetime64[D]"))
        is_bizday = self._index.is_bizday(_dt)
        return is_bizday[0] if single_value else is_bizday

    def adjust_next(
        self, dt: date_types | list[date_types] | pd.DatetimeIndex | npt.NDArray[np.datetime64]
    ) -> date_types | npt.NDArray[np.datetime64]:
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
        single_value = not isseq(dt)
        _dt: npt.NDArray[np.datetime64] = np.atleast_1d(np.asarray(dt, dtype="datetime64[D]"))
        adt = self._index.adjust(_dt, 1)
        return adt[0] if single_value else adt

    following = adjust_next

    def modified_following(
        self, dt: date_types | list[date_types] | pd.DatetimeIndex | npt.NDArray[np.datetime64]
    ) -> date_types | npt.NDArray[np.datetime64]:
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
        single_value = not isseq(dt)
        _dt: npt.NDArray[np.datetime64] = np.atleast_1d(np.asarray(dt, dtype="datetime64[D]"))
        adt = self._index.adjust(_dt, 1)
        months_dt = _dt.astype("datetime64[M]") % 12 + 1
        months_adt = adt.astype("datetime64[M]") % 12 + 1
        idx = months_dt != months_adt
        adt[idx] = self._index.adjust(_dt[idx], -1)
        return adt[0] if single_value else adt

    def adjust_previous(
        self, dt: date_types | list[date_types] | pd.DatetimeIndex | npt.NDArray[np.datetime64]
    ) -> date_types | npt.NDArray[np.datetime64]:
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
        single_value = not isseq(dt)
        _dt: npt.NDArray[np.datetime64] = np.atleast_1d(np.asarray(dt, dtype="datetime64[D]"))
        adt = self._index.adjust(_dt, -1)
        return adt[0] if single_value else adt

    preceding = adjust_previous

    def modified_preceding(
        self, dt: date_types | list[date_types] | pd.DatetimeIndex | npt.NDArray[np.datetime64]
    ) -> date_types | npt.NDArray[np.datetime64]:
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
        single_value = not isseq(dt)
        _dt: npt.NDArray[np.datetime64] = np.atleast_1d(np.asarray(dt, dtype="datetime64[D]"))
        adt = self._index.adjust(_dt, -1)
        months_dt = _dt.astype("datetime64[M]") % 12 + 1
        months_adt = adt.astype("datetime64[M]") % 12 + 1
        idx = months_dt != months_adt
        adt[idx] = self._index.adjust(_dt[idx], 1)
        return adt[0] if single_value else adt

    def seq(self, date_from: date_types, date_to: date_types) -> npt.NDArray[np.datetime64]:
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
        _from: np.datetime64 = np.datetime64(date_from)
        _to: np.datetime64 = np.datetime64(date_to)
        reverse = False
        if _from > _to:
            _from, _to = _to, _from
            reverse = True
        _seq = self._index.seq(_from, _to)
        return _seq[::-1] if reverse else _seq

    def offset(
        self,
        dt: date_types | list[date_types] | pd.DatetimeIndex | npt.NDArray[np.datetime64],
        n: int | list[int] | npt.NDArray[np.int_],
    ) -> date_types | npt.NDArray[np.datetime64]:
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
        single_value = not isseq(dt)
        _dt: npt.NDArray[np.datetime64] = np.atleast_1d(np.asarray(dt, dtype="datetime64[D]"))
        _n: npt.NDArray[np.int_] = np.atleast_1d(np.asarray(n, dtype=np.int_))
        _dt, _n = recycle_arrays(_dt, _n)
        dts = self._index.offset(_dt, _n)
        return dts[0] if single_value else dts

    def diff(self, dts: list[date_types] | pd.DatetimeIndex | npt.NDArray[np.datetime64]) -> npt.NDArray[np.int_]:
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
        _dts: npt.NDArray[np.datetime64] = np.asarray(dts, dtype="datetime64[D]")
        if len(_dts) <= 1:
            return np.array([], dtype=np.int_)
        return self.bizdays(_dts[:-1], _dts[1:])  # type: ignore

    # def getdate(self, expr, year, month=None):
    #     """
    #     Get dates using other dates (or month or year) as reference.

    #     Imagine you have one date and want the first or last day of this
    #     date's month. For example, you have the date 2018-02-01 and want
    #     the last day of its month. You have to check whether or not its year
    #     is a leap year, and this sounds a tough task. getdate helps with
    #     returning specific dates according to a reference than can be another
    #     date, a month or an year.

    #     Parameters
    #     ----------

    #     expr : str, list of str
    #         String specifying the date to be returned.

    #         See :doc:`getdate` for more information.

    #     year : int, list of int
    #         Year

    #     month : int, list of int
    #         Month

    #     Returns
    #     -------
    #     date, list of dates, pandas.DatetimeIndex
    #         Returns dates according to a reference that can be a month or an
    #         year.

    #     """
    #     if any([isseq(expr), isseq(year), isseq(month)]):
    #         return recseq(self.vec.getdate(expr, year, month))
    #     else:
    #         dt = self._index.getdate(expr, year, month)
    #         return retdate(Date(dt).date)

    # def getbizdays(self, year, month=None):
    #     """
    #     Business days in a specific year or month.

    #     Parameters
    #     ----------

    #     year : int, list of int
    #         Year

    #     month : int, list of int
    #         Month

    #     Returns
    #     -------
    #     int, list of int
    #         Returns the number of business days in the given time span.

    #     """
    #     if any([isseq(year), isseq(month)]):
    #         return recseq(self.vec.getbizdays(year, month), "array")
    #     else:
    #         return self._index.getbizdays(year, month)

    @classmethod
    def load(cls, name: Optional[str] = None, filename: Optional[str] = None) -> "Calendar":
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
            _cal = cls._load_calendar_from_file(res)
        elif name:
            if name.startswith("PMC/"):
                try:
                    import pandas_market_calendars as mcal  # type: ignore[import-untyped]
                except ImportError:
                    raise Exception("pandas_market_calendars must be installed to use PMC calendars")
                cal = mcal.get_calendar(name[4:])  # type: ignore
                hol = cal.holidays()
                _cal = Calendar([d.item() for d in hol.holidays], weekdays=["Saturday", "Sunday"], name=name)  # type: ignore
            else:
                res = _checklocalfile(name)
                _cal = cls._load_calendar_from_file(res)
        else:
            raise Exception("You must provide a calendar name or a filename")
        return _cal

    @classmethod
    def _load_calendar_from_file(cls, res: tuple[str, TextIO]) -> "Calendar":
        w = "|".join(w.lower() for w in cls._weekdays)
        wre = "^%s$" % w
        _holidays: list[str] = []
        _nonwork_weekdays: list[str] = []
        with res[1] as fcal:
            for cal_reg in fcal:
                cal_reg = cal_reg.strip()
                if cal_reg == "":
                    continue
                if re.match(wre, cal_reg.lower()):
                    _nonwork_weekdays.append(cal_reg)
                elif re.match(r"^\d\d\d\d-\d\d-\d\d$", cal_reg):
                    _holidays.append(Date(cal_reg).format())
        return Calendar(_holidays, weekdays=_nonwork_weekdays, name=res[0])

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
