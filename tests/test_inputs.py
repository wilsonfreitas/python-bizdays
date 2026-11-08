import warnings
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from bizdays import DateOutOfRange
from bizdays.calendar import Calendar


@pytest.fixture(scope="module")
def anbima():
    return Calendar.load(name="ANBIMA")


@pytest.fixture(scope="module")
def actual():
    return Calendar(name="actual")


ONE_DATE_CALLS = [
    pytest.param(lambda c, d: c.isbizday(d), id="isbizday"),
    pytest.param(lambda c, d: c.following(d), id="following"),
    pytest.param(lambda c, d: c.adjust_next(d), id="adjust_next"),
    pytest.param(lambda c, d: c.preceding(d), id="preceding"),
    pytest.param(lambda c, d: c.adjust_previous(d), id="adjust_previous"),
    pytest.param(lambda c, d: c.modified_following(d), id="modified_following"),
    pytest.param(lambda c, d: c.modified_preceding(d), id="modified_preceding"),
    pytest.param(lambda c, d: c.bizdays(d, "2024-01-10"), id="bizdays_from"),
    pytest.param(lambda c, d: c.bizdays("2024-01-10", d), id="bizdays_to"),
    pytest.param(lambda c, d: c.offset(d, 1), id="offset_dt"),
]


def _string_dtype(dt):
    if dt == "nan-string":
        try:
            return pd.StringDtype(na_value=np.nan)
        except TypeError:
            pytest.skip("pandas < 2.3 has no StringDtype(na_value=np.nan)")
    return dt


@pytest.mark.parametrize("call", ONE_DATE_CALLS)
@pytest.mark.parametrize("value", [5, 5.0, True, [5, 6]], ids=["int", "float", "bool", "list"])
def test_numbers_are_not_dates(actual, call, value):
    with pytest.raises(ValueError, match="numbers are not dates"):
        call(actual, value)


@pytest.mark.parametrize("call", ONE_DATE_CALLS)
@pytest.mark.parametrize("value", ["2024-01", "2024", "", "NaT"])
def test_partial_and_empty_strings_are_invalid(anbima, call, value):
    with pytest.raises(ValueError, match="invalid date string"):
        call(anbima, value)


@pytest.mark.parametrize("call", ONE_DATE_CALLS)
@pytest.mark.parametrize(
    "value",
    [np.datetime64("2024-01"), np.datetime64("2024"), np.datetime64("2024-01-04", "W")],
    ids=["M", "Y", "W"],
)
def test_coarse_datetime64_units_rejected(anbima, call, value):
    with pytest.raises(ValueError, match="unit"):
        call(anbima, value)


@pytest.mark.parametrize(
    "value",
    [
        datetime(2024, 1, 5, 23, 30, tzinfo=timezone(timedelta(hours=-3))),
        pd.Timestamp("2024-01-05 23:30", tz="America/Sao_Paulo"),
        pd.DatetimeIndex(["2024-01-05 23:30"], tz="America/Sao_Paulo"),
        pd.Series(pd.to_datetime(["2024-01-05 23:30"]).tz_localize("America/Sao_Paulo")),
        "2024-01-05T23:30-03:00",
    ],
    ids=["datetime", "timestamp", "datetimeindex", "series", "string"],
)
def test_time_zone_uses_wall_clock_date(anbima, value):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert np.atleast_1d(anbima.following(value)).astype(str).tolist() == ["2024-01-05"]


@pytest.mark.parametrize(
    "value",
    [None, float("nan"), pd.NaT, pd.NA, np.datetime64("NaT"), np.ma.masked],
    ids=["None", "nan", "NaT", "NA", "np-NaT", "masked"],
)
def test_missing_scalars(anbima, value):
    assert anbima.isbizday(value) is np.ma.masked
    assert np.isnat(anbima.following(value))
    assert np.isnan(anbima.bizdays(value, "2024-01-10"))
    assert np.isnat(anbima.offset(value, 1))


def test_masked_array_input_is_missing(anbima):
    md = np.ma.masked_array(np.array(["2024-01-02", "2024-01-03"], dtype="datetime64[D]"), mask=[False, True])
    assert anbima.isbizday(md).mask.tolist() == [False, True]
    assert anbima.following(md).astype(str).tolist() == ["2024-01-02", "NaT"]


