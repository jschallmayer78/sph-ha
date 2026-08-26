"""Schulportal Hessen Vertretungsplan module."""

from .binary_sensor import SphFirstLessonCancelledSensor
from .client import SphVertretungClient
from .coordinator import SphVertretungCoordinator
from .sensor import SphVertretungSensor

__all__ = [
    "SphFirstLessonCancelledSensor",
    "SphVertretungClient",
    "SphVertretungCoordinator",
    "SphVertretungSensor",
]
