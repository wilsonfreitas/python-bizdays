import json

import numpy as np
import pandas as pd
import pytest

import bizdays.calendar as calendar_module
from bizdays import list_calendars
from bizdays.calendar import Calendar


@pytest.fixture(scope="module")
def anbima():
    return Calendar.load(name="ANBIMA")


@pytest.fixture(scope="module")
def actual():
    return Calendar(name="actual")


def test_calendar_load():
    cal = Calendar.load(name="B3")
    assert cal.name == "B3"
    cal = Calendar.load(name="ANBIMA")
    assert cal.name == "ANBIMA"


def test_calendar_load_invalid():
    with pytest.raises(Exception):
        Calendar.load(name="B1")


def test_calendar_load_requires_keyword_arguments():
    with pytest.raises(TypeError):
        Calendar.load("B3")


def test_calendar_load_requires_exactly_one_source():
    with pytest.raises(ValueError, match="exactly one"):
        Calendar.load()
    with pytest.raises(ValueError, match="exactly one"):
        Calendar.load(name="B3", filename="bizdays/data/ANBIMA.json")


def test_calendar_load_json_file(tmp_path):
    filename = tmp_path / "custom.json"
    filename.write_text(
        json.dumps(
            {
                "name": "Custom",
                "weekdays": ["saturday", "sunday"],
                "holidays": ["2024-01-01", "2024-01-03"],
                "financial": False,
                "adjust.from": "following",
                "adjust.to": "preceding",
            }
        ),
        encoding="utf-8",
    )

    cal = Calendar.load(filename=str(filename))
    assert cal.name == "Custom"
    assert cal.weekdays == ("Saturday", "Sunday")
    assert cal.holidays == [
        np.datetime64("2024-01-01").astype(object),
        np.datetime64("2024-01-03").astype(object),
    ]
    assert cal.financial is False
    assert not hasattr(cal, "adjust_from")
    assert not hasattr(cal, "adjust_to")


def test_calendar_load_pmc():
    cal = Calendar.load(name="PMC/B3")
    assert cal.name == "PMC/B3"
    assert len(cal.holidays) > 4000


def test_public_import():
    """Calendar is importable from the top-level package."""
    from bizdays import Calendar
    cal = Calendar.load(name="B3")
    assert cal.name == "B3"


def test_list_calendars_packaged_names():
    result = list_calendars()
    assert result["packaged"] == ["ANBIMA", "B3", "Actual"]


def test_list_calendars_reports_pmc_metadata():
    result = list_calendars()
    pmc = result["pandas_market_calendars"]
    assert pmc["prefix"] == "PMC/"
    assert isinstance(pmc["available"], bool)
    assert isinstance(pmc["calendars"], list)


def test_list_calendars_reports_available_pmc_names():
    result = list_calendars()
    pmc = result["pandas_market_calendars"]
    assert pmc["available"] is True
    assert "B3" in pmc["calendars"]


def test_list_calendars_reports_unavailable_pmc(monkeypatch):
    monkeypatch.setattr(
        calendar_module,
        "_list_pandas_market_calendars",
        lambda: {
            "available": False,
            "prefix": "PMC/",
            "calendars": [],
        },
    )

    result = calendar_module.list_calendars()
    assert result == {
        "packaged": ["ANBIMA", "B3", "Actual"],
        "pandas_market_calendars": {
            "available": False,
            "prefix": "PMC/",
            "calendars": [],
        },
    }


def test_calendar_default_args_are_not_shared():
    """Default holiday/weekday lists must not be shared between Calendar instances."""
    from bizdays.calendar import Calendar
    cal1 = Calendar()
    cal2 = Calendar()
    # The internal _holidays arrays must be distinct objects (not the same list)
    assert cal1._holidays is not cal2._holidays


# --- bizdays tests ---


def test_bizdays_scalar(anbima):
    assert anbima.bizdays("2013-01-02", "2013-01-31") == 21


def test_bizdays_reversed_is_negative(anbima):
    assert anbima.bizdays("2013-01-31", "2013-01-02") == -21


def test_bizdays_same_date(anbima):
    assert anbima.bizdays("2013-01-02", "2013-01-02") == 0


def test_bizdays_vectorized(anbima):
    result = anbima.bizdays(
        ["2013-01-02", "2013-01-02"],
        ["2013-01-31", "2013-02-28"],
    )
    assert list(result) == [21, 39]


def test_bizdays_scalar_returns_numpy_int(actual):
    result = actual.bizdays("2024-01-01", "2024-01-05")
    assert isinstance(result, np.int_)


def test_bizdays_scalar_none_returns_masked(actual):
    result = actual.bizdays(None, "2024-01-05")
    assert np.ma.is_masked(result)


