from __future__ import annotations

import logging
import requests

from ..const import SPH_CONNECT, SPH_LOGIN
from .client import SphClient

_LOGGER = logging.getLogger(__name__)


class SphAuthClient(SphClient):
    """SPH client using the proven authentication bootstrap flow.

    The same client instance is shared by the timetable and calendar
    coordinators. The authenticated session is therefore reused instead of
    performing the complete login handshake once per module.
    """

    def __init__(self, school_id, username, password):
        super().__init__(school_id, username, password)
        self._logged_in = False

    def login(self, force: bool = False):
        """Authenticate once and reuse the session for all SPH modules."""
        if self._logged_in and not force:
            _LOGGER.debug("SPH: verwende bestehende Login-Session für Benutzer %s", self.username)
            return

        self._logged_in = False
        login_url = self._get_login_url()
        response = self.session.get(login_url, allow_redirects=False, timeout=15)
        _LOGGER.debug("SPH: Ziel der Login-Weiterleitung HTTP %s, URL=%s", response.status_code, login_url)
        if response.status_code not in (200, 301, 302, 303, 307, 308):
            raise RuntimeError("SPH-Anmeldung konnte nicht abgeschlossen werden.")

        _LOGGER.debug("SPH: Login erfolgreich für Benutzer %s", self.username)
        self._handshake()
        self._logged_in = True

    def _get_login_url(self):
        _LOGGER.debug("SPH: starte Login-Handshake für Schulnummer %s", self.school_id)

        bootstrap = requests.Session()
        bootstrap.headers["User-Agent"] = self.session.headers["User-Agent"]

        response = bootstrap.post(
            f"{SPH_LOGIN}?i={self.school_id}",
            data={
                "user": f"{self.school_id}.{self.username}",
                "user2": self.username,
                "password": self.password,
            },
            allow_redirects=False,
            timeout=15,
        )

        _LOGGER.debug("SPH: Login-Request HTTP %s", response.status_code)

        if response.status_code == 503:
            raise RuntimeError("Schulportal Hessen ist nicht verfügbar.")

        location = response.headers.get("Location")
        if not location:
            _LOGGER.debug("SPH: login.php lieferte keine Weiterleitung")
            raise RuntimeError("SPH-Anmeldung fehlgeschlagen. Zugangsdaten prüfen.")

        connect = bootstrap.get(SPH_CONNECT, allow_redirects=False, timeout=15)
        _LOGGER.debug(
            "SPH: connect.php HTTP %s, Location vorhanden=%s",
            connect.status_code,
            bool(connect.headers.get("Location")),
        )

        login_url = connect.headers.get("Location")
        if not login_url:
            raise RuntimeError("SPH-Anmeldung konnte nicht abgeschlossen werden.")

        return login_url
