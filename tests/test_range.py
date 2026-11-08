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


@pytest.fixture(scope="module")
def mid():
    return Calendar(weekdays=["Saturday", "Sunday"], startdate="2024-06-01", enddate="2024-06-15")


@pytest.fixture(scope="module")
def mid2():
    return Calendar(weekdays=["Saturday", "Sunday"], startdate="2024-06-02", enddate="2024-06-30")


def _positions(call, *args):
    with pytest.raises(DateOutOfRange) as e:
        call(*args)
    return e.value.positions.tolist()


def test_offset_past_the_ends(anbima):
    # contract section 2; R add.bizdays("2090-12-20", 30) rewritten for our range
    for d, n in [("2099-12-25", 5), ("2000-01-03", -3), ("2099-12-20", 30)]:
        assert _positions(anbima.offset, d, n) == [0]


def test_offset_backward_from_last_day(anbima):
    assert anbima.offset("2099-12-25", -1) == np.datetime64("2099-12-24")


def test_adjust_past_the_ends(anbima):
    for call, d in [
        (anbima.following, "2099-12-25"),
        (anbima.adjust_next, "2099-12-25"),
        (anbima.preceding, "2000-01-01"),
        (anbima.adjust_previous, "2000-01-01"),
    ]:
        assert _positions(call, d) == [0]
    assert anbima.following("2000-01-01") == np.datetime64("2000-01-03")
    assert anbima.preceding("2099-12-25") == np.datetime64("2099-12-24")


def test_modified_rules_at_range_edges(anbima, b3, mid, mid2):
    # contract section 9: raise only when the answer needs days outside the range
    assert b3.modified_following("2026-12-31") == np.datetime64("2026-12-30")
    assert anbima.modified_preceding("2000-01-01") == np.datetime64("2000-01-03")
    assert _positions(mid.modified_following, "2024-06-15") == [0]
    assert mid.modified_preceding("2024-06-01") == np.datetime64("2024-06-03")
    assert _positions(mid2.modified_preceding, "2024-06-02") == [0]
    assert mid2.modified_following("2024-06-30") == np.datetime64("2024-06-28")


def test_positions_after_pairing(anbima):
    assert _positions(anbima.bizdays, "1900-01-01", ["2024-01-02", "2024-01-03"]) == [0, 1]
    assert _positions(anbima.isbizday, ["2024-01-02", "1900-01-01", None, "2300-01-01"]) == [1, 3]
    assert _positions(anbima.offset, ["2024-01-02", "2099-12-20", "2099-12-21"], [1, 30, 30]) == [1, 2]
    assert _positions(anbima.offset, "1900-01-01", 1) == [0]


def test_positions_inputs_and_results(anbima):
    assert _positions(anbima.offset, ["1900-01-01", "2024-01-02", "2099-12-24"], 1) == [0, 2]


def test_range_message(anbima):
    with pytest.raises(DateOutOfRange) as e:
        anbima.offset(["2024-01-02", "2099-12-20", "2099-12-21"], [1, 30, 30])
    message = str(e.value)
    for part in ["2 of 3", "2000-01-01..2099-12-25", "position 1", "dt=2099-12-20", "n=30"]:
        assert part in message
    assert "n=30.0" not in message


def test_missing_never_out_of_range(anbima):
    assert anbima.offset([None, "2024-01-02"], [1, 1]).astype(str).tolist() == ["NaT", "2024-01-03"]
    assert _positions(anbima.bizdays, [None, "1900-01-01"], "2024-01-02") == [1]


def test_empty_result_still_checked(anbima):
    # contract section 7
    for call, arg in [(lambda x: anbima.bizdays([], x), "2300-01-01"), (anbima.diff, ["1900-01-01"])]:
        with pytest.raises(DateOutOfRange) as e:
            call(arg)
        assert e.value.positions.tolist() == []
        assert "the result is empty" in str(e.value)
    with pytest.raises(DateOutOfRange, match="2300-01-01"):
        anbima.bizdays([], "2300-01-01")


def test_seq_and_diff_ranges(anbima):
    assert _positions(anbima.seq, "1999-12-30", "2000-01-05") == [0]
    assert _positions(anbima.diff, ["2024-01-02", "1900-01-01", "2024-01-05"]) == [0, 1]
    assert anbima.seq("2099-12-20", "2099-12-25")[-1] == np.datetime64("2099-12-24")


def test_bizdays_never_needs_outside_days(anbima):
    assert anbima.bizdays("2099-12-24", "2099-12-25") == 0
    # Saturday to Monday is 0, as in R bizdays
    assert anbima.bizdays("2000-01-01", "2000-01-03") == 0
    assert anbima.bizdays("2000-01-01", "2000-01-04") == 1


def test_bizdays_span_without_bizdays_is_zero(anbima):
    # intended difference: R bizdays gives -1, -1, +1 here; v1.0.19 gives 0
    for a, b in [("2007-11-17", "2007-11-18"), ("2007-11-18", "2007-11-18"), ("2007-11-18", "2007-11-17")]:
        assert anbima.bizdays(a, b) == 0


def test_r_range_errors(short):
    # R test-calendar.R:8-44
    cal = Calendar(weekdays=["Saturday", "Sunday"])
    for to, expected in [("2013-01-03", 1), ("2013-01-04", 2), ("2013-01-05", 2), ("2013-01-06", 2), ("2013-01-07", 3)]:
        assert cal.bizdays("2013-01-02", to) == expected
    for a, b in [("2013-01-02", "2090-01-07"), ("1700-01-02", "2013-01-07")]:
        with pytest.raises(DateOutOfRange):
            cal.bizdays(a, b)
    assert short.bizdays("2013-01-02", "2013-01-03") == 1
    for a, b in [("2013-01-02", "2014-01-02"), ("2012-01-02", "2013-01-02")]:
        with pytest.raises(DateOutOfRange):
            short.bizdays(a, b)


def test_no_internal_errors_at_edges(anbima, b3, short, mid, mid2):
    one = np.timedelta64(1, "D")
    for cal in (anbima, b3, short, mid, mid2):
        start, end = np.datetime64(cal.startdate, "D"), np.datetime64(cal.enddate, "D")
        for d in (start, start + one, end - one, end):
            calls = [
                lambda: cal.isbizday(d),
                lambda: cal.following(d),
                lambda: cal.preceding(d),
                lambda: cal.modified_following(d),
                lambda: cal.modified_preceding(d),
                lambda: cal.bizdays(d, d),
            ]
            calls += [lambda k=k: cal.offset(d, k) for k in (-2, -1, 0, 1, 2)]
            for call in calls:
                try:
                    call()
                except DateOutOfRange:
                    pass
