import numpy as np
import numpy.typing as npt

from bizdays.utils import DateOutOfRange, match


def _create_rev_index(idx: npt.NDArray[np.int_]) -> npt.NDArray[np.int_]:
    x = np.cumsum(idx) + 1 - idx.astype(np.int_)
    m = np.sum(idx)
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
        _is_holiday = np.isin(self._n_dates, self._n_holidays)
        _is_weekday = np.isin((self._n_dates + 3) % 7, self.weekdays)
        self._is_bizday = np.logical_not(np.logical_or(_is_holiday, _is_weekday))
        self._n_bizdays = self._n_dates[self._is_bizday]
        self._bizdays = self._dates[self._is_bizday]
        self._bizdays_index = np.arange(len(self._n_bizdays))
        self._fwd_index = np.cumsum(self._is_bizday) - 1
        self._rev_index = _create_rev_index(self._is_bizday) - 1
        assert self._fwd_index[-1] == self._rev_index[-1]
        assert self._fwd_index[-1] == self._bizdays_index[-1]
        assert self._fwd_index[-1] == len(self._n_bizdays) - 1
        # self._rev_index = np.cumsum(self._is_bizday[::-1])[::-1]
        dtype = [("dates", "i4"), ("year", "i4"), ("month", "i4"), ("is_bizday", "i4"), ("weekday", "i4")]
        self._dates_table = np.array(
            [
                self._n_dates,
                self._dates.astype("datetime64[Y]").astype(int) + 1970,
                self._dates.astype("datetime64[M]").astype(int) % 12 + 1,
                self._is_bizday.astype(int),
                self._dates.astype("datetime64[D]").astype(int) % 7,
            ],
            dtype=dtype,
        )

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
        d_from = date_from.astype(int)
        d_to = date_to.astype(int)
        return self._bizdays[(self._n_bizdays >= d_from) & (self._n_bizdays <= d_to)]
