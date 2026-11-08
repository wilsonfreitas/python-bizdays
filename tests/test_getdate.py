from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from bizdays import Calendar, DateOutOfRange
from bizdays.calendarfile import load_packaged_calendar_definition
from bizdays.dateindex import DateIndex
from bizdays.getdate_parser import normalize_ref, parse_getdate_expression


@pytest.fixture(scope="module")
def anbima():
    return Calendar.load(name="ANBIMA")


@pytest.fixture(scope="module")
def actual():
    return Calendar(name="actual")


@pytest.fixture(scope="module")
def anbima_index():
    definition = load_packaged_calendar_definition("ANBIMA")
    nonwork_weekdays = {weekday[:3].lower() for weekday in definition.weekdays}
    weekdays = [
        index
        for index, weekday in enumerate(
            (
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            )
        )
        if weekday[:3].lower() in nonwork_weekdays
    ]
    return DateIndex(
        np.array(definition.holidays, dtype="datetime64[D]"),
        np.datetime64(definition.holidays[0]),
        np.datetime64(definition.holidays[-1]),
        weekdays,
    )


@pytest.mark.parametrize(
    ("expr", "ref", "expected"),
    [
        ("15th day", "2002-01", "2002-01-15"),
        ("first day before 15th day", "2002-01", "2002-01-14"),
        ("second day after 15th day", "2002-01", "2002-01-17"),
        ("second bizday before 15th day", "2002-01", "2002-01-11"),
        ("second bizday after 15th day", "2002-01", "2002-01-17"),
        ("first bizday", "2002-01", "2002-01-02"),
        ("second bizday", "2002-01", "2002-01-03"),
        ("third bizday", "2002-01", "2002-01-04"),
        ("second bizday before 10th bizday", "2002-01", "2002-01-11"),
        ("first tue before first day", "2002-01", "2001-12-25"),
        ("first tue after first day", "2002-01", "2002-01-08"),
        ("first tue before second day", "2002-01", "2002-01-01"),
        ("first tue after second day", "2002-01", "2002-01-08"),
        ("2nd bizday", "2002-01", "2002-01-03"),
        ("3rd bizday", "2002-01", "2002-01-04"),
        ("first tue", "2002-01", "2002-01-01"),
        ("last fri", "2002-01", "2002-01-25"),
        ("first day before first day", "2002-01", "2001-12-31"),
        ("2nd day before first day", "2002-01", "2001-12-30"),
        ("last day", "2002-01", "2002-01-31"),
        ("first bizday before last day", "2002-01", "2002-01-30"),
        ("second bizday before last day", "2002-01", "2002-01-29"),
        ("10th fri before 10th bizday", "2002-05", "2002-03-08"),
        ("first wed after 15th day", "2002-05", "2002-05-22"),
        ("first wed before 15th day", "2002-05", "2002-05-08"),
        ("1st bizday before 2nd fri", "2002-05", "2002-05-09"),
        ("first bizday before first day", "2002-01", "2001-12-31"),
        ("2nd bizday before first day", "2002-01", "2001-12-28"),
    ],
)
def test_getdate_month_reference_matches_legacy_behavior(
    anbima, expr, ref, expected
):
    assert str(anbima.getdate(expr, ref)) == expected


@pytest.mark.parametrize(
    ("expr", "ref", "expected"),
    [
        ("first bizday", 2002, "2002-01-02"),
        ("first bizday", "2002", "2002-01-02"),
        ("last day", 2006, "2006-12-31"),
    ],
)
def test_getdate_year_reference(anbima, expr, ref, expected):
    assert str(anbima.getdate(expr, ref)) == expected


@pytest.mark.parametrize(
    ("expr", "ref", "expected"),
    [
        ("next wed", "2021-02-10", "2021-02-17"),
        ("previous mon", "2021-02-10", "2021-02-08"),
        ("first wed", "2021-02-10", "2021-02-17"),
        ("second fri", "2026-04-20", "2026-05-01"),
        ("third tue", date(2021, 2, 10), "2021-03-02"),
        ("next wed", datetime(2021, 2, 10, 9, 30), "2021-02-17"),
    ],
)
def test_getdate_date_reference(anbima, expr, ref, expected):
    assert str(anbima.getdate(expr, ref)) == expected


def test_getdate_scalar_returns_numpy_datetime64(anbima):
    result = anbima.getdate("first bizday", "2002-01")
    assert isinstance(result, np.datetime64)


def test_getdate_vectorized_expr(anbima):
    result = anbima.getdate(["first day", "last day"], "2002-01")
    assert result.dtype == np.dtype("datetime64[D]")
    assert result.astype(str).tolist() == ["2002-01-01", "2002-01-31"]


