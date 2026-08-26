"""Shared helpers for the SPH substitution plan module."""

from __future__ import annotations

from datetime import date, timedelta

from homeassistant.util import dt as dt_util


def plan_days(data) -> list[dict]:
    """Return the day entries of a substitution plan payload."""
    if not isinstance(data, dict):
        return []
    days = data.get("tage")
    return days if isinstance(days, list) else []


def day_for_date(data, wanted: date) -> dict | None:
    """Return the plan of a specific date, if the plan covers it."""
    target = wanted.isoformat()
    for day in plan_days(data):
        if day.get("datum") == target:
            return day
    return None


def today() -> date:
    """Return the current local date."""
    return dt_util.now().date()


def tomorrow() -> date:
    """Return the next local date."""
    return today() + timedelta(days=1)


def entries_for(data, wanted: date) -> list[dict]:
    """Return the substitution entries of a specific date."""
    day = day_for_date(data, wanted)
    if not day:
        return []
    entries = day.get("eintraege")
    return entries if isinstance(entries, list) else []


def covers_lesson(entry: dict, lesson: int) -> bool:
    """Return whether an entry applies to a given school lesson."""
    lessons = entry.get("stunden")
    if isinstance(lessons, list) and lessons:
        return lesson in lessons
    return False


def first_lesson_cancelled(data, wanted: date, lesson: int = 1) -> bool | None:
    """Return whether a given lesson is cancelled on a date.

    ``None`` means the plan does not cover that date at all, so no statement
    can be made. That is deliberately different from ``False`` ("plan exists,
    lesson takes place").
    """
    day = day_for_date(data, wanted)
    if day is None:
        return None
    return any(
        entry.get("entfall") and covers_lesson(entry, lesson)
        for entry in day.get("eintraege", [])
    )
