import json
import warnings
from datetime import date

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
    with pytest.raises(ValueError, match="B1"):
        Calendar.load(name="B1")


def test_calendar_load_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        Calendar.load(filename=str(tmp_path / "nope.json"))
    with pytest.raises(FileNotFoundError):
        Calendar.load(filename=str(tmp_path))


def test_calendar_load_cal_file(tmp_path):
    filename = tmp_path / "x.cal"
    filename.write_text("2001-01-01\n2001-02-26\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no longer supported"):
        Calendar.load(filename=str(filename))


def _write_calendar_json(tmp_path, **adjust):
    filename = tmp_path / "custom.json"
    payload = {"name": "Custom", "weekdays": ["Saturday", "Sunday"], "holidays": ["2024-01-01", "2024-01-03"]}
    payload.update(adjust)
    filename.write_text(json.dumps(payload), encoding="utf-8")
    return str(filename)


def test_calendar_load_json_rejects_non_default_adjust(tmp_path):
    with pytest.raises(ValueError, match="adjust.to"):
        Calendar.load(filename=_write_calendar_json(tmp_path, **{"adjust.to": "following"}))
    with pytest.raises(ValueError, match="adjust.from"):
        Calendar.load(filename=_write_calendar_json(tmp_path, **{"adjust.from": "preceding"}))


def test_calendar_load_json_accepts_default_adjust(tmp_path):
    filename = _write_calendar_json(tmp_path, **{"adjust.from": "following", "adjust.to": "preceding"})
    assert Calendar.load(filename=filename).name == "Custom"


PROVIDERS = [
    ("PMC/B3", "pandas_market_calendar", "pandas_market_calendars", "pmc"),
    ("XCAL/XNYS", "exchange_calendar", "exchange_calendars", "xcal"),
    ("WORK/FR", "workalendar_calendar", "workalendar", "work"),
]


def _patch_provider(monkeypatch, provider, names, loader):
    monkeypatch.setattr(calendar_module, f"list_{provider}_names", names)
    monkeypatch.setattr(calendar_module, f"load_{provider}", loader)


def _raise(error):
    def raiser(*args):
        raise error

    return raiser


@pytest.mark.parametrize("name,provider,package,extra", PROVIDERS)
def test_calendar_load_missing_provider(monkeypatch, name, provider, package, extra):
    _patch_provider(monkeypatch, provider, _raise(ImportError), _raise(ImportError))
    with pytest.raises(ImportError, match=package) as excinfo:
        Calendar.load(name=name)
    assert f"bizdays[{extra}]" in str(excinfo.value)


@pytest.mark.parametrize("name,provider,package,extra", PROVIDERS)
def test_calendar_load_unknown_provider_name(monkeypatch, name, provider, package, extra):
    _patch_provider(monkeypatch, provider, lambda: [name.split("/")[1]], _raise(AssertionError("not called")))
    prefix = name.split("/")[0]
    with pytest.raises(ValueError, match="NOPE") as excinfo:
        Calendar.load(name=f"{prefix}/NOPE")
    assert prefix in str(excinfo.value)


@pytest.mark.parametrize("name,provider,package,extra", PROVIDERS)
def test_calendar_load_provider_error_for_known_name_passes_through(monkeypatch, name, provider, package, extra):
    _patch_provider(monkeypatch, provider, lambda: [name.split("/")[1]], _raise(RuntimeError("provider failed")))
    with pytest.raises(RuntimeError, match="provider failed"):
        Calendar.load(name=name)


def test_calendar_load_prefix_without_slash_is_packaged_lookup():
    with pytest.raises(ValueError, match="Unknown calendar: 'PMC'"):
        Calendar.load(name="PMC")


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
    pytest.importorskip("pandas_market_calendars")
    cal = Calendar.load(name="PMC/B3")
    assert cal.name == "PMC/B3"
    assert len(cal.holidays) > 4000


def test_calendar_load_xcal():
    pytest.importorskip("exchange_calendars")
    cal = Calendar.load(name="XCAL/XNYS")
    assert cal.name == "XCAL/XNYS"
    assert cal.isbizday("2024-01-02")
    assert not cal.isbizday("2024-01-01")
    assert not cal.isbizday("2024-01-06")