def test_getdate_vectorized_ref(anbima):
    result = anbima.getdate("first bizday", ["2002-01", "2002-02"])
    assert result.astype(str).tolist() == ["2002-01-02", "2002-02-01"]


def test_getdate_vectorized_expr_and_ref(anbima):
    result = anbima.getdate(
        ["15th day", "16th day"],
        ["2002-01", "2001-01"],
    )
    assert result.astype(str).tolist() == ["2002-01-15", "2001-01-16"]


def test_getdate_recycles_expr_and_ref(anbima):
    # one kind of ref per call (contract D6)
    with pytest.raises(ValueError, match="one kind") as e:
        anbima.getdate(["first day", "next wed"], ["2002-01", "2021-02-10"])
    assert "found: date, month" in str(e.value)


def test_getdate_missing_inputs_return_nat(anbima):
    result = anbima.getdate(["first bizday", None], ["2002-01", "2002-01"])
    assert result.astype(str).tolist()[0] == "2002-01-02"
    assert np.isnat(result[1])


def test_getdate_missing_scalar_ref_returns_nat(anbima):
    assert np.isnat(anbima.getdate("first bizday", None))


def test_getdate_requires_string_expressions(anbima):
    with pytest.raises(ValueError, match="expressions must be strings"):
        anbima.getdate(123, "2002-01")


def test_getdate_date_relative_requires_date_ref(anbima):
    # R: next means first with period refs; only previous needs a date ref
    assert anbima.getdate("next wed", "2002-01") == np.datetime64("2002-01-02")
    for ref in ["2002-01", 2002]:
        with pytest.raises(ValueError, match="date ref"):
            anbima.getdate("previous wed", ref)


def test_getdate_date_ref_rejects_non_weekday_expressions(anbima):
    # R's date-ref forms: first bizday is offset(date, 1)
    assert anbima.getdate("first bizday", "2021-02-10") == np.datetime64("2021-02-11")


def test_getdate_rejects_invalid_ref(anbima):
    with pytest.raises(ValueError, match="Invalid getdate ref"):
        anbima.getdate("first bizday", "2021/02")


@pytest.mark.parametrize(
    ("expr", "ref", "expected"),
    [
        ("first day", "2002-01", "2002-01-01"),
        ("first bizday", "2002-01", "2002-01-02"),
        ("first wed", "2002-02", "2002-02-06"),
        ("last day", "2002-02", "2002-02-28"),
        ("last bizday", "2002-02", "2002-02-28"),
        ("second bizday", "2002-02", "2002-02-04"),
        ("third tue", "2002-02", "2002-02-19"),
    ],
)
def test_getdate_additional_legacy_calendar_cases(anbima, expr, ref, expected):
    assert str(anbima.getdate(expr, ref)) == expected


def test_dateindex_getdate_is_strict(anbima_index):
    expr, ref = parse_getdate_expression("first bizday"), normalize_ref("2002-01")
    assert anbima_index.getdate(expr, ref) == np.datetime64("2002-01-02")


# --- WIL-149: getdate argument conversion ---


def test_getdate_whole_float_year_ref(anbima):
    assert anbima.getdate("first bizday", 2002.0) == np.datetime64("2002-01-02")
    with pytest.raises(ValueError, match="Invalid getdate ref"):
        anbima.getdate("first bizday", 2002.5)


def test_getdate_datetime64_period_refs(anbima):
    assert anbima.getdate("first bizday", np.datetime64("2002-01")) == np.datetime64("2002-01-02")
    assert anbima.getdate("first bizday", np.datetime64("2002")) == np.datetime64("2002-01-02")
    refs = np.array(["2002-01", "2002-02"], dtype="datetime64[M]")
    assert anbima.getdate("first bizday", refs).astype(str).tolist() == ["2002-01-02", "2002-02-01"]
    with pytest.raises(ValueError, match="Invalid getdate ref"):
        anbima.getdate("first bizday", np.datetime64("2002-01-03", "W"))


def test_getdate_date_ref_wall_clock(anbima):
    assert anbima.getdate("next wed", "2021-02-10T23:30-03:00") == np.datetime64("2021-02-17")
    ref = pd.Timestamp("2021-02-10 23:30", tz="America/Sao_Paulo")
    assert anbima.getdate("next wed", ref) == np.datetime64("2021-02-17")


@pytest.mark.parametrize(
    "ref",
    [np.ma.masked, pd.NA, np.datetime64("NaT"), float("nan")],
    ids=["masked", "NA", "NaT", "nan"],
)
def test_getdate_missing_values(anbima, ref):
    assert np.isnat(anbima.getdate("first bizday", ref))
    assert np.isnat(anbima.getdate(pd.NA, "2002-01"))