@pytest.mark.parametrize("dt", ["string", "nan-string"])
def test_pandas_string_dtypes(anbima, dt):
    s = pd.Series(["2024-01-02", None], dtype=_string_dtype(dt))
    r = anbima.isbizday(s)
    assert r.data.tolist() == [True, False]
    assert r.mask.tolist() == [False, True]
    np.testing.assert_array_equal(anbima.bizdays(s, "2024-01-10"), [6.0, np.nan])


@pytest.mark.parametrize("call", ONE_DATE_CALLS)
@pytest.mark.parametrize(
    "value",
    [{"2024-01-02"}, range(2), {"2024-01-02": 1}, "generator"],
    ids=["set", "range", "dict", "generator"],
)
def test_non_vector_iterables_rejected(anbima, call, value):
    if value == "generator":
        value = (s for s in ["2024-01-02"])
    with pytest.raises(ValueError, match="not a supported sequence"):
        call(anbima, value)


def test_zero_d_array_is_a_scalar(anbima):
    d = np.array("2024-01-02", dtype="datetime64[D]")
    assert isinstance(anbima.isbizday(d), np.bool_)
    assert isinstance(anbima.bizdays(d, "2024-01-10"), np.float64)


def test_two_d_input_rejected(anbima):
    df = pd.DataFrame({"a": ["2024-01-02", "2024-01-03"], "b": ["2024-01-04", "2024-01-05"]})
    calls = [
        lambda: anbima.isbizday(np.array([["2024-01-02"]], dtype="datetime64[D]")),
        lambda: anbima.isbizday([["2024-01-02", "2024-01-03"]]),
        lambda: anbima.bizdays(df, "2024-02-01"),
        lambda: anbima.offset(df, 1),
        lambda: anbima.offset("2024-01-02", [[1, 2]]),
    ]
    for call in calls:
        with pytest.raises(ValueError, match="must be 1-D"):
            call()


def test_offset_count_inputs(anbima):
    with pytest.raises(ValueError, match="whole numbers"):
        anbima.offset("2024-01-02", True)
    assert anbima.offset("2024-01-02", 2.0) == np.datetime64("2024-01-04")
    assert anbima.offset("2024-01-02", np.int64(2)) == np.datetime64("2024-01-04")
    assert anbima.offset("2024-01-02", pd.Series([1, np.nan])).astype(str).tolist() == ["2024-01-03", "NaT"]


def test_offset_reads_missing_counts(anbima):
    counts = anbima.bizdays(["2024-01-02", None], "2024-01-10")
    assert anbima.offset(["2024-01-02", "2024-01-03"], counts).astype(str).tolist() == ["2024-01-10", "NaT"]
    n = np.ma.masked_array([1, 2], mask=[False, True])
    assert anbima.offset("2024-01-02", n).astype(str).tolist() == ["2024-01-03", "NaT"]
    assert np.isnat(anbima.offset("2024-01-02", np.ma.masked))


def test_non_missing_partner_still_checked(anbima):
    with pytest.raises(DateOutOfRange):
        anbima.bizdays(None, "1900-01-01")
    with pytest.raises(DateOutOfRange):
        anbima.bizdays([None], "1900-01-01")
    with pytest.raises(DateOutOfRange):
        anbima.offset("1900-01-01", None)
    with pytest.raises(ValueError, match="invalid date string"):
        anbima.offset("abc", None)
    with pytest.raises(ValueError, match="invalid date string"):
        anbima.bizdays("abc", None)


def test_checks_before_empty_shortcut(anbima):
    with pytest.raises(DateOutOfRange):
        anbima.bizdays([], "2300-01-01")
    with pytest.raises(ValueError, match="whole numbers"):
        anbima.offset([], 1.5)
    with pytest.raises(ValueError, match="invalid date string"):
        anbima.bizdays([], "abc")


def test_r_missing_values(actual):
    # R test-bizdays.R: "handling NA values" and "bizdays all NA values"
    dates = ["2013-12-31", "2014-12-31", None]
    np.testing.assert_array_equal(actual.bizdays("2013-01-01", dates), [364, 729, np.nan])
    assert actual.adjust_next(dates).astype(str).tolist() == ["2013-12-31", "2014-12-31", "NaT"]
    assert actual.adjust_previous(dates).astype(str).tolist() == ["2013-12-31", "2014-12-31", "NaT"]
    r = actual.isbizday(dates)
    assert r.data.tolist() == [True, True, False]
    assert r.mask.tolist() == [False, False, True]
    assert np.isnan(actual.bizdays("2013-01-01", None))
    np.testing.assert_array_equal(actual.bizdays(["2013-01-01", "2013-02-01"], None), [np.nan, np.nan])
    np.testing.assert_array_equal(actual.bizdays("2013-01-01", [None, None]), [np.nan, np.nan])


