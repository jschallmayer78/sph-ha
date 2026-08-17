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
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Schulportal Hessen Kalender",
            update_interval=timedelta(
                minutes=int(entry.data.get(CONF_UPDATE_INTERVAL, 15))
            ),
        )

    async def _async_update_data(self):
        try:
            today = datetime.now().date()

            # Always request the complete CURRENT German school year.
            # Do not derive the school year from a rolling look-back window:
            # in July/August this could otherwise select the previous school
            # year and return only the events overlapping that window.
            school_year_start = today.year if today.month >= 8 else today.year - 1
            start = datetime(school_year_start, 8, 1)
            end = datetime(school_year_start + 1, 8, 1) - timedelta(seconds=1)

            _LOGGER.debug(
                "SPH: Kalender-Zeitraum aktuelles Schuljahr %s/%s: %s bis %s",
                school_year_start,
                school_year_start + 1,
                start.date(),
                end.date(),
            )

            return await self.hass.async_add_executor_job(
                self.client.get_calendar, start, end
            )
        except Exception as err:
            raise UpdateFailed(str(err)) from err
