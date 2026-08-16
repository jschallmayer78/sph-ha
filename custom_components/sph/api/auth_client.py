from __future__ import annotations

import logging
import requests

from ..const import SPH_CONNECT, SPH_LOGIN
from .client import SphClient

_LOGGER = logging.getLogger(__name__)


class SphAuthClient(SphClient):
    """SPH client using the login flow used by the previously working integration.

    Schulportal Hessen creates the authentication redirect in a bootstrap
    session.  The resulting one-time URL is then consumed by the main session.
    This is intentionally kept separate from the generic SphClient so the
    shared API can be changed without changing the proven authentication flow.
    """

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
