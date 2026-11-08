import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

PACKAGED_CALENDARS: tuple[str, str, str] = ("ANBIMA", "B3", "Actual")


@dataclass(frozen=True)
class CalendarDefinition:
    name: str
    weekdays: list[str]
    holidays: list[str]
    financial: bool
    startdate: str | None = None
    enddate: str | None = None


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

    # v2 always adjusts from following and to preceding; other values cannot be honoured.
    for key, default in (("adjust.from", "following"), ("adjust.to", "preceding")):
        value = _as_optional_string(payload.get(key), key)
        if value is not None and value != default:
            raise ValueError(f"Invalid calendar JSON: '{key}' must be {default!r}, got {value!r}")

    return CalendarDefinition(
        name=name,
        weekdays=_as_string_list(payload.get("weekdays"), "weekdays"),
        holidays=_as_string_list(payload.get("holidays"), "holidays"),
        financial=_as_bool(payload.get("financial", True), "financial"),
        startdate=_as_optional_string(payload.get("start.date"), "start.date"),
        enddate=_as_optional_string(payload.get("end.date"), "end.date"),
    )


def load_calendar_definition(filename: str) -> CalendarDefinition:
    path = Path(filename)
    if not path.is_file():
        raise FileNotFoundError(f"Calendar file not found: {filename}")
    with path.open(encoding="utf-8-sig") as calendar_file:
        try:
            payload = json.load(calendar_file)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid calendar file {filename}: a JSON calendar is expected. "
                "Text .cal files are no longer supported since bizdays 2.0; "
                "see the migration guide at https://wilsonfreitas.github.io/python-bizdays/migration.html"
            ) from exc
    return _parse_calendar_payload(payload, path.stem)


def load_packaged_calendar_definition(name: str) -> CalendarDefinition:
    resource = resources.files("bizdays.data").joinpath(f"{name}.json")
    if name not in PACKAGED_CALENDARS or not resource.is_file():
        raise ValueError(f"Unknown calendar: {name!r}; packaged calendars are {', '.join(PACKAGED_CALENDARS)}")
    with resource.open("r", encoding="utf-8") as calendar_file:
        return _parse_calendar_payload(json.load(calendar_file), name)


def get_packaged_calendar_names() -> list[str]:
    return list(PACKAGED_CALENDARS)
