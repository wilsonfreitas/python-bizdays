import warnings
from collections.abc import Callable, Sequence
from datetime import date, datetime
from typing import Any, TypedDict, TypeAlias, overload

import numpy as np
import numpy.typing as npt
import pandas as pd
from numpy.ma.core import MaskedConstant

from bizdays.calendarfile import (
    CalendarDefinition,
    get_packaged_calendar_names,
    load_calendar_definition,
    load_packaged_calendar_definition,
)
from bizdays.convert import to_counts, to_dates
from bizdays.date import Date
from bizdays.dateindex import DateIndex
from bizdays.external import (
    load_exchange_calendar,
    load_pandas_market_calendar,
    load_workalendar_calendar,
    list_exchange_calendar_names,
    list_pandas_market_calendar_names,
    list_workalendar_calendar_names,
)
from bizdays.getdate_parser import to_exprs, to_refs
from bizdays.utils import DateOutOfRange, broadcast_pair

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
FloatArray: TypeAlias = npt.NDArray[np.float64]


class CalendarIntegrationListing(TypedDict):
    available: bool
    prefix: str
    calendars: list[str]


class CalendarListing(TypedDict):
    packaged: list[str]
    pandas_market_calendars: CalendarIntegrationListing
    exchange_calendars: CalendarIntegrationListing
    workalendar: CalendarIntegrationListing


def _constructor_date(value: object, name: str) -> np.datetime64:
    dates, is_vector = to_dates(value, name)
    if is_vector:
        raise ValueError(f"{name} must be a single date")
    if np.isnat(dates[0]):
        raise ValueError(f"{name} cannot be missing")
    return dates[0]


def _constructor_holidays(holidays: object) -> DateArray:
    if holidays is None:
        return np.array([], dtype="datetime64[D]")
    dates, is_vector = to_dates(holidays, "holidays")
    if not is_vector:
        raise ValueError("holidays must be a sequence of dates")
    if np.isnat(dates).any():
        raise ValueError("holidays cannot contain missing values")
    return dates


_WEEKDAY_NUMBERS = {
    key: i
    for i, name in enumerate(("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"))
    for key in (name, name[:3])
}


def _parse_weekdays(weekdays: Sequence[object]) -> list[int]:
    """Weekday numbers (Monday = 0) from full or 3-letter English names, any case, without duplicates."""
    out = []
    for item in weekdays:
        key = item.lower() if isinstance(item, str) else None
        if key not in _WEEKDAY_NUMBERS:
            raise ValueError(f"Invalid weekday {item!r}; use English names such as 'Saturday' or 'sat'")
        out.append(_WEEKDAY_NUMBERS[key])
    return list(dict.fromkeys(out))


def _format_value(value: object) -> str:
    # counts arrive as float64; print them as the integers the caller passed
    if isinstance(value, np.floating) and np.isfinite(value):
        return str(int(value))
    return str(value)


def _finalize_date_result(result: DateArray, single_value: bool) -> np.datetime64 | DateArray:
    return result[0] if single_value else result


def _finalize_count_result(result: FloatArray, single_value: bool) -> np.float64 | FloatArray:
    return result[0] if single_value else result


def _finalize_flag_result(
    result: BoolArray, missing: BoolArray, single_value: bool
) -> np.bool_ | MaskedConstant | np.ma.MaskedArray:
    if single_value:
        return np.ma.masked if missing[0] else result[0]
    return np.ma.masked_array(result, mask=missing, fill_value=False)


def _list_pandas_market_calendars() -> CalendarIntegrationListing:
    prefix = "PMC/"
    try:
        calendars = list_pandas_market_calendar_names()
    except ImportError:
        return {
            "available": False,
            "prefix": prefix,
            "calendars": [],
        }
    return {
        "available": True,
        "prefix": prefix,
        "calendars": calendars,
    }


def _list_exchange_calendars() -> CalendarIntegrationListing:
    prefix = "XCAL/"
    try:
        calendars = list_exchange_calendar_names()
    except ImportError:
        return {
            "available": False,
            "prefix": prefix,
            "calendars": [],
        }

    return {
        "available": True,
        "prefix": prefix,
        "calendars": calendars,
    }


