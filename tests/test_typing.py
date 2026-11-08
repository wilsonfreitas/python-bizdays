"""Static and run-time types of the public API (contract section 6).

mypy checks this module (``assert_type``) and pytest runs it (``isinstance``
and ``dtype``), so each static type is tested next to its run-time type.
"""

import datetime
import importlib.resources
import sys
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt
import pandas as pd
import pytest
from numpy.ma.core import MaskedConstant

from bizdays import Calendar, DateOutOfRange, list_calendars

if TYPE_CHECKING:
    from typing_extensions import assert_type
elif sys.version_info >= (3, 11):
    from typing import assert_type
else:

    def assert_type(val: Any, typ: Any) -> Any:
        return val


cal = Calendar.load(name="B3")

xs: list[str] = ["2024-01-02", "2024-01-03"]
s = pd.Series(xs)
di = pd.DatetimeIndex(xs)
arr = np.array(xs, dtype="datetime64[D]")


def _is_float_array(r: Any) -> None:
    assert isinstance(r, np.ndarray) and r.dtype == np.float64


def _is_date_array(r: Any) -> None:
    assert isinstance(r, np.ndarray) and r.dtype == np.dtype("datetime64[D]")


def _is_flag_array(r: Any) -> None:
    assert isinstance(r, np.ma.MaskedArray) and r.dtype == np.bool_ and r.fill_value == False


def test_py_typed_marker_present() -> None:
    assert importlib.resources.files("bizdays").joinpath("py.typed").is_file()


def test_bizdays_types() -> None:
    r1 = cal.bizdays("2024-01-02", "2024-02-01")
    assert_type(r1, np.float64)
    assert isinstance(r1, np.float64)
    r2 = cal.bizdays(pd.Timestamp("2024-01-02"), datetime.date(2024, 2, 1))
    assert_type(r2, np.float64)
    assert isinstance(r2, np.float64)
    r3 = cal.bizdays(None, "2024-02-01")
    assert_type(r3, np.float64)
    assert isinstance(r3, np.float64) and np.isnan(r3)
    v1 = cal.bizdays(xs, "2024-02-01")
    assert_type(v1, npt.NDArray[np.float64])
    _is_float_array(v1)
    v2 = cal.bizdays(s, "2024-02-01")
    assert_type(v2, npt.NDArray[np.float64])
    _is_float_array(v2)
    v3 = cal.bizdays(di, "2024-02-01")
    assert_type(v3, npt.NDArray[np.float64])
    _is_float_array(v3)
    v4 = cal.bizdays(arr, "2024-02-01")
    assert_type(v4, npt.NDArray[np.float64])
    _is_float_array(v4)
    v5 = cal.bizdays("2024-01-02", s)
    assert_type(v5, npt.NDArray[np.float64])
    _is_float_array(v5)


def test_flag_types() -> None:
    f1 = cal.isbizday("2024-01-02")
    assert_type(f1, np.bool_ | MaskedConstant)
    assert isinstance(f1, np.bool_)
    f2 = cal.inrange("2024-01-02")
    assert_type(f2, np.bool_ | MaskedConstant)
    assert isinstance(f2, np.bool_)
    f3 = cal.isbizday(None)
    assert_type(f3, np.bool_ | MaskedConstant)
    assert f3 is np.ma.masked
    v1 = cal.isbizday(s)
    assert_type(v1, np.ma.MaskedArray[Any, np.dtype[np.bool_]])
    _is_flag_array(v1)
    v2 = cal.inrange(xs)
    assert_type(v2, np.ma.MaskedArray[Any, np.dtype[np.bool_]])
    _is_flag_array(v2)


def test_adjust_types() -> None:
    d = "2024-01-01"
    r1 = cal.adjust_next(d)
    assert_type(r1, np.datetime64)
    assert isinstance(r1, np.datetime64)
    r2 = cal.following(d)
    assert_type(r2, np.datetime64)
    assert isinstance(r2, np.datetime64)
    r3 = cal.modified_following(d)
    assert_type(r3, np.datetime64)
    assert isinstance(r3, np.datetime64)
    r4 = cal.adjust_previous(d)
    assert_type(r4, np.datetime64)
    assert isinstance(r4, np.datetime64)
    r5 = cal.preceding(d)
    assert_type(r5, np.datetime64)
    assert isinstance(r5, np.datetime64)
    r6 = cal.modified_preceding(d)
    assert_type(r6, np.datetime64)
    assert isinstance(r6, np.datetime64)
    v1 = cal.adjust_next(s)
    assert_type(v1, npt.NDArray[np.datetime64])
    _is_date_array(v1)
    v2 = cal.following(s)
    assert_type(v2, npt.NDArray[np.datetime64])
    _is_date_array(v2)
    v3 = cal.modified_following(s)
    assert_type(v3, npt.NDArray[np.datetime64])
    _is_date_array(v3)
    v4 = cal.adjust_previous(s)
    assert_type(v4, npt.NDArray[np.datetime64])
    _is_date_array(v4)
    v5 = cal.preceding(s)
    assert_type(v5, npt.NDArray[np.datetime64])
    _is_date_array(v5)
    v6 = cal.modified_preceding(s)
    assert_type(v6, npt.NDArray[np.datetime64])
    _is_date_array(v6)


