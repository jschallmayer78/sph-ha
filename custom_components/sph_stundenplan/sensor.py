from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, CONF_CLASS

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SphTimetableSensor(hass.data[DOMAIN][entry.entry_id], entry)])

class SphTimetableSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_timetable"
        self._attr_name = "Stundenplan"

    @property
    def native_value(self):
        return "verfügbar" if self.coordinator.data else "unbekannt"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {"klasse": self.entry.data.get(CONF_CLASS, ""), "wochenkennung": data.get("week_badge"), "tage": data.get("all", []), "eigener_plan": data.get("own", [])}

    async def async_update(self):
        await self.coordinator.async_request_refresh()