@pytest.mark.parametrize("dt", ["string", "nan-string"])
def test_getdate_pandas_string_exprs(anbima, dt):
    if dt == "nan-string":
        try:
            dt = pd.StringDtype(na_value=np.nan)
        except TypeError:
            pytest.skip("pandas < 2.3 has no StringDtype(na_value=np.nan)")
    exprs = pd.Series(["first bizday", None], dtype=dt)
    assert anbima.getdate(exprs, "2002-01").astype(str).tolist() == ["2002-01-02", "NaT"]


def test_getdate_non_missing_partner_checked(anbima):
    with pytest.raises(ValueError, match="Invalid getdate ref"):
        anbima.getdate(None, "2021/02")
    with pytest.raises(ValueError, match="expressions must be strings"):
        anbima.getdate(123, None)
    with pytest.raises(DateOutOfRange):
        anbima.getdate(None, "1900-01-02")


def test_getdate_rejects_2d(anbima):
    with pytest.raises(ValueError, match="must be 1-D"):
        anbima.getdate([["first day"]], "2002-01")


# --- WIL-140: strict getdate, never wraps ---


def test_getdate_zero_ordinal(anbima):
    for expr in ["0th day", "0th bizday after 1st day", "1st bizday before 0th day"]:
        with pytest.raises(ValueError, match="ordinal"):
            anbima.getdate(expr, "2024-02")


@pytest.mark.parametrize("expr", ["5th fri", "22nd bizday", "31st day", "1st bizday after 5th fri"])
def test_getdate_date_does_not_exist(anbima, expr):
    with pytest.raises(ValueError, match="does not exist") as e:
        anbima.getdate(expr, "2024-02")
    assert not isinstance(e.value, DateOutOfRange)
    assert expr in str(e.value) and "2024-02" in str(e.value)


def test_getdate_period_must_be_inside_range(anbima):
    for expr, ref in [("last bizday", "2099-12"), ("first day", "2099-12"), ("last bizday", 2099), ("first bizday", 1999)]:
        with pytest.raises(DateOutOfRange):
            anbima.getdate(expr, ref)
    assert anbima.getdate("last bizday", "2099-11") == np.datetime64("2099-11-30")
    assert anbima.getdate("first bizday", "2000-01") == np.datetime64("2000-01-03")


def test_getdate_never_wraps(anbima):
    for expr, ref in [
        ("first bizday before first day", "2000-01"),
        ("first day before first day", "2000-01"),
        ("next mon", "2099-12-24"),
        ("1st tue before first day", "2000-01"),
    ]:
        with pytest.raises(DateOutOfRange):
            anbima.getdate(expr, ref)
    assert anbima.getdate("first day before first day", "2000-02") == np.datetime64("2000-01-31")


def _range_error(call, *args):
    with pytest.raises(DateOutOfRange) as e:
        call(*args)
    return e.value


def test_getdate_positions(anbima):
    e = _range_error(anbima.getdate, ["first bizday", "last bizday", "first bizday"], ["2024-01", "2099-12", "1999-01"])
    assert e.positions.tolist() == [1, 2]
    for part in ["2 of 3", "expr='last bizday'", "ref=2099-12"]:
        assert part in str(e)
    assert _range_error(anbima.getdate, "next mon", ["2024-01-03", "2099-12-24"]).positions.tolist() == [1]
    assert _range_error(anbima.getdate, None, "1900-01").positions.tolist() == [0]
    assert _range_error(anbima.getdate, [], "1900-01").positions.tolist() == []


def test_getdate_does_not_exist_message(anbima):
    with pytest.raises(ValueError, match=r"does not exist.*5th fri.*2024-02") as e:
        anbima.getdate(["first fri", "5th fri"], "2024-02")
    assert not isinstance(e.value, DateOutOfRange)


# --- WIL-227: getdate parity with R ---


@pytest.mark.parametrize(
    ("expr", "expected"),
    [("11th day", "2002-01-11"), ("12th day", "2002-01-12"), ("13th day", "2002-01-13"),
     ("21st day", "2002-01-21"), ("22nd day", "2002-01-22"), ("23rd day", "2002-01-23")],
)
def test_getdate_ordinal_suffixes(anbima, expr, expected):
    assert anbima.getdate(expr, "2002-01") == np.datetime64(expected)


