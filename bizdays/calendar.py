from collections.abc import Sequence
from datetime import date, datetime
from importlib import import_module
from typing import TypedDict, TypeAlias, overload

import numpy as np
import numpy.typing as npt
import pandas as pd

from bizdays.calendarfile import (
    CalendarDefinition,
    get_packaged_calendar_names,
    load_calendar_definition,
    load_packaged_calendar_definition,
)
from bizdays.date import Date
from bizdays.dateindex import DateIndex
from bizdays.utils import isseq, recycle_arrays

DateScalar: TypeAlias = str | date | datetime | pd.Timestamp | np.datetime64
DateArray: TypeAlias = npt.NDArray[np.datetime64]
DateSequence: TypeAlias = list[DateScalar] | tuple[DateScalar, ...]
DateVector: TypeAlias = DateSequence | pd.DatetimeIndex | DateArray
DateInput: TypeAlias = DateScalar | DateVector
GetDateRefScalar: TypeAlias = int | DateScalar
GetDateRefSequence: TypeAlias = list[GetDateRefScalar] | tuple[GetDateRefScalar, ...]
GetDateRefVector: TypeAlias = GetDateRefSequence | pd.Index | npt.NDArray[np.object_]
GetDateRefInput: TypeAlias = GetDateRefScalar | GetDateRefVector
IntArray: TypeAlias = npt.NDArray[np.int_]
IntSequence: TypeAlias = list[int] | tuple[int, ...]
IntVector: TypeAlias = IntSequence | IntArray
IntInput: TypeAlias = int | IntVector
BoolArray: TypeAlias = npt.NDArray[np.bool_]
MaskedIntResult: TypeAlias = np.int_ | IntArray | np.ma.MaskedArray
MaskedBoolResult: TypeAlias = np.bool_ | BoolArray | np.ma.MaskedArray


class CalendarIntegrationListing(TypedDict):
    available: bool
    prefix: str
    calendars: list[str]


class CalendarListing(TypedDict):
    packaged: list[str]
    pandas_market_calendars: CalendarIntegrationListing


def _normalize_date_input(dt: DateInput) -> DateArray:
    return np.atleast_1d(np.asarray(dt, dtype="datetime64[D]"))


def _normalize_offset_input(n: IntInput) -> tuple[IntArray, BoolArray]:
    raw = np.atleast_1d(np.asarray(n, dtype=object))
    missing = np.asarray(pd.isna(raw), dtype=np.bool_)
    values = np.zeros(raw.shape, dtype=np.int_)

    for idx, value in np.ndenumerate(raw):
        if missing[idx]:
            continue
        if isinstance(value, (int, np.integer)):
            values[idx] = int(value)
            continue
        if isinstance(value, (float, np.floating)) and np.isfinite(value) and float(value).is_integer():
            values[idx] = int(value)
            continue
        raise ValueError("Offset values must be integers or missing")

    return values, missing


def _finalize_date_result(result: DateArray, single_value: bool) -> np.datetime64 | DateArray:
    return result[0] if single_value else result


def _finalize_masked_int_result(
    result: IntArray, missing: BoolArray, single_value: bool
) -> MaskedIntResult:
    if np.any(missing):
        masked = np.ma.masked_array(result, mask=missing)
        return masked[0] if single_value else masked
    return result[0] if single_value else result


def _finalize_masked_bool_result(
    result: BoolArray, missing: BoolArray, single_value: bool
) -> MaskedBoolResult:
    if np.any(missing):
        masked = np.ma.masked_array(result, mask=missing)
        return masked[0] if single_value else masked
    return result[0] if single_value else result


def _list_pandas_market_calendars() -> CalendarIntegrationListing:
    prefix = "PMC/"
    try:
        mcal = import_module("pandas_market_calendars")
    except ImportError:
        return {
            "available": False,
            "prefix": prefix,
            "calendars": [],
        }

    calendars = [str(name) for name in dict.fromkeys(mcal.get_calendar_names())]
    return {
        "available": True,
        "prefix": prefix,
        "calendars": calendars,
    }