def test_calendar_load_work():
    pytest.importorskip("workalendar")
    cal = Calendar.load(name="WORK/FR")
    assert cal.name == "WORK/FR"
    assert not cal.isbizday("2024-01-01")
    assert cal.isbizday("2024-01-02")
    assert not cal.isbizday("2024-01-07")
    assert (cal.startdate, cal.enddate) == (date(1991, 1, 1), date(2051, 12, 31))


def test_calendar_load_pmc_tase_weekmask():
    pytest.importorskip("pandas_market_calendars")
    assert set(Calendar.load(name="PMC/TASE").weekdays) == {"Friday", "Saturday"}


def test_calendar_load_pmc_b3_matches_b3_2024():
    pytest.importorskip("pandas_market_calendars")
    assert Calendar.load(name="PMC/B3").getbizdays(2024) == Calendar.load(name="B3").getbizdays(2024) == 251


def test_calendar_load_work_partial_years():
    pytest.importorskip("workalendar")
    cal = Calendar.load(name="WORK/CN")
    assert cal.startdate > date(1991, 1, 1)


def test_calendar_load_xcal_range_follows_today():
    pytest.importorskip("exchange_calendars")
    cal = Calendar.load(name="XCAL/XNYS")
    assert cal.startdate < date.today() <= cal.enddate


def test_calendar_load_xcal_session_semantics():
    pytest.importorskip("exchange_calendars")
    cal = Calendar.load(name="XCAL/XNYS")
    assert cal.isbizday("2024-11-29")  # early close
    assert not cal.isbizday("2025-01-09")  # closure


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


def test_list_calendars_reports_exchange_metadata():
    result = list_calendars()
    xcal = result["exchange_calendars"]
    assert xcal["prefix"] == "XCAL/"
    assert isinstance(xcal["available"], bool)
    assert isinstance(xcal["calendars"], list)


def test_list_calendars_reports_workalendar_metadata():
    result = list_calendars()
    work = result["workalendar"]
    assert work["prefix"] == "WORK/"
    assert isinstance(work["available"], bool)
    assert isinstance(work["calendars"], list)


def test_list_calendars_reports_available_pmc_names():
    pytest.importorskip("pandas_market_calendars")
    result = list_calendars()
    pmc = result["pandas_market_calendars"]
    assert pmc["available"] is True
    assert "B3" in pmc["calendars"]


def test_list_calendars_reports_available_xcal_names():
    pytest.importorskip("exchange_calendars")
    result = list_calendars()
    xcal = result["exchange_calendars"]
    assert xcal["available"] is True
    assert "XNYS" in xcal["calendars"]


def test_list_calendars_reports_available_workalendar_names():
    pytest.importorskip("workalendar")
    result = list_calendars()
    work = result["workalendar"]
    assert work["available"] is True
    assert "FR" in work["calendars"]


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
    assert result["pandas_market_calendars"] == {
        "available": False,
        "prefix": "PMC/",
        "calendars": [],
    }


def test_list_calendars_reports_unavailable_xcal(monkeypatch):
    monkeypatch.setattr(
        calendar_module,
        "_list_exchange_calendars",
        lambda: {
            "available": False,
            "prefix": "XCAL/",
            "calendars": [],
        },
    )

    result = calendar_module.list_calendars()
    assert result["exchange_calendars"] == {
        "available": False,
        "prefix": "XCAL/",
        "calendars": [],
    }


