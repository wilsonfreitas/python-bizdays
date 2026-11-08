import warnings
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from bizdays.convert import to_1d, to_counts, to_dates

DAY = np.dtype("datetime64[D]")


def _dates(x):
    values, is_vector = to_dates(x, "dt")
    assert values.dtype == DAY
    return values, is_vector


def test_to_1d_scalar():
    values, missing, is_vector = to_1d("2024-01-02", "dt")
    assert values.shape == (1,)
    assert missing.tolist() == [False]
    assert is_vector is False
    assert to_1d(np.array("2024-01-02", dtype="datetime64[D]"), "dt")[2] is False


@pytest.mark.parametrize(
    "x",
    [
        ["2024-01-02", "2024-01-03"],
        ("2024-01-02", "2024-01-03"),
        np.array(["2024-01-02", "2024-01-03"], dtype="datetime64[D]"),
        pd.Series(["2024-01-02", "2024-01-03"]),
        pd.Index(["2024-01-02", "2024-01-03"]),
        pd.DatetimeIndex(["2024-01-02", "2024-01-03"]),
    ],
)
def test_to_1d_vectors(x):
    values, _, is_vector = to_1d(x, "dt")
    assert is_vector is True
    assert len(values) == 2


@pytest.mark.parametrize(
    "x",
    [{"2024-01-02"}, {"2024-01-02": 1}, range(2), (s for s in ["2024-01-02"])],
    ids=["set", "dict", "range", "generator"],
)
def test_to_1d_rejects_non_vectors(x):
    with pytest.raises(ValueError, match="not a supported sequence"):
        to_1d(x, "dt")


@pytest.mark.parametrize(
    "x",
    [
        np.array([["2024-01-02"]], dtype="datetime64[D]"),
        [["2024-01-02", "2024-01-03"]],
        pd.DataFrame({"a": ["2024-01-02"]}),
    ],
    ids=["array", "list", "dataframe"],
)
def test_to_1d_rejects_2d(x):
    with pytest.raises(ValueError, match="must be 1-D"):
        to_1d(x, "dt")


def test_to_1d_missing():
    x = [None, float("nan"), pd.NaT, pd.NA, np.datetime64("NaT"), np.ma.masked, "2024-01-02", ""]
    assert to_1d(x, "dt")[1].tolist() == [True] * 6 + [False, False]
    md = np.ma.masked_array(np.array(["2024-01-02", "2024-01-03"], dtype="datetime64[D]"), mask=[False, True])
    assert to_1d(md, "dt")[1].tolist() == [False, True]
    _, missing, is_vector = to_1d(np.ma.masked, "dt")
    assert missing.tolist() == [True]
    assert is_vector is False


@pytest.mark.parametrize(
    "s",
    [
        "2024-01-02",
        "2024-01-02T10:30",
        "2024-01-02 10:30:15",
        "2024-01-02T10:30:15.123456",
        "2024-01-02T23:30-03:00",
        "2024-01-02T01:00Z",
    ],
)
def test_to_dates_strings(s):
    assert _dates(s)[0].tolist() == [date(2024, 1, 2)]


@pytest.mark.parametrize("s", ["2024-01", "2024", "2024-1-2", "", "NaT", "abc", "2024-02-30", "2024-01-02x"])
def test_to_dates_rejects_bad_strings(s):
    with pytest.raises(ValueError, match="invalid date string"):
        to_dates(s, "dt")


@pytest.mark.parametrize(
    "x",
    [
        date(2024, 1, 2),
        datetime(2024, 1, 2, 23, 59),
        pd.Timestamp("2024-01-02 23:59"),
        np.datetime64("2024-01-02T23:59:59.999999999"),
    ],
)
def test_to_dates_python_numpy_pandas(x):
    assert _dates(x)[0].tolist() == [date(2024, 1, 2)]


