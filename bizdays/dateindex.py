import numpy as np
import numpy.typing as npt

from bizdays.getdate_parser import (
    CompositeGetDateExpression,
    GetDateExpression,
    GetDateTarget,
    NormalizedRef,
    RelativeGetDateExpression,
    SimpleGetDateExpression,
)
from bizdays.utils import DateOutOfRange


class DateIndex(object):
    # mon = 0, tue = 1, wed = 2, thu = 3, fri = 4
    # sat = 5, sun = 6

    def __init__(
        self,
        holidays: npt.NDArray[np.datetime64],
        startdate: np.datetime64,
        enddate: np.datetime64,
        weekdays: list[int],
    ):
        if holidays.dtype != np.dtype("datetime64[D]"):
            raise ValueError("holidays must be a datetime64[D] array")
        self.weekdays: list[int] = weekdays
        self.holidays = holidays
        self._n_holidays = holidays.astype("datetime64[D]").astype(int)
        self.startdate: np.datetime64 = startdate
        self.enddate: np.datetime64 = enddate

        self._dates: npt.NDArray[np.datetime64] = np.arange(self.startdate, self.enddate + np.timedelta64(1, "D"))
        self._n_dates = self._dates.astype("datetime64[D]").astype(int)
        self._years = self._dates.astype("datetime64[Y]").astype(int) + 1970
        self._months = self._dates.astype("datetime64[M]").astype(int) % 12 + 1
        self._weekday_index = (self._n_dates + 3) % 7
        _is_holiday = np.isin(self._n_dates, self._n_holidays)
        _is_weekday = np.isin(self._weekday_index, self.weekdays)
        self._is_bizday = np.logical_not(np.logical_or(_is_holiday, _is_weekday))
        if not self._is_bizday.any():
            raise ValueError(f"The calendar has no business days in {startdate}..{enddate}")
        self._n_bizdays = self._n_dates[self._is_bizday]
        self._bizdays = self._dates[self._is_bizday]
        self._weekday_dates = [self._dates[self._weekday_index == weekday] for weekday in range(7)]
        self._fwd_index = np.cumsum(self._is_bizday) - 1
        dtype = [("dates", "i8"), ("year", "i8"), ("month", "i8"), ("is_bizday", "i4"), ("weekday", "i4")]
        self._dates_table = np.empty(len(self._dates), dtype=dtype)
        self._dates_table["dates"] = self._n_dates
        self._dates_table["year"] = self._years
        self._dates_table["month"] = self._months
        self._dates_table["is_bizday"] = self._is_bizday.astype(int)
        self._dates_table["weekday"] = self._weekday_index

    def inrange(self, dates: npt.NDArray[np.datetime64]) -> npt.NDArray[np.bool_]:
        """``True`` where a date lies inside ``startdate..enddate`` (``NaT`` gives ``False``)."""
        return (dates >= self.startdate) & (dates <= self.enddate)

    def _pos(self, dates: npt.NDArray[np.datetime64]) -> npt.NDArray[np.int64]:
        return (dates - self.startdate).astype(np.int64)

    def _check(self, *dates: npt.NDArray[np.datetime64]) -> list[npt.NDArray[np.int64]]:
        """Positions of equal-length date arrays; any date outside the range raises."""
        bad = np.zeros(len(dates[0]), dtype=np.bool_)
        for d in dates:
            bad |= ~self.inrange(d)
        if bad.any():
            raise DateOutOfRange("Given date out of calendar range", positions=np.flatnonzero(bad))
        return [self._pos(d) for d in dates]

    def bizdays(
        self,
        date_from: npt.NDArray[np.datetime64],
        date_to: npt.NDArray[np.datetime64],
        financial: bool = True,
    ) -> npt.NDArray[np.int64]:
        p_from, p_to = self._check(date_from, date_to)
        lo, hi = np.minimum(p_from, p_to), np.maximum(p_from, p_to)
        # business days in the closed interval [lo, hi]
        bdays = self._fwd_index[hi] - self._fwd_index[lo] + self._is_bizday[lo]
        if financial:
            # minus one: the two ends move to following(lo) and preceding(hi)
            bdays = np.maximum(bdays - 1, 0)
        return np.where(p_from > p_to, -bdays, bdays)

    def count_bizdays(
        self, first: npt.NDArray[np.datetime64], last: npt.NDArray[np.datetime64]
    ) -> npt.NDArray[np.int64]:
        """Business days in the closed intervals [first, last]; both ends must be in range."""
        p_first, p_last = self._check(first, last)
        return self._fwd_index[p_last] - self._fwd_index[p_first] + self._is_bizday[p_first]

    def is_bizday(self, date: npt.NDArray[np.datetime64]) -> npt.NDArray[np.bool_]:
        (p,) = self._check(date)
        return self._is_bizday[p]

    def _raise_results(self, bad: npt.NDArray[np.bool_]) -> None:
        if bad.any():
            raise DateOutOfRange("Result out of calendar range", positions=np.flatnonzero(bad))

    def _bizday_at(self, k: npt.NDArray[np.int64]) -> npt.NDArray[np.datetime64]:
        # callers raise for k outside 0..m-1 first; the clip only keeps the lookup safe
        return self._bizdays[np.clip(k, 0, len(self._bizdays) - 1)]

    def offset(self, date: npt.NDArray[np.datetime64], n: npt.NDArray[np.int64]) -> npt.NDArray[np.datetime64]:
        if len(date) != len(n):
            raise ValueError("Date and n must have the same length")
        (p,) = self._check(date)
        # _fwd_index is the last business day on or before the date; from a non-business day, -1 is that day
        k = self._fwd_index[p] + n + ((n < 0) & ~self._is_bizday[p])
        self._raise_results((n != 0) & ((k < 0) | (k >= len(self._bizdays))))
        return np.where(n == 0, date, self._bizday_at(k))

    def adjust(
        self, date: npt.NDArray[np.datetime64], n: int, modified: bool = False
    ) -> npt.NDArray[np.datetime64]:
        """Following (``n=1``) or preceding (``n=-1``) business day; ``modified`` stays in the month."""
        (p,) = self._check(date)
        k_pre = self._fwd_index[p]
        k_fol = k_pre + ~self._is_bizday[p]
        ok_pre, ok_fol = k_pre >= 0, k_fol < len(self._bizdays)
        first, other = (self._bizday_at(k_fol), self._bizday_at(k_pre))
        ok_first, ok_other = ok_fol, ok_pre
        if n < 0:
            first, other, ok_first, ok_other = other, first, ok_other, ok_first
        if not modified:
            self._raise_results(~ok_first)
            return first
        month = date.astype("datetime64[M]")
        # where the first choice lies outside the range, it leaves the month for certain only
        # when the whole month side toward that end is inside the range
        if n > 0:
            month_end = (month + np.timedelta64(1, "M")).astype("datetime64[D]") - np.timedelta64(1, "D")
            edge_known = month_end <= self.enddate
        else:
            edge_known = month.astype("datetime64[D]") >= self.startdate
        leaves = np.where(ok_first, first.astype("datetime64[M]") != month, edge_known)
        self._raise_results((~ok_first & ~edge_known) | (leaves & ~ok_other))
        return np.where(leaves, other, first)

    def seq(self, date_from: np.datetime64, date_to: np.datetime64) -> npt.NDArray[np.datetime64]:
        if date_from < self.startdate or date_from > self.enddate:
            raise DateOutOfRange("Given date out of calendar range")
        if date_to < self.startdate or date_to > self.enddate:
            raise DateOutOfRange("Given date out of calendar range")
        d_from = int(date_from.astype(int))
        d_to = int(date_to.astype(int))
        return self._bizdays[(self._n_bizdays >= d_from) & (self._n_bizdays <= d_to)]

    def getdate(self, expr: GetDateExpression, ref: NormalizedRef) -> np.datetime64:
        """Resolve a parsed expression against a normalized ref (both from ``Calendar``)."""
        if ref.kind == "date":
            assert ref.date is not None
            return self._resolve_date_relative_expression(expr, ref.date)

        if isinstance(expr, RelativeGetDateExpression):
            raise ValueError("previous <weekday> needs a date ref")

        period_idx = self._period_indices(ref)
        if isinstance(expr, SimpleGetDateExpression):
            return self._resolve_period_target(expr.count, expr.target, period_idx)
        anchor = self._resolve_period_target(expr.anchor_count, expr.anchor_target, period_idx)
        return self._resolve_relative_target(expr.count, expr.target, expr.operator, anchor)

    def _period_bounds(self, ref: NormalizedRef) -> tuple[int, int]:
        """Positions of the first day of a year or month ref and of the day after it."""
        assert ref.year is not None
        if ref.kind == "month":
            assert ref.month is not None
            first = np.datetime64((ref.year - 1970) * 12 + ref.month - 1, "M")
            after = first + np.timedelta64(1, "M")
        else:
            first = np.datetime64(ref.year - 1970, "Y")
            after = first + np.timedelta64(1, "Y")
        lo = int((first.astype("datetime64[D]") - self.startdate).astype(np.int64))
        hi = int((after.astype("datetime64[D]") - self.startdate).astype(np.int64))
        return lo, hi

    def ref_inrange(self, ref: NormalizedRef) -> bool:
        """A date ref inside the range, or a year or month ref whose whole period is inside it."""
        if ref.kind == "date":
            return ref.date is not None and bool(self.startdate <= ref.date <= self.enddate)
        lo, hi = self._period_bounds(ref)
        return lo >= 0 and hi <= len(self._dates)

    def _period_indices(self, ref: NormalizedRef) -> npt.NDArray[np.int_]:
        if not self.ref_inrange(ref):
            raise DateOutOfRange("Reference period not fully inside the calendar range")
        lo, hi = self._period_bounds(ref)
        return np.arange(lo, hi)

    def _candidate_indices(
        self, target: GetDateTarget, period_idx: npt.NDArray[np.int_]
    ) -> npt.NDArray[np.int_]:
        if target.kind == "day":
            return period_idx
        if target.kind == "bizday":
            return period_idx[self._is_bizday[period_idx]]
        assert target.weekday is not None
        return period_idx[self._weekday_index[period_idx] == target.weekday]

    def _resolve_period_target(
        self, count: int, target: GetDateTarget, period_idx: npt.NDArray[np.int_]
    ) -> np.datetime64:
        candidates = self._candidate_indices(target, period_idx)
        if len(candidates) == 0 or count > len(candidates):
            raise ValueError("The date does not exist in its period")
        pos = count - 1 if count > 0 else count
        return self._dates[int(candidates[pos])]

    def _resolve_relative_target(
        self,
        count: int,
        target: GetDateTarget,
        operator: str,
        anchor: np.datetime64,
    ) -> np.datetime64:
        if target.kind == "day":
            dates = self._dates
            k = int((anchor - self.startdate).astype(np.int64)) + (count if operator == "after" else -count)
        else:
            if target.kind == "bizday":
                dates = self._bizdays
            else:
                assert target.weekday is not None
                dates = self._weekday_dates[target.weekday]
            pos = int(np.searchsorted(dates, anchor, side="right" if operator == "after" else "left"))
            k = pos + count - 1 if operator == "after" else pos - count
        if not 0 <= k < len(dates):
            raise DateOutOfRange("Result out of calendar range")
        return dates[k]

    def _resolve_date_relative_expression(
        self, parsed: GetDateExpression, ref_date: np.datetime64
    ) -> np.datetime64:
        if ref_date < self.startdate or ref_date > self.enddate:
            raise DateOutOfRange("Reference out of calendar range")

        if isinstance(parsed, CompositeGetDateExpression):
            raise ValueError("Composite getdate expressions need a year or month ref, not a date ref")
        if isinstance(parsed, RelativeGetDateExpression):  # previous <weekday>
            return self._resolve_relative_target(1, GetDateTarget("weekday", parsed.weekday), "before", ref_date)
        if parsed.count < 0:  # last <day|bizday|weekday>
            return self._resolve_relative_target(1, parsed.target, "before", ref_date)
        return self._resolve_relative_target(parsed.count, parsed.target, "after", ref_date)
