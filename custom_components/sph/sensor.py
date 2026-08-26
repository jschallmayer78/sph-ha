"""Sensor platform dispatcher for the SPH modules."""

from .const import DOMAIN
from .module.kalender.sensor import SphCalendarSensor
from .module.meinunterricht.sensor import SphMeinUnterrichtSensor
from .module.stundenplan.sensor import SphTimetableSensor
from .module.vertretung.sensor import SphVertretungSensor


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [
        SphTimetableSensor(data["timetable"], entry),
        SphCalendarSensor(data["calendar"], data["timetable"], entry),
        SphMeinUnterrichtSensor(data["meinunterricht"], entry),
    ]
    if data.get("vertretung") is not None:
        entities.append(
            SphVertretungSensor(data["vertretung"], data["timetable"], entry)
        )
    async_add_entities(entities)


__all__ = [
    "async_setup_entry",
    "SphTimetableSensor",
    "SphCalendarSensor",
    "SphMeinUnterrichtSensor",
    "SphVertretungSensor",
]
