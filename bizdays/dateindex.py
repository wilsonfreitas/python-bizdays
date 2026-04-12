import numpy as np
import numpy.typing as npt

from bizdays.getdate_parser import (
    CompositeGetDateExpression,
    GetDateExpression,
    GetDateTarget,
    RelativeGetDateExpression,
    SimpleGetDateExpression,
    normalize_ref,
    parse_getdate_expression,
)
from bizdays.utils import DateOutOfRange, match


def _create_rev_index(idx: npt.NDArray[np.int_]) -> npt.NDArray[np.int_]:
    x = np.cumsum(idx) + 1 - idx.astype(np.int_)
    m = int(np.sum(idx))
    x[x > m] = m
    return x


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
        self.weekdays: list[int] = weekdays
        self.holidays = holidays
        self._n_holidays = holidays.astype("datetime64[D]").astype(int)
        self.startdate: np.datetime64 = startdate
        self.enddate: np.datetime64 = enddate

        self._dates: npt.NDArray[np.datetime64] = np.arange(self.startdate, self.enddate + np.timedelta64(1, "D"))
        self._n_dates = self._dates.astype("datetime64[D]").astype(int)
        self._n_dates_index: dict[np.int_, int] = dict(zip(self._n_dates, range(len(self._n_dates))))
        self._years = self._dates.astype("datetime64[Y]").astype(int) + 1970
        self._months = self._dates.astype("datetime64[M]").astype(int) % 12 + 1
        self._weekday_index = (self._n_dates + 3) % 7
        _is_holiday = np.isin(self._n_dates, self._n_holidays)
        _is_weekday = np.isin(self._weekday_index, self.weekdays)
        self._is_bizday = np.logical_not(np.logical_or(_is_holiday, _is_weekday))
        self._n_bizdays = self._n_dates[self._is_bizday]
        self._bizdays = self._dates[self._is_bizday]
        self._bizdays_index = np.arange(len(self._n_bizdays))
        self._weekday_dates = [self._dates[self._weekday_index == weekday] for weekday in range(7)]
        self._n_weekday_dates = [dates.astype("datetime64[D]").astype(int) for dates in self._weekday_dates]
        self._fwd_index = np.cumsum(self._is_bizday) - 1
        self._rev_index = _create_rev_index(self._is_bizday) - 1
        assert self._fwd_index[-1] == self._rev_index[-1]
        assert self._fwd_index[-1] == self._bizdays_index[-1]
        assert self._fwd_index[-1] == len(self._n_bizdays) - 1
        # self._rev_index = np.cumsum(self._is_bizday[::-1])[::-1]
        dtype = [("dates", "i8"), ("year", "i8"), ("month", "i8"), ("is_bizday", "i4"), ("weekday", "i4")]
        self._dates_table = np.empty(len(self._dates), dtype=dtype)
        self._dates_table["dates"] = self._n_dates
        self._dates_table["year"] = self._years
        self._dates_table["month"] = self._months
        self._dates_table["is_bizday"] = self._is_bizday.astype(int)
        self._dates_table["weekday"] = self._weekday_index

    def bizdays(
        self, date_from: npt.NDArray[np.datetime64], date_to: npt.NDArray[np.datetime64]
    ) -> npt.NDArray[np.int_]:
        if any(date_from < self.startdate) or any(date_from > self.enddate):
            raise DateOutOfRange("Given date out of calendar range")
        if any(date_to < self.startdate) or any(date_to > self.enddate):
            raise DateOutOfRange("Given date out of calendar range")
        # adjust dates ----
        idx = date_from > date_to
        new_from = date_from.copy()
        new_to = date_to.copy()
        new_from[idx] = date_to[idx]
        new_to[idx] = date_from[idx]
        # create indexes ----
        d_from = new_from.astype("datetime64[D]").astype(int)
        d_to = new_to.astype("datetime64[D]").astype(int)
        _m_from = [self._n_dates_index[val] for val in d_from]
        _m_to = [self._n_dates_index[val] for val in d_to]
        # fwd index dif
        _fwd_dif = self._fwd_index[_m_to] - self._fwd_index[_m_from]
        # rev index dif
        _rev_dif = self._rev_index[_m_to] - self._rev_index[_m_from]
        # bizdays calculations and adjustments ----
        bdays = np.minimum(_fwd_dif, _rev_dif)
        adj_vec = (~(self._is_bizday[_m_from] | self._is_bizday[_m_to])).astype(int)
        bdays = bdays - adj_vec
        # adjust for the case when it is a weekend and the index returns bdays = 1
        _wx = (~self._is_bizday[_m_from]) & (~self._is_bizday[_m_to]) & (np.abs(bdays) == 1)
        bdays[_wx] = 0
        # adjuste for the case when date_from > date_to
        bdays[idx] = -bdays[idx]
        return bdays

    def is_bizday(self, date: npt.NDArray[np.datetime64]) -> npt.NDArray[np.bool_]:
        if any(date < self.startdate) or any(date > self.enddate):
            raise DateOutOfRange("Given date out of calendar range")
        d = date.astype("datetime64[D]").astype(int)
        return self._is_bizday[[self._n_dates_index[val] for val in d]]

    def offset(self, date: npt.NDArray[np.datetime64], n: npt.NDArray[np.int_]) -> npt.NDArray[np.datetime64]:
        if any(date < self.startdate) or any(date > self.enddate):
            raise DateOutOfRange("Given date out of calendar range")
        if len(date) != len(n):
            raise ValueError("Date and n must have the same length")
        ref = np.zeros(len(date), dtype=np.int_)
        ix = n > 0
        d = date.astype(int)
        if len(d[ix]) > 0:
            ref[ix] = self._fwd_index[[self._n_dates_index[val] for val in d[ix]]]
        if len(d[~ix]) > 0:
            ref[~ix] = self._rev_index[[self._n_dates_index[val] for val in d[~ix]]]
        _date = self._bizdays[match(ref + n, self._bizdays_index)]
        # This is to handle the case when n == 0
        # this is necessary because the offset function
        # should return the same date when n == 0
        # even if the date is not a business day
        _date[n == 0] = date[n == 0]
        return _date

    def adjust(self, date: npt.NDArray[np.datetime64], n: int) -> npt.NDArray[np.datetime64]:
        if any(date < self.startdate) or any(date > self.enddate):
            raise DateOutOfRange("Given date out of calendar range")
        d = date.astype(int)
        idx = self._is_bizday[[self._n_dates_index[val] for val in d]]
        while not all(idx):
            d[~idx] = d[~idx] + n
            idx = self._is_bizday[[self._n_dates_index[val] for val in d]]
        return self._dates[[self._n_dates_index[val] for val in d]]

    def seq(self, date_from: np.datetime64, date_to: np.datetime64) -> npt.NDArray[np.datetime64]:
        if date_from < self.startdate or date_from > self.enddate:
            raise DateOutOfRange("Given date out of calendar range")
        if date_to < self.startdate or date_to > self.enddate:
            raise DateOutOfRange("Given date out of calendar range")
        d_from = int(date_from.astype(int))
        d_to = int(date_to.astype(int))
        return self._bizdays[(self._n_bizdays >= d_from) & (self._n_bizdays <= d_to)]

    def getdate(self, expr: str, ref: object) -> np.datetime64:
        parsed = parse_getdate_expression(expr)
        normalized = normalize_ref(ref)

        if normalized.kind == "date":
            assert normalized.date is not None
            return self._resolve_date_relative_expression(parsed, normalized.date)

        if isinstance(parsed, RelativeGetDateExpression):
            raise ValueError("Date-relative expressions require a date ref")

        assert normalized.year is not None
        period_idx = self._period_indices(normalized.year, normalized.month)
        if isinstance(parsed, SimpleGetDateExpression):
            return self._resolve_period_target(parsed.count, parsed.target, period_idx)
        assert isinstance(parsed, CompositeGetDateExpression)
        anchor = self._resolve_period_target(parsed.anchor_count, parsed.anchor_target, period_idx)
        return self._resolve_relative_target(parsed.count, parsed.target, parsed.operator, anchor)

    def _period_indices(self, year: int, month: int | None) -> npt.NDArray[np.int_]:
        mask = self._years == year
        if month is not None:
            mask &= self._months == month
        period_idx = np.flatnonzero(mask).astype(np.int_)
        if len(period_idx) == 0:
            raise DateOutOfRange("Reference out of calendar range")
        return period_idx

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
        if len(candidates) == 0:
            raise ValueError("No matching dates found for getdate expression")
        pos = count - 1 if count > 0 else count
        return self._dates[int(candidates[pos])]

    def _resolve_relative_target(
        self,
        count: int,
        target: GetDateTarget,
        operator: str,
        anchor: np.datetime64,
    ) -> np.datetime64:
        anchor_n = int(anchor.astype("datetime64[D]").astype(int))
        if target.kind == "day":
            anchor_pos = self._n_dates_index[np.int_(anchor_n)]
            delta = count if operator == "after" else -count
            return self._dates[anchor_pos + delta]
        if target.kind == "bizday":
            pos = np.searchsorted(self._n_bizdays, anchor_n, side="right" if operator == "after" else "left")
            if operator == "after":
                return self._bizdays[pos + count - 1]
            return self._bizdays[pos - count]
        assert target.weekday is not None
        dates = self._weekday_dates[target.weekday]
        weekday_numbers = self._n_weekday_dates[target.weekday]
        pos = np.searchsorted(weekday_numbers, anchor_n, side="right" if operator == "after" else "left")
        if operator == "after":
            return dates[pos + count - 1]
        return dates[pos - count]

    def _resolve_date_relative_expression(
        self, parsed: GetDateExpression, ref_date: np.datetime64
    ) -> np.datetime64:
        if ref_date < self.startdate or ref_date > self.enddate:
            raise DateOutOfRange("Reference out of calendar range")

        if isinstance(parsed, RelativeGetDateExpression):
            operator = "after" if parsed.operator == "next" else "before"
            return self._resolve_relative_target(1, GetDateTarget("weekday", parsed.weekday), operator, ref_date)

        if isinstance(parsed, SimpleGetDateExpression) and parsed.target.kind == "weekday" and parsed.count > 0:
            return self._resolve_relative_target(parsed.count, parsed.target, "after", ref_date)

        raise ValueError("Date refs only support weekday expressions such as 'next wed', 'previous mon', or 'second fri'")
