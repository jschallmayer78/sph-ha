from __future__ import annotations
import re
from collections import Counter
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import CONF_CHILD_NAME, CONF_CHILD_SHORTCUT, DOMAIN

SUBJECT_NAMES = {
    "M": "Mathematik", "D": "Deutsch", "E": "Englisch", "F": "Französisch", "L": "Latein", "G": "Geschichte", "GE": "Geschichte", "EK": "Erdkunde", "POW": "Politik und Wirtschaft", "PW": "Politik und Wirtschaft", "PH": "Physik", "CH": "Chemie", "BIO": "Biologie", "SP": "Sport", "MU": "Musik", "ETH": "Ethik", "RKA": "Religion katholisch", "REV": "Religion evangelisch", "RELI": "Religion", "INF": "Informatik", "KU": "Kunst", "LRS": "Lese-Rechtschreib-Schwäche",
}

# Home Assistant limits state attributes stored by Recorder to 16 KiB. A full
# school-year calendar can exceed that limit, so the entity deliberately exposes
# a useful preview while the coordinator keeps the complete event list in memory.
CALENDAR_ATTRIBUTE_LIMIT = 50


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


def _calendar_preview(events):
    """Return a compact, recorder-safe preview of calendar events."""
    preview = []
    for event in sorted(events or [], key=lambda item: str(item.get("start", "")))[:CALENDAR_ATTRIBUTE_LIMIT]:
        preview.append({
            "start": event.get("start", ""),
            "end": event.get("end", ""),
            "all_day": bool(event.get("all_day", False)),
            "summary": event.get("summary", ""),
            "art": event.get("art", ""),
            "verantwortlich": event.get("verantwortlich", ""),
            "location": event.get("location", ""),
            "uid": event.get("uid", ""),
        })
    return preview


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SphTimetableSensor(data["timetable"], entry),
        SphCalendarSensor(data["calendar"], entry),
    ])


class SphTimetableSensor(CoordinatorEntity, SensorEntity):
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
        return {
            "kind": self.entry.data.get(CONF_CHILD_NAME, ""),
            "kind_kürzel": self.entry.data.get(CONF_CHILD_SHORTCUT, ""),
            "wochenkennung": data.get("week_badge"),
            "tage": enrich_days(data.get("all", [])),
            "eigener_plan": enrich_days(data.get("own", [])),
        }


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
        events = self.coordinator.data or []
        art_counts = Counter(str(event.get("art", "")).strip() for event in events if str(event.get("art", "")).strip())
        responsible_counts = Counter(str(event.get("verantwortlich", "")).strip() for event in events if str(event.get("verantwortlich", "")).strip())
        return {
            "kind": self.entry.data.get(CONF_CHILD_NAME, ""),
            "kind_kürzel": self.entry.data.get(CONF_CHILD_SHORTCUT, ""),
            "termine": _calendar_preview(events),
            "termine_gesamt": len(events),
            "termine_weitere": max(0, len(events) - CALENDAR_ATTRIBUTE_LIMIT),
            "arten": dict(art_counts),
            "verantwortliche": dict(responsible_counts),
            "attribution": "Schulportal Hessen",
        }
