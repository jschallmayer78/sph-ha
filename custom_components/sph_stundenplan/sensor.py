from __future__ import annotations

import re

from homeassistant.components.sensor import SensorEntity

from .const import CONF_CHILD_SHORTCUT, DOMAIN

SUBJECT_NAMES = {
    "M": "Mathematik", "D": "Deutsch", "E": "Englisch", "F": "Französisch",
    "L": "Latein", "G": "Geschichte", "GE": "Geschichte", "EK": "Erdkunde",
    "POW": "Politik und Wirtschaft", "PW": "Politik und Wirtschaft", "PH": "Physik",
    "CH": "Chemie", "BIO": "Biologie", "SP": "Sport", "MU": "Musik",
    "ETH": "Ethik", "RKA": "Religion katholisch", "REV": "Religion evangelisch",
    "RELI": "Religion", "INF": "Informatik", "KU": "Kunst", "LRS": "Lese-Rechtschreib-Schwäche",
}


def subject_name(subject):
    """Expand a subject code while preserving group numbers/details."""
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


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SphTimetableSensor(hass.data[DOMAIN][entry.entry_id], entry)])


class SphTimetableSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_timetable"
        self.child_shortcut = entry.data.get(CONF_CHILD_SHORTCUT, "").strip()
        # Existing entries without a shortcut remain selectable by their entity ID.
        self._attr_name = f"Stundenplan {self.child_shortcut}" if self.child_shortcut else "Stundenplan"

    @property
    def native_value(self):
        return "verfügbar" if self.coordinator.data else "unbekannt"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "kind": self.child_shortcut,
            "kind_kürzel": self.child_shortcut,
            "wochenkennung": data.get("week_badge"),
            "tage": enrich_days(data.get("all", [])),
            "eigener_plan": enrich_days(data.get("own", [])),
        }

    async def async_update(self):
        await self.coordinator.async_request_refresh()
