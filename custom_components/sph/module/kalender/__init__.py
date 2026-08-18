"""Schulportal Hessen calendar module."""

from .client import SphCalendarClient
from .coordinator import SphCalendarCoordinator
from .sensor import SphCalendarSensor

__all__ = ["SphCalendarClient", "SphCalendarCoordinator", "SphCalendarSensor"]