def test_to_dates_mixed_list():
    x = [date(2024, 1, 2), datetime(2024, 1, 3, 5), pd.Timestamp("2024-01-04"), "2024-01-05", None]
    assert _dates(x)[0].astype(str).tolist() == ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "NaT"]


@pytest.mark.parametrize(
    "x",
    [
        datetime(2024, 1, 5, 23, 30, tzinfo=timezone(timedelta(hours=-3))),
        pd.Timestamp("2024-01-05 23:30", tz="America/Sao_Paulo"),
        pd.DatetimeIndex(["2024-01-05 23:30"], tz="America/Sao_Paulo"),
        pd.Series(pd.to_datetime(["2024-01-05 23:30"]).tz_localize("America/Sao_Paulo")),
        "2024-01-05T23:30-03:00",
    ],
    ids=["datetime", "timestamp", "datetimeindex", "series", "string"],
)
def test_to_dates_time_zone_wall_clock(x):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert _dates(x)[0].tolist() == [date(2024, 1, 5)]


@pytest.mark.parametrize(
    "x",
    [5, 5.0, True, np.int64(5), [5, 6], np.array([1.5]), ["2024-01-02", 5], pd.Series([1, 2])],
    ids=["int", "float", "bool", "np-int", "list", "array", "mixed", "series"],
)
def test_to_dates_rejects_numbers(x):
    with pytest.raises(ValueError, match="numbers are not dates"):
        to_dates(x, "dt")


def test_to_dates_all_nan_floats_are_missing():
    assert np.isnat(_dates(pd.Series([np.nan, np.nan]))[0]).all()


@pytest.mark.parametrize(
    "x",
    [
        np.datetime64("2024-01"),
        np.datetime64("2024"),
        np.datetime64("2024-01-04", "W"),
        np.array(["2024-01"], dtype="datetime64[M]"),
    ],
    ids=["M", "Y", "W", "array-M"],
)
def test_to_dates_rejects_coarse_units(x):
    with pytest.raises(ValueError, match="unit"):
        to_dates(x, "dt")


def _string_dtype(dt):
    if dt == "nan-string":
        try:
            return pd.StringDtype(na_value=np.nan)
        except TypeError:
            pytest.skip("pandas < 2.3 has no StringDtype(na_value=np.nan)")
    return dt


@pytest.mark.parametrize("dt", [object, "string", "nan-string"])
def test_to_dates_pandas_string_dtypes(dt):
    s = pd.Series(["2024-01-02", None], dtype=_string_dtype(dt))
    assert _dates(s)[0].astype(str).tolist() == ["2024-01-02", "NaT"]


def test_to_dates_floors_before_epoch():
    x = np.array(["1969-12-31T23:00"], dtype="datetime64[ns]")
    assert _dates(x)[0].astype(str).tolist() == ["1969-12-31"]


def test_to_dates_empty():
    values, is_vector = _dates([])
    assert values.shape == (0,)
    assert is_vector is True


def test_to_counts_values():
    values, _ = to_counts([1, np.int64(2), 3.0, None, np.nan, pd.NA], "n")
    assert values.dtype == np.float64
    np.testing.assert_array_equal(values, [1, 2, 3, np.nan, np.nan, np.nan])
    for x in [pd.Series([1, np.nan]), pd.Series([1, None], dtype="Int64"), np.ma.masked_array([1, 2], mask=[False, True])]:
        values, is_vector = to_counts(x, "n")
        assert values.dtype == np.float64
        assert is_vector is True
        np.testing.assert_array_equal(values, [1, np.nan])
    values, is_vector = to_counts(np.ma.masked, "n")
    assert values.dtype == np.float64
    np.testing.assert_array_equal(values, [np.nan])
    assert is_vector is False


@pytest.mark.parametrize(
    "x",
    [
        1.5,
        True,
        np.bool_(True),
        "1",
        float("inf"),
        [1, "2"],
        np.array([True]),
        np.array(["2024-01-02"], dtype="datetime64[D]"),
    ],
    ids=["fraction", "bool", "np-bool", "str", "inf", "mixed", "bool-array", "dates"],
)
def test_to_counts_rejects(x):
    with pytest.raises(ValueError, match="whole numbers"):
        to_counts(x, "n")