def test_list_calendars_reports_unavailable_workalendar(monkeypatch):
    monkeypatch.setattr(
        calendar_module,
        "_list_workalendar_calendars",
        lambda: {
            "available": False,
            "prefix": "WORK/",
            "calendars": [],
        },
    )

    result = calendar_module.list_calendars()
    assert result["workalendar"] == {
        "available": False,
        "prefix": "WORK/",
        "calendars": [],
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


def test_bizdays_scalar_returns_numpy_float64(actual):
    result = actual.bizdays("2024-01-01", "2024-01-05")
    assert isinstance(result, np.float64)
    assert result == 4.0


def test_bizdays_scalar_none_returns_nan(actual):
    result = actual.bizdays(None, "2024-01-05")
    assert isinstance(result, np.float64)
    assert np.isnan(result)


def test_bizdays_vectorized_missing_inputs_return_nan(actual):
    result = actual.bizdays(["2024-01-01", None, np.datetime64("NaT")], "2024-01-05")
    assert type(result) is np.ndarray
    assert result.dtype == np.float64
    np.testing.assert_array_equal(result, [4.0, np.nan, np.nan])


def test_bizdays_tuple_with_none_returns_nan(actual):
    result = actual.bizdays(("2013-01-02", "2013-01-03", None), "2013-01-01")
    assert type(result) is np.ndarray
    assert result.dtype == np.float64
    np.testing.assert_array_equal(result, [-1.0, -2.0, np.nan])


def test_bizdays_vector_without_missing_is_float64(anbima):
    result = anbima.bizdays(["2013-01-02"], "2013-01-31")
    assert type(result) is np.ndarray
    assert result.dtype == np.float64
    assert result.tolist() == [21.0]


# financial=False counts the business days in the closed interval [from, to] (values checked with R bizdays)
@pytest.mark.parametrize(
    "date_from, date_to, expected",
    [
        ("2013-06-22", "2013-06-23", 0),  # Sat -> Sun
        ("2013-06-23", "2013-06-22", 0),  # Sun -> Sat
        ("2013-06-22", "2013-06-22", 0),  # Sat -> same Sat
        ("2013-06-23", "2013-06-23", 0),  # Sun -> same Sun
        ("2013-06-22", "2013-06-29", 5),  # Sat -> next Sat
        ("2013-06-29", "2013-06-22", -5),
        ("2013-06-24", "2013-06-25", 2),  # Mon -> Tue
        ("2013-06-24", "2013-06-24", 1),  # Mon -> same Mon
        ("2013-06-25", "2013-06-24", -2),  # Tue -> Mon
        ("2018-03-02", "2018-03-05", 2),  # Fri -> Mon
    ],
)
def test_bizdays_nonfinancial_closed_interval(date_from, date_to, expected):
    cal = Calendar(weekdays=["Saturday", "Sunday"], financial=False)
    assert cal.bizdays(date_from, date_to) == expected


def test_bizdays_nonfinancial_vectorized():
    cal = Calendar(weekdays=["Saturday", "Sunday"], financial=False)
    result = cal.bizdays(["2013-06-22", "2013-06-24", None, "2013-06-25"], ["2013-06-23", "2013-06-25", "2013-06-25", "2013-06-24"])
    np.testing.assert_array_equal(result, [0.0, 2.0, np.nan, -2.0])


def test_bizdays_nonfinancial_anbima(anbima):
    cal = Calendar(holidays=anbima.holidays, weekdays=["Saturday", "Sunday"], financial=False)
    result = cal.bizdays(
        ["2013-01-01", "2013-02-08", "2013-02-15", "2013-12-31", "2013-12-24", "2013-01-01"],
        ["2013-01-02", "2013-02-15", "2013-02-08", "2014-01-01", "2013-12-26", "2014-01-01"],
    )
    np.testing.assert_array_equal(result, [1, 4, -4, 1, 2, 253])
    assert anbima.bizdays("2013-01-01", "2014-01-01") == 252


def test_bizdays_nonfinancial_r_consistency():
    # R test-bizdays.R "it should check consistency in bizdays" (nursery calendar)
    hol = ["2024-01-01", "2024-03-29", "2024-04-01", "2024-05-06", "2024-05-27", "2024-08-26", "2024-12-25", "2024-12-26"]
    weekdays = ["Monday", "Tuesday", "Wednesday", "Saturday", "Sunday"]
    cal = Calendar(hol, weekdays, startdate="2024-01-01", enddate="2024-12-31", financial=False)
    assert cal.bizdays("2024-12-23", "2024-12-29") == 1
    assert cal.bizdays("2024-12-29", "2024-12-23") == -1
    # R: one single day and reversed sign on a non-financial actual calendar
    actual = Calendar(name="actual-no-fin", financial=False)
    assert actual.bizdays("2021-12-30", "2021-12-30") == 1
    assert -actual.bizdays("2014-07-12", "2013-07-12") == actual.bizdays("2013-07-12", "2014-07-12")


def test_bizdays_nonfinancial_r_usa2017_ends():
    # R test-calendar.R "it should create non financial calendars": non-business ends do not count
    hd = ["2017-01-02", "2017-01-16", "2017-02-20", "2017-05-29", "2017-07-04", "2017-09-04", "2017-10-09"]
    hd += ["2017-11-10", "2017-11-23", "2017-12-25"]
    cal = Calendar(hd, ["Saturday", "Sunday"], startdate="2017-01-01", enddate="2017-12-31", financial=False)
    assert cal.bizdays("2017-09-04", "2017-09-08") == cal.bizdays("2017-09-04", "2017-09-09") == 4
    assert cal.bizdays("2017-09-04", "2017-09-08") == cal.bizdays("2017-09-05", "2017-09-08")
    assert cal.bizdays("2017-09-05", "2017-09-09") == cal.bizdays("2017-09-05", "2017-09-08")


def test_diff_nonfinancial_is_pairwise_bizdays():
    cal = Calendar(weekdays=["Saturday", "Sunday"], financial=False)
    dts = ["2013-06-22", "2013-06-23", "2013-06-24", "2013-06-25", "2013-06-29"]
    result = cal.diff(dts)
    np.testing.assert_array_equal(result, cal.bizdays(dts[:-1], dts[1:]))
    np.testing.assert_array_equal(result, [0, 1, 2, 4])  # not additive: sum 7 != bizdays(first, last) == 5
    assert cal.bizdays(dts[0], dts[-1]) == 5


def test_isbizday_vector_is_always_masked_array(anbima):
    r = anbima.isbizday(["2013-01-01", "2013-01-02"])
    assert isinstance(r, np.ma.MaskedArray)
    assert r.fill_value == False
    assert np.ma.getmaskarray(r).tolist() == [False, False]
    assert r.data.tolist() == [False, True]


def test_isbizday_masked_fill_value_is_false(actual):
    r = actual.isbizday(["2024-01-02", None])
    assert r.fill_value == False
    assert r.filled().tolist() == [True, False]


def test_diff_returns_float64(anbima):
    result = anbima.diff(["2013-01-02", "2013-01-03", "2013-01-04"])
    assert result.dtype == np.float64
    assert result.tolist() == [1.0, 1.0]
    result = anbima.diff(["2013-01-02"])
    assert result.dtype == np.float64
    assert len(result) == 0


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


# --- constructor date rules (WIL-149) ---


def test_calendar_constructor_dates_follow_input_rules():
    assert Calendar(startdate="2020-01-01T10:00").startdate == date(2020, 1, 1)
    expected = [date(2024, 1, 1), date(2024, 12, 25)]
    cal = Calendar(holidays=[pd.Timestamp("2024-01-01 23:30", tz="America/Sao_Paulo"), "2024-12-25"])
    assert cal.holidays == expected
    assert Calendar(holidays=pd.Series(["2024-01-01", "2024-12-25"], dtype="string")).holidays == expected


def test_calendar_constructor_rejects_missing_dates():
    with pytest.raises(ValueError, match="holidays cannot contain missing"):
        Calendar(holidays=[None, "2024-12-25"])
    with pytest.raises(ValueError, match="startdate cannot be missing"):
        Calendar(startdate=float("nan"))
    with pytest.raises(ValueError, match="enddate cannot be missing"):
        Calendar(enddate=pd.NaT)


def test_calendar_constructor_rejects_bad_dates():
    with pytest.raises(ValueError, match="numbers are not dates"):
        Calendar(holidays=[5, "2024-12-25"])
    with pytest.raises(ValueError, match="invalid date string"):
        Calendar(holidays=["2024-01", "2024-12-25"])
    with pytest.raises(ValueError, match="single date"):
        Calendar(startdate=["2020-01-01"])
    with pytest.raises(ValueError, match="sequence of dates"):
        Calendar(holidays="2024-01-01")


# --- construction checks (WIL-140) ---


def test_calendar_startdate_after_enddate():
    with pytest.raises(ValueError, match="after enddate") as e:
        Calendar(startdate="2024-02-01", enddate="2024-01-01")
    assert "defaults" not in str(e.value)
    with pytest.raises(ValueError, match=r"\(enddate defaults to the last holiday\)"):
        Calendar(holidays=["2024-01-01"], weekdays=[], startdate="2024-02-01")
    with pytest.raises(ValueError, match=r"\(startdate defaults to the first holiday\)"):
        Calendar(holidays=["2024-12-25"], weekdays=[], enddate="2024-01-01")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"holidays": ["2024-01-01"], "weekdays": []},
        {
            "weekdays": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "startdate": "2024-01-01",
            "enddate": "2024-01-10",
        },
    ],
)
def test_calendar_without_business_days(kwargs):
    with pytest.raises(ValueError, match="no business days"):
        Calendar(**kwargs)


