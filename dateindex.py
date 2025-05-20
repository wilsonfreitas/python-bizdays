import numpy as np
import numpy.typing as npt

from utils import DateOutOfRange, match


def _create_rev_index(idx: npt.NDArray[np.int_]) -> npt.NDArray[np.int_]:
    return np.cumsum(idx) + 1 - idx.astype(np.int_)


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

        dts: npt.NDArray[np.datetime64] = np.arange(self.startdate, self.enddate + np.timedelta64(1, "D"))
        self._n_dts = dts.astype("datetime64[D]").astype(int)
        _is_holiday = np.isin(self._n_dts, self._n_holidays)
        _is_weekday = np.isin((self._n_dts + 3) % 7, self.weekdays)
        self._is_bizday = np.logical_not(np.logical_or(_is_holiday, _is_weekday))
        self._n_bizdays = self._n_dts[self._is_bizday]
        self._seq_bizdays = np.arange(len(self._n_bizdays))
        self._fwd_index = np.cumsum(self._is_bizday)
        self._rev_index = _create_rev_index(self._is_bizday)
        # self._rev_index = np.cumsum(self._is_bizday[::-1])[::-1]

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
        _m_from = match(d_from, self._n_dts)
        _m_to = match(d_to, self._n_dts)
        # fwd index dif
        _fwd_dif = self._fwd_index[_m_to] - self._fwd_index[_m_from]
        # rev index dif
        _rev_dif = self._rev_index[_m_to] - self._rev_index[_m_from]
        # bizdays calculations ----
        bdays = np.minimum(_fwd_dif, _rev_dif)
        adj_vec = ~(self._is_bizday[_m_from] | self._is_bizday[_m_to])
        adj_vec = adj_vec.astype(int)
        bdays = bdays - adj_vec
        bdays[idx] = -bdays[idx]
        return bdays

    def is_bizday(self, date: npt.NDArray[np.datetime64]) -> npt.NDArray[np.bool_]:
        if any(date < self.startdate) or any(date > self.enddate):
            raise DateOutOfRange("Given date out of calendar range")
        d = date.astype("datetime64[D]").astype(int)
        _m = match(d, self._n_dts)
        return self._is_bizday[_m]
