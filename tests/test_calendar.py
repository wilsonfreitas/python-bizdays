import pytest

from bizdays.calendar import Calendar


@pytest.fixture(scope="module")
def anbima():
    return Calendar.load("ANBIMA")


@pytest.fixture(scope="module")
def actual():
    return Calendar(name="actual")


def test_calendar_load():
    cal = Calendar.load("B3")
    assert cal.name == "B3"
    cal = Calendar.load("ANBIMA")
    assert cal.name == "ANBIMA"


def test_calendar_load_invalid():
    with pytest.raises(Exception):
        Calendar.load("B1")


def test_calendar_load_pmc():
    cal = Calendar.load("PMC/B3")
    assert cal.name == "PMC/B3"
    assert len(cal.holidays) > 4000


def test_public_import():
    """Calendar is importable from the top-level package."""
    from bizdays import Calendar
    cal = Calendar.load("B3")
    assert cal.name == "B3"


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


# --- isbizday tests ---


def test_isbizday_true(anbima):
    assert anbima.isbizday("2013-01-02")


def test_isbizday_false_holiday(anbima):
    # 2013-01-01 is a holiday in ANBIMA
    assert not anbima.isbizday("2013-01-01")


def test_isbizday_vectorized(anbima):
    result = anbima.isbizday(["2013-01-01", "2013-01-02"])
    assert list(result) == [False, True]


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