def test_calendar_load_single_holiday_json(tmp_path):
    path = tmp_path / "one.json"
    path.write_text(json.dumps({"name": "one", "holidays": ["2024-01-01"]}))
    with pytest.raises(ValueError, match="no business days"):
        Calendar.load(filename=str(path))


def test_calendar_weekdays_validation():
    for weekdays in ([5, 6], ["Saturnday"], ["sa"]):
        with pytest.raises(ValueError, match="Invalid weekday"):
            Calendar(weekdays=weekdays)
    with pytest.raises(ValueError, match="weekdays must be a list of weekday names"):
        Calendar(weekdays="Saturday")
    assert Calendar(weekdays=["sat", "Saturday", "SUN"]).weekdays == ("Saturday", "Sunday")
    assert Calendar(weekdays=["SATURDAY", "sun"]).weekdays == ("Saturday", "Sunday")


def test_calendar_holidays_outside_explicit_range_ignored():
    cal = Calendar(
        holidays=["2023-12-25", "2024-12-25", "2025-01-01"],
        weekdays=[],
        startdate="2024-01-01",
        enddate="2024-12-31",
    )
    assert cal.holidays == [date(2024, 12, 25)]
    assert "Holidays: 1" in str(cal)
    cal = Calendar(holidays=["2023-12-25", "2024-12-25"], weekdays=[], startdate="2024-01-01")
    assert cal.holidays == [date(2024, 12, 25)]
    assert cal.enddate == date(2024, 12, 25)


