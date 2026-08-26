from __future__ import annotations

from datetime import date

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ...const import CONF_CHILD_NAME, CONF_CHILD_SHORTCUT, CONF_FIRST_LESSON
from ..stundenplan.sensor import child_label
from .helpers import day_for_date, first_lesson_cancelled, today, tomorrow


class SphFirstLessonCancelledSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor telling whether the first lesson of a day is cancelled.

    One entity exists for today and one for tomorrow. Keeping them separate
    avoids guessing which day a user means at a given time of day: an
    automation that switches off the alarm clock looks at tomorrow, a
    notification in the morning looks at today.
    """

    _attr_has_entity_name = False
    _attr_icon = "mdi:alarm-off"

    def __init__(self, coordinator, entry, offset: int):
        super().__init__(coordinator)
        self.entry = entry
        self.offset = offset
        slug = "heute" if offset == 0 else "morgen"
        label = "heute" if offset == 0 else "morgen"
        self._attr_unique_id = f"{entry.entry_id}_erste_stunde_entfaellt_{slug}"
        self._attr_name = f"Erste Stunde entfällt {label} {child_label(entry)}"

    @property
    def _lesson(self) -> int:
        return int(self.entry.data.get(CONF_FIRST_LESSON, 1))

    @property
    def _date(self) -> date:
        return today() if self.offset == 0 else tomorrow()

    def _current_data(self):
        return self.coordinator.data or self.coordinator.last_successful_data or {}

    @property
    def available(self):
        """Unavailable while no plan for that day has been published.

        Home Assistant would otherwise show ``off``, which reads as "lessons
        take place" even though the school has not published anything yet.
        """
        return day_for_date(self._current_data(), self._date) is not None

    @property
    def is_on(self):
        return bool(first_lesson_cancelled(self._current_data(), self._date, self._lesson))

    @property
    def extra_state_attributes(self):
        data = self._current_data()
        day = day_for_date(data, self._date) or {}
        entries = [
            entry
            for entry in day.get("eintraege", [])
            if entry.get("entfall") and self._lesson in (entry.get("stunden") or [])
        ]
        return {
            "kind": self.entry.data.get(CONF_CHILD_NAME, ""),
            "kind_kürzel": self.entry.data.get(CONF_CHILD_SHORTCUT, ""),
            "bezugstag": self._date.isoformat(),
            "wochentag": day.get("wochentag", ""),
            "stunde": self._lesson,
            "plan_veröffentlicht": bool(day),
            "betroffene_eintraege": entries,
            "attribution": "Schulportal Hessen",
        }
