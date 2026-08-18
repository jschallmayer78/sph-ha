"""Sensor platform dispatcher for the SPH modules."""

from .module.kalender.sensor import SphCalendarSensor
from .module.stundenplan.sensor import SphTimetableSensor


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data["sph"][entry.entry_id]
    async_add_entities(
        [
            SphTimetableSensor(data["timetable"], entry),
            SphCalendarSensor(data["calendar"], data["timetable"], entry),
        ]
    )


__all__ = ["async_setup_entry", "SphTimetableSensor", "SphCalendarSensor"]
