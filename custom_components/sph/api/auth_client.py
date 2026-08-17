from __future__ import annotations

from datetime import datetime, timedelta
import logging
import requests

from ..const import SPH_CONNECT, SPH_LOGIN
from .client import SphClient

_LOGGER = logging.getLogger(__name__)


class SphAuthClient(SphClient):
    """SPH client with a shared, renewable authenticated session.

    Timetable and calendar use the same client instance. The session is reused
    while it is considered fresh, but is deliberately re-authenticated before
    it can become stale on the Schulportal side. If the server invalidates the
    session unexpectedly, the first failed authenticated request triggers one
    forced login and is retried once.
    """

    SESSION_MAX_AGE = timedelta(minutes=45)

    def __init__(self, school_id, username, password):
        super().__init__(school_id, username, password)
        self._logged_in = False
        self._authenticated_at: datetime | None = None

    def login(self, force: bool = False):
        """Authenticate once and reuse the session for all SPH modules."""
        now = datetime.now()
        if (
            self._logged_in
            and self._authenticated_at is not None
            and not force
            and now - self._authenticated_at < self.SESSION_MAX_AGE
        ):
            _LOGGER.debug(
                "SPH: verwende bestehende Login-Session für Benutzer %s",
                self.username,
            )
            return

        if self._logged_in and not force:
            _LOGGER.debug(
                "SPH: gespeicherte Login-Session ist älter als %s Minuten; erneuere Session",
                int(self.SESSION_MAX_AGE.total_seconds() / 60),
            )

        self._logged_in = False
        self._authenticated_at = None

        login_url = self._get_login_url()
        response = self.session.get(login_url, allow_redirects=False, timeout=15)
        _LOGGER.debug(
            "SPH: Ziel der Login-Weiterleitung HTTP %s, URL=%s",
            response.status_code,
            login_url,
        )
        if response.status_code not in (200, 301, 302, 303, 307, 308):
            raise RuntimeError("SPH-Anmeldung konnte nicht abgeschlossen werden.")

        _LOGGER.debug("SPH: Login erfolgreich für Benutzer %s", self.username)
        self._handshake()
        self._logged_in = True
        self._authenticated_at = datetime.now()

    def _force_relogin(self):
        """Invalidate the cached authentication state."""
        self._logged_in = False
        self._authenticated_at = None
        self.key = None

    def get_timetable(self):
        """Fetch the timetable and recover once from an expired SPH session."""
        try:
            return super().get_timetable()
        except RuntimeError as err:
            message = str(err)
            if "stundenplan.php enthält weder #all noch #own" not in message:
                raise

            _LOGGER.warning(
                "SPH: Stundenplan-Abruf sieht nach abgelaufener Session aus; erneuere Anmeldung und versuche es erneut"
            )
            self._force_relogin()
            return super().get_timetable()

    def get_calendar(self, start, end, school_year=None):
        """Fetch the calendar and recover once from an expired SPH session."""
        try:
            return super().get_calendar(start, end, school_year)
        except RuntimeError as err:
            message = str(err)
            if not any(
                marker in message
                for marker in (
                    "CSV-Antwort enthält keine erwarteten Kalenderdaten",
                    "CSV-Antwort ist leer",
                    "konnte nicht als iCal abgerufen werden",
                )
            ):
                raise

            _LOGGER.warning(
                "SPH: Kalender-Abruf sieht nach abgelaufener Session aus; erneuere Anmeldung und versuche es erneut"
            )
            self._force_relogin()
            return super().get_calendar(start, end, school_year)

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