def list_calendars() -> CalendarListing:
    """
    List the packaged calendars and supported optional calendar integrations.

    Returns
    -------
    dict
        A dictionary containing the packaged calendars and integration metadata.
    """
    return {
        "packaged": get_packaged_calendar_names(),
        "pandas_market_calendars": _list_pandas_market_calendars(),
    }


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
        holidays: Sequence[DateScalar] | None = None,
        weekdays: Sequence[str] | None = None,
        startdate: DateScalar | None = None,
        enddate: DateScalar | None = None,
        name: str = "",
        financial: bool = True,
    ) -> None:
        if holidays is None:
            holidays = []
        if weekdays is None:
            weekdays = []
        self.financial: bool = financial
        self.name: str = name
        self._holidays: DateArray = np.array([Date(d).format() for d in holidays], dtype="datetime64[D]")
        self._nonwork_weekdays: list[int] = [
            [w[:3].lower() for w in self._weekdays].index(wd[:3].lower()) for wd in weekdays
        ]
        self._startdate: Date
        self._enddate: Date
        if len(self._holidays):
            if startdate is not None:
                self._startdate = Date(startdate)
            else:
                self._startdate = Date(min(self._holidays).astype("O"))
            if enddate is not None:
                self._enddate = Date(enddate)
            else:
                self._enddate = Date(max(self._holidays).astype("O"))
        else:
            if startdate is not None:
                self._startdate = Date(startdate)
            else:
                self._startdate = Date("1970-01-01")
            if enddate is not None:
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
        return self._startdate.date  # type: ignore

    startdate = property(__get_startdate)

    def __get_enddate(self) -> date:
        return self._enddate.date  # type: ignore

    enddate = property(__get_enddate)

    def __get_holidays(self) -> list[date]:
        return [d.astype("O") for d in self._holidays]

    holidays = property(__get_holidays)

    @overload
    def bizdays(self, date_from: DateScalar, date_to: DateScalar) -> np.int_: ...

    @overload
    def bizdays(self, date_from: DateVector, date_to: DateInput) -> IntArray: ...

    @overload
    def bizdays(self, date_from: DateScalar, date_to: DateVector) -> IntArray: ...

    def bizdays(self, date_from: DateInput, date_to: DateInput) -> MaskedIntResult:
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
        numpy scalar or numpy.ndarray
            The number of business days between ``date_from`` and ``date_to``.
        """
        single_value = not (isseq(date_from) or isseq(date_to))
        _date_from = _normalize_date_input(date_from)
        _date_to = _normalize_date_input(date_to)
        _date_from, _date_to = recycle_arrays(_date_from, _date_to)
        missing = np.isnat(_date_from) | np.isnat(_date_to)
        bdays = np.zeros(_date_from.shape, dtype=np.int_)
        valid = ~missing
        if np.any(valid):
            bdays[valid] = self._index.bizdays(_date_from[valid], _date_to[valid])
            if not self.financial:
                date_reverse = _date_from[valid] > _date_to[valid]
                adjust = np.where(date_reverse, -1, 1)
                bdays[valid] = bdays[valid] + adjust
        return _finalize_masked_int_result(bdays, missing, single_value)

    @overload
    def isbizday(self, dt: DateScalar) -> np.bool_: ...

    @overload
    def isbizday(self, dt: DateVector) -> BoolArray: ...

    def isbizday(self, dt: DateInput) -> MaskedBoolResult:
        """
        Checks if the given dates are business days.

        Parameters
        ----------

        dt : datetime.date, datetime.datetime, pandas.Timestamp, str
            Dates to be checked

        Returns
        -------

        numpy scalar or numpy.ndarray
            Returns ``True`` if the given date is a business day and ``False`` otherwise.
        """
        single_value = not isseq(dt)
        _dt = _normalize_date_input(dt)
        missing = np.isnat(_dt)
        is_bizday = np.zeros(_dt.shape, dtype=np.bool_)
        valid = ~missing
        if np.any(valid):
            is_bizday[valid] = self._index.is_bizday(_dt[valid])
        return _finalize_masked_bool_result(is_bizday, missing, single_value)

    @overload
    def adjust_next(self, dt: DateScalar) -> np.datetime64: ...

    @overload
    def adjust_next(self, dt: DateVector) -> DateArray: ...

    def adjust_next(self, dt: DateInput) -> np.datetime64 | DateArray:
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

        numpy.datetime64 or numpy.ndarray
            Returns the next business day if the given date is not a business day.

        """
        single_value = not isseq(dt)
        _dt = _normalize_date_input(dt)
        missing = np.isnat(_dt)
        adt = np.full(_dt.shape, np.datetime64("NaT"), dtype="datetime64[D]")
        valid = ~missing
        if np.any(valid):
            adt[valid] = self._index.adjust(_dt[valid], 1)
        return _finalize_date_result(adt, single_value)

    @overload
    def following(self, dt: DateScalar) -> np.datetime64: ...

    @overload
    def following(self, dt: DateVector) -> DateArray: ...

    def following(self, dt: DateInput) -> np.datetime64 | DateArray:
        return self.adjust_next(dt)

    @overload
    def modified_following(self, dt: DateScalar) -> np.datetime64: ...

    @overload
    def modified_following(self, dt: DateVector) -> DateArray: ...

    def modified_following(self, dt: DateInput) -> np.datetime64 | DateArray:
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

        numpy.datetime64 or numpy.ndarray
            Returns the next business day unless that would cross into the next month.

        """
        single_value = not isseq(dt)
        _dt = _normalize_date_input(dt)
        missing = np.isnat(_dt)
        adt = np.full(_dt.shape, np.datetime64("NaT"), dtype="datetime64[D]")
        valid = ~missing
        if np.any(valid):
            valid_dt = _dt[valid]
            valid_adt = self._index.adjust(valid_dt, 1)
            months_dt = valid_dt.astype("datetime64[M]").astype(int) % 12 + 1
            months_adt = valid_adt.astype("datetime64[M]").astype(int) % 12 + 1
            idx = months_dt != months_adt
            valid_adt[idx] = self._index.adjust(valid_dt[idx], -1)
            adt[valid] = valid_adt
        return _finalize_date_result(adt, single_value)

    @overload
    def adjust_previous(self, dt: DateScalar) -> np.datetime64: ...

    @overload
    def adjust_previous(self, dt: DateVector) -> DateArray: ...

    def adjust_previous(self, dt: DateInput) -> np.datetime64 | DateArray:
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

        numpy.datetime64 or numpy.ndarray
            Returns the previous business day if the given date is not a business day.

        """
        single_value = not isseq(dt)
        _dt = _normalize_date_input(dt)
        missing = np.isnat(_dt)
        adt = np.full(_dt.shape, np.datetime64("NaT"), dtype="datetime64[D]")
        valid = ~missing
        if np.any(valid):
            adt[valid] = self._index.adjust(_dt[valid], -1)
        return _finalize_date_result(adt, single_value)

    @overload
    def preceding(self, dt: DateScalar) -> np.datetime64: ...

    @overload
    def preceding(self, dt: DateVector) -> DateArray: ...

    def preceding(self, dt: DateInput) -> np.datetime64 | DateArray:
        return self.adjust_previous(dt)

    @overload
    def modified_preceding(self, dt: DateScalar) -> np.datetime64: ...

    @overload
    def modified_preceding(self, dt: DateVector) -> DateArray: ...

    def modified_preceding(self, dt: DateInput) -> np.datetime64 | DateArray:
        """
        Adjusts the given dates to the previous business day with a small
        difference.

        Rolls the given date to the previous business day,
        unless it happens in the previous month, in this case
        it returns the following business day.

        Parameters
        ----------

        dt : datetime.date, datetime.datetime, pandas.Timestamp, str
            Dates to be adjusted

        Returns
        -------

        numpy.datetime64 or numpy.ndarray
            Returns the previous business day unless that would cross into the previous month.

        """
        single_value = not isseq(dt)
        _dt = _normalize_date_input(dt)
        missing = np.isnat(_dt)
        adt = np.full(_dt.shape, np.datetime64("NaT"), dtype="datetime64[D]")
        valid = ~missing
        if np.any(valid):
            valid_dt = _dt[valid]
            valid_adt = self._index.adjust(valid_dt, -1)
            months_dt = valid_dt.astype("datetime64[M]").astype(int) % 12 + 1
            months_adt = valid_adt.astype("datetime64[M]").astype(int) % 12 + 1
            idx = months_dt != months_adt
            valid_adt[idx] = self._index.adjust(valid_dt[idx], 1)
            adt[valid] = valid_adt
        return _finalize_date_result(adt, single_value)

    def seq(self, date_from: DateScalar, date_to: DateScalar) -> DateArray:
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
        numpy.ndarray
            Returns a NumPy array containing business days only.
        """
        _from: np.datetime64 = np.datetime64(date_from)
        _to: np.datetime64 = np.datetime64(date_to)
        reverse = False
        if _from > _to:
            _from, _to = _to, _from
            reverse = True
        _seq = self._index.seq(_from, _to)
        return _seq[::-1] if reverse else _seq

    @overload
    def offset(self, dt: DateScalar, n: int) -> np.datetime64: ...

    @overload
    def offset(self, dt: DateVector, n: IntInput) -> DateArray: ...

    @overload
    def offset(self, dt: DateScalar, n: IntVector) -> DateArray: ...

    def offset(self, dt: DateInput, n: IntInput) -> np.datetime64 | DateArray:
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
        numpy.datetime64 or numpy.ndarray
            Returns the given dates offset by the given amount of business days.

        """
        single_value = not (isseq(dt) or isseq(n))
        _dt = _normalize_date_input(dt)
        _n, missing_n = _normalize_offset_input(n)
        _dt, _n = recycle_arrays(_dt, _n)
        _, missing_n = recycle_arrays(_dt, missing_n)
        missing_dt = np.isnat(_dt)
        missing = missing_dt | missing_n
        dts = np.full(_dt.shape, np.datetime64("NaT"), dtype="datetime64[D]")
        valid = ~missing
        if np.any(valid):
            dts[valid] = self._index.offset(_dt[valid], _n[valid])
        return _finalize_date_result(dts, single_value)

    def diff(self, dts: Sequence[DateScalar] | pd.DatetimeIndex | DateArray) -> IntArray:
        """
        Compute the number of business days between dates in a given vector
        of dates.

        Parameters
        ----------

        dts : list of date
            Sequence containing the dates to be differenced.

        Returns
        -------

        numpy.ndarray
            The number of business days between consecutive dates.
        """
        _dts: DateArray = np.asarray(dts, dtype="datetime64[D]")
        if len(_dts) <= 1:
            return np.array([], dtype=np.int_)
        return np.asarray(self.bizdays(_dts[:-1], _dts[1:]), dtype=np.int_)

    def getdate(
        self,
        expr: str | Sequence[str] | npt.NDArray[np.object_],
        ref: GetDateRefInput,
    ) -> np.datetime64 | DateArray:
        """
        Get dates using a month, year, or date reference.

        Parameters
        ----------

        expr : str, list of str
            String specifying the date to be returned.

        ref : int, str, datetime.date, datetime.datetime, numpy.datetime64
            Reference used to resolve the expression.

            - `YYYY-MM` strings refer to a month
            - `YYYY` strings and integers refer to a year
            - date-like values such as `YYYY-MM-DD` refer to a date

        Returns
        -------
        numpy.datetime64 or numpy.ndarray
            Returns dates according to the given reference.
        """
        single_value = not (isseq(expr) or isseq(ref))
        _expr = np.atleast_1d(np.asarray(expr, dtype=object))
        _ref = np.atleast_1d(np.asarray(ref, dtype=object))
        _expr, _ref = recycle_arrays(_expr, _ref)

        missing = np.array([pd.isna(expr_value) or pd.isna(ref_value) for expr_value, ref_value in zip(_expr, _ref)])
        dates = np.full(_expr.shape, np.datetime64("NaT"), dtype="datetime64[D]")
        valid = ~missing

        for idx in np.flatnonzero(valid):
            expr_value = _expr[idx]
            if not isinstance(expr_value, str):
                raise ValueError("getdate expressions must be strings or missing")
            dates[idx] = self._index.getdate(expr_value, _ref[idx])

        return _finalize_date_result(dates, single_value)

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

    @overload
    @classmethod
    def load(cls, *, name: str) -> "Calendar": ...

    @overload
    @classmethod
    def load(cls, *, filename: str) -> "Calendar": ...

    @classmethod
    def load(
        cls,
        *,
        name: str | None = None,
        filename: str | None = None,
    ) -> "Calendar":
        """
        Load calendars from a file.

        Parameters
        ----------

        name : str
            Name of the calendar.
            Packaged calendars delivered with the package are:

            * B3
            * ANBIMA
            * Actual

            Calendars from pandas_market_calendars can also be loaded with the
            prefix "PMC/<calendar name>" when that optional dependency is
            installed.

        filename : str
            JSON calendar file using the R-bizdays-style schema.

        Returns
        -------
        Calendar
            A Calendar object.

        """
        if (name is None) == (filename is None):
            raise ValueError("Provide exactly one of 'name' or 'filename'")

        if filename is not None:
            definition = load_calendar_definition(filename)
            _cal = cls._load_calendar_definition(definition)
        else:
            assert name is not None
            if name.startswith("PMC/"):
                try:
                    import pandas_market_calendars as mcal  # type: ignore[import-untyped]
                except ImportError:
                    raise Exception("pandas_market_calendars must be installed to use PMC calendars")
                cal = mcal.get_calendar(name[4:])  # type: ignore
                hol = cal.holidays()
                _cal = cls([d.item() for d in hol.holidays], weekdays=["Saturday", "Sunday"], name=name)
            else:
                definition = load_packaged_calendar_definition(name)
                _cal = cls._load_calendar_definition(definition)
        return _cal

    @classmethod
    def _load_calendar_definition(cls, definition: CalendarDefinition) -> "Calendar":
        return cls(
            definition.holidays,
            weekdays=definition.weekdays,
            name=definition.name,
            financial=definition.financial,
        )

    def __str__(self) -> str:
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
