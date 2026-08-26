from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ...const import CONF_CHILD_NAME, CONF_CHILD_SHORTCUT
from ...api.subjects import subject_name
from ..stundenplan.sensor import child_label
from .helpers import entries_for, plan_days, today, tomorrow


def enrich_entries(entries):
    """Add the long subject name to every entry."""
    return [
        dict(entry, fach_lang=subject_name(entry.get("fach")))
        for entry in (entries or [])
    ]


class SphVertretungSensor(CoordinatorEntity, SensorEntity):
    """Sensor exposing the published substitution plan."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:account-switch"
    _attr_native_unit_of_measurement = "Einträge"

    def __init__(self, coordinator, timetable_coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self.timetable_coordinator = timetable_coordinator
        self._attr_unique_id = f"{entry.entry_id}_vertretungsplan"
        self._attr_name = f"Vertretungsplan {child_label(entry)}"

    def _current_data(self):
        """Return current data or the last successfully parsed plan."""
        return self.coordinator.data or self.coordinator.last_successful_data or {}

    @property
    def available(self):
        """Keep the entity available when a refresh temporarily fails."""
        return bool(self._current_data())

    @property
    def native_value(self):
        return sum(day.get("anzahl", 0) for day in plan_days(self._current_data()))

    @property
    def extra_state_attributes(self):
        data = self._current_data()
        days = plan_days(data)
        timetable_data = self.timetable_coordinator.data or {}
        heute = enrich_entries(entries_for(data, today()))
        morgen = enrich_entries(entries_for(data, tomorrow()))
        return {
            "kind": self.entry.data.get(CONF_CHILD_NAME, ""),
            "kind_kürzel": self.entry.data.get(CONF_CHILD_SHORTCUT, ""),
            "klasse": timetable_data.get("klasse", ""),
            "tage": [
                dict(day, eintraege=enrich_entries(day.get("eintraege")))
                for day in days
            ],
            "heute": heute,
            "morgen": morgen,
            "anzahl_heute": len(heute),
            "anzahl_morgen": len(morgen),
            "entfaelle_heute": sum(1 for entry in heute if entry.get("entfall")),
            "entfaelle_morgen": sum(1 for entry in morgen if entry.get("entfall")),
            "hinweise": [note for day in days for note in day.get("hinweise", [])],
            "aktualisiert": data.get("aktualisiert"),
            "wird_aktualisiert": bool(data.get("wird_aktualisiert")),
            "geplante_tage": [day.get("datum") for day in days],
            "attribution": "Schulportal Hessen",
        }