@pytest.mark.parametrize(
    "expr", ["2st bizday", "1nd day", "3th day", "11st day", "12nd day", "21th day", "1st bizday after 2st day", "01st day"]
)
def test_getdate_wrong_ordinal_suffix(anbima, expr):
    with pytest.raises(ValueError, match="ordinal"):
        anbima.getdate(expr, "2002-01")


def test_getdate_case_insensitive(anbima):
    assert anbima.getdate("FIRST BizDay", "2002-01") == np.datetime64("2002-01-02")
    assert anbima.getdate("Last FRI", "2002-01") == np.datetime64("2002-01-25")
    assert anbima.getdate("NEXT Wednesday", "2002-01") == np.datetime64("2002-01-02")
    assert anbima.getdate("Previous MON", "2021-02-10") == np.datetime64("2021-02-08")


@pytest.mark.parametrize(
    ("short", "full"),
    [("mon", "monday"), ("tue", "tuesday"), ("wed", "wednesday"), ("thu", "thursday"),
     ("fri", "friday"), ("sat", "saturday"), ("sun", "sunday")],
)
def test_getdate_full_weekday_names(anbima, short, full):
    for ref in ["2002-01", "2021-02-10"]:
        assert anbima.getdate(f"first {full}", ref) == anbima.getdate(f"first {short}", ref)


@pytest.mark.parametrize(
    "expr",
    ["first monkey", "first wedn", "first thurs", "first tues", "first mo", "first bizdays",
     "1st bizday around 15th day", "next", ""],
)
def test_getdate_rejects_unknown_words(anbima, expr):
    with pytest.raises(ValueError):
        anbima.getdate(expr, "2002-01")


def test_getdate_next_with_period_refs(anbima):
    assert anbima.getdate("next wed", "2002-01") == np.datetime64("2002-01-02")
    assert anbima.getdate("next bizday", "2002-01") == np.datetime64("2002-01-02")
    assert anbima.getdate("next day", "2002-01") == np.datetime64("2002-01-01")
    assert anbima.getdate("next bizday", 2002) == np.datetime64("2002-01-02")


def test_getdate_composite_first_slot(anbima):
    expected = np.datetime64("2002-01-16")
    assert anbima.getdate("next bizday after 15th day", "2002-01") == expected
    assert anbima.getdate("1st bizday after 15th day", "2002-01") == expected
    assert anbima.getdate("last bizday before 15th day", "2002-01") == np.datetime64("2002-01-14")
    assert anbima.getdate("next wed after 15th day", "2002-05") == np.datetime64("2002-05-22")


@pytest.mark.parametrize("expr", ["previous bizday", "previous day"])
def test_getdate_previous_only_weekdays(anbima, expr):
    with pytest.raises(ValueError, match="weekday"):
        anbima.getdate(expr, "2021-02-10")


def test_getdate_new_forms_do_not_exist(anbima):
    with pytest.raises(ValueError, match="does not exist") as e:
        anbima.getdate("next bizday after 5th fri", "2024-02")
    assert not isinstance(e.value, DateOutOfRange)


def _ordinal(n):
    return f"{n}{'th' if n % 100 in (11, 12, 13) else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def test_getdate_r_period_refs(actual, anbima):
    assert actual.getdate("10th wed", 2018) == np.datetime64("2018-03-07")
    assert anbima.getdate("last bizday", list(range(2010, 2019))).astype(str).tolist() == [
        "2010-12-31", "2011-12-30", "2012-12-31", "2013-12-31", "2014-12-31",
        "2015-12-31", "2016-12-30", "2017-12-29", "2018-12-31",
    ]
    assert anbima.getdate("first bizday", [f"2018-{m:02d}" for m in range(1, 13)]).astype(str).tolist() == [
        "2018-01-02", "2018-02-01", "2018-03-01", "2018-04-02", "2018-05-02", "2018-06-01",
        "2018-07-02", "2018-08-01", "2018-09-03", "2018-10-01", "2018-11-01", "2018-12-03",
    ]


_TODAY = np.datetime64(date.today(), "D")


@pytest.mark.parametrize(
    ("cal", "expr", "ref", "expected"),
    [
        ("actual", "next day", date.today(), _TODAY + 1),
        ("actual", "last day", date.today(), _TODAY - 1),
        ("actual", "next day", "2022-06-20", "2022-06-21"),
        ("actual", "last day", "2022-06-20", "2022-06-19"),
        ("anbima", "next bizday", "2022-06-18", "2022-06-20"),
        ("anbima", "last bizday", "2022-06-19", "2022-06-17"),
        ("anbima", "2nd wed", "2022-06-20", "2022-06-29"),
        ("anbima", "next wed", "2022-06-20", "2022-06-22"),
        ("anbima", "last wed", "2022-06-20", "2022-06-15"),
        ("anbima", "next mon", "2022-06-20", "2022-06-27"),
        ("anbima", "last mon", "2022-06-20", "2022-06-13"),
    ],
)
def test_getdate_r_date_refs(request, cal, expr, ref, expected):
    assert request.getfixturevalue(cal).getdate(expr, ref) == np.datetime64(expected, "D")


