import pytest

from bizdays.calendar import Calendar


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


def test_public_option_import():
    """get_option and set_option are importable from the top-level package."""
    from bizdays import get_option, set_option
    set_option("mode", "python")
    assert get_option("mode") == "python"
