"""Adapter tests with fake providers: they run whether or not the providers are installed."""

import sys
from collections.abc import Callable
from datetime import date
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest

import bizdays.external
from bizdays import Calendar, list_calendars


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Install fake provider modules behind the single seam ``bizdays.external.import_module``."""

    def install(
        weekmask: str = "Mon Tue Wed Thu Fri",
        pmc_holidays: tuple[str, ...] = ("2024-01-01", "2024-12-25"),
        sessions: list[str] | None = None,
        early_closes: list[str] | None = None,
        work_year_ok: Callable[[int], bool] = lambda y: True,
    ) -> None:
        pmc_cal = SimpleNamespace(
            weekmask=weekmask,
            holidays=lambda: SimpleNamespace(holidays=tuple(np.datetime64(d) for d in pmc_holidays)),
        )
        idx = pd.DatetimeIndex(sessions or [])
        xcal_cal = SimpleNamespace(
            first_session=idx.min() if len(idx) else None,
            last_session=idx.max() if len(idx) else None,
            sessions_in_range=lambda a, b: idx[(idx >= a) & (idx <= b)],
            early_closes=pd.DatetimeIndex(early_closes or []),
        )

        class WorkCalendar:
            def get_weekend_days(self) -> tuple[int, int]:
                return (5, 6)

            def holidays(self, year: int) -> list[tuple[date, str]]:
                if not work_year_ok(year):
                    raise KeyError(year)
                return [(date(year, 1, 1), "New year")]

        registry = SimpleNamespace(
            get_calendars=lambda include_subregions=True: {"FAKE": WorkCalendar},
            get=lambda code: {"FAKE": WorkCalendar}.get(code),
        )
        modules: dict[str, Any] = {
            "pandas_market_calendars": SimpleNamespace(get_calendar_names=lambda: ["FAKE"], get_calendar=lambda n: pmc_cal),
            "exchange_calendars": SimpleNamespace(get_calendar_names=lambda: ["FAKE"], get_calendar=lambda n: xcal_cal),
            "workalendar.registry": SimpleNamespace(registry=registry),
        }
        monkeypatch.setattr(bizdays.external, "import_module", lambda n: modules[n])

    return install


@pytest.mark.parametrize(
    "weekmask, weekdays",
    [
        ("Mon Tue Wed Thu Fri", ["Saturday", "Sunday"]),
        ("Sun Mon Tue Wed Thu", ["Friday", "Saturday"]),
        ("1111100", ["Saturday", "Sunday"]),
        ("Mon Tue Wed Thu Fri Sat Sun", []),
    ],
)
def test_pmc_weekdays_from_weekmask(fake: Callable[..., None], weekmask: str, weekdays: list[str]) -> None:
    fake(weekmask=weekmask)
    assert bizdays.external.load_pandas_market_calendar("FAKE")["weekdays"] == weekdays


def test_pmc_range_from_holidays(fake: Callable[..., None]) -> None:
    fake()
    cal = Calendar.load(name="PMC/FAKE")
    assert cal.name == "PMC/FAKE"
    assert (cal.startdate, cal.enddate) == (date(2024, 1, 1), date(2024, 12, 25))


_WEEKDAYS_EXCEPT_8 = [str(d.date()) for d in pd.bdate_range("2024-01-01", "2024-01-12") if d.day != 8]


def test_xcal_early_close_is_bizday(fake: Callable[..., None]) -> None:
    fake(sessions=_WEEKDAYS_EXCEPT_8, early_closes=["2024-01-09"])
    # a session counts whatever its hours
    assert Calendar.load(name="XCAL/FAKE").isbizday("2024-01-09")


def test_xcal_non_sessions_become_holidays(fake: Callable[..., None]) -> None:
    fake(sessions=_WEEKDAYS_EXCEPT_8)
    cal = Calendar.load(name="XCAL/FAKE")
    assert cal.weekdays == ()
    assert cal.holidays == [date(2024, 1, 6), date(2024, 1, 7), date(2024, 1, 8)]
    assert (cal.startdate, cal.enddate) == (date(2024, 1, 1), date(2024, 1, 12))
    assert not cal.isbizday("2024-01-08")
    assert cal.isbizday("2024-01-09")


def test_work_full_window_when_every_year_works(fake: Callable[..., None]) -> None:
    fake()
    cal = Calendar.load(name="WORK/FAKE")
    assert (cal.startdate, cal.enddate) == (date(1991, 1, 1), date(2051, 12, 31))
    assert cal.weekdays == ("Saturday", "Sunday")


def test_work_range_is_computable_years(fake: Callable[..., None]) -> None:
    fake(work_year_ok=lambda y: 2018 <= y <= 2023)
    cal = Calendar.load(name="WORK/FAKE")
    assert (cal.startdate, cal.enddate) == (date(2018, 1, 1), date(2023, 12, 31))


def test_work_latest_run_wins(fake: Callable[..., None]) -> None:
    fake(work_year_ok=lambda y: 1995 <= y <= 1999 or 2010 <= y <= 2020)
    cal = Calendar.load(name="WORK/FAKE")
    assert (cal.startdate, cal.enddate) == (date(2010, 1, 1), date(2020, 12, 31))


def test_work_no_computable_year_raises(fake: Callable[..., None]) -> None:
    fake(work_year_ok=lambda y: False)
    with pytest.raises(ValueError, match="no computable year"):
        Calendar.load(name="WORK/FAKE")


@pytest.mark.parametrize(
    "prefix, key, modules, extra",
    [
        ("PMC/", "pandas_market_calendars", ["pandas_market_calendars"], "pmc"),
        ("XCAL/", "exchange_calendars", ["exchange_calendars"], "xcal"),
        ("WORK/", "workalendar", ["workalendar", "workalendar.registry"], "work"),
    ],
)
def test_provider_absent(
    monkeypatch: pytest.MonkeyPatch, prefix: str, key: str, modules: list[str], extra: str
) -> None:
    for m in modules:
        # None in sys.modules makes import raise ImportError, even when the package is installed
        monkeypatch.setitem(sys.modules, m, None)
    assert list_calendars()[key] == {"available": False, "prefix": prefix, "calendars": []}
    with pytest.raises(ImportError, match=rf"bizdays\[{extra}\]"):
        Calendar.load(name=f"{prefix}ANY")
