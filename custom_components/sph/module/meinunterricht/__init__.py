"""Schulportal Hessen Mein-Unterricht module."""

from .client import SphMeinUnterrichtClient
from .helpers import subject_overview
from .coordinator import SphMeinUnterrichtCoordinator
from .sensor import SphMeinUnterrichtSensor

__all__ = [
    "SphMeinUnterrichtClient",
    "subject_overview",
    "SphMeinUnterrichtCoordinator",
    "SphMeinUnterrichtSensor",
]