def test_r_negative_bizdays_with_missing(anbima):
    # R test-bizdays.R: "it should return negative bizdays"
    result = anbima.bizdays(["2013-08-21", "2013-01-31", "2013-01-01"], [None, "2013-01-01", "2014-01-01"])
    np.testing.assert_array_equal(result, [np.nan, -21, 252])


def test_r_invalid_date_string(anbima):
    with pytest.raises(ValueError):
        anbima.bizdays("2013-31-02", "2013-01-03")


# --- seq and diff ---


def test_seq_missing_endpoint_raises(anbima):
    for a, b in [(None, "2024-01-10"), ("2024-01-02", None), (pd.NA, "2024-01-10")]:
        with pytest.raises(ValueError, match="missing"):
            anbima.seq(a, b)


def test_seq_rejects_vectors(anbima):
    with pytest.raises(ValueError, match="single dates"):
        anbima.seq(["2024-01-02"], "2024-01-05")
    with pytest.raises(ValueError, match="single dates"):
        anbima.seq(["2024-01-02", "2024-01-03"], "2024-01-05")
    with pytest.raises(ValueError, match="single dates"):
        anbima.seq("2024-01-02", np.array(["2024-01-05"], dtype="datetime64[D]"))


def test_seq_time_part_and_time_zone(anbima):
    calls = [
        (np.datetime64("2024-01-02"), np.datetime64("2024-01-05T10:00")),
        (date(2024, 1, 2), datetime(2024, 1, 5, 10)),
        (pd.Timestamp("2024-01-02 23:30", tz="America/Sao_Paulo"), "2024-01-05"),
    ]
    for a, b in calls:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = anbima.seq(a, b)
        assert result.dtype == np.dtype("datetime64[D]")
        assert result.astype(str).tolist() == ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]


def test_seq_rejects_numbers(actual):
    with pytest.raises(ValueError, match="numbers are not dates"):
        actual.seq(5, 10)


def test_diff_missing_gives_nan(anbima):
    np.testing.assert_array_equal(anbima.diff(["2024-01-02", None, "2024-01-10"]), [np.nan, np.nan])
    np.testing.assert_array_equal(anbima.diff(pd.Series(["2024-01-02", "2024-01-05", None])), [3, np.nan])


def test_diff_checks_range(anbima):
    with pytest.raises(DateOutOfRange):
        anbima.diff(["1900-01-01"])


def test_diff_scalar_and_empty(anbima):
    for x in ["2024-01-02", []]:
        result = anbima.diff(x)
        assert result.dtype == np.float64
        assert result.shape == (0,)


def test_diff_time_zone(anbima):
    s = pd.Series(pd.to_datetime(["2024-01-02 23:30", "2024-01-05 23:30"]).tz_localize("America/Sao_Paulo"))
    assert anbima.diff(s).tolist() == [3.0]


def test_diff_rejects_2d(anbima):
    with pytest.raises(ValueError, match="must be 1-D"):
        anbima.diff([["2024-01-02", "2024-01-10"]])


def test_offset_rejects_time_and_huge_counts(anbima):
    with pytest.raises(ValueError, match="whole numbers"):
        anbima.offset("2024-01-02", np.timedelta64(48, "h"))
    for n in [1e20, 2**63, np.uint64(2**64 - 1), [2**70]]:
        with pytest.raises(ValueError, match="too large"):
            anbima.offset("2024-01-02", n)


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"weekdays": 5}, id="weekdays_int"),
        pytest.param({"weekdays": [], "name": 5}, id="name_int"),
        pytest.param({"weekdays": [], "financial": "x"}, id="financial_str"),
        pytest.param({"weekdays": [], "financial": 1}, id="financial_int"),
    ],
)
def test_constructor_wrong_type_raises_value_error(kwargs):
    with pytest.raises(ValueError):
        Calendar(**kwargs)


@pytest.mark.parametrize("kwargs", [{"name": 5}, {"filename": 5}], ids=["name_int", "filename_int"])
def test_load_wrong_type_raises_value_error(kwargs):
    with pytest.raises(ValueError):
        Calendar.load(**kwargs)


def test_load_accepts_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        Calendar.load(filename=tmp_path / "nope.json")