def test_offset_types() -> None:
    d = "2024-01-02"
    r1 = cal.offset(d, 1)
    assert_type(r1, np.datetime64)
    assert isinstance(r1, np.datetime64)
    r2 = cal.offset(d, np.int64(1))
    assert_type(r2, np.datetime64)
    assert isinstance(r2, np.datetime64)
    r3 = cal.offset(d, 1.0)
    assert_type(r3, np.datetime64)
    assert isinstance(r3, np.datetime64)
    r4 = cal.offset(d, cal.bizdays("2024-01-02", "2024-01-10"))
    assert_type(r4, np.datetime64)
    assert isinstance(r4, np.datetime64)
    v1 = cal.offset(s, cal.bizdays(s, "2024-02-01"))
    assert_type(v1, npt.NDArray[np.datetime64])
    _is_date_array(v1)
    v2 = cal.offset(d, [1, 2])
    assert_type(v2, npt.NDArray[np.datetime64])
    _is_date_array(v2)
    v3 = cal.offset(xs, 1)
    assert_type(v3, npt.NDArray[np.datetime64])
    _is_date_array(v3)


def test_getdate_types() -> None:
    r1 = cal.getdate("last bizday", "2024-01")
    assert_type(r1, np.datetime64)
    assert isinstance(r1, np.datetime64)
    r2 = cal.getdate("first bizday", 2024)
    assert_type(r2, np.datetime64)
    assert isinstance(r2, np.datetime64)
    v1 = cal.getdate(["last bizday"], "2024-01")
    assert_type(v1, npt.NDArray[np.datetime64])
    _is_date_array(v1)
    v2 = cal.getdate("last bizday", ["2024-01", "2024-02"])
    assert_type(v2, npt.NDArray[np.datetime64])
    _is_date_array(v2)


def test_count_types() -> None:
    r1 = cal.getbizdays(2024)
    assert_type(r1, np.float64)
    assert isinstance(r1, np.float64)
    r2 = cal.getbizdays(2024, 1)
    assert_type(r2, np.float64)
    assert isinstance(r2, np.float64)
    r3 = cal.getbizdays(np.int64(2024), 1.0)
    assert_type(r3, np.float64)
    assert isinstance(r3, np.float64)
    v1 = cal.getbizdays([2024, 2025])
    assert_type(v1, npt.NDArray[np.float64])
    _is_float_array(v1)
    v2 = cal.getbizdays(2024, [1, 2])
    assert_type(v2, npt.NDArray[np.float64])
    _is_float_array(v2)
    v3 = cal.diff(s)
    assert_type(v3, npt.NDArray[np.float64])
    _is_float_array(v3)
    v4 = cal.seq("2024-01-02", "2024-01-10")
    assert_type(v4, npt.NDArray[np.datetime64])
    _is_date_array(v4)


def test_property_types() -> None:
    assert_type(cal.holidays, list[datetime.date])
    assert isinstance(cal.holidays, list) and isinstance(cal.holidays[0], datetime.date)
    assert_type(cal.weekdays, tuple[str, ...])
    assert isinstance(cal.weekdays, tuple) and all(isinstance(w, str) for w in cal.weekdays)
    assert_type(cal.startdate, datetime.date)
    assert isinstance(cal.startdate, datetime.date)
    assert_type(cal.enddate, datetime.date)
    assert isinstance(cal.enddate, datetime.date)
    assert_type(cal.name, str)
    assert isinstance(cal.name, str)
    assert_type(cal.financial, bool)
    assert isinstance(cal.financial, bool)
    packaged = list_calendars()["packaged"]
    assert_type(packaged, list[str])
    assert isinstance(packaged, list) and all(isinstance(n, str) for n in packaged)


def test_date_out_of_range_positions_type() -> None:
    with pytest.raises(DateOutOfRange) as exc:
        cal.offset("2026-12-30", 100000)
    assert_type(exc.value.positions, npt.NDArray[np.int64])
    assert exc.value.positions.dtype == np.int64
    assert exc.value.positions.tolist() == [0]
