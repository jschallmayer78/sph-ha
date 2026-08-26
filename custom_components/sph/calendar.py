"""Calendar platform dispatcher for the SPH modules."""

from .const import DOMAIN
from .module.kalender.calendar import SphSchoolCalendar


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    calendar = data.get("calendar")
    if calendar is None:
        return
    async_add_entities([SphSchoolCalendar(calendar, entry)])


__all__ = ["async_setup_entry", "SphSchoolCalendar"]
