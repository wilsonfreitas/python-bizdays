from __future__ import annotations

from datetime import date
from importlib import import_module
from typing import TypedDict

import pandas as pd


class ExternalCalendarData(TypedDict):
    holidays: list[date]
    weekdays: list[str]
    startdate: date | None
    enddate: date | None


def list_pandas_market_calendar_names() -> list[str]:
    mcal = import_module("pandas_market_calendars")
    return [str(name) for name in dict.fromkeys(mcal.get_calendar_names())]


def load_pandas_market_calendar(name: str) -> ExternalCalendarData:
    mcal = import_module("pandas_market_calendars")
    cal = mcal.get_calendar(name)
    hol = cal.holidays()
    return {
        "holidays": [pd.Timestamp(d).date() for d in hol.holidays],
        "weekdays": ["Saturday", "Sunday"],
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
