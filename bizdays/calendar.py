from __future__ import annotations

import os
import warnings
from collections.abc import Callable, Iterable, Sequence
from datetime import date
from typing import TYPE_CHECKING, Any, TypedDict, TypeAlias, overload

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

if TYPE_CHECKING:
    from pandas._libs.missing import NAType
    from pandas._libs.tslibs.nattype import NaTType

# strings: pd.Series[Any] cannot be subscripted at run time with pandas 2
Missing: TypeAlias = "None | NaTType | NAType"
# date covers datetime and pd.Timestamp
DateScalar: TypeAlias = "str | date | np.datetime64 | Missing"
CountScalar: TypeAlias = "int | float | np.integer[Any] | np.floating[Any] | Missing"
# getdate ref: a year, "YYYY", "YYYY-MM" or a date
RefScalar: TypeAlias = "CountScalar | DateScalar"
ExprScalar: TypeAlias = "str | None"
# the inputs that convert.to_1d accepts as vectors; element types are checked at run time
Vector: TypeAlias = "list[Any] | tuple[Any, ...] | npt.NDArray[Any] | pd.Series[Any] | pd.Index[Any]"
DateArray: TypeAlias = npt.NDArray[np.datetime64]
FloatArray: TypeAlias = npt.NDArray[np.float64]
BoolArray: TypeAlias = npt.NDArray[np.bool_]
BoolMaskedArray: TypeAlias = "np.ma.MaskedArray[Any, np.dtype[np.bool_]]"


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
    return np.unique(dates)


_WEEKDAY_NUMBERS = {
    key: i
    for i, name in enumerate(("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"))
    for key in (name, name[:3])
}


