from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.sph_stundenplan.sph_client import SphClient

from .const import CONF_SOURCE_ENTRY, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SphCalendarCoordinator(DataUpdateCoordinator):
    """Fetch the personal SPH calendar using an existing SPH account."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        source_id = entry.data[CONF_SOURCE_ENTRY]
        source = hass.config_entries.async_get_entry(source_id)
        if source is None:
            raise ValueError("Das ausgewählte Schulportal-Konto existiert nicht mehr.")

        # Reuse the already authenticated timetable client/session when it is
        # available. This keeps calendar and timetable on the same credentials
        # and avoids an unnecessary second login.
        timetable_data = hass.data.get("sph_stundenplan", {})
        timetable_coordinator = timetable_data.get(source_id)
        if timetable_coordinator is not None:
            self.client = timetable_coordinator.client
        else:
            self.client = SphClient(
                source.data["school_id"],
                source.data["username"],
                source.data["password"],
            )

        interval = source.data.get("update_interval", 15)
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Schulportal Hessen Kalender",
            update_interval=timedelta(minutes=int(interval)),
        )

    async def _async_update_data(self):
        try:
            today = datetime.now().date()
            start = datetime.combine(today - timedelta(days=31), datetime.min.time())
            end = datetime.combine(today + timedelta(days=365), datetime.max.time())
            return await self.hass.async_add_executor_job(
                self.client.get_calendar, start, end
            )
        except Exception as err:
            raise UpdateFailed(str(err)) from err