def test_getdate_date_ref_day_forms(anbima):
    ref = np.datetime64("2024-02-27")
    for n in [1, 2, 3, 10]:
        assert anbima.getdate(f"{_ordinal(n)} day", ref) == ref + n
    assert anbima.getdate("first day", ref) == ref + 1
    assert anbima.getdate("last day", "2024-03-01") == np.datetime64("2024-02-29")


@pytest.mark.parametrize("ref", ["2021-02-10", "2021-02-13", "2021-02-15", "2021-02-16"])
def test_getdate_date_ref_bizday_equals_offset(anbima, ref):
    for n in range(1, 6):
        assert anbima.getdate(f"{_ordinal(n)} bizday", ref) == anbima.offset(ref, n)
    assert anbima.getdate("next bizday", ref) == anbima.offset(ref, 1)
    assert anbima.getdate("last bizday", ref) == anbima.offset(ref, -1)


_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@pytest.mark.parametrize("target", range(7))
@pytest.mark.parametrize("ref", np.arange("2022-06-20", "2022-06-27", dtype="datetime64[D]"))
def test_getdate_date_ref_weekday_matrix(anbima, ref, target):
    def wd(d):
        return (d.astype("datetime64[D]").astype(int) + 3) % 7

    w = _NAMES[target]
    after = next(ref + k for k in range(1, 8) if wd(ref + k) == target)
    before = next(ref - k for k in range(1, 8) if wd(ref - k) == target)
    for expr in [f"next {w}", f"1st {w}", f"first {w}"]:
        assert anbima.getdate(expr, ref) == after
    assert anbima.getdate(f"2nd {w}", ref) == after + 7
    assert anbima.getdate(f"last {w}", ref) == before
    assert anbima.getdate(f"previous {w}", ref) == before


@pytest.mark.parametrize(
    ("expr", "ref"),
    [("next day", "2099-12-25"), ("next bizday", "2099-12-24"), ("last day", "2000-01-01"), ("last bizday", "2000-01-03")],
)
def test_getdate_date_ref_edges(anbima, expr, ref):
    with pytest.raises(DateOutOfRange):
        anbima.getdate(expr, ref)


def test_getdate_composite_rejects_date_ref(anbima):
    with pytest.raises(ValueError, match="year or month ref"):
        anbima.getdate("1st bizday before 2nd fri", "2021-02-10")
    # rejected before the range check
    with pytest.raises(ValueError, match="year or month ref") as e:
        anbima.getdate("1st bizday before 2nd fri", "1990-01-05")
    assert not isinstance(e.value, DateOutOfRange)


@pytest.mark.parametrize(
    ("refs", "found"),
    [
        (["2002-01", "2021-02-10"], "date, month"),
        ([2002, "2002-01"], "month, year"),
        (["2002", date(2021, 2, 10)], "date, year"),
        ([np.datetime64("2002-01"), np.datetime64("2002-01-10")], "date, month"),
        (["2002-01", 2002, "2021-02-10"], "date, month, year"),
    ],
)
def test_getdate_one_ref_kind_per_call(anbima, refs, found):
    with pytest.raises(ValueError, match="one kind") as e:
        anbima.getdate("first bizday", refs)
    assert f"found: {found}" in str(e.value)


def test_getdate_missing_refs_do_not_count(anbima):
    result = anbima.getdate("first bizday", ["2002-01", None, np.datetime64("2002-02")])
    assert result.astype(str).tolist() == ["2002-01-02", "NaT", "2002-02-01"]
    assert anbima.getdate("next bizday", [None, "2021-02-10"]).astype(str).tolist() == ["NaT", "2021-02-11"]


def test_getdate_ref_kind_checked_before_range(anbima):
    with pytest.raises(ValueError, match="one kind") as e:
        anbima.getdate("first day", ["1900-01", "2021-02-10"])
    assert not isinstance(e.value, DateOutOfRange)


@pytest.mark.parametrize("ref", [10**19, 2**64, 1e20, 1e300])
def test_getdate_huge_year_ref_raises_value_error(ref):
    with pytest.raises(ValueError, match="Invalid getdate ref"):
        Calendar.load(name="ANBIMA").getdate("first bizday", ref)