def test_bizdays_vectorized_missing_inputs_return_masked_array(actual):
    result = actual.bizdays(["2024-01-01", None, np.datetime64("NaT")], "2024-01-05")
    assert isinstance(result, np.ma.MaskedArray)
    assert result.dtype == np.int_
    assert result.data.tolist() == [4, 0, 0]
    assert result.mask.tolist() == [False, True, True]


def test_bizdays_tuple_with_none_returns_masked_array(actual):
    result = actual.bizdays(("2013-01-02", "2013-01-03", None), "2013-01-01")
    assert isinstance(result, np.ma.MaskedArray)
    assert result.dtype == np.int_
    assert result.data.tolist() == [-1, -2, 0]
    assert result.mask.tolist() == [False, False, True]


# --- isbizday tests ---


def test_isbizday_true(anbima):
    assert anbima.isbizday("2013-01-02")


def test_isbizday_false_holiday(anbima):
    # 2013-01-01 is a holiday in ANBIMA
    assert not anbima.isbizday("2013-01-01")


def test_isbizday_vectorized(anbima):
    result = anbima.isbizday(["2013-01-01", "2013-01-02"])
    assert list(result) == [False, True]


def test_isbizday_scalar_returns_numpy_bool(actual):
    result = actual.isbizday("2024-01-02")
    assert isinstance(result, np.bool_)


def test_isbizday_scalar_none_returns_masked(actual):
    result = actual.isbizday(None)
    assert np.ma.is_masked(result)


def test_isbizday_vectorized_missing_inputs_return_masked_array(actual):
    result = actual.isbizday(["2024-01-02", None, np.datetime64("NaT")])
    assert isinstance(result, np.ma.MaskedArray)
    assert result.dtype == np.bool_
    assert result.data.tolist() == [True, False, False]
    assert result.mask.tolist() == [False, True, True]


def test_isbizday_with_datetimeindex_and_nat(actual):
    dt = pd.to_datetime(["2021-12-30", "2021-11-30", None])
    result = actual.isbizday(dt)
    assert isinstance(result, np.ndarray)
    assert isinstance(result, np.ma.MaskedArray)
    assert result.dtype == np.bool_
    assert result[0]
    assert result[1]
    assert np.ma.is_masked(result[2])


def test_isbizday_tuple_with_none_returns_masked_array(actual):
    result = actual.isbizday(("2013-01-02", "2013-01-03", None))
    assert isinstance(result, np.ma.MaskedArray)
    assert result.dtype == np.bool_
    assert result.data.tolist() == [True, True, False]
    assert result.mask.tolist() == [False, False, True]


def test_actual_calendar_all_days_are_bizdays(actual):
    # The "actual" calendar has no holidays/weekdays — every day is a business day
    assert actual.isbizday("2013-01-01")   # New Year — holiday in other cals, not here
    assert actual.isbizday("2013-01-05")   # Saturday — non-working in other cals, not here
    assert actual.isbizday("2013-01-06")   # Sunday


# --- offset tests ---


def test_offset_positive(anbima):
    result = anbima.offset("2013-01-02", 1)
    assert str(result) == "2013-01-03"


def test_offset_zero_on_holiday(anbima):
    # offset by 0 returns the same date even if it's a holiday
    result = anbima.offset("2013-01-01", 0)
    assert str(result) == "2013-01-01"


def test_offset_negative(anbima):
    result = anbima.offset("2013-01-03", -1)
    assert str(result) == "2013-01-02"


def test_offset_vectorized(anbima):
    result = anbima.offset(["2013-01-02", "2013-01-03"], [1, 1])
    assert str(result[0]) == "2013-01-03"
    assert str(result[1]) == "2013-01-04"


def test_offset_scalar_returns_numpy_datetime64(actual):
    result = actual.offset("2024-01-05", 1)
    assert isinstance(result, np.datetime64)


def test_offset_scalar_none_returns_nat(actual):
    result = actual.offset(None, 1)
    assert np.isnat(result)


def test_offset_scalar_missing_n_returns_nat(actual):
    result = actual.offset("2024-01-05", None)
    assert np.isnat(result)


def test_offset_all_scalar_missing_combinations_return_nat(anbima):
    assert np.isnat(anbima.offset(None, 1))
    assert np.isnat(anbima.offset("2013-01-02", None))
    assert np.isnat(anbima.offset(None, None))


def test_offset_vectorized_missing_inputs_return_nat(actual):
    result = actual.offset(["2024-01-05", None], [1, np.nan])
    assert result.dtype == np.dtype("datetime64[D]")
    assert str(result[0]) == "2024-01-06"
    assert np.isnat(result[1])


def test_offset_missing_vectors_return_nat(anbima):
    result = anbima.offset([None, None], 1)
    assert result.dtype == np.dtype("datetime64[D]")
    assert np.isnat(result).tolist() == [True, True]

    result = anbima.offset("2013-01-02", [None, None])
    assert result.dtype == np.dtype("datetime64[D]")
    assert np.isnat(result).tolist() == [True, True]

    result = anbima.offset(None, [None, None])
    assert result.dtype == np.dtype("datetime64[D]")
    assert np.isnat(result).tolist() == [True, True]