def test_calendar_warns_holidays_without_weekdays():
    # R test-calendar.R:317-323
    holidays = Calendar.load(name="ANBIMA").holidays
    message = "You provided holidays without set weekdays.\nThat setup leads to inconsistencies!"
    with pytest.warns(UserWarning, match=message):
        Calendar(holidays=holidays)


def test_calendar_no_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Calendar(holidays=["2024-01-01", "2024-12-25"], weekdays=[])
        Calendar()
        Calendar(weekdays=["sat"])
        for name in ("ANBIMA", "B3", "Actual"):
            Calendar.load(name=name)


def test_calendar_xcal_no_warning():
    pytest.importorskip("exchange_calendars")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Calendar.load(name="XCAL/XNYS")


def test_constructor_name_none_is_empty_string():
    # 1.0.19 had name=None as the default, so v1 code may still pass it
    assert Calendar(weekdays=["sat", "sun"], startdate="2024-01-01", enddate="2024-12-31", name=None).name == ""


@pytest.mark.parametrize("weekdays", [np.array(["sat", "sun"]), pd.Series(["sat", "sun"])])
def test_constructor_weekdays_array_like(weekdays):
    cal = Calendar(weekdays=weekdays, startdate="2024-01-01", enddate="2024-12-31")
    assert not cal.isbizday("2024-01-06")
    assert cal.isbizday("2024-01-08")


def test_load_json_with_utf8_bom(tmp_path):
    path = tmp_path / "bom.json"
    path.write_bytes(b'\xef\xbb\xbf{"weekdays": ["Saturday", "Sunday"], "holidays": ["2024-01-01", "2024-12-25"]}')
    cal = Calendar.load(filename=str(path))
    assert not cal.isbizday("2024-01-01")
