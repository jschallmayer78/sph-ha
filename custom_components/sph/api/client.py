from __future__ import annotations

import base64
import csv
import hashlib
import io
import logging
import random
import re
from datetime import datetime
from html import unescape

import requests
from bs4 import BeautifulSoup

from ..const import SPH_BASE, SPH_CONNECT, SPH_LOGIN

_LOGGER = logging.getLogger(__name__)


class SphClient:
    """Shared Schulportal Hessen client used by all SPH modules."""

    def __init__(self, school_id, username, password):
        self.school_id, self.username, self.password = str(school_id), username, password
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Home Assistant Schulportal Hessen/0.3.1"
        self.key = None
        self._logged_in = False

    @staticmethod
    def _crypto():
        from Crypto.Cipher import AES, PKCS1_v1_5
        from Crypto.PublicKey import RSA
        from Crypto.Random import get_random_bytes
        from Crypto.Util.Padding import unpad
        return AES, PKCS1_v1_5, RSA, get_random_bytes, unpad

    @staticmethod
    def _kdf(salt, key):
        out, previous = b"", b""
        while len(out) < 48:
            previous = hashlib.md5(previous + key + salt).digest()
            out += previous
        return out[:48]

    @classmethod
    def _decrypt(cls, payload, key):
        AES, _, _, _, unpad = cls._crypto()
        if len(payload) < 16 or payload[:8] != b"Salted__":
            return None
        k = cls._kdf(payload[8:16], key)
        return unpad(AES.new(k[:32], AES.MODE_CBC, k[32:48]).decrypt(payload[16:]), AES.block_size)

    def _decrypt_tags(self, html):
        if not self.key:
            return html

        def repl(match):
            try:
                data = self._decrypt(base64.b64decode(match.group(1)), self.key)
                return data.decode("utf-8") if data else ""
            except Exception:
                _LOGGER.debug("SPH: verschlüsselten Seitenbereich konnte nicht entschlüsseln", exc_info=True)
                return ""

        return re.sub(r"<encoded>(.*?)</encoded>", repl, html, flags=re.S)

    def _get_login_url(self):
        _LOGGER.debug("SPH: starte Login-Handshake für Schulnummer %s", self.school_id)
        response = self.session.post(
            f"{SPH_LOGIN}?i={self.school_id}",
            data={"user": f"{self.school_id}.{self.username}", "user2": self.username, "password": self.password},
            allow_redirects=False,
            timeout=15,
        )
        _LOGGER.debug("SPH: Login-Request HTTP %s", response.status_code)
        if response.status_code == 503:
            raise RuntimeError("Schulportal Hessen ist nicht verfügbar.")
        if response.status_code not in (200, 301, 302, 303, 307, 308):
            raise RuntimeError(f"SPH-Anmeldung fehlgeschlagen (HTTP {response.status_code}). Zugangsdaten prüfen.")
        connect = self.session.head(SPH_CONNECT, allow_redirects=False, timeout=15)
        _LOGGER.debug("SPH: connect.php HTTP %s, Location vorhanden=%s", connect.status_code, bool(connect.headers.get("Location")))
        if connect.status_code in (401, 403):
            raise RuntimeError("SPH-Anmeldung fehlgeschlagen. Zugangsdaten prüfen.")
        login_url = connect.headers.get("Location")
        if not login_url:
            raise RuntimeError("SPH-Anmeldung konnte nicht abgeschlossen werden.")
        return login_url

    def login(self, force: bool = False):
        """Authenticate once and reuse the shared session for all modules.

        Timetable and calendar coordinators deliberately share one SphClient.
        Avoiding a second login on every module refresh both reduces load on SPH
        and prevents two independent authentication sessions from expiring at
        different times.
        """
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

    def _handshake(self):
        _, PKCS1_v1_5, RSA, get_random_bytes, _ = self._crypto()
        response = self.session.post(f"{SPH_BASE}/ajax.php", params={"f": "rsaPublicKey"}, timeout=15)
        response.raise_for_status()
        public_key = RSA.import_key(response.json()["publickey"])
        self.key = get_random_bytes(46)
        encrypted = PKCS1_v1_5.new(public_key).encrypt(self.key)
        response = self.session.post(f"{SPH_BASE}/ajax.php", params={"f": "rsaHandshake", "s": random.randrange(2000)}, data={"key": base64.b64encode(encrypted).decode()}, timeout=15)
        response.raise_for_status()
        challenge = base64.b64decode(response.json()["challenge"])
        if self._decrypt(challenge, self.key) != self.key:
            self.key = None
            raise RuntimeError("SPH RSA/AES-Handshake fehlgeschlagen.")

    def get_timetable(self):
        self.login()
        response = self.session.get(f"{SPH_BASE}/stundenplan.php", allow_redirects=False, timeout=20)
        if response.status_code in (301, 302, 303, 307, 308):
            # The session may have expired since the last refresh. Re-authenticate
            # once and retry instead of exposing the login page as timetable data.
            self.login(force=True)
            response = self.session.get(f"{SPH_BASE}/stundenplan.php", allow_redirects=False, timeout=20)
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    raise RuntimeError("Keine SPH-Weiterleitung für Stundenplan.")
                response = self.session.get(location if location.startswith("http") else f"{SPH_BASE}/{location.lstrip('/')}", allow_redirects=False, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(self._decrypt_tags(response.text), "html.parser")
        badge = soup.select_one("#aktuelleWoche")
        all_table = soup.select_one("#all tbody")
        own_table = soup.select_one("#own tbody")
        if all_table is None and own_table is None:
            raise RuntimeError("Kein Stundenplan für dieses Konto verfügbar. Die SPH-Anmeldung war erfolgreich, aber stundenplan.php enthält weder #all noch #own.")
        return {"week_badge": badge.get_text(" ", strip=True) if badge else None, "all": self._parse(all_table) if all_table else [], "own": self._parse(own_table) if own_table else []}

    @staticmethod
    def _school_year_start_year(value: datetime) -> int:
        return value.year if value.month >= 8 else value.year - 1

    def _calendar_export_url(self, school_year: int, export_type: str) -> str:
        _LOGGER.debug("SPH: verwende Kalenderexport %s für Schuljahr %s/%s", export_type, school_year, school_year + 1)
        return f"{SPH_BASE}/kalender.php"

    def get_calendar(self, start: datetime, end: datetime, school_year: int | None = None):
        """Fetch one explicit school-year export and filter it to the requested range."""
        self.login()
        if school_year is None:
            school_year = self._school_year_start_year(start)
        _LOGGER.debug("SPH: Kalenderabruf explizit für Schuljahr %s/%s", school_year, school_year + 1)

        try:
            events = self._get_calendar_csv(school_year)
            if events:
                _LOGGER.debug("SPH: CSV-Kalender für Schuljahr %s/%s erfolgreich geparst: %s Termine", school_year, school_year + 1, len(events))
                return [e for e in events if self._event_overlaps(e, start, end)]
            _LOGGER.warning("SPH: CSV-Kalender für Schuljahr %s/%s enthält keine Termine; versuche iCal-Fallback", school_year, school_year + 1)
        except Exception as err:
            _LOGGER.warning("SPH: CSV-Kalender konnte nicht verarbeitet werden: %s; versuche iCal-Fallback", err)

        events = self._get_calendar_ical(school_year)
        return [e for e in events if self._event_overlaps(e, start, end)]

    def _get_calendar_csv(self, school_year: int):
        url = self._calendar_export_url(school_year, "csv")
        response = self.session.get(url, params={"a": "export", "export": "csv", "year": school_year}, allow_redirects=True, timeout=30)
        if response.status_code in (401, 403):
            self.login(force=True)
            response = self.session.get(url, params={"a": "export", "export": "csv", "year": school_year}, allow_redirects=True, timeout=30)
        _LOGGER.debug("SPH: CSV-Export für Schuljahr %s/%s HTTP %s, URL=%s, Content-Type=%s, Bytes=%s", school_year, school_year + 1, response.status_code, response.url.split("?", 1)[0], response.headers.get("Content-Type"), len(response.content))
        response.raise_for_status()
        text = response.content.decode("utf-8-sig", errors="replace")
        if "<!doctype" in text[:500].lower() or "<html" in text[:500].lower():
            text = self._decrypt_tags(text)
        if not text.strip() or "Von_Datum" not in text:
            raise RuntimeError("CSV-Antwort enthält keine erwarteten Kalenderdaten.")
        return self._parse_csv(text)

    @classmethod
    def _parse_csv(cls, text):
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if not reader.fieldnames:
            return []
        field_map = {re.sub(r"^\ufeff", "", (name or "")).strip().lower(): name for name in reader.fieldnames}

        def value(row, *names):
            for name in names:
                original = field_map.get(name.lower())
                if original is not None:
                    return (row.get(original) or "").strip()
            return ""

        events = []
        for row in reader:
            date_start = value(row, "Von_Datum", "Von Datum", "Startdatum")
            date_end = value(row, "Bis_Datum", "Bis Datum", "Enddatum") or date_start
            time_start = value(row, "Von_Uhrzeit", "Von Uhrzeit", "Startzeit")
            time_end = value(row, "Bis_Uhrzeit", "Bis Uhrzeit", "Endzeit")
            summary = value(row, "Titel", "Title")
            if not date_start or not summary:
                continue
            start = cls._parse_csv_datetime(date_start, time_start)
            end = cls._parse_csv_datetime(date_end, time_end, end_of_day=not bool(time_end))
            if not start or not end:
                continue
            events.append({"start": start, "end": end, "all_day": not bool(time_start), "summary": summary, "description": value(row, "Beschreibung", "Description"), "location": value(row, "Ort", "Location"), "art": value(row, "Art", "art", "Kategorie", "Category", "Typ", "Type"), "verantwortlich": value(row, "Verantwortlich", "verantwortlich", "Verantwortlicher", "Responsible"), "uid": value(row, "UID", "Uid")})
        return events

    @staticmethod
    def _parse_csv_datetime(date_value, time_value="", end_of_day=False):
        date_value = date_value.strip()
        time_value = time_value.strip()
        parsed_date = None
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                parsed_date = datetime.strptime(date_value, fmt)
                break
            except ValueError:
                continue
        if parsed_date is None:
            return None
        if time_value:
            for fmt in ("%H:%M", "%H:%M:%S"):
                try:
                    return datetime.combine(parsed_date.date(), datetime.strptime(time_value, fmt).time()).isoformat()
                except ValueError:
                    continue
        if end_of_day:
            return datetime.combine(parsed_date.date(), datetime.max.time()).isoformat()
        return parsed_date.isoformat()

    def _get_calendar_ical(self, school_year: int):
        url = self._calendar_export_url(school_year, "ical")
        response = self.session.get(url, params={"a": "export", "export": "ical", "year": school_year}, allow_redirects=True, timeout=30)
        _LOGGER.debug("SPH: iCal-Export für Schuljahr %s/%s HTTP %s, URL=%s, Content-Type=%s, Bytes=%s", school_year, school_year + 1, response.status_code, response.url.split("?", 1)[0], response.headers.get("Content-Type"), len(response.content))
        response.raise_for_status()
        text = response.content.decode("utf-8-sig", errors="replace")
        if "BEGIN:VCALENDAR" not in text:
            text = self._decrypt_tags(response.text)
        if "BEGIN:VCALENDAR" not in text:
            raise RuntimeError(f"Der persönliche Schulkalender für das Schuljahr {school_year}/{school_year + 1} konnte nicht als iCal abgerufen werden.")
        return self._parse_ical(text)

    @staticmethod
    def _event_overlaps(event, start, end):
        event_start = datetime.fromisoformat(event["start"])
        event_end = datetime.fromisoformat(event["end"])
        return event_end >= start and event_start <= end

    @staticmethod
    def _unfold_ical(text):
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        result = []
        for line in lines:
            if line.startswith((" ", "\t")) and result:
                result[-1] += line[1:]
            else:
                result.append(line)
        return result

    @classmethod
    def _parse_ical(cls, text):
        events, current = [], None
        for line in cls._unfold_ical(text):
            if line == "BEGIN:VEVENT":
                current = {}
                continue
            if line == "END:VEVENT":
                if current and current.get("start") and current.get("summary"):
                    events.append(current)
                current = None
                continue
            if current is None or ":" not in line:
                continue
            key, value = line.split(":", 1)
            name = key.split(";", 1)[0].upper()
            if name == "DTSTART":
                current["start"] = cls._parse_ical_datetime(value)
                current["all_day"] = len(value) == 8 and value.isdigit()
            elif name == "DTEND":
                current["end"] = cls._parse_ical_datetime(value)
            elif name == "SUMMARY":
                current["summary"] = cls._ical_unescape(value)
            elif name == "DESCRIPTION":
                current["description"] = cls._ical_unescape(value)
            elif name == "LOCATION":
                current["location"] = cls._ical_unescape(value)
            elif name == "UID":
                current["uid"] = value
            elif name in ("CATEGORIES", "CATEGORY"):
                current["art"] = cls._ical_unescape(value)
            elif name in ("ORGANIZER", "X-RESPONSIBLE", "X-VERANTWORTLICH"):
                current["verantwortlich"] = cls._ical_unescape(value)
        for event in events:
            event.setdefault("end", event["start"])
            event.setdefault("description", "")
            event.setdefault("location", "")
            event.setdefault("art", "")
            event.setdefault("verantwortlich", "")
            event.setdefault("uid", "")
        return events

    @staticmethod
    def _ical_unescape(value):
        return unescape(value.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\"))

    @staticmethod
    def _parse_ical_datetime(value):
        value = value.strip()
        for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M", "%Y%m%d"):
            try:
                return datetime.strptime(value[:15] if fmt != "%Y%m%d" else value[:8], fmt).isoformat()
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse(table):
        if table is None:
            return []
        result = []
        for row in table.select("tr"):
            cells = row.select("td")
            if not cells:
                continue
            result.append({"subject": cells[0].get_text(" ", strip=True), "teacher": cells[1].get_text(" ", strip=True) if len(cells) > 1 else "", "room": cells[2].get_text(" ", strip=True) if len(cells) > 2 else "", "badge": cells[3].get_text(" ", strip=True) if len(cells) > 3 else None})
        return result
