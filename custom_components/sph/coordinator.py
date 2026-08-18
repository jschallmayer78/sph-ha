from datetime import timedelta
from html import unescape
import logging
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api.auth_client import SphAuthClient
from .const import CONF_PASSWORD, CONF_SCHOOL_ID, CONF_USERNAME, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, SPH_BASE

_LOGGER = logging.getLogger(__name__)


class SphTimetableCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.entry = entry
        self.client = SphAuthClient(
            entry.data[CONF_SCHOOL_ID],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
        )
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Schulportal Hessen Stundenplan",
            update_interval=timedelta(
                minutes=int(entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
            ),
        )

    @staticmethod
    def _extract_student_class(html, page_url=""):
        """Extract the student's class from the authenticated timetable page."""
        soup = BeautifulSoup(html, "html.parser")

        # Prefer the explicit k= parameter used by Schulportal in timetable links.
        sources = [page_url]
        sources.extend(
            unescape(anchor.get("href", ""))
            for anchor in soup.select('a[href*="stundenplan.php"]')
        )
        for source in sources:
            try:
                value = parse_qs(urlparse(source).query).get("k", [""])[0].strip()
            except Exception:
                value = ""
            if value:
                return value

        # The page title also contains the class, e.g. <h1>7n</h1>.
        heading = soup.find("h1")
        if heading:
            text = heading.get_text(" ", strip=True)
            if text and len(text) <= 20 and text[0].isdigit():
                return text
        return ""

    async def _async_update_data(self):
        try:
            data = await self.hass.async_add_executor_job(self.client.get_timetable)

            # get_timetable() has already authenticated the shared session. Reuse
            # that session to read the class without performing another login.
            def read_class():
                response = self.client.session.get(
                    f"{SPH_BASE}/stundenplan.php",
                    allow_redirects=True,
                    timeout=20,
                )
                response.raise_for_status()
                return self._extract_student_class(response.text, response.url)

            try:
                data["klasse"] = await self.hass.async_add_executor_job(read_class)
            except Exception as class_err:
                _LOGGER.debug("SPH: Schülerklasse konnte nicht ermittelt werden: %s", class_err)
                data.setdefault("klasse", "")
            return data
        except Exception as err:
            # DataUpdateCoordinator keeps the last successful data when an
            # update raises UpdateFailed. This deliberately prevents short
            # network/SPH outages from replacing valid timetable data.
            raise UpdateFailed(str(err)) from err
