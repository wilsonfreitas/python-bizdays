import hashlib
import json
import re
from datetime import date, timedelta
from importlib import resources
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from dateutil.easter import easter

from bizdays import Calendar, list_calendars
from bizdays.calendarfile import PACKAGED_CALENDARS, load_packaged_calendar_definition
from bizdays.utils import DateOutOfRange

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


ALLOWED_KEYS = {"name", "weekdays", "holidays", "financial", "adjust.from", "adjust.to", "start.date", "end.date"}


def _raw(name: str) -> Any:
    return json.loads(resources.files("bizdays.data").joinpath(f"{name}.json").read_text("utf-8"))


def test_packaged_files_are_the_packaged_calendars() -> None:
    files = sorted(p.name for p in resources.files("bizdays.data").iterdir() if p.name.endswith(".json"))
    assert files == ["ANBIMA.json", "Actual.json", "B3.json"]


@pytest.mark.parametrize("name", PACKAGED_CALENDARS)
def test_packaged_json_schema(name: str) -> None:
    raw = _raw(name)
    assert set(raw) <= ALLOWED_KEYS
    assert raw["name"] == name
    for h in raw.get("holidays", []):
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", h), h
        date.fromisoformat(h)
    # ANBIMA and B3 store lowercase names
    assert [w.lower() for w in raw.get("weekdays", [])] in (["saturday", "sunday"], [])
    load_packaged_calendar_definition(name)


@pytest.mark.parametrize("name", PACKAGED_CALENDARS)
def test_packaged_holidays_sorted_and_unique(name: str) -> None:
    h = _raw(name).get("holidays", [])
    assert h == sorted(h)
    assert len(h) == len(set(h))


def test_packaged_holiday_sets_match_v1_0_19() -> None:
    # counts of the 1.0.19 .cal sets on master, checked 2026-11-07
    anbima = _raw("ANBIMA")["holidays"]
    assert len(anbima) == 1275
    assert (anbima[0], anbima[-1]) == ("2000-01-01", "2099-12-25")
    b3 = _raw("B3")["holidays"]
    assert len([d for d in b3 if d <= "2026-12-31"]) == 427
    assert b3[0] == "2000-01-01"


def test_load_rejects_non_packaged_name() -> None:
    with pytest.raises(ValueError, match="Unknown calendar: 'Test'"):
        Calendar.load(name="Test")


# R bizdays 1.0.17: getbizdays(2001:2078, "Brazil/ANBIMA")
ANBIMA_YEARS_R = [
    250, 253, 253, 252, 251, 249, 250, 254, 250, 251, 251, 251, 253, 253, 250, 251, 249, 250, 253, 251,
    251, 251, 249, 253, 252, 249, 251, 248, 249, 252, 252, 252, 251, 248, 249, 253, 249, 251, 251, 250,
    252, 252, 249, 251, 248, 249, 252, 250, 251, 251, 248, 253, 252, 249, 251, 248, 249, 252, 252, 252,
    251, 248, 249, 253, 249, 251, 251, 250, 252, 252, 249, 251, 248, 249, 252, 250, 251, 251,
]  # fmt: skip


@pytest.fixture(scope="module")
def anbima() -> Calendar:
    return Calendar.load(name="ANBIMA")


def test_anbima_year_counts_match_r(anbima: Calendar) -> None:
    assert anbima.getbizdays(list(range(2001, 2079))).tolist() == ANBIMA_YEARS_R
    assert anbima.bizdays("2001-01-02", "2078-12-30") == 19553


def _national_holidays(y: int) -> set[str]:
    e = easter(y)
    days = {e - timedelta(days=48), e - timedelta(days=47), e - timedelta(days=2), e + timedelta(days=60)}
    days |= {date(y, m, d) for m, d in ((1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25))}
    if y >= 2024:
        days.add(date(y, 11, 20))
    return {d.isoformat() for d in days}


def test_anbima_follows_national_holiday_rule() -> None:
    for y in range(2001, 2100):
        assert {h for h in ANBIMA_HOLIDAYS if h[:4] == str(y)} == _national_holidays(y), y
    year_2000 = {h for h in ANBIMA_HOLIDAYS if h[:4] == "2000"}
    assert year_2000 - _national_holidays(2000) == {"2000-04-23"}
    assert _national_holidays(2000) - year_2000 == set()


def test_b3_year_counts_match_r_2024_2025(b3: Calendar) -> None:
    assert b3.getbizdays([2024, 2025]).tolist() == [251, 250]


