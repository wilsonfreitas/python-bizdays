import importlib

import pytest

import bizdays
import bizdays.utils
from bizdays import Calendar


def test_all_names():
    assert bizdays.__all__ == ["Calendar", "list_calendars", "DateOutOfRange"]
    for name in bizdays.__all__:
        assert hasattr(bizdays, name)


def test_date_out_of_range_is_value_error():
    assert issubclass(bizdays.DateOutOfRange, ValueError)
    assert bizdays.DateOutOfRange is bizdays.utils.DateOutOfRange


def test_out_of_range_caught_as_value_error():
    cal = Calendar.load(name="ANBIMA")
    with pytest.raises(ValueError):
        cal.bizdays("1900-01-02", "2024-01-02")
    with pytest.raises(bizdays.DateOutOfRange):
        cal.bizdays("1900-01-02", "2024-01-02")


def test_legacy_names_removed():
    with pytest.raises(ImportError):
        from bizdays import get_option  # noqa: F401
    with pytest.raises(ImportError):
        from bizdays import set_option  # noqa: F401
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("bizdays.bizdays")
