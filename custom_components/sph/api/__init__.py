"""Shared SPH API helpers."""

from __future__ import annotations

from datetime import date, datetime

_HESSEN_SUMMER_HOLIDAY_END = {
    2025: date(2025, 8, 15),
    2026: date(2026, 8, 7),
    2027: date(2027, 8, 6),
    2028: date(2028, 8, 11),
    2029: date(2029, 8, 24),
    2030: date(2030, 8, 30),
}


def current_school_year_start(value: datetime | date) -> int:
    """Return the start year of the current Hessen school year."""
    current = value.date() if isinstance(value, datetime) else value
    for school_year, summer_end in sorted(_HESSEN_SUMMER_HOLIDAY_END.items()):
        next_summer_end = _HESSEN_SUMMER_HOLIDAY_END.get(school_year + 1)
        if current > summer_end and (next_summer_end is None or current <= next_summer_end):
            return school_year
    return current.year if current.month >= 8 else current.year - 1


from .client import SphAuthClient, SphClient  # noqa: E402

__all__ = ["SphAuthClient", "SphClient", "current_school_year_start"]
