"""Schulportal Hessen timetable module."""

from .client import SphTimetableClient
from .coordinator import SphTimetableCoordinator
from .sensor import SphTimetableSensor

__all__ = ["SphTimetableClient", "SphTimetableCoordinator", "SphTimetableSensor"]
