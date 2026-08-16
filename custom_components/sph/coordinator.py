from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api.client import SphClient
from .const import CONF_PASSWORD, CONF_SCHOOL_ID, CONF_USERNAME, CONF_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

class SphTimetableCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.entry = entry
        self.client = SphClient(entry.data[CONF_SCHOOL_ID], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
        super().__init__(hass, logger=_LOGGER, name="Schulportal Hessen Stundenplan", update_interval=timedelta(minutes=int(entry.data.get(CONF_UPDATE_INTERVAL, 15))))

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.client.get_timetable)
        except Exception as err:
            raise UpdateFailed(str(err)) from err
