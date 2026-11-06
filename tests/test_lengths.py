"""Length rules (NumPy 1-D broadcasting) and empty input, contract section 8."""

import warnings

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


def as_str(x):
    return x.astype(str).tolist()


def test_lengths_r_bizdays_set_of_dates(actual):
    dates_from = [f"2013-01-0{d}" for d in range(1, 6)]
    dates_to = [f"2013-01-{d:02d}" for d in range(6, 11)]
    assert actual.bizdays(dates_from, dates_to).tolist() == [5.0] * 5
    assert actual.bizdays("2013-01-02", dates_to).tolist() == [4.0, 5.0, 6.0, 7.0, 8.0]
    assert actual.bizdays(dates_from, "2013-01-08").tolist() == [7.0, 6.0, 5.0, 4.0, 3.0]
    with pytest.raises(ValueError, match="date_from has length 3 and date_to has length 2"):
        actual.bizdays(["2013-01-08"] * 3, ["2013-01-08"] * 2)


def test_lengths_r_add_bizdays(anbima):
    assert as_str(anbima.offset(["2013-01-01", "2013-01-02"], 1)) == ["2013-01-02", "2013-01-03"]
    assert as_str(anbima.offset("2013-01-02", [1, 3])) == ["2013-01-03", "2013-01-07"]
    assert as_str(anbima.offset(["2013-01-01", "2013-01-02"], [1, 3])) == ["2013-01-02", "2013-01-07"]


@pytest.mark.parametrize(
    "call, match",
    [
        (lambda c: c.bizdays(["2024-01-02"] * 2, ["2024-01-10"] * 4), "date_from has length 2 and date_to has length 4"),
        (
            lambda c: c.bizdays(pd.Series(["2024-01-02"] * 2), pd.Series(["2024-01-10"] * 3)),
            "date_from has length 2 and date_to has length 3",
        ),
        (lambda c: c.offset(["2024-01-02"] * 2, [1, 2, 3, 4]), "dt has length 2 and n has length 4"),
        (lambda c: c.offset(["2024-01-02"] * 2, [1, 2, 3]), "dt has length 2 and n has length 3"),
        (lambda c: c.getdate(["first day"] * 2, ["2002-01"] * 4), "expr has length 2 and ref has length 4"),
        (lambda c: c.getdate(["first day"] * 2, ["2002-01"] * 3), "expr has length 2 and ref has length 3"),
    ],
)
def test_lengths_other_combinations_rejected(anbima, call, match):
    with pytest.raises(ValueError, match=match):
        call(anbima)


def test_lengths_length_one_vector_broadcasts(anbima):
    assert anbima.bizdays(["2024-01-02"], ["2024-01-03", "2024-01-04"]).tolist() == [1.0, 2.0]
    assert as_str(anbima.offset(["2024-01-02"], [1, 2])) == ["2024-01-03", "2024-01-04"]
    assert as_str(anbima.getdate(["first bizday"], ["2002-01", "2002-02"])) == ["2002-01-02", "2002-02-01"]
    result = anbima.bizdays(["2024-01-02"], "2024-01-03")
    assert isinstance(result, np.ndarray)
    assert result.tolist() == [1.0]


@pytest.mark.parametrize(
    "call, dtype",
    [
        (lambda c: c.bizdays([], "2024-01-02"), "float64"),
        (lambda c: c.bizdays([], ["2024-01-02"]), "float64"),
        (lambda c: c.bizdays("2024-01-02", []), "float64"),
        (lambda c: c.bizdays([], []), "float64"),
        (lambda c: c.offset([], 1), "datetime64[D]"),
        (lambda c: c.offset([], [1]), "datetime64[D]"),
        (lambda c: c.offset("2024-01-02", []), "datetime64[D]"),
        (lambda c: c.offset([], []), "datetime64[D]"),
        (lambda c: c.getdate([], "2002-01"), "datetime64[D]"),
        (lambda c: c.getdate("first day", []), "datetime64[D]"),
        (lambda c: c.getdate([], []), "datetime64[D]"),
    ],
)
def test_lengths_empty_results(anbima, call, dtype):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = call(anbima)
    assert isinstance(result, np.ndarray)
    assert result.shape == (0,)
    assert result.dtype == np.dtype(dtype)


def test_lengths_empty_with_longer_partner_rejected(anbima):
    with pytest.raises(ValueError, match="date_from has length 0 and date_to has length 2"):
        anbima.bizdays([], ["2024-01-02", "2024-01-03"])
    with pytest.raises(ValueError, match="dt has length 2 and n has length 0"):
        anbima.offset(["2024-01-02", "2024-01-03"], [])
    with pytest.raises(ValueError, match="expr has length 0 and ref has length 2"):
        anbima.getdate([], ["2002-01", "2002-02"])


def test_lengths_checks_before_empty_shortcut(anbima):
    with pytest.raises(DateOutOfRange):
        anbima.bizdays([], ["2300-01-01"])
    with pytest.raises(ValueError, match="whole numbers"):
        anbima.offset([], [1.5])
    with pytest.raises(ValueError, match="Invalid getdate ref"):
        anbima.getdate([], ["2021/02"])
