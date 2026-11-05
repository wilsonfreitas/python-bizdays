import pickle

import numpy as np
import pytest

from bizdays import Calendar, DateOutOfRange


@pytest.fixture(scope="module")
def anbima():
    return Calendar.load(name="ANBIMA")


@pytest.fixture(scope="module")
def b3():
    return Calendar.load(name="B3")


@pytest.fixture(scope="module")
def actual():
    return Calendar(name="actual")


@pytest.fixture(scope="module")
def short():
    return Calendar(weekdays=["Saturday", "Sunday"], startdate="2013-01-01", enddate="2013-12-31")


def test_date_out_of_range_positions():
    assert DateOutOfRange("x").positions.tolist() == [0]
    e = DateOutOfRange("x", [3, 1])
    assert e.positions.tolist() == [1, 3]
    assert e.positions.dtype == np.int64
    assert pickle.loads(pickle.dumps(DateOutOfRange("x", [2]))).positions.tolist() == [2]
    assert str(pickle.loads(pickle.dumps(DateOutOfRange("x", [2])))) == "x"


def test_inrange(anbima):
    r = anbima.inrange(["1999-12-31", "2000-01-01", "2099-12-25", "2099-12-26", None])
    assert isinstance(r, np.ma.MaskedArray)
    assert r.data.tolist() == [False, True, True, False, False]
    assert r.mask.tolist() == [False, False, False, False, True]
    assert r.fill_value == False  # noqa: E712
    s = anbima.inrange("1900-01-01")
    assert isinstance(s, np.bool_) and not s
    assert anbima.inrange(None) is np.ma.masked
    e = anbima.inrange([])
    assert isinstance(e, np.ma.MaskedArray) and len(e) == 0
    with pytest.raises(ValueError, match="invalid date string"):
        anbima.inrange("2024-01")
