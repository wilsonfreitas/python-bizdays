import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CalendarDefinition:
    name: str
    weekdays: list[str]
    holidays: list[str]
    financial: bool


def _as_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Invalid calendar JSON: '{field_name}' must be a list of strings")
    return value


def _as_optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Invalid calendar JSON: '{field_name}' must be a string")
    return value


def _as_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"Invalid calendar JSON: '{field_name}' must be a boolean")
    return value


def _parse_calendar_payload(payload: Any, fallback_name: str) -> CalendarDefinition:
    if not isinstance(payload, dict):
        raise ValueError("Invalid calendar JSON: expected a JSON object")

    name = payload.get("name", fallback_name)
    if not isinstance(name, str):
        raise ValueError("Invalid calendar JSON: 'name' must be a string")

    _as_optional_string(payload.get("adjust.from"), "adjust.from")
    _as_optional_string(payload.get("adjust.to"), "adjust.to")

    return CalendarDefinition(
        name=name,
        weekdays=_as_string_list(payload.get("weekdays"), "weekdays"),
        holidays=_as_string_list(payload.get("holidays"), "holidays"),
        financial=_as_bool(payload.get("financial", True), "financial"),
    )


def load_calendar_definition(filename: str) -> CalendarDefinition:
    path = Path(filename)
    if not path.exists():
        raise Exception(f"Invalid calendar: {filename}")
    with path.open(encoding="utf-8") as calendar_file:
        return _parse_calendar_payload(json.load(calendar_file), path.stem)


def load_packaged_calendar_definition(name: str) -> CalendarDefinition:
    resource = resources.files("bizdays.data").joinpath(f"{name}.json")
    if not resource.is_file():
        raise Exception(f"Invalid calendar: {name}")
    with resource.open("r", encoding="utf-8") as calendar_file:
        return _parse_calendar_payload(json.load(calendar_file), name)