def _parse_weekdays(weekdays: Sequence[object]) -> list[int]:
    """Weekday numbers (Monday = 0) from full or 3-letter English names, any case, without duplicates."""
    if isinstance(weekdays, str) or not isinstance(weekdays, Iterable):
        raise ValueError(f"weekdays must be a list of weekday names, not {weekdays!r}")
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

    holidays : list of datetime.date

    enddate : datetime.date

    startdate : datetime.date

    weekdays : tuple of str

    financial : bool


    Parameters
    ----------
    holidays : 1-D sequence of str, datetime.date, datetime.datetime, pandas.Timestamp or numpy.datetime64
        Holidays; missing values are not allowed.
        Holidays outside ``startdate..enddate`` are ignored.

    weekdays : list
        A list with weekdays representing nonworking days.

        Accepts full or 3-letter English names in any case, such as
        'Saturday', 'sat' or 'SUN'. Duplicates are removed. Giving holidays
        with ``weekdays=None`` emits a ``UserWarning``, as in R bizdays; pass
        ``weekdays=[]`` for a calendar without nonworking weekdays.

    startdate : str, datetime.date, datetime.datetime, pandas.Timestamp or numpy.datetime64
        Calendar's start date

    enddate : str, datetime.date, datetime.datetime, pandas.Timestamp or numpy.datetime64
        Calendar's end date

    name : str
        Calendar's name

    financial : bool
        Defines a financial calendar

    Raises
    ------
    ValueError
        For an invalid weekday name, ``startdate`` after ``enddate``, a
        calendar without business days in its whole range, or an argument of
        the wrong type (for example ``weekdays`` not a list, ``name`` not a
        string, ``financial`` not a bool).
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
        name: str | None = "",
        financial: bool = True,
    ) -> None:
        if name is None:  # the 1.0.19 default
            name = ""
        if not isinstance(name, str):
            raise ValueError(f"name must be a string, not {name!r}")
        if not isinstance(financial, (bool, np.bool_)):
            raise ValueError(f"financial must be True or False, not {financial!r}")
        self.financial: bool = bool(financial)
        self.name: str = name
        self._holidays: DateArray = _constructor_holidays(holidays)
        if weekdays is None and len(self._holidays):
            warnings.warn(
                "You provided holidays without set weekdays.\nThat setup leads to inconsistencies!",
                UserWarning,
                stacklevel=2,
            )
        self._nonwork_weekdays: list[int] = _parse_weekdays([] if weekdays is None else weekdays)
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
            defaults = [
                f"{name} defaults to the {which} holiday"
                for name, given, which in (("startdate", startdate, "first"), ("enddate", enddate, "last"))
                if given is None and len(self._holidays)
            ]
            note = f" ({'; '.join(defaults)})" if defaults else ""
            raise ValueError(f"startdate {start} is after enddate {end}{note}")
        self._holidays = self._holidays[(self._holidays >= start) & (self._holidays <= end)]
        self._index: DateIndex = DateIndex(
            self._holidays,
            np.datetime64(self._startdate.date),
            np.datetime64(self._enddate.date),
            self._nonwork_weekdays,
        )

    @property
    def weekdays(self) -> tuple[str, ...]:
        return tuple(self._weekdays[nwd] for nwd in self._nonwork_weekdays)

    @property
    def startdate(self) -> date:
        assert self._startdate.date is not None
        return self._startdate.date

    @property
    def enddate(self) -> date:
        assert self._enddate.date is not None
        return self._enddate.date

    @property
    def holidays(self) -> list[date]:
        return [d.astype("O") for d in self._holidays]

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
        # a missing count (NaN) is left out: it is not the reason for the error
        args = ", ".join(
            f"{name}={_format_value(values[i])}"
            for name, values in paired.items()
            if not (isinstance(values[i], np.floating) and np.isnan(values[i]))
        )
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

    def _adjust(self, dt: DateScalar | Vector, n: int, modified: bool = False) -> np.datetime64 | DateArray:
        _dt, is_vector = to_dates(dt, "dt")
        out = np.full(_dt.shape, np.datetime64("NaT", "D"), dtype="datetime64[D]")
        self._apply(lambda d: self._index.adjust(d, n, modified), out, np.isnat(_dt), {"dt": _dt})
        return _finalize_date_result(out, not is_vector)

    @overload
    def bizdays(self, date_from: DateScalar, date_to: DateScalar) -> np.float64: ...

    @overload
    def bizdays(self, date_from: Vector, date_to: DateScalar | Vector) -> FloatArray: ...

    @overload
    def bizdays(self, date_from: DateScalar, date_to: Vector) -> FloatArray: ...

    def bizdays(self, date_from: DateScalar | Vector, date_to: DateScalar | Vector) -> np.float64 | FloatArray:
        """
        Calculate the amount of business days between two dates

        Vector arguments must have equal lengths, or one of them must have length 1;
        otherwise ``ValueError``.

        Parameters
        ----------

        date_from : str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
            Start date

        date_to : str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
            End date

        Returns
        -------
        numpy.float64 or numpy.ndarray
            The number of business days between ``date_from`` and ``date_to``,
            as ``float64``. A missing input gives ``NaN``. When no business day
            lies between the two dates the count is 0, unlike R bizdays, which
            returns -1 or +1. With ``financial=False`` the count is the number
            of business days in the closed interval [``date_from``, ``date_to``],
            both ends included, negative when ``date_from > date_to``.

        Raises
        ------
        DateOutOfRange
            An input date, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            Invalid input, such as a string that is not a full ISO date, or a number
            given as a date; or vector lengths that do not match, when neither is 1.
        """
        _date_from, vec_from = to_dates(date_from, "date_from")
        _date_to, vec_to = to_dates(date_to, "date_to")
        single_value = not (vec_from or vec_to)
        raw = {"date_from": _date_from, "date_to": _date_to}
        _date_from, _date_to = broadcast_pair(_date_from, _date_to, "date_from", "date_to")

        bdays = self._apply(
            lambda d_from, d_to: self._index.bizdays(d_from, d_to, self.financial),
            np.full(_date_from.shape, np.nan),
            np.isnat(_date_from) | np.isnat(_date_to),
            {"date_from": _date_from, "date_to": _date_to},
            raw,
        )
        return _finalize_count_result(bdays, single_value)

    @overload
    def isbizday(self, dt: DateScalar) -> np.bool_ | MaskedConstant: ...

    @overload
    def isbizday(self, dt: Vector) -> BoolMaskedArray: ...

    def isbizday(self, dt: DateScalar | Vector) -> np.bool_ | MaskedConstant | BoolMaskedArray:
        """
        Checks if the given dates are business days.

        Parameters
        ----------

        dt : str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
            Dates to be checked

        Returns
        -------

        ``numpy.bool_`` or ``numpy.ma.MaskedArray``
            Returns ``True`` if the given date is a business day and ``False`` otherwise.
            A vector result is always a masked array with ``fill_value=False``;
            a missing scalar gives ``numpy.ma.masked``.

        Raises
        ------
        DateOutOfRange
            An input date, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            Invalid input, such as a string that is not a full ISO date, or a number given as a date.
        """
        _dt, is_vector = to_dates(dt, "dt")
        missing = np.isnat(_dt)
        is_bizday = self._apply(self._index.is_bizday, np.zeros(_dt.shape, dtype=np.bool_), missing, {"dt": _dt})
        return _finalize_flag_result(is_bizday, missing, not is_vector)

    @overload
    def inrange(self, dates: DateScalar) -> np.bool_ | MaskedConstant: ...

    @overload
    def inrange(self, dates: Vector) -> BoolMaskedArray: ...

    def inrange(self, dates: DateScalar | Vector) -> np.bool_ | MaskedConstant | BoolMaskedArray:
        """
        Checks if the given dates lie inside the calendar range.

        Use it to check input dates before a call; it never raises
        :class:`DateOutOfRange`. Results that leave the range (``offset``,
        ``following``, ``getdate``) cannot be checked in advance: catch
        :class:`DateOutOfRange` and read its ``positions`` instead.

        Parameters
        ----------

        dates : str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
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
    def adjust_next(self, dt: Vector) -> DateArray: ...

    def adjust_next(self, dt: DateScalar | Vector) -> np.datetime64 | DateArray:
        """
        Adjusts the given dates to the next business day

        Rolls the given date to the next business day,
        unless it is a business day.

        Parameters
        ----------

        dt : str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
            Dates to be adjusted

        Returns
        -------

        numpy.datetime64 or numpy.ndarray
            Returns the next business day if the given date is not a business day.

        Raises
        ------
        DateOutOfRange
            An input date, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            Invalid input, such as a string that is not a full ISO date, or a number given as a date.
        """
        return self._adjust(dt, 1)

    @overload
    def following(self, dt: DateScalar) -> np.datetime64: ...

    @overload
    def following(self, dt: Vector) -> DateArray: ...

    def following(self, dt: DateScalar | Vector) -> np.datetime64 | DateArray:
        """
        Alias of :meth:`adjust_next`.

        Parameters
        ----------

        dt : str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
            Dates to be adjusted

        Returns
        -------

        numpy.datetime64 or numpy.ndarray
            Returns the next business day if the given date is not a business day.

        Raises
        ------
        DateOutOfRange
            An input date, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            Invalid input, such as a string that is not a full ISO date, or a number given as a date.
        """
        return self.adjust_next(dt)

    @overload
    def modified_following(self, dt: DateScalar) -> np.datetime64: ...

    @overload
    def modified_following(self, dt: Vector) -> DateArray: ...

    def modified_following(self, dt: DateScalar | Vector) -> np.datetime64 | DateArray:
        """
        Adjusts the given dates to the next business day with a small
        difference.

        Rolls the given date to the next business day,
        unless it happens in the next month, in this case
        it returns the previous business day.

        Parameters
        ----------

        dt : str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
            Dates to be adjusted

        Returns
        -------

        numpy.datetime64 or numpy.ndarray
            Returns the next business day unless that would cross into the next month.

        Raises
        ------
        DateOutOfRange
            An input date, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            Invalid input, such as a string that is not a full ISO date, or a number given as a date.
        """
        return self._adjust(dt, 1, modified=True)

    @overload
    def adjust_previous(self, dt: DateScalar) -> np.datetime64: ...

    @overload
    def adjust_previous(self, dt: Vector) -> DateArray: ...

    def adjust_previous(self, dt: DateScalar | Vector) -> np.datetime64 | DateArray:
        """
        Adjusts the given dates to the previous business day

        Rolls the given date to the previous business day,
        unless it is a business day.

        Parameters
        ----------

        dt : str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
            Dates to be adjusted

        Returns
        -------

        numpy.datetime64 or numpy.ndarray
            Returns the previous business day if the given date is not a business day.

        Raises
        ------
        DateOutOfRange
            An input date, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            Invalid input, such as a string that is not a full ISO date, or a number given as a date.
        """
        return self._adjust(dt, -1)

    @overload
    def preceding(self, dt: DateScalar) -> np.datetime64: ...

    @overload
    def preceding(self, dt: Vector) -> DateArray: ...

    def preceding(self, dt: DateScalar | Vector) -> np.datetime64 | DateArray:
        """
        Alias of :meth:`adjust_previous`.

        Parameters
        ----------

        dt : str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
            Dates to be adjusted

        Returns
        -------

        numpy.datetime64 or numpy.ndarray
            Returns the previous business day if the given date is not a business day.

        Raises
        ------
        DateOutOfRange
            An input date, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            Invalid input, such as a string that is not a full ISO date, or a number given as a date.
        """
        return self.adjust_previous(dt)

    @overload
    def modified_preceding(self, dt: DateScalar) -> np.datetime64: ...

    @overload
    def modified_preceding(self, dt: Vector) -> DateArray: ...

    def modified_preceding(self, dt: DateScalar | Vector) -> np.datetime64 | DateArray:
        """
        Adjusts the given dates to the previous business day with a small
        difference.

        Rolls the given date to the previous business day,
        unless it happens in the previous month, in this case
        it returns the following business day.

        Parameters
        ----------

        dt : str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
            Dates to be adjusted

        Returns
        -------

        numpy.datetime64 or numpy.ndarray
            Returns the previous business day unless that would cross into the previous month.

        Raises
        ------
        DateOutOfRange
            An input date, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            Invalid input, such as a string that is not a full ISO date, or a number given as a date.
        """
        return self._adjust(dt, -1, modified=True)

    def seq(self, date_from: str | date | np.datetime64, date_to: str | date | np.datetime64) -> DateArray:
        """
        Sequence of business days.

        Parameters
        ----------

        date_from : str, datetime.date, datetime.datetime, pandas.Timestamp or numpy.datetime64
            Start date

        date_to : str, datetime.date, datetime.datetime, pandas.Timestamp or numpy.datetime64
            End date

        Returns
        -------
        numpy.ndarray
            Returns a NumPy array containing business days only.

        Raises
        ------
        DateOutOfRange
            An input date, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            Invalid input, such as a string that is not a full ISO date, or a number
            given as a date; a vector; or a missing end.
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
    def offset(self, dt: DateScalar, n: CountScalar) -> np.datetime64: ...

    @overload
    def offset(self, dt: Vector, n: CountScalar | Vector) -> DateArray: ...

    @overload
    def offset(self, dt: DateScalar, n: Vector) -> DateArray: ...

    def offset(self, dt: DateScalar | Vector, n: CountScalar | Vector) -> np.datetime64 | DateArray:
        """
        Offsets the given dates by n business days.

        Vector arguments must have equal lengths, or one of them must have length 1;
        otherwise ``ValueError``.

        Parameters
        ----------

        dt : str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
            Dates to be offset

        n : int, numpy integer or float with a whole value, or a 1-D sequence of them
            The number of business days to move; negative moves back. ``NaN``
            is missing and gives ``NaT``.

        Returns
        -------
        numpy.datetime64 or numpy.ndarray
            Returns the given dates offset by the given amount of business days.

        Raises
        ------
        DateOutOfRange
            An input date, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            Invalid input, such as a string that is not a full ISO date, or a number
            given as a date; a count with a fraction; or vector lengths that do not
            match, when neither is 1.
        """
        _dt, vec_dt = to_dates(dt, "dt")
        _n, vec_n = to_counts(n, "n")
        single_value = not (vec_dt or vec_n)
        raw = {"dt": _dt, "n": _n}
        _dt, _n = broadcast_pair(_dt, _n, "dt", "n")
        dts = self._apply(
            lambda d, k: self._index.offset(d, k.astype(np.int64)),
            np.full(_dt.shape, np.datetime64("NaT", "D"), dtype="datetime64[D]"),
            np.isnat(_dt) | np.isnan(_n),
            {"dt": _dt, "n": _n},
            raw,
        )
        return _finalize_date_result(dts, single_value)

    def diff(self, dts: Vector) -> FloatArray:
        """
        Compute the number of business days between dates in a given vector
        of dates.

        Parameters
        ----------

        dts : 1-D sequence of str, datetime.date, datetime.datetime, pandas.Timestamp or numpy.datetime64
            Sequence containing the dates to be differenced.

        Returns
        -------

        numpy.ndarray
            The number of business days between consecutive dates, as ``float64``
            with ``NaN`` for missing values.

        Raises
        ------
        DateOutOfRange
            An input date, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            Invalid input, such as a string that is not a full ISO date, or a number given as a date.
        """
        _dts, _ = to_dates(dts, "dts")
        if len(_dts) <= 1:
            self._bad_inputs({"dts": _dts[:0]}, {"dts": _dts})
            return np.array([], dtype=np.float64)
        return np.asarray(self.bizdays(_dts[:-1], _dts[1:]), dtype=np.float64)

    @overload
    def getdate(self, expr: ExprScalar, ref: RefScalar) -> np.datetime64: ...

    @overload
    def getdate(self, expr: Vector, ref: RefScalar | Vector) -> DateArray: ...

    @overload
    def getdate(self, expr: ExprScalar, ref: Vector) -> DateArray: ...

    def getdate(self, expr: ExprScalar | Vector, ref: RefScalar | Vector) -> np.datetime64 | DateArray:
        """
        Get dates using a month, year, or date reference.

        Vector arguments must have equal lengths, or one of them must have length 1;
        otherwise ``ValueError``.

        Parameters
        ----------

        expr : str, or a 1-D sequence of str
            String specifying the date to be returned, such as ``"first bizday"``,
            ``"next wed"``, ``"last day"`` or ``"1st bizday before 2nd fri"``.
            With a year or month ref it is the n-th day, business day or weekday
            inside the period (``next`` means the first). With a date ref,
            ``<n> day`` is the date plus n days, ``<n> bizday`` is
            ``offset(date, n)`` and ``<n> <weekday>`` the n-th one strictly after
            the date; ``last`` (or ``previous <weekday>``) is the one strictly
            before. Composite expressions need a year or month ref.

        ref : int, float with a whole value, str, datetime.date, datetime.datetime, pandas.Timestamp, numpy.datetime64, or a 1-D sequence of them
            Reference used to resolve the expression. All refs in one call must
            be of one kind, otherwise ``ValueError``.

            - `YYYY-MM` strings refer to a month
            - `YYYY` strings and integers refer to a year
            - date-like values such as `YYYY-MM-DD` refer to a date

        Returns
        -------
        numpy.datetime64 or numpy.ndarray
            Returns dates according to the given reference.

        Raises
        ------
        DateOutOfRange
            A ref period, or a result, lies outside ``startdate..enddate``;
            its ``positions`` attribute gives the index of every bad element.
        ValueError
            An invalid expression or ref, refs of more than one kind, a date that does not
            exist in its period (such as ``5th fri`` in a month with four Fridays), a
            composite expression with a date ref, or vector lengths that do not
            match, when neither is 1.
        """
        _expr, vec_expr = to_exprs(expr)
        _ref, vec_ref = to_refs(ref)
        kinds = {r.kind for r in _ref if r is not None}
        if len(kinds) > 1:
            raise ValueError(
                f"getdate refs must all be of one kind (year, month or date); found: {', '.join(sorted(kinds))}"
            )
        single_value = not (vec_expr or vec_ref)
        # refs are checked even where the expression is missing
        raw_ref = _ref
        raw_bad = np.array([r is not None and not self._index.ref_inrange(r) for r in raw_ref], dtype=np.bool_)
        _expr, _ref = broadcast_pair(_expr, _ref, "expr", "ref")
        # before the range check, so this ValueError wins over DateOutOfRange
        for e, r in zip(_expr, _ref):
            if e is not None and r is not None and e.kind == "composite" and r.kind == "date":
                raise ValueError(
                    f"Composite getdate expressions need a year or month ref, not a date ref: expr={e.text!r}, ref={r}"
                )
        if len(_ref) == 0 and raw_bad.any():
            raise DateOutOfRange(
                f"ref={raw_ref[raw_bad][0]} is out of {self._range_text()} (the result is empty)",
                positions=[],
            )
        bad = np.broadcast_to(raw_bad, _ref.shape).copy()

        missing = pd.isna(_expr) | pd.isna(_ref)
        dates = np.full(_expr.shape, np.datetime64("NaT", "D"), dtype="datetime64[D]")
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

    @overload
    def getbizdays(self, year: CountScalar, month: CountScalar = None) -> np.float64: ...

    @overload
    def getbizdays(self, year: Vector, month: CountScalar | Vector = None) -> FloatArray: ...

    @overload
    def getbizdays(self, year: CountScalar, month: Vector) -> FloatArray: ...

    def getbizdays(
        self, year: CountScalar | Vector, month: CountScalar | Vector = None
    ) -> np.float64 | FloatArray:
        """
        Business days in a whole year, or in one month.

        Vector arguments must have equal lengths, or one of them must have length 1;
        otherwise ``ValueError``.

        Parameters
        ----------

        year : int, numpy integer or float with a whole value, or a 1-D sequence of them
            Year

        month : int, numpy integer or float with a whole value, or a 1-D sequence of them, optional
            Month, 1 to 12. The default ``None`` counts the whole year. Only the
            single value ``None`` means "whole year"; a missing value inside a
            vector, or any other missing scalar, gives ``NaN``.

        Returns
        -------
        numpy.float64 or numpy.ndarray
            The number of business days in each period, as ``float64``, with
            ``NaN`` where ``year`` or ``month`` is missing. ``financial`` makes
            no difference. The whole period must lie inside the calendar range,
            otherwise ``DateOutOfRange``: on ANBIMA, which ends on 2099-12-25,
            ``getbizdays(2099, 11)`` works while ``getbizdays(2099, 12)`` and
            ``getbizdays(2099)`` raise.

        Raises
        ------
        DateOutOfRange
            A period is not fully inside ``startdate..enddate``; its
            ``positions`` attribute gives the index of every bad element.
        ValueError
            A year or month that is not a whole number, a month outside 1 to 12, or
            vector lengths that do not match, when neither is 1.
        """
        _year, vec_y = to_counts(year, "year")
        _month: FloatArray
        if month is None:
            _month, vec_m = np.zeros(1), False  # month 0 = whole year, internal only
        else:
            _month, vec_m = to_counts(month, "month")
            wrong = ~np.isnan(_month) & ((_month < 1) | (_month > 12))
            if wrong.any():
                raise ValueError(f"month must be between 1 and 12 (got {_format_value(_month[wrong][0])})")
        y0, y1 = self.startdate.year, self.enddate.year

        def bad_year(y: FloatArray) -> BoolArray:
            return ~np.isnan(y) & ((y < y0) | (y > y1))

        raw_bad = bad_year(_year)
        _y, _m = broadcast_pair(_year, _month, "year", "month")
        if len(_y) == 0 and raw_bad.any():
            raise DateOutOfRange(
                f"year={_format_value(_year[raw_bad][0])} is out of {self._range_text()} (the result is empty)",
                positions=[],
            )

        def count(y: FloatArray, m: FloatArray | None = None) -> npt.NDArray[np.int64]:
            # the clip keeps huge years out of range without overflow; a NaN month only comes with a bad year
            y_int = np.clip(y, y0 - 1, y1 + 1).astype(np.int64)
            m_int = np.zeros(len(y), dtype=np.int64) if m is None else np.nan_to_num(m, nan=1).astype(np.int64)
            first = ((y_int - 1970) * 12 + np.maximum(m_int, 1) - 1).astype("datetime64[M]")
            months = np.where(m_int == 0, 12, 1).astype("timedelta64[M]")
            last = (first + months).astype("datetime64[D]") - np.timedelta64(1, "D")
            return self._index.count_bizdays(first.astype("datetime64[D]"), last)

        # a non-missing year is range-checked even when its month is missing
        missing = np.isnan(_y) | (np.isnan(_m) & ~bad_year(_y))
        paired = {"year": _y} if month is None else {"year": _y, "month": _m}
        out = self._apply(count, np.full(_y.shape, np.nan), missing, paired)
        return _finalize_count_result(out, not (vec_y or vec_m))

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
        Load a packaged, provider or JSON calendar.

        Give exactly one of ``name`` and ``filename``, as keywords.

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

        Raises
        ------
        ValueError
            Both or neither of ``name`` and ``filename``; ``name`` not a
            string or ``filename`` not a string or path; an unknown packaged
            or provider calendar; a v1 ``.cal`` file; invalid JSON content,
            including a value other than the default for ``adjust.from``
            (``"following"``) or ``adjust.to`` (``"preceding"``).
        FileNotFoundError
            ``filename`` does not exist.
        ImportError
            The provider package for a ``PMC/``, ``XCAL/`` or ``WORK/`` name is
            not installed. The message names the extra to install:
            ``bizdays[pmc]``, ``bizdays[xcal]`` or ``bizdays[work]``.
        """
        if (name is None) == (filename is None):
            raise ValueError("Provide exactly one of 'name' or 'filename'")
        if name is not None and not isinstance(name, str):
            raise ValueError(f"name must be a string, not {name!r}")
        if filename is not None and not isinstance(filename, (str, os.PathLike)):
            raise ValueError(f"filename must be a string or a path, not {filename!r}")

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
            startdate=definition.startdate,
            enddate=definition.enddate,
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
