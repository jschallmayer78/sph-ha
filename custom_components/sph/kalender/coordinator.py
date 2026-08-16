from __future__ import annotations
from datetime import datetime, timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from ..api.client import SphClient
from ..const import CONF_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

class SphCalendarCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client: SphClient):
        self.entry = entry
        self.client = client
        super().__init__(hass, logger=_LOGGER, name="Schulportal Hessen Kalender", update_interval=timedelta(minutes=int(entry.data.get(CONF_UPDATE_INTERVAL, 15))))

    async def _async_update_data(self):
        try:
            today = datetime.now().date()
            start = datetime.combine(today - timedelta(days=31), datetime.min.time())
            end = datetime.combine(today + timedelta(days=365), datetime.max.time())
            return await self.hass.async_add_executor_job(self.client.get_calendar, start, end)
        except Exception as err:
            raise UpdateFailed(str(err)) from err
