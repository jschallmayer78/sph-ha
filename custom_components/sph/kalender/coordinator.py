from __future__ import annotations

from datetime import date, datetime, timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..api.client import SphClient
from ..const import CONF_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


# Official Hessian summer holidays.  The calendar export contains some
# events from the preceding school year (most notably the summer holidays),
# so using August 1st as the boundary is not sufficient.  These dates are
# taken from the Hessian Ministry of Education's published holiday schedule.
HESSEN_SOMMERFERIEN = {
    2025: (date(2025, 7, 7), date(2025, 8, 15)),
    2026: (date(2026, 6, 29), date(2026, 8, 7)),
    2027: (date(2027, 6, 28), date(2027, 8, 6)),
    2028: (date(2028, 7, 3), date(2028, 8, 11)),
    2029: (date(2029, 7, 16), date(2029, 8, 24)),
    2030: (date(2030, 7, 22), date(2030, 8, 30)),
}


def _current_school_year(today: date) -> int:
    """Return the first calendar year of the current Hessian school year."""
    # Before the summer holidays of year N the current school year is N-1.
    # During/after the summer holidays it is still N-1 until the holidays
    # have ended.  This matters especially in July/August.
    for year, (_, summer_end) in HESSEN_SOMMERFERIEN.items():
        if summer_end < today <= date(year, 8, 31):
            return year
        if today <= summer_end and today >= date(year, 6, 1):
            return year - 1

    return today.year if today.month >= 8 else today.year - 1


def _school_year_bounds(school_year_start: int) -> tuple[datetime, datetime]:
    """Return the effective beginning/end of a Hessian school year."""
    # The first day after the previous summer holidays is the beginning of
    # the school year.  If it falls on a weekend, the calendar simply starts
    # collecting events from that date; actual events normally begin Monday.
    previous_summer = HESSEN_SOMMERFERIEN.get(school_year_start)
    next_summer = HESSEN_SOMMERFERIEN.get(school_year_start + 1)

    if previous_summer:
        start_date = previous_summer[1] + timedelta(days=1)
    else:
        start_date = date(school_year_start, 8, 1)

    if next_summer:
        end_date = next_summer[0] - timedelta(days=1)
    else:
        end_date = date(school_year_start + 1, 7, 31)

    return datetime.combine(start_date, datetime.min.time()), datetime.combine(
        end_date, datetime.max.time()
    )


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
            school_year_start = _current_school_year(today)
            start, end = _school_year_bounds(school_year_start)

            _LOGGER.debug(
                "SPH: Kalender aktuelles Schuljahr %s/%s: %s bis %s",
                school_year_start,
                school_year_start + 1,
                start.date(),
                end.date(),
            )

            events = await self.hass.async_add_executor_job(
                self.client.get_calendar, start, end
            )

            _LOGGER.debug(
                "SPH: Kalender liefert für Schuljahr %s/%s insgesamt %d Termine",
                school_year_start,
                school_year_start + 1,
                len(events or []),
            )
            return events or []
        except Exception as err:
            raise UpdateFailed(str(err)) from err
