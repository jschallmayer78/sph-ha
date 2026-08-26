from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ...api.subjects import SUBJECT_NAMES, subject_name  # noqa: F401  (re-exported)
from ...const import CONF_CHILD_NAME, CONF_CHILD_SHORTCUT


def enrich_days(days):
    return [
        [dict(lesson, fach=subject_name(lesson.get("subject"))) for lesson in day]
        for day in (days or [])
    ]


def child_label(entry) -> str:
    name = str(entry.data.get(CONF_CHILD_NAME, "")).strip()
    shortcut = str(entry.data.get(CONF_CHILD_SHORTCUT, "")).strip()
    if name and shortcut:
        return f"{name} ({shortcut})"
    return name or shortcut or "Schulportal Hessen"


class SphTimetableSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = False
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_timetable"
        self._attr_name = f"Stundenplan {child_label(entry)}"

    def _current_data(self):
        """Return current data or the last successfully parsed timetable."""
        return self.coordinator.data or self.coordinator.last_successful_data or {}

    @property
    def available(self):
        """Keep the entity available when a refresh temporarily fails."""
        return bool(self._current_data())

    @property
    def native_value(self):
        return "verfügbar" if self._current_data() else "unbekannt"

    @property
    def extra_state_attributes(self):
        data = self._current_data()
        return {
            "kind": self.entry.data.get(CONF_CHILD_NAME, ""),
            "kind_kürzel": self.entry.data.get(CONF_CHILD_SHORTCUT, ""),
            "klasse": data.get("klasse", ""),
            "wochenkennung": data.get("week_badge"),
            "tage": enrich_days(data.get("all", [])),
            "eigener_plan": enrich_days(data.get("own", [])),
        }