def _list_workalendar_calendars() -> CalendarIntegrationListing:
    prefix = "WORK/"
    try:
        calendars = list_workalendar_calendar_names()
    except ImportError:
        return {
            "available": False,
            "prefix": prefix,
            "calendars": [],
        }

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
        "exchange_calendars": _list_exchange_calendars(),
        "workalendar": _list_workalendar_calendars(),
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
        Holidays outside ``startdate..enddate`` are ignored.

    weekdays : list
        A list with weekdays representing nonworking days.

        Accepts full or 3-letter English names in any case, such as
        'Saturday', 'sat' or 'SUN'. Duplicates are removed. Giving holidays
        with ``weekdays=None`` emits a ``UserWarning``, as in R bizdays; pass
        ``weekdays=[]`` for a calendar without nonworking weekdays.

    startdate : str or datetime.date
        Calendar's start date

    enddate : str or datetime.date
        Calendar's end date

    name : str
        Calendar's name

    financial : bool
        Defines a financial calendar

    Raises
    ------
    ValueError
        For an invalid weekday name, ``startdate`` after ``enddate``, or a
        calendar without business days in its whole range.
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
        self.financial: bool = financial
        self.name: str = name
        self._holidays: DateArray = _constructor_holidays(holidays)
        if weekdays is None and len(self._holidays):
            warnings.warn(
                "You provided holidays without set weekdays.\nThat setup leads to inconsistencies!",
                UserWarning,
                stacklevel=2,
            )
        self._nonwork_weekdays: list[int] = _parse_weekdays(weekdays or [])
        self._startdate: Date
        self._enddate: Date
        if len(self._holidays):
            if startdate is not None:
                self._startdate = Date(_constructor_date(startdate, "startdate").astype(object))
            else:
                self._startdate = Date(min(self._holidays).astype("O"))
            if enddate is not None:
                self._enddate = Date(_constructor_date(enddate, "enddate").astype(object))
            else:
                self._enddate = Date(max(self._holidays).astype("O"))
        else:
            if startdate is not None:
                self._startdate = Date(_constructor_date(startdate, "startdate").astype(object))
            else:
                self._startdate = Date("1970-01-01")
            if enddate is not None:
                self._enddate = Date(_constructor_date(enddate, "enddate").astype(object))
            else:
                self._enddate = Date("2071-01-01")
        start, end = np.datetime64(self._startdate.date, "D"), np.datetime64(self._enddate.date, "D")
        if start > end:
            raise ValueError(f"startdate {start} is after enddate {end}")
        self._holidays = self._holidays[(self._holidays >= start) & (self._holidays <= end)]
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

    def _range_text(self) -> str:
        return f"calendar range {self._index.startdate}..{self._index.enddate}"

    def _bad_inputs(
        self, paired: dict[str, npt.NDArray[Any]], raw: dict[str, npt.NDArray[Any]] | None = None
    ) -> BoolArray:
        """Result-space mask of non-missing input dates outside the range.

        ``raw`` holds the arguments before pairing: an empty result still raises
        for an out-of-range date there, with ``positions == []``.
        """
        def outside(values: npt.NDArray[Any]) -> BoolArray:
            if values.dtype.kind != "M":
                return np.zeros(len(values), dtype=np.bool_)
            return ~np.isnat(values) & ~self._index.inrange(values)

        size = len(next(iter(paired.values())))
        bad = np.zeros(size, dtype=np.bool_)
        for values in paired.values():
            bad |= outside(values)
        if size == 0:
            for name, values in (raw or {}).items():
                dates = values[outside(values)]
                if len(dates):
                    raise DateOutOfRange(
                        f"{name}={dates[0]} is out of {self._range_text()} (the result is empty)", positions=[]
                    )
        return bad

    def _raise_range(self, bad: BoolArray, paired: dict[str, npt.NDArray[Any]]) -> None:
        if not bad.any():
            return
        positions = np.flatnonzero(bad)
        i = positions[0]
        args = ", ".join(f"{name}={_format_value(values[i])}" for name, values in paired.items())
        raise DateOutOfRange(
            f"{len(positions)} of {len(bad)} elements out of {self._range_text()}; first at position {i}: {args}",
            positions=positions,
        )

    def _apply(
        self,
        fn: Callable[..., npt.NDArray[Any]],
        out: npt.NDArray[Any],
        missing: BoolArray,
        paired: dict[str, npt.NDArray[Any]],
        raw: dict[str, npt.NDArray[Any]] | None = None,
    ) -> npt.NDArray[Any]:
        """Fill ``out`` with ``fn`` on the good elements; one ``DateOutOfRange`` covers bad inputs and results."""
        bad = self._bad_inputs(paired, raw)
        valid = ~missing & ~bad
        bad_results = np.zeros_like(bad)
        if valid.any():
            try:
                out[valid] = fn(*(values[valid] for values in paired.values()))
            except DateOutOfRange as e:
                bad_results[np.flatnonzero(valid)[e.positions]] = True
        self._raise_range(bad | bad_results, paired)
        return out

    def _adjust(self, dt: DateInput, n: int, modified: bool = False) -> np.datetime64 | DateArray:
        _dt, is_vector = to_dates(dt, "dt")
        out = np.full(_dt.shape, np.datetime64("NaT"), dtype="datetime64[D]")
        self._apply(lambda d: self._index.adjust(d, n, modified), out, np.isnat(_dt), {"dt": _dt})
        return _finalize_date_result(out, not is_vector)

    @overload
    def bizdays(self, date_from: DateScalar, date_to: DateScalar) -> np.float64: ...

    @overload
    def bizdays(self, date_from: DateVector, date_to: DateInput) -> FloatArray: ...

    @overload
    def bizdays(self, date_from: DateScalar, date_to: DateVector) -> FloatArray: ...

    def bizdays(self, date_from: DateInput, date_to: DateInput) -> np.float64 | FloatArray:
        """
        Calculate the amount of business days between two dates

        Vector arguments must have equal lengths, or one of them must have length 1;
        otherwise ``ValueError``.

        Parameters
        ----------

        date_from : datetime.date, datetime.datetime, pandas.Timestamp, str
            Start date

        date_to : datetime.date, datetime.datetime, pandas.Timestamp, str
            End date

        Returns
        -------
        numpy.float64 or numpy.ndarray
            The number of business days between ``date_from`` and ``date_to``,
            as ``float64``. A missing input gives ``NaN``.
        """
        _date_from, vec_from = to_dates(date_from, "date_from")
        _date_to, vec_to = to_dates(date_to, "date_to")
        single_value = not (vec_from or vec_to)
        raw = {"date_from": _date_from, "date_to": _date_to}
        _date_from, _date_to = broadcast_pair(_date_from, _date_to, "date_from", "date_to")

        def count(d_from: DateArray, d_to: DateArray) -> npt.NDArray[np.int64]:
            counts = self._index.bizdays(d_from, d_to)
            if not self.financial:
                counts = counts + np.where(d_from > d_to, -1, 1)
            return counts

        bdays = self._apply(
            count,
            np.full(_date_from.shape, np.nan),
            np.isnat(_date_from) | np.isnat(_date_to),
            {"date_from": _date_from, "date_to": _date_to},
            raw,
        )
        return _finalize_count_result(bdays, single_value)

    @overload
    def isbizday(self, dt: DateScalar) -> np.bool_ | MaskedConstant: ...

    @overload
    def isbizday(self, dt: DateVector) -> np.ma.MaskedArray: ...

    def isbizday(self, dt: DateInput) -> np.bool_ | MaskedConstant | np.ma.MaskedArray:
        """
        Checks if the given dates are business days.

        Parameters
        ----------

        dt : datetime.date, datetime.datetime, pandas.Timestamp, str
            Dates to be checked

        Returns
        -------

        ``numpy.bool_`` or ``numpy.ma.MaskedArray``
            Returns ``True`` if the given date is a business day and ``False`` otherwise.
            A vector result is always a masked array with ``fill_value=False``;
            a missing scalar gives ``numpy.ma.masked``.
        """
        _dt, is_vector = to_dates(dt, "dt")
        missing = np.isnat(_dt)
        is_bizday = self._apply(self._index.is_bizday, np.zeros(_dt.shape, dtype=np.bool_), missing, {"dt": _dt})
        return _finalize_flag_result(is_bizday, missing, not is_vector)

    @overload
    def inrange(self, dates: DateScalar) -> np.bool_ | MaskedConstant: ...

    @overload
    def inrange(self, dates: DateVector) -> np.ma.MaskedArray: ...

    def inrange(self, dates: DateInput) -> np.bool_ | MaskedConstant | np.ma.MaskedArray:
        """
        Checks if the given dates lie inside the calendar range.

        Use it to check input dates before a call; it never raises
        :class:`DateOutOfRange`. Results that leave the range (``offset``,
        ``following``, ``getdate``) cannot be checked in advance: catch
        :class:`DateOutOfRange` and read its ``positions`` instead.

        Parameters
        ----------

        dates : datetime.date, datetime.datetime, pandas.Timestamp, str
            Dates to be checked

        Returns
        -------

        ``numpy.bool_`` or ``numpy.ma.MaskedArray``
            ``True`` where the date lies inside ``startdate..enddate``, both ends
            included. Output rules as for :meth:`isbizday`: a vector result is a
            masked array with ``fill_value=False``; a missing scalar gives
            ``numpy.ma.masked``.
        """
        _x, is_vector = to_dates(dates, "dates")
        return _finalize_flag_result(self._index.inrange(_x), np.isnat(_x), not is_vector)

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
        return self._adjust(dt, 1)

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
        return self._adjust(dt, 1, modified=True)

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
        return self._adjust(dt, -1)

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
        return self._adjust(dt, -1, modified=True)

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
        from_arr, vec_from = to_dates(date_from, "date_from")
        to_arr, vec_to = to_dates(date_to, "date_to")
        if vec_from or vec_to:
            raise ValueError("seq takes single dates, not vectors")
        _from, _to = from_arr[0], to_arr[0]
        if np.isnat(_from) or np.isnat(_to):
            raise ValueError("seq endpoints cannot be missing")
        endpoints = {"date_from": from_arr, "date_to": to_arr}
        self._raise_range(self._bad_inputs(endpoints), endpoints)
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

        Vector arguments must have equal lengths, or one of them must have length 1;
        otherwise ``ValueError``.

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
        _dt, vec_dt = to_dates(dt, "dt")
        _n, vec_n = to_counts(n, "n")
        single_value = not (vec_dt or vec_n)
        raw = {"dt": _dt, "n": _n}
        _dt, _n = broadcast_pair(_dt, _n, "dt", "n")
        dts = self._apply(
            lambda d, k: self._index.offset(d, k.astype(np.int64)),
            np.full(_dt.shape, np.datetime64("NaT"), dtype="datetime64[D]"),
            np.isnat(_dt) | np.isnan(_n),
            {"dt": _dt, "n": _n},
            raw,
        )
        return _finalize_date_result(dts, single_value)

    def diff(self, dts: Sequence[DateScalar] | pd.DatetimeIndex | DateArray) -> FloatArray:
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
            The number of business days between consecutive dates, as ``float64``
            with ``NaN`` for missing values.
        """
        _dts, _ = to_dates(dts, "dts")
        if len(_dts) <= 1:
            self._bad_inputs({"dts": _dts[:0]}, {"dts": _dts})
            return np.array([], dtype=np.float64)
        return np.asarray(self.bizdays(_dts[:-1], _dts[1:]), dtype=np.float64)

    def getdate(
        self,
        expr: str | Sequence[str] | npt.NDArray[np.object_],
        ref: GetDateRefInput,
    ) -> np.datetime64 | DateArray:
        """
        Get dates using a month, year, or date reference.

        Vector arguments must have equal lengths, or one of them must have length 1;
        otherwise ``ValueError``.

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
        _expr, vec_expr = to_exprs(expr)
        _ref, vec_ref = to_refs(ref)
        single_value = not (vec_expr or vec_ref)
        # refs are checked even where the expression is missing
        raw_ref = _ref
        raw_bad = np.array([r is not None and not self._index.ref_inrange(r) for r in raw_ref], dtype=np.bool_)
        _expr, _ref = broadcast_pair(_expr, _ref, "expr", "ref")
        if len(_ref) == 0 and raw_bad.any():
            raise DateOutOfRange(
                f"ref={raw_ref[raw_bad][0]} is out of {self._range_text()} (the result is empty)",
                positions=[],
            )
        bad = np.broadcast_to(raw_bad, _ref.shape).copy()

        missing = pd.isna(_expr) | pd.isna(_ref)
        dates = np.full(_expr.shape, np.datetime64("NaT"), dtype="datetime64[D]")
        for idx in np.flatnonzero(~missing & ~bad):
            try:
                dates[idx] = self._index.getdate(_expr[idx], _ref[idx])
            except DateOutOfRange:  # before ValueError: it is one
                bad[idx] = True
            except ValueError as e:
                raise ValueError(f"{e}: expr={_expr[idx].text!r}, ref={_ref[idx]}") from e

        if bad.any():
            texts = np.array([repr(e.text) if e is not None else "None" for e in _expr], dtype=object)
            self._raise_range(bad, {"expr": texts, "ref": np.array([str(r) for r in _ref], dtype=object)})
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

            Calendars from exchange_calendars can also be loaded with the prefix
            "XCAL/<calendar name>" when that optional dependency is installed.

            Calendars from workalendar can also be loaded with the prefix
            "WORK/<calendar code>" when that optional dependency is installed.

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
                lister, loader = list_pandas_market_calendar_names, load_pandas_market_calendar
                package, extra = "pandas_market_calendars", "pmc"
            elif name.startswith("XCAL/"):
                lister, loader = list_exchange_calendar_names, load_exchange_calendar
                package, extra = "exchange_calendars", "xcal"
            elif name.startswith("WORK/"):
                lister, loader = list_workalendar_calendar_names, load_workalendar_calendar
                package, extra = "workalendar", "work"
            else:
                definition = load_packaged_calendar_definition(name)
                return cls._load_calendar_definition(definition)
            prefix, _, provider_name = name.partition("/")
            try:
                if provider_name not in lister():
                    raise ValueError(f"Unknown {prefix} calendar: {provider_name!r}")
                data = loader(provider_name)
            except ImportError as exc:
                raise ImportError(
                    f'{package} must be installed to use {prefix} calendars: pip install "bizdays[{extra}]"'
                ) from exc
            _cal = cls(
                data["holidays"],
                weekdays=data["weekdays"],
                startdate=data["startdate"],
                enddate=data["enddate"],
                name=name,
            )
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
