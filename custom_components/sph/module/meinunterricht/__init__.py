"""Schulportal Hessen Mein-Unterricht module."""

from .client import SphMeinUnterrichtClient
from .coordinator import SphMeinUnterrichtCoordinator
from .sensor import SphMeinUnterrichtSensor

__all__ = [
    "SphMeinUnterrichtClient",
    "SphMeinUnterrichtCoordinator",
    "SphMeinUnterrichtSensor",
]
