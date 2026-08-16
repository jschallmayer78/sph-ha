from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_SOURCE_ENTRY, DOMAIN
from .coordinator import SphCalendarCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = SphCalendarCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    async_add_entities([SphCalendarSensor(coordinator, entry)])


class SphCalendarSensor(CoordinatorEntity[SphCalendarCoordinator], SensorEntity):
    _attr_icon = "mdi:calendar-multiple"
    _attr_native_unit_of_measurement = "Termine"

    def __init__(self, coordinator: SphCalendarCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        source_id = entry.data[CONF_SOURCE_ENTRY]
        source = coordinator.hass.config_entries.async_get_entry(source_id)
        child = source.data.get("child_name", source.title) if source else entry.title
        shortcut = source.data.get("child_shortcut", "") if source else ""
        self._attr_name = f"Schulkalender {child}"
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        if shortcut:
            self._attr_name = f"Schulkalender {child} ({shortcut})"

    @property
    def native_value(self):
        return len(self.coordinator.data or [])

    @property
    def extra_state_attributes(self):
        return {
            ATTR_ATTRIBUTION: "Schulportal Hessen",
            "kind": self._entry_title_child(),
            "termine": self.coordinator.data or [],
        }

    def _entry_title_child(self) -> str:
        source = self.coordinator.hass.config_entries.async_get_entry(
            self._entry.data[CONF_SOURCE_ENTRY]
        )
        return source.data.get("child_name", source.title) if source else self._entry.title