def test_b3_2026_holidays(b3: Calendar) -> None:
    # B3 trading calendar 2026 as published by B3 (checked 2026-11-07)
    expected = [
        "2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03", "2026-04-21", "2026-05-01", "2026-06-04",
        "2026-09-07", "2026-10-12", "2026-11-02", "2026-11-20", "2026-12-24", "2026-12-25", "2026-12-31",
    ]  # fmt: skip
    assert [h for h in B3_HOLIDAYS if h[:4] == "2026"] == expected
    assert b3.getbizdays(2026) == 247


_BOTH = [
    ("2024-02-29", True),  # leap day
    ("2024-02-12", False),  # Carnival
    ("2024-02-13", False),
    ("2024-02-14", True),
    ("2024-03-29", False),  # Good Friday
    ("2023-11-20", True),  # national holiday from 2024
    ("2024-11-20", False),
    ("2024-01-06", False),  # weekend
    ("2024-01-07", False),
    ("2000-01-03", True),  # first Monday of the range
]


@pytest.mark.parametrize(
    "calendar, day, expected",
    [(c, d, e) for c in ("ANBIMA", "B3") for d, e in _BOTH]
    + [
        ("ANBIMA", "2024-12-24", True),
        ("ANBIMA", "2024-12-31", True),
        ("B3", "2024-12-24", False),
        ("B3", "2024-12-31", False),
        ("ANBIMA", "2099-12-24", True),
        ("ANBIMA", "2099-12-25", False),  # last day of the range
    ],
)
def test_representative_days(calendar: str, day: str, expected: bool) -> None:
    assert Calendar.load(name=calendar).isbizday(day) == expected


def test_packaged_ranges(anbima: Calendar, b3: Calendar) -> None:
    assert (anbima.startdate, anbima.enddate) == (date(2000, 1, 1), date(2099, 12, 25))
    assert b3.startdate == date(2000, 1, 1)


def test_actual_range() -> None:
    cal = Calendar.load(name="Actual")
    assert (cal.startdate, cal.enddate) == (date(1900, 1, 1), date(2199, 12, 31))
    assert cal.weekdays == ()
    assert cal.bizdays("2071-01-01", "2100-01-01") == 10592


def test_default_range_matches_r() -> None:
    # R test-calendar.R "default calendar"
    cal = Calendar(weekdays=["Saturday", "Sunday"])
    assert (cal.startdate, cal.enddate) == (date(1970, 1, 1), date(2071, 1, 1))
    ends = ["2013-01-03", "2013-01-04", "2013-01-05", "2013-01-06", "2013-01-07"]
    assert [cal.bizdays("2013-01-02", d) for d in ends] == [1, 2, 2, 2, 3]
    with pytest.raises(DateOutOfRange):
        cal.bizdays("2013-01-02", "2090-01-07")
    with pytest.raises(DateOutOfRange):
        cal.bizdays("1700-01-02", "2013-01-07")


def test_actual_default_range_matches_r() -> None:
    # R test-calendar.R "Actual Calendar"
    cal = Calendar(weekdays=[])
    assert (cal.startdate, cal.enddate) == (date(1970, 1, 1), date(2071, 1, 1))
    assert cal.bizdays("2013-01-02", "2013-02-03") == 32


def _write_calendar(tmp_path: Path, **fields: Any) -> str:
    payload = {"name": "X", "weekdays": ["Saturday", "Sunday"], "holidays": ["2023-06-01", "2024-12-25"]}
    path = tmp_path / "X.json"
    path.write_text(json.dumps({**payload, **fields}), encoding="utf-8")
    return str(path)


def test_json_range_fields(tmp_path: Path) -> None:
    cal = Calendar.load(filename=_write_calendar(tmp_path, **{"start.date": "2024-01-01", "end.date": "2024-12-31"}))
    assert cal.startdate == date(2024, 1, 1)
    assert cal.enddate == date(2024, 12, 31)
    assert cal.holidays == [date(2024, 12, 25)]


@pytest.mark.parametrize(
    "fields, match",
    [({"start.date": 20240101}, "start.date"), ({"end.date": "2024-13-01"}, None)],
    ids=["start", "end"],
)
def test_json_range_field_errors(tmp_path: Path, fields: dict[str, Any], match: str | None) -> None:
    with pytest.raises(ValueError, match=match):
        Calendar.load(filename=_write_calendar(tmp_path, **fields))


def test_calendar_holidays_sorted_unique() -> None:
    cal = Calendar(["2024-01-03", "2024-01-01", "2024-01-01"], weekdays=["Sat", "Sun"])
    assert cal.holidays == [date(2024, 1, 1), date(2024, 1, 3)]
    assert len(Calendar.load(name="ANBIMA").holidays) == 1275
