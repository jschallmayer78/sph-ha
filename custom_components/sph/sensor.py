from __future__ import annotations
import re
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import CONF_CHILD_NAME, CONF_CHILD_SHORTCUT, DOMAIN

SUBJECT_NAMES = {
    "M": "Mathematik", "D": "Deutsch", "E": "Englisch", "F": "Französisch", "L": "Latein", "G": "Geschichte", "GE": "Geschichte", "EK": "Erdkunde", "POW": "Politik und Wirtschaft", "PW": "Politik und Wirtschaft", "PH": "Physik", "CH": "Chemie", "BIO": "Biologie", "SP": "Sport", "MU": "Musik", "ETH": "Ethik", "RKA": "Religion katholisch", "REV": "Religion evangelisch", "RELI": "Religion", "INF": "Informatik", "KU": "Kunst", "LRS": "Lese-Rechtschreib-Schwäche",
}


def subject_name(subject):
    if not subject:
        return subject
    value = str(subject).strip()
    match = re.match(r"^([A-Za-zÄÖÜäöü]+)(\d+)(.*)$", value)
    if match:
        code, number, suffix = match.groups()
        base = SUBJECT_NAMES.get(code.upper())
        if base:
            return f"{base} {number}{suffix}"
    return SUBJECT_NAMES.get(value.upper(), value)


def enrich_days(days):
    return [[dict(lesson, fach=subject_name(lesson.get("subject"))) for lesson in day] for day in (days or [])]


def _child_label(entry) -> str:
    name = str(entry.data.get(CONF_CHILD_NAME, "")).strip()
    shortcut = str(entry.data.get(CONF_CHILD_SHORTCUT, "")).strip()
    if name and shortcut:
        return f"{name} ({shortcut})"
    return name or shortcut or "Schulportal Hessen"


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SphTimetableSensor(data["timetable"], entry),
        SphCalendarSensor(data["calendar"], entry),
    ])


class SphTimetableSensor(CoordinatorEntity, SensorEntity):
    # Include the child in the entity name, yielding e.g. sensor.stundenplan_maxim_mk.
    _attr_has_entity_name = False
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_timetable"
        self._attr_name = f"Stundenplan {_child_label(entry)}"

    @property
    def native_value(self):
        return "verfügbar" if self.coordinator.data else "unbekannt"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {"kind": self.entry.data.get(CONF_CHILD_NAME, ""), "kind_kürzel": self.entry.data.get(CONF_CHILD_SHORTCUT, ""), "wochenkennung": data.get("week_badge"), "tage": enrich_days(data.get("all", [])), "eigener_plan": enrich_days(data.get("own", []))}


class SphCalendarSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = False
    _attr_icon = "mdi:calendar-multiple"
    _attr_native_unit_of_measurement = "Termine"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_name = f"Schulkalender {_child_label(entry)}"

    @property
    def native_value(self):
        return len(self.coordinator.data or [])

    @property
    def extra_state_attributes(self):
        return {"kind": self.entry.data.get(CONF_CHILD_NAME, ""), "kind_kürzel": self.entry.data.get(CONF_CHILD_SHORTCUT, ""), "termine": self.coordinator.data or [], "attribution": "Schulportal Hessen"}
