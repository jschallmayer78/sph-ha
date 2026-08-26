"""Binary sensor platform dispatcher for the SPH modules."""

from .const import DOMAIN
from .module.vertretung.binary_sensor import SphFirstLessonCancelledSensor


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    vertretung = data.get("vertretung")
    if vertretung is None:
        return
    async_add_entities(
        [
            SphFirstLessonCancelledSensor(vertretung, entry, offset=0),
            SphFirstLessonCancelledSensor(vertretung, entry, offset=1),
        ]
    )


__all__ = ["async_setup_entry", "SphFirstLessonCancelledSensor"]
