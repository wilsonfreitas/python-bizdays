from bizdays import *
import pandas as pd
import numpy as np


actual = Calendar(name="actual")

set_option("mode", "pandas")


def test_isbizday_with_timestamp_and_nat():
    assert pd.isna(actual.isbizday(pd.NaT))


def test_isbizday_with_timestamp():
    dt = pd.to_datetime("2021-12-30")
    assert actual.isbizday(dt)
    dt = pd.Timestamp("2021-12-30")
    assert actual.isbizday(dt)


def test_bizdays_with_timestamp():
    dt1 = pd.to_datetime("2021-12-30")
    dt2 = pd.to_datetime("2021-12-30")
    assert actual.bizdays(dt1, dt2) == 0
    dt1 = pd.to_datetime("2021-12-29")
    dt2 = pd.to_datetime("2021-12-30")
    assert actual.bizdays(dt1, dt2) == 1
    assert actual.bizdays(dt2, dt1) == -1


def test_adjust_with_timestamp():
    dt = pd.to_datetime("2021-12-30")
    assert isinstance(actual.following(dt), pd.Timestamp)
    assert actual.following(dt) == dt.date()
    assert actual.preceding(dt) == dt.date()
    assert actual.modified_following(dt) == dt.date()
    assert actual.modified_preceding(dt) == dt.date()


def test_offset_with_timestamp():
    dt = pd.to_datetime("2021-01-01")
    assert isinstance(actual.offset(dt, 5), pd.Timestamp)
    assert actual.offset(dt, 5) == pd.to_datetime("2021-01-06").date()


def test_isbizday_with_datetimeindex():
    dt = pd.to_datetime(["2021-12-30", "2021-11-30"])
    x = actual.isbizday(dt)
    assert isinstance(x, np.ndarray)
    assert np.all(x)


def test_isbizday_with_datetimeindex_and_nat():
    dt = pd.to_datetime(["2021-12-30", "2021-11-30", None])
    x = actual.isbizday(dt)
    assert isinstance(x, np.ndarray)
    assert x[0]
    assert pd.isna(x[2])
    assert [pd.NaT] == [pd.NaT]


def test_bizdays_with_datetimeindex():
    dt1 = pd.to_datetime(["2021-12-30", "2021-11-30"])
    dt2 = pd.to_datetime(["2021-12-30", "2021-11-30"])
    x = actual.bizdays(dt1, dt2)
    assert isinstance(x, np.ndarray)
    assert np.all(x == np.array([0, 0]))


def test_adjust_with_datetimeindex():
    dt = pd.to_datetime(["2021-12-30", "2021-11-30"])
    x = actual.following(dt)
    assert isinstance(x, pd.DatetimeIndex)
    assert all(actual.following(dt) == dt.date)
    assert all(actual.preceding(dt) == dt.date)
    assert all(actual.modified_following(dt) == dt.date)
    assert all(actual.modified_preceding(dt) == dt.date)


def test_offset_with_datetimeindex():
    dt = pd.to_datetime(["2021-01-01", "2021-01-02"])
    dts = pd.to_datetime(["2021-01-06", "2021-01-07"])
    x = actual.offset(dt, 5)
    assert isinstance(x, pd.DatetimeIndex)

    assert all(x == dts)
    dt = pd.to_datetime(["2021-01-01", "2021-01-02"])
    dts = pd.to_datetime(["2021-01-06", "2021-01-08"])
    assert all(actual.offset(dt, [5, 6]) == dts.date)
    dt = pd.to_datetime("2021-01-01")
    dts = pd.to_datetime(["2021-01-06", "2021-01-07"])
    assert all(actual.offset(dt, [5, 6]) == dts.date)


def test_offset_with_datetimeindex_and_nat():
    dt = pd.to_datetime(["2021-01-01", "2021-01-02", pd.NaT])
    x = actual.offset(dt, 5)
    assert isinstance(x, type(dt))


def test_seq_return_datetimeindex():
    actual.seq("2014-01-02", "2014-01-07")
