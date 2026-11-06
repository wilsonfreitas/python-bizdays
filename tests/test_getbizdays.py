import warnings

import numpy as np
import pandas as pd
import pytest

from bizdays import Calendar, DateOutOfRange

actual = Calendar(name="actual")
anbima = Calendar.load(name="ANBIMA")
b3 = Calendar.load(name="B3")

# R bizdays tests/testthat/test-getbizdays.R; B3.json starts in 2000
B3_YEARS = [248, 246, 249, 250, 249, 249, 246, 245, 249, 246, 247, 249,
            246, 248, 248, 246, 249, 246, 245, 248, 249, 247, 250, 248]  # fmt: skip
B3_MONTHS = {
    2000: [20, 21, 21, 19, 22, 21, 21, 23, 20, 21, 20, 19],
    2001: [21, 18, 22, 20, 22, 20, 21, 23, 19, 22, 20, 18],
    2002: [21, 18, 20, 22, 21, 20, 22, 22, 21, 23, 20, 19],
    2003: [22, 20, 19, 20, 21, 20, 22, 21, 22, 23, 20, 20],
    2004: [21, 18, 23, 20, 21, 21, 21, 22, 21, 20, 20, 21],
    2005: [20, 18, 22, 20, 21, 22, 21, 23, 21, 20, 20, 21],
    2006: [21, 18, 23, 18, 22, 21, 21, 23, 20, 21, 19, 19],
    2007: [21, 18, 22, 20, 22, 20, 21, 23, 19, 22, 19, 18],
    2008: [21, 19, 20, 21, 20, 21, 22, 21, 22, 23, 19, 20],
    2009: [21, 18, 22, 20, 20, 21, 22, 21, 21, 21, 19, 20],
    2010: [19, 18, 23, 20, 21, 21, 21, 22, 21, 20, 20, 21],
    2011: [20, 20, 21, 19, 22, 21, 21, 23, 21, 20, 20, 21],
    2012: [21, 19, 22, 20, 22, 20, 21, 23, 19, 22, 19, 18],
    2013: [21, 18, 20, 22, 21, 20, 22, 22, 21, 23, 19, 19],
    2014: [22, 20, 19, 20, 21, 19, 22, 21, 22, 23, 19, 20],
    2015: [21, 18, 22, 20, 20, 21, 22, 21, 21, 21, 19, 20],
    2016: [19, 19, 22, 20, 21, 22, 21, 23, 21, 20, 20, 21],
    2017: [21, 18, 23, 18, 22, 21, 21, 23, 20, 21, 19, 19],
    2018: [21, 18, 21, 21, 21, 21, 21, 23, 19, 22, 19, 18],
    2019: [21, 20, 19, 21, 22, 19, 22, 22, 21, 23, 19, 19],
    2020: [22, 18, 22, 20, 20, 21, 23, 21, 21, 21, 20, 20],
    2021: [19, 18, 23, 20, 21, 21, 21, 22, 21, 20, 20, 21],
    2022: [21, 19, 22, 19, 22, 21, 21, 23, 21, 20, 20, 21],
    2023: [22, 18, 23, 18, 22, 21, 21, 23, 20, 21, 20, 19],
}
ACTUAL_2021 = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def test_getbizdays_contract_values():
    cases = [
        (actual, (2021,), 365),
        (actual, (2024,), 366),
        (actual, (2024, 2), 29),
        (anbima, (2024,), 253),
        (anbima, (2024, 1), 22),
        (anbima, (2024, 2), 19),
        (anbima, (2024, 12), 21),
    ]
    for cal, args, expected in cases:
        r = cal.getbizdays(*args)
        assert isinstance(r, np.float64)
        assert r == expected


def test_getbizdays_legacy_months():
    assert [actual.getbizdays(2021, m) for m in range(1, 13)] == ACTUAL_2021
    assert [actual.getbizdays(2024, m) for m in range(1, 13)] == [31, 29] + ACTUAL_2021[2:]


def test_getbizdays_vectors():
    r = actual.getbizdays([2002, 2001], [1, 2])
    assert isinstance(r, np.ndarray)
    assert r.dtype == np.float64
    assert r.tolist() == [31.0, 28.0]
    assert actual.getbizdays([2002, 2001], 1).tolist() == [31.0, 31.0]
    assert actual.getbizdays(2024, [1, 2]).tolist() == [31.0, 29.0]
    r = actual.getbizdays([2024])
    assert isinstance(r, np.ndarray)
    assert r.tolist() == [366.0]
    for years in (np.array([2022, 2023, 2024]), pd.Series([2022, 2023, 2024]), (2022, 2023, 2024)):
        assert actual.getbizdays(years).tolist() == [365.0, 365.0, 366.0]


def test_getbizdays_r_actual():
    assert actual.getbizdays(2022) == 365
    assert actual.getbizdays([2022, 2023, 2024]).tolist() == [365, 365, 366]
    assert actual.getbizdays(2022, 12) == 31
    assert actual.getbizdays(2022, [10, 11, 12]).tolist() == [31, 30, 31]
    assert actual.getbizdays(2022, list(range(1, 13))).tolist() == ACTUAL_2021


