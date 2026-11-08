from __future__ import annotations

from datetime import date
from importlib import import_module
from typing import TypedDict

import numpy as np
import pandas as pd


class ExternalCalendarData(TypedDict):
    holidays: list[date]
    weekdays: list[str]
    startdate: date | None
    enddate: date | None


WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
WORKALENDAR_START_YEAR = 1991
WORKALENDAR_END_YEAR = 2051


def list_pandas_market_calendar_names() -> list[str]:
    mcal = import_module("pandas_market_calendars")
    return [str(name) for name in dict.fromkeys(mcal.get_calendar_names())]


def load_pandas_market_calendar(name: str) -> ExternalCalendarData:
    mcal = import_module("pandas_market_calendars")
    cal = mcal.get_calendar(name)
    hol = cal.holidays()
    return {
        "holidays": [pd.Timestamp(d).date() for d in hol.holidays],
        # busdaycalendar accepts both "Sun Mon Tue Wed Thu" and "1111100"
        "weekdays": [
            WEEKDAY_NAMES[i] for i, open_ in enumerate(np.busdaycalendar(weekmask=cal.weekmask).weekmask) if not open_
        ],
        "startdate": None,
        "enddate": None,
    }


def list_exchange_calendar_names() -> list[str]:
    xcals = import_module("exchange_calendars")
    return [str(name) for name in dict.fromkeys(xcals.get_calendar_names())]


def load_exchange_calendar(name: str) -> ExternalCalendarData:
    xcals = import_module("exchange_calendars")
    cal = xcals.get_calendar(name)
    first_session = pd.Timestamp(cal.first_session).normalize()
    last_session = pd.Timestamp(cal.last_session).normalize()
    all_days = pd.date_range(start=first_session, end=last_session, freq="D")
    sessions = pd.DatetimeIndex(
        cal.sessions_in_range(first_session, last_session)
    ).normalize()
    holidays = all_days.difference(sessions)
    return {
        "holidays": [session.date() for session in holidays],
        "weekdays": [],
        "startdate": first_session.date(),
        "enddate": last_session.date(),
    }


def list_workalendar_calendar_names() -> list[str]:
    registry_module = import_module("workalendar.registry")
    registry = registry_module.registry
    calendars = registry.get_calendars(include_subregions=True)
    return [str(name) for name in calendars.keys()]


def load_workalendar_calendar(name: str) -> ExternalCalendarData:
    registry_module = import_module("workalendar.registry")
    registry = registry_module.registry
    calendar_class = registry.get(name)
    if calendar_class is None:
        raise ValueError(f"Unknown workalendar code: {name}")

    cal = calendar_class()
    weekend_days = tuple(cal.get_weekend_days())
    run: list[int] = []
    holidays: set[date] = set()
    for year in range(WORKALENDAR_END_YEAR, WORKALENDAR_START_YEAR - 1, -1):
        try:
            year_holidays = cal.holidays(year)
        except Exception:  # workalendar raises its own types for years it does not know
            if run:
                break
            continue
        run.append(year)
        holidays.update(holiday for holiday, _ in year_holidays)
    if not run:
        raise ValueError(
            f"workalendar calendar {name!r} has no computable year in {WORKALENDAR_START_YEAR}..{WORKALENDAR_END_YEAR}"
        )

    return {
        "holidays": sorted(holidays),
        "weekdays": [WEEKDAY_NAMES[weekday] for weekday in weekend_days],
        "startdate": date(run[-1], 1, 1),
        "enddate": date(run[0], 12, 31),
    }
