"""Shared SPH API helpers and compatibility patches."""

from __future__ import annotations

from datetime import date, datetime

# Official Hessen summer vacation end dates.
# Source: Hessisches Ministerium für Kultus, Bildung und Chancen:
# https://kultus.hessen.de/schulsystem/ferien/ferientermine
_HESSEN_SUMMER_HOLIDAY_END = {
    2025: date(2025, 8, 15),
    2026: date(2026, 8, 7),
    2027: date(2027, 8, 6),
    2028: date(2028, 8, 11),
    2029: date(2029, 8, 24),
    2030: date(2030, 8, 30),
}


def current_school_year_start(value: datetime | date) -> int:
    """Return the start year of the current Hessen school year.

    Hessen school years are determined by the official summer-vacation
    boundary, not by a fixed calendar-month rule. The first day after the
    previous summer vacation belongs to the following school year.

    Example: 2026-08-17 -> 2026/2027 because the 2025/2026 summer vacation
    ended on 2026-08-07.
    """
    current = value.date() if isinstance(value, datetime) else value

    for school_year, summer_end in sorted(_HESSEN_SUMMER_HOLIDAY_END.items()):
        next_summer_end = _HESSEN_SUMMER_HOLIDAY_END.get(school_year + 1)
        if current > summer_end and (
            next_summer_end is None or current <= next_summer_end
        ):
            return school_year

    # Graceful fallback for years not yet published in the table.
    return current.year if current.month >= 8 else current.year - 1


# client.py already contains the school-year helper, but historically used a
# simple month check. Replace it centrally so all SPH modules share the same
# Hessen-specific school-year calculation.
from .client import SphClient  # noqa: E402

SphClient._school_year_start_year = staticmethod(current_school_year_start)
