from __future__ import annotations

from datetime import date, datetime, timedelta
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from ..stundenplan.sensor import child_label

_LOGGER = logging.getLogger(__name__)


def _parse(value):
    """Parse an ISO timestamp from the calendar client."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        _LOGGER.debug("SPH: Kalender-Zeitstempel nicht lesbar: %s", value)
        return None


def to_calendar_event(raw: dict) -> CalendarEvent | None:
    """Convert one calendar entry of the SPH export into a HA calendar event."""
    start = _parse(raw.get("start"))
    if start is None:
        return None
    end = _parse(raw.get("end")) or start

    if raw.get("all_day"):
        start_value: date = start.date()
        # Home Assistant treats the end of an all-day event as exclusive, while
        # the SPH export marks the last day itself (23:59:59 of that day).
        end_value: date = end.date() + timedelta(days=1)
        if end_value <= start_value:
            end_value = start_value + timedelta(days=1)
    else:
        start_value = dt_util.as_local(start) if start.tzinfo else start.replace(
            tzinfo=dt_util.DEFAULT_TIME_ZONE
        )
        end_dt = dt_util.as_local(end) if end.tzinfo else end.replace(
            tzinfo=dt_util.DEFAULT_TIME_ZONE
        )
        if end_dt <= start_value:
            end_dt = start_value + timedelta(hours=1)
        end_value = end_dt

    description_parts = [
        str(raw.get("description") or "").strip(),
        f"Art: {raw['art']}" if str(raw.get("art") or "").strip() else "",
        f"Verantwortlich: {raw['verantwortlich']}"
        if str(raw.get("verantwortlich") or "").strip()
        else "",
    ]
    description = "\n".join(part for part in description_parts if part)

    return CalendarEvent(
        start=start_value,
        end=end_value,
        summary=str(raw.get("summary") or "Termin"),
        description=description or None,
        location=str(raw.get("location") or "") or None,
        uid=str(raw.get("uid") or "") or None,
    )


class SphSchoolCalendar(CoordinatorEntity, CalendarEntity):
    """Real calendar entity for the SPH school calendar."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:school"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_calendar_entity"
        self._attr_name = f"Schulkalender {child_label(entry)}"

    def _events(self) -> list[CalendarEvent]:
        events = []
        for raw in self.coordinator.data or []:
            event = to_calendar_event(raw)
            if event is not None:
                events.append(event)
        events.sort(key=lambda item: _sort_key(item.start))
        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next or currently running event."""
        now = dt_util.now()
        upcoming = [event for event in self._events() if _end_dt(event) > now]
        return upcoming[0] if upcoming else None

    async def async_get_events(self, hass, start_date, end_date):
        """Return all events overlapping the requested range."""
        return [
            event
            for event in self._events()
            if _start_dt(event) < end_date and _end_dt(event) > start_date
        ]


def _sort_key(value):
    return _as_datetime(value)


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return datetime.combine(value, datetime.min.time(), tzinfo=dt_util.DEFAULT_TIME_ZONE)


def _start_dt(event: CalendarEvent) -> datetime:
    return _as_datetime(event.start)


def _end_dt(event: CalendarEvent) -> datetime:
    return _as_datetime(event.end)
