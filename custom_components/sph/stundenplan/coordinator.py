from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..api.client import SphAuthClient
from ..const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from .client import SphTimetableClient

_LOGGER = logging.getLogger(__name__)


class SphTimetableCoordinator(DataUpdateCoordinator):
    """Coordinator for the SPH timetable module."""

    def __init__(self, hass, entry, auth: SphAuthClient):
        self.entry = entry
        self.client = SphTimetableClient(auth)
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Schulportal Hessen Stundenplan",
            update_interval=timedelta(
                minutes=int(entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
            ),
        )

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.client.get_timetable)
        except Exception as err:
            # Keep the last successful coordinator data during short outages.
            raise UpdateFailed(str(err)) from err