@pytest.mark.parametrize(
    "x",
    [
        np.timedelta64(48, "h"),
        np.timedelta64(2, "D"),
        np.array([1, 2], dtype="timedelta64[D]"),
        [np.timedelta64(1, "D")],
        np.datetime64("2024-01-02"),
        [np.datetime64("2024-01-02")],
    ],
    ids=["td-h", "td-D", "td-array", "td-list", "dt64", "dt64-list"],
)
def test_to_counts_rejects_time_values(x):
    with pytest.raises(ValueError, match="whole numbers"):
        to_counts(x, "n")


@pytest.mark.parametrize(
    "x",
    [1e20, -1e20, 2**63, -(2**63), np.uint64(2**64 - 1), [2**70], np.array([2**60]), 2**53 + 1],
    ids=["1e20", "-1e20", "2**63", "-2**63", "uint64-max", "list-2**70", "array-2**60", "2**53+1"],
)
def test_to_counts_rejects_huge_values(x):
    with pytest.raises(ValueError, match="too large"):
        to_counts(x, "n")


def test_to_counts_accepts_2_pow_53():
    np.testing.assert_array_equal(to_counts(2**53, "n")[0], [2.0**53])


@pytest.mark.parametrize(
    "s",
    ["2024-01-02T99:99", "2024-01-02T24:00", "2024-01-02T23:60", "2024-01-02T23:59:60", "2024-01-02 25:00:00"],
)
def test_to_dates_rejects_bad_times(s):
    with pytest.raises(ValueError, match="invalid date string"):
        to_dates(s, "dt")


def test_to_dates_accepts_edge_times():
    for s in ["2024-01-02T00:00", "2024-01-02T23:59:59.999999999", "2024-01-02 23:59:59+14:00"]:
        assert _dates(s)[0].tolist() == [date(2024, 1, 2)]


@pytest.mark.parametrize(
    "s",
    ["2024-13-01", "2024-00-10", "2024-01-32", "2023-02-29", "2024/01/02", "2024-01-0a", "+024-01-02", "2024-01-02 "],
)
def test_to_dates_rejects_bad_ten_char_strings(s):
    with pytest.raises(ValueError, match="invalid date string"):
        to_dates(np.array([s, "2024-01-02"]), "dt")
    with pytest.raises(ValueError, match="invalid date string"):
        to_dates(["2024-01-02", s], "dt")


def test_to_dates_mixed_lengths_and_date_objects():
    x = ["2024-01-02", "2024-01-03T10:00", None, "2024-01-04"]
    assert _dates(x)[0].astype(str).tolist() == ["2024-01-02", "2024-01-03", "NaT", "2024-01-04"]
    x = [date(2024, 1, 2), None, date(2024, 1, 3)]
    assert _dates(x)[0].astype(str).tolist() == ["2024-01-02", "NaT", "2024-01-03"]
    aware = datetime(2024, 1, 5, 23, 30, tzinfo=timezone(timedelta(hours=-3)))
    x = [date(2024, 1, 2), aware, pd.Timestamp("2024-01-05 23:30", tz="America/Sao_Paulo")]
    assert _dates(x)[0].astype(str).tolist() == ["2024-01-02", "2024-01-05", "2024-01-05"]


def test_to_dates_rejects_structured_array():
    with pytest.raises(ValueError):
        to_dates(np.zeros(2, dtype=[("a", "i4")]), "dates")


@pytest.mark.parametrize("value", ["٢٠٢٤-01-01T00:00", "２０２４-01-01T00:00"])
def test_to_dates_rejects_non_ascii_digits_in_long_strings(value):
    with pytest.raises(ValueError, match="invalid date string"):
        to_dates(value, "dates")