def test_getbizdays_r_b3_years():
    assert b3.getbizdays(list(range(2000, 2024))).tolist() == B3_YEARS


def test_getbizdays_r_b3_months():
    years = list(B3_MONTHS)
    r = b3.getbizdays(np.repeat(years, 12), np.tile(np.arange(1, 13), len(years)))
    assert r.tolist() == [v for y in years for v in B3_MONTHS[y]]
    for y in years:
        assert sum(B3_MONTHS[y]) == B3_YEARS[y - 2000]


def test_getbizdays_financial_ignored():
    cal = Calendar(holidays=anbima.holidays, weekdays=["Saturday", "Sunday"], financial=False)
    assert cal.getbizdays(2024) == 253


def test_getbizdays_range():
    # ANBIMA covers 2000-01-01..2099-12-25
    assert anbima.getbizdays(2099, 11) == 19
    assert not np.isnan(anbima.getbizdays(2000, 1))
    for args in [(2099, 12), (2099,), (1999, 12), (1e15,)]:
        with pytest.raises(DateOutOfRange) as e:
            anbima.getbizdays(*args)
        assert e.value.positions.tolist() == [0]
    with pytest.raises(DateOutOfRange) as e:
        anbima.getbizdays([2024, 2099, 1999])
    assert e.value.positions.tolist() == [1, 2]
    assert "2 of 3" in str(e.value)
    assert "year=2099" in str(e.value)
    with pytest.raises(DateOutOfRange) as e:
        anbima.getbizdays(2099, [11, 12])
    assert e.value.positions.tolist() == [1]
    assert "year=2099, month=12" in str(e.value)
    with pytest.raises(ValueError):
        anbima.getbizdays(2099, 12)


def test_getbizdays_too_large_year():
    with pytest.raises(ValueError, match="too large"):
        anbima.getbizdays(1e20)


def test_getbizdays_missing():
    for args in [(None,), (np.nan,), (2024, np.nan), (2024, pd.NA), (2024, np.ma.masked), (pd.NA, 1)]:
        r = anbima.getbizdays(*args)
        assert isinstance(r, np.float64)
        assert np.isnan(r)
    np.testing.assert_array_equal(anbima.getbizdays(2024, [1, None]), [22.0, np.nan])
    np.testing.assert_array_equal(anbima.getbizdays([2024, None], 1), [22.0, np.nan])
    np.testing.assert_array_equal(anbima.getbizdays(pd.Series([2024, None])), [253.0, np.nan])
    np.testing.assert_array_equal(anbima.getbizdays(pd.Series([2024, None], dtype="Int64"), 1), [22.0, np.nan])


def test_getbizdays_month_none_is_whole_year():
    assert anbima.getbizdays(2024, None) == 253
    np.testing.assert_array_equal(anbima.getbizdays(2024, [None]), [np.nan])
    assert anbima.getbizdays([2024, 2023], None).tolist() == [253.0, anbima.getbizdays(2023)]


@pytest.mark.parametrize(
    "year, month, match",
    [
        (2024, 0, "between 1 and 12"),
        (2024, 13, "between 1 and 12"),
        (2024, -1, "between 1 and 12"),
        (2024, [1, 13], "between 1 and 12"),
        (2024, np.array([12, 0]), "between 1 and 12"),
        (2024.5, None, "whole numbers"),
        (True, None, "whole numbers"),
        (np.bool_(True), None, "whole numbers"),
        ("2024", None, "whole numbers"),
        (np.datetime64("2024"), None, "whole numbers"),
        ([2024, "2025"], None, "whole numbers"),
        (2024, 1.5, "whole numbers"),
        (2024, True, "whole numbers"),
        (2024, "1", "whole numbers"),
        ([[2024]], None, "must be 1-D"),
        ({2024}, None, "not a supported sequence"),
    ],
)
def test_getbizdays_invalid_values(year, month, match):
    with pytest.raises(ValueError, match=match):
        anbima.getbizdays(year, month)


def test_getbizdays_partner_still_checked():
    with pytest.raises(ValueError, match="between 1 and 12"):
        anbima.getbizdays(None, 13)
    with pytest.raises(ValueError, match="whole numbers"):
        anbima.getbizdays(2024.5, np.nan)
    with pytest.raises(DateOutOfRange) as e:
        anbima.getbizdays(1900, np.nan)
    assert str(e.value).endswith("first at position 0: year=1900")
    assert np.isnan(anbima.getbizdays(2024, np.nan))


def test_getbizdays_lengths():
    with pytest.raises(ValueError, match="year has length 2 and month has length 3"):
        anbima.getbizdays([2024, 2023], [1, 2, 3])
    with pytest.raises(ValueError, match="year has length 0 and month has length 2"):
        anbima.getbizdays([], [1, 2])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for args in [([],), ([], 1), (2024, []), ([], [])]:
            r = anbima.getbizdays(*args)
            assert r.dtype == np.float64
            assert r.shape == (0,)
    with pytest.raises(ValueError, match="between 1 and 12"):
        anbima.getbizdays([], 13)
    with pytest.raises(DateOutOfRange, match=r"year=1900 is out of .*\(the result is empty\)") as e:
        anbima.getbizdays(1900, [])
    assert e.value.positions.tolist() == []
