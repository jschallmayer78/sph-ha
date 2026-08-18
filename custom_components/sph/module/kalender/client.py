from __future__ import annotations

import csv
from datetime import datetime
import io
import logging
import re
from html import unescape

from ...api.client import SphAuthClient
from ...const import SPH_BASE

_LOGGER = logging.getLogger(__name__)


class SphCalendarClient:
    """Schulportal Hessen calendar exports and parsers."""

    def __init__(self, auth: SphAuthClient):
        self.auth = auth

    @property
    def session(self):
        return self.auth.session

    def get_calendar(self, start: datetime, end: datetime, school_year: int):
        """Fetch one school year's calendar and filter it to the requested range."""
        for attempt in range(2):
            try:
                self.auth.login(force=attempt == 1)
                try:
                    events = self._get_calendar_csv(school_year)
                    if events:
                        return [e for e in events if self._event_overlaps(e, start, end)]
                    _LOGGER.warning("SPH: CSV-Kalender enthält keine Termine; versuche iCal-Fallback")
                except Exception as err:
                    _LOGGER.warning("SPH: CSV-Kalender konnte nicht verarbeitet werden: %s; versuche iCal-Fallback", err)

                events = self._get_calendar_ical(school_year)
                return [e for e in events if self._event_overlaps(e, start, end)]
            except RuntimeError:
                if attempt == 0:
                    _LOGGER.warning("SPH: Kalender-Abruf fehlgeschlagen; erneuere Anmeldung und versuche es erneut")
                    continue
                raise

    def _get_calendar_csv(self, school_year: int):
        response = self.session.get(
            f"{SPH_BASE}/kalender.php",
            params={"a": "export", "export": "csv", "year": school_year},
            allow_redirects=True,
            timeout=30,
        )
        _LOGGER.debug(
            "SPH: CSV-Export für Schuljahr %s/%s HTTP %s, URL=%s, Content-Type=%s, Bytes=%s",
            school_year,
            school_year + 1,
            response.status_code,
            response.url.split("?", 1)[0],
            response.headers.get("Content-Type"),
            len(response.content),
        )
        response.raise_for_status()
        text = response.content.decode("utf-8-sig", errors="replace")
        if not text.strip():
            raise RuntimeError("CSV-Antwort ist leer.")
        if "<!doctype" in text[:500].lower() or "<html" in text[:500].lower():
            text = self.auth._decrypt_tags(text)
        if not text.strip() or "Von_Datum" not in text:
            raise RuntimeError("CSV-Antwort enthält keine erwarteten Kalenderdaten.")
        return self._parse_csv(text)

    @classmethod
    def _parse_csv(cls, text):
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=";,\t")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if not reader.fieldnames:
            return []
        field_map = {
            re.sub(r"^\ufeff", "", (name or "")).strip().lower(): name
            for name in reader.fieldnames
        }

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
            events.append(
                {
                    "start": start,
                    "end": end,
                    "all_day": not bool(time_start),
                    "summary": summary,
                    "description": value(row, "Beschreibung", "Description"),
                    "location": value(row, "Ort", "Location"),
                    "art": value(row, "Art", "art", "Kategorie", "Category", "Typ", "Type"),
                    "verantwortlich": value(row, "Verantwortlich", "verantwortlich", "Verantwortlicher", "Responsible"),
                    "uid": value(row, "UID", "Uid"),
                }
            )
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
        response = self.session.get(
            f"{SPH_BASE}/kalender.php",
            params={"a": "export", "export": "ical", "year": school_year},
            allow_redirects=True,
            timeout=30,
        )
        response.raise_for_status()
        text = response.content.decode("utf-8-sig", errors="replace")
        if "BEGIN:VCALENDAR" not in text:
            text = self.auth._decrypt_tags(response.text)
        if "BEGIN:VCALENDAR" not in text:
            raise RuntimeError(
                f"Der persönliche Schulkalender für das Schuljahr {school_year}/{school_year + 1} konnte nicht als iCal abgerufen werden."
            )
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
        return unescape(
            value.replace("\\n", "\n")
            .replace("\\,", ",")
            .replace("\\;", ";")
            .replace("\\\\", "\\")
        ).strip()

    @staticmethod
    def _parse_ical_datetime(value):
        value = value.strip()
        if len(value) == 8 and value.isdigit():
            return datetime.strptime(value, "%Y%m%d").isoformat()
        if value.endswith("Z"):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").isoformat() + "+00:00"
        return datetime.strptime(value[:15], "%Y%m%dT%H%M%S").isoformat()
