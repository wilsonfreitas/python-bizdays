from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, TypeAlias

import numpy as np

TargetKind: TypeAlias = Literal["day", "bizday", "weekday"]
RefKind: TypeAlias = Literal["year", "month", "date"]

_YEAR_RE = re.compile(r"^\d{4}$")
_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_ORDINALS = {
    "first": 1,
    "1st": 1,
    "second": 2,
    "2nd": 2,
    "third": 3,
    "3rd": 3,
    "last": -1,
}

_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass(frozen=True)
class GetDateTarget:
    kind: TargetKind
    weekday: int | None = None


@dataclass(frozen=True)
class SimpleGetDateExpression:
    kind: Literal["simple"]
    count: int
    target: GetDateTarget


@dataclass(frozen=True)
class CompositeGetDateExpression:
    kind: Literal["composite"]
    count: int
    target: GetDateTarget
    operator: Literal["before", "after"]
    anchor_count: int
    anchor_target: GetDateTarget


@dataclass(frozen=True)
class RelativeGetDateExpression:
    kind: Literal["relative"]
    operator: Literal["next", "previous"]
    weekday: int


GetDateExpression: TypeAlias = (
    SimpleGetDateExpression
    | CompositeGetDateExpression
    | RelativeGetDateExpression
)


@dataclass(frozen=True)
class NormalizedRef:
    kind: RefKind
    year: int | None = None
    month: int | None = None
    date: np.datetime64 | None = None


def _parse_ordinal(token: str, *, relative_offset: bool = False) -> int:
    token = token.lower()
    if token in _ORDINALS:
        value = _ORDINALS[token]
        if relative_offset and value < 0:
            return 1
        return value
    match = re.fullmatch(r"(\d+)(st|nd|rd|th)", token)
    if match is None:
        raise ValueError(f"Invalid ordinal in getdate expression: {token}")
    return int(match.group(1))


def _parse_target(token: str) -> GetDateTarget:
    token = token.lower()
    if token == "day":
        return GetDateTarget("day")
    if token == "bizday":
        return GetDateTarget("bizday")
    key = token[:3]
    if key in _WEEKDAYS:
        return GetDateTarget("weekday", weekday=_WEEKDAYS.index(key))
    raise ValueError(f"Invalid day token in getdate expression: {token}")


def parse_getdate_expression(expr: str) -> GetDateExpression:
    tokens = expr.lower().split()
    if len(tokens) == 2 and tokens[0] in {"next", "previous"}:
        target = _parse_target(tokens[1])
        if target.kind != "weekday":
            raise ValueError(
                "Date-relative next/previous expressions require a "
                "weekday target"
            )
        assert target.weekday is not None
        if tokens[0] == "next":
            return RelativeGetDateExpression(
                "relative", "next", target.weekday
            )
        return RelativeGetDateExpression(
            "relative", "previous", target.weekday
        )
    if len(tokens) == 2:
        return SimpleGetDateExpression(
            "simple",
            _parse_ordinal(tokens[0]),
            _parse_target(tokens[1]),
        )
    if len(tokens) == 5:
        operator = tokens[2]
        if operator not in {"before", "after"}:
            raise ValueError(
                f"Invalid operator in getdate expression: {operator}"
            )
        relative_operator: Literal["before", "after"] = (
            "before" if operator == "before" else "after"
        )
        return CompositeGetDateExpression(
            "composite",
            _parse_ordinal(tokens[0], relative_offset=True),
            _parse_target(tokens[1]),
            relative_operator,
            _parse_ordinal(tokens[3]),
            _parse_target(tokens[4]),
        )
    raise ValueError(f"Invalid getdate expression: {expr}")


def normalize_ref(ref: object) -> NormalizedRef:
    if isinstance(ref, bool):
        raise ValueError(f"Invalid getdate ref: {ref!r}")
    if isinstance(ref, (int, np.integer)):
        return NormalizedRef("year", year=int(ref))
    if isinstance(ref, str):
        if _DATE_RE.fullmatch(ref):
            return NormalizedRef("date", date=np.datetime64(ref, "D"))
        month_match = _MONTH_RE.fullmatch(ref)
        if month_match is not None:
            year = int(month_match.group(1))
            month = int(month_match.group(2))
            if not 1 <= month <= 12:
                raise ValueError(f"Invalid getdate ref: {ref!r}")
            return NormalizedRef("month", year=year, month=month)
        if _YEAR_RE.fullmatch(ref):
            return NormalizedRef("year", year=int(ref))
        raise ValueError(f"Invalid getdate ref: {ref!r}")
    if isinstance(ref, datetime):
        return NormalizedRef("date", date=np.datetime64(ref.date(), "D"))
    if isinstance(ref, date):
        return NormalizedRef("date", date=np.datetime64(ref, "D"))
    if isinstance(ref, np.datetime64):
        if np.isnat(ref):
            raise ValueError("Invalid getdate ref: NaT")
        return NormalizedRef("date", date=ref.astype("datetime64[D]"))
    raise ValueError(f"Invalid getdate ref: {ref!r}")
