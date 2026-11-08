import hashlib
from datetime import date, timedelta

import numpy as np
import pytest

from bizdays import Calendar, list_calendars
from bizdays.calendarfile import load_packaged_calendar_definition

# When B3 publishes year Y: replace Y's entries in B3.json with the official
# list, set B3_OFFICIAL_LAST_YEAR = Y and update the count, last date and hash
# in test_b3_official_years_unchanged.
B3_OFFICIAL_LAST_YEAR = 2026
PROJECTED_LAST_YEAR = 2099

ANBIMA_HOLIDAYS = load_packaged_calendar_definition("ANBIMA").holidays
B3_HOLIDAYS = load_packaged_calendar_definition("B3").holidays


def b3_rule(year: int) -> set[str]:
    """Projected B3 holidays: ANBIMA holidays, December 24 and the last weekday."""
    last = date(year, 12, 31)
    while last.weekday() >= 5:
        last -= timedelta(days=1)
    rule = {h for h in ANBIMA_HOLIDAYS if h[:4] == str(year)}
    return rule | {f"{year}-12-24", last.isoformat()}


@pytest.fixture(scope="module")
def b3() -> Calendar:
    return Calendar.load(name="B3")


@pytest.mark.parametrize("name", list_calendars()["packaged"])
def test_packaged_calendars_cover_ten_years_ahead(name: str) -> None:
    cal = Calendar.load(name=name)
    assert cal.enddate.year - date.today().year >= 10, f"{name} ends on {cal.enddate}"


def test_b3_range(b3: Calendar) -> None:
    assert b3.startdate == date(2000, 1, 1)
    assert b3.enddate == date(2099, 12, 31)


@pytest.mark.parametrize("year", range(B3_OFFICIAL_LAST_YEAR + 1, PROJECTED_LAST_YEAR + 1))
def test_b3_projected_years_follow_rule(year: int) -> None:
    assert {h for h in B3_HOLIDAYS if h[:4] == str(year)} == b3_rule(year)


def test_b3_holidays_sorted_and_unique() -> None:
    hols = list(B3_HOLIDAYS)
    assert hols == sorted(set(hols))


def test_b3_official_years_unchanged() -> None:
    official = [h for h in B3_HOLIDAYS if h <= f"{B3_OFFICIAL_LAST_YEAR}-12-31"]
    assert len(official) == 427
    assert official[0] == "2000-01-01"
    assert official[-1] == "2026-12-31"
    digest = hashlib.sha256("\n".join(official).encode()).hexdigest()
    assert digest == "473098bdc3c1d096d6eefd454505ef7eb3bbaed96cb628a9c86e243c038c54b9"


@pytest.mark.parametrize("year", range(2022, 2027))
def test_b3_rule_matches_official_business_days(b3: Calendar, year: int) -> None:
    start, end = f"{year}-01-01", f"{year}-12-31"
    rule = Calendar(sorted(b3_rule(year)), ["saturday", "sunday"], startdate=start, enddate=end)
    assert rule.seq(start, end).tolist() == b3.seq(start, end).tolist()


def test_b3_2027_values(b3: Calendar) -> None:
    assert b3.getbizdays(2027) == 249
    assert b3.getbizdays(2027, 12) == 21
    assert b3.offset("2027-12-23", 1) == np.datetime64("2027-12-27")
    assert not b3.isbizday("2027-12-24")
    assert not b3.isbizday("2028-12-29")  # last weekday when December 31 is a Sunday
    assert b3.isbizday("2028-12-28")
