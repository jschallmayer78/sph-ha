from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import CONF_PASSWORD, CONF_SCHOOL_ID, CONF_USERNAME, CONF_UPDATE_INTERVAL
from .sph_client import SphClient

_LOGGER = logging.getLogger(__name__)

class SphTimetableCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.entry = entry
        self.client = SphClient(entry.data[CONF_SCHOOL_ID], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
        interval = entry.data.get(CONF_UPDATE_INTERVAL, 15)
        super().__init__(hass, logger=_LOGGER, name="Schulportal Hessen Stundenplan", update_interval=timedelta(minutes=int(interval)))

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.client.get_timetable)
        except Exception as err:
            raise UpdateFailed(str(err)) from err
