import datetime as dt
from pathlib import Path

import pytest

import bizdays
from bizdays import Calendar

# When B3 publishes year Y: replace Y's lines in bizdays/B3.cal with the official list
# and set B3_OFFICIAL_LAST_YEAR = Y.
B3_OFFICIAL_LAST_YEAR = 2026
PROJECTED_LAST_YEAR = 2099
DATA = Path(bizdays.__file__).parent


def cal_dates(name):
    return [line.strip() for line in (DATA / f"{name}.cal").read_text().splitlines() if line.strip()[:1].isdigit()]


def b3_rule(year):
    last = dt.date(year, 12, 31)
    while last.weekday() >= 5:
        last -= dt.timedelta(days=1)
    return {h for h in cal_dates("ANBIMA") if h[:4] == str(year)} | {f"{year}-12-24", last.isoformat()}


@pytest.mark.parametrize("name", ["B3", "ANBIMA", "Actual"])
def test_packaged_calendars_cover_ten_years_ahead(name):
    cal = Calendar.load(name)
    assert cal.enddate.year - dt.date.today().year >= 10, f"{name} ends on {cal.enddate}"


def test_b3_range():
    cal = Calendar.load("B3")
    assert cal.startdate == dt.date(2000, 1, 1)
    assert cal.enddate == dt.date(2099, 12, 31)


@pytest.mark.parametrize("year", range(B3_OFFICIAL_LAST_YEAR + 1, PROJECTED_LAST_YEAR + 1))
def test_b3_projected_years_follow_rule(year):
    assert {h for h in cal_dates("B3") if h[:4] == str(year)} == b3_rule(year)


def test_b3_dates_sorted_and_unique():
    hols = cal_dates("B3")
    assert hols == sorted(set(hols))


def test_b3_official_years_unchanged():
    official = [h for h in cal_dates("B3") if h <= f"{B3_OFFICIAL_LAST_YEAR}-12-31"]
    assert (len(official), official[0], official[-1]) == (427, "2000-01-01", "2026-12-31")


@pytest.mark.parametrize("year", range(2022, B3_OFFICIAL_LAST_YEAR + 1))
def test_b3_rule_matches_official_business_days(year):
    start, end = f"{year}-01-01", f"{year}-12-31"
    rule = Calendar(sorted(b3_rule(year)), weekdays=["Saturday", "Sunday"], startdate=start, enddate=end)
    assert list(rule.seq(start, end)) == list(Calendar.load("B3").seq(start, end))


def test_b3_2027_values():
    cal = Calendar.load("B3")
    assert cal.getbizdays(2027) == 249
    assert cal.getbizdays(2027, 12) == 21
    assert cal.offset("2027-12-23", 1) == dt.date(2027, 12, 27)
    assert not cal.isbizday("2027-12-24")
    assert not cal.isbizday("2028-12-29")  # last weekday: December 31, 2028 is a Sunday
    assert cal.isbizday("2028-12-28")
