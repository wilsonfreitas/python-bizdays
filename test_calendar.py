from bizdays import Calendar
import pytest


def test_calendar_load():
    cal = Calendar.load("B3")
    assert cal.name == "B3"
    cal = Calendar.load("ANBIMA")
    assert cal.name == "ANBIMA"


def test_calendar_load_invalid():
    with pytest.raises(Exception):
        cal = Calendar.load("B1")


def test_calendar_load_pmc():
    cal = Calendar.load("PMC/B3")
    assert cal.name == "PMC/B3"
    assert len(cal.holidays) > 4000