def test_offset_scalar_date_and_vector_n_returns_array(actual):
    result = actual.offset("2024-01-05", [1, 2])
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.dtype("datetime64[D]")
    assert result.tolist() == [np.datetime64("2024-01-06"), np.datetime64("2024-01-07")]


# --- seq tests ---


def test_seq_returns_only_bizdays(anbima):
    seq = anbima.seq("2013-01-02", "2013-01-11")
    for d in seq:
        assert anbima.isbizday(str(d))


def test_seq_reversed(anbima):
    fwd = anbima.seq("2013-01-02", "2013-01-11")
    rev = anbima.seq("2013-01-11", "2013-01-02")
    assert list(fwd) == list(reversed(list(rev)))


# --- adjust_next / adjust_previous tests ---


def test_adjust_next_on_holiday(anbima):
    # 2013-01-01 (New Year) -> next bizday is 2013-01-02
    result = anbima.adjust_next("2013-01-01")
    assert str(result) == "2013-01-02"


def test_adjust_next_on_bizday(anbima):
    result = anbima.adjust_next("2013-01-02")
    assert str(result) == "2013-01-02"


def test_adjust_previous_on_holiday(anbima):
    result = anbima.adjust_previous("2013-01-01")
    assert str(result) == "2012-12-31"


def test_adjust_previous_on_bizday(anbima):
    result = anbima.adjust_previous("2013-01-02")
    assert str(result) == "2013-01-02"


def test_adjust_next_scalar_returns_numpy_datetime64(actual):
    result = actual.adjust_next("2024-01-06")
    assert isinstance(result, np.datetime64)


@pytest.mark.parametrize(
    ("method_name", "dt", "expected"),
    [
        ("adjust_next", "2013-01-01", "2013-01-02"),
        ("following", "2013-01-01", "2013-01-02"),
        ("adjust_previous", "2013-01-01", "2012-12-31"),
        ("preceding", "2013-01-01", "2012-12-31"),
        ("modified_following", "2022-04-30", "2022-04-29"),
        ("modified_preceding", "2015-03-01", "2015-03-02"),
    ],
)
def test_date_adjust_methods_preserve_nat_for_missing_inputs(anbima, method_name, dt, expected):
    method = getattr(anbima, method_name)
    assert np.isnat(method(None))

    result = method([dt, np.datetime64("NaT")])
    assert result.dtype == np.dtype("datetime64[D]")
    assert str(result[0]) == expected
    assert np.isnat(result[1])


@pytest.mark.parametrize(
    ("method_name", "values", "expected"),
    [
        ("preceding", ("2013-01-01", "2013-01-03", None), ["2012-12-31", "2013-01-03", "NaT"]),
        (
            "modified_preceding",
            ("2013-01-01", "2013-01-03", None),
            ["2013-01-02", "2013-01-03", "NaT"],
        ),
        ("following", ("2013-01-01", "2013-01-03", None), ["2013-01-02", "2013-01-03", "NaT"]),
        (
            "modified_following",
            ("2022-04-30", "2013-01-03", None),
            ["2022-04-29", "2013-01-03", "NaT"],
        ),
    ],
)
def test_adjust_methods_with_none_values_return_nat(anbima, method_name, values, expected):
    result = getattr(anbima, method_name)(values)
    assert result.dtype == np.dtype("datetime64[D]")
    assert result.astype(str).tolist() == expected


@pytest.mark.parametrize(
    "method_name",
    ["preceding", "modified_preceding", "following", "modified_following"],
)
def test_adjust_methods_all_none_return_nat(anbima, method_name):
    result = getattr(anbima, method_name)([None, None])
    assert result.dtype == np.dtype("datetime64[D]")
    assert np.isnat(result).tolist() == [True, True]


# --- modified_following / modified_preceding tests ---


def test_modified_following_stays_in_month(anbima):
    # 2022-04-30 is Saturday; following=2022-05-02 (next month)
    # so modified_following returns the preceding bizday = 2022-04-29
    result = anbima.modified_following("2022-04-30")
    assert str(result)[:7] == "2022-04"  # stays in April


def test_modified_preceding_stays_in_month(anbima):
    # 2015-03-01 is Sunday; preceding=2015-02-27 (previous month)
    # so modified_preceding returns the following bizday = 2015-03-02
    result = anbima.modified_preceding("2015-03-01")
    assert str(result)[:7] == "2015-03"  # stays in March


# --- diff tests ---


def test_diff(anbima):
    dates = ["2013-01-02", "2013-01-03", "2013-01-04"]
    result = anbima.diff(dates)
    assert list(result) == [1, 1]


def test_diff_single_element(anbima):
    result = anbima.diff(["2013-01-02"])
    assert len(result) == 0
