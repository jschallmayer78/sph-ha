from __future__ import annotations

import base64
import hashlib
import logging
import random
import re
from datetime import datetime
from html import unescape
from urllib.parse import urljoin, urlparse, parse_qs

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
        _LOGGER.debug(
            "SPH: starte Login-Handshake für Schulnummer %s und Benutzer %s",
            self.school_id,
            self.username,
        )
        response = self.session.post(
            f"{SPH_LOGIN}?i={self.school_id}",
            data={
                "user": f"{self.school_id}.{self.username}",
                "user2": self.username,
                "password": self.password,
            },
            allow_redirects=False,
            timeout=15,
        )
        _LOGGER.debug(
            "SPH: Login-Request HTTP %s, Location vorhanden=%s, Cookies=%s",
            response.status_code,
            bool(response.headers.get("Location")),
            list(self.session.cookies.keys()),
        )
        if response.status_code == 503:
            raise RuntimeError("Schulportal Hessen ist nicht verfügbar.")
        if response.status_code not in (200, 301, 302, 303, 307, 308):
            raise RuntimeError(
                f"SPH-Anmeldung fehlgeschlagen (HTTP {response.status_code}). Zugangsdaten prüfen."
            )
        connect = self.session.head(SPH_CONNECT, allow_redirects=False, timeout=15)
        _LOGGER.debug(
            "SPH: connect HTTP %s, Location vorhanden=%s, Cookies=%s",
            connect.status_code,
            bool(connect.headers.get("Location")),
            list(self.session.cookies.keys()),
        )
        if connect.status_code in (401, 403):
            raise RuntimeError("SPH-Anmeldung fehlgeschlagen. Zugangsdaten prüfen.")
        login_url = connect.headers.get("Location")
        if not login_url:
            raise RuntimeError("SPH-Anmeldung konnte nicht abgeschlossen werden.")
        return login_url

    def login(self):
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

    def _handshake(self):
        _, PKCS1_v1_5, RSA, get_random_bytes, _ = self._crypto()
        response = self.session.post(f"{SPH_BASE}/ajax.php", params={"f": "rsaPublicKey"}, timeout=15)
        response.raise_for_status()
        public_key = RSA.import_key(response.json()["publickey"])
        self.key = get_random_bytes(46)
        encrypted = PKCS1_v1_5.new(public_key).encrypt(self.key)
        response = self.session.post(
            f"{SPH_BASE}/ajax.php",
            params={"f": "rsaHandshake", "s": random.randrange(2000)},
            data={"key": base64.b64encode(encrypted).decode()},
            timeout=15,
        )
        response.raise_for_status()
        challenge = base64.b64decode(response.json()["challenge"])
        if self._decrypt(challenge, self.key) != self.key:
            self.key = None
            raise RuntimeError("SPH RSA/AES-Handshake fehlgeschlagen.")

    def get_timetable(self):
        self.login()
        response = self.session.get(f"{SPH_BASE}/stundenplan.php", allow_redirects=False, timeout=20)
        if response.status_code == 302:
            location = response.headers.get("Location")
            if not location:
                raise RuntimeError("Keine SPH-Weiterleitung für Stundenplan.")
            response = self.session.get(
                location if location.startswith("http") else f"{SPH_BASE}/{location.lstrip('/')}",
                allow_redirects=False,
                timeout=20,
            )
        response.raise_for_status()
        html = self._decrypt_tags(response.text)
        soup = BeautifulSoup(html, "html.parser")
        badge = soup.select_one("#aktuelleWoche")
        all_table = soup.select_one("#all tbody")
        own_table = soup.select_one("#own tbody")
        if all_table is None and own_table is None:
            raise RuntimeError("Kein Stundenplan für dieses Konto verfügbar. Die SPH-Anmeldung war erfolgreich, aber stundenplan.php enthält weder #all noch #own.")
        return {"week_badge": badge.get_text(" ", strip=True) if badge else None, "all": self._parse(all_table) if all_table else [], "own": self._parse(own_table) if own_table else []}

    def _calendar_export_url(self):
        """Find the personal iCal export URL from the logged-in calendar page.

        SPH normally exposes a tokenized URL such as
        kalender.php?i=<school>&a=ical&t=<token>.  Calling a=ical without
        the token can return the normal HTML calendar instead of ICS.
        """
        page = self.session.get(
            f"{SPH_BASE}/kalender.php",
            params={"i": self.school_id},
            allow_redirects=True,
            timeout=20,
        )
        _LOGGER.debug(
            "SPH: Kalenderseite HTTP %s, URL=%s, Content-Type=%s",
            page.status_code,
            page.url,
            page.headers.get("Content-Type"),
        )
        page.raise_for_status()
        html = self._decrypt_tags(page.text)
        soup = BeautifulSoup(html, "html.parser")

        candidates = []
        for anchor in soup.find_all("a", href=True):
            href = unescape(anchor["href"])
            parsed = urlparse(href)
            query = parse_qs(parsed.query)
            if query.get("a", [""])[0].lower() in {"ical", "ics"}:
                candidates.append(urljoin(page.url, href))

        # Some SPH versions render the export link in JavaScript instead of
        # as a normal anchor. Look for the same tokenized URL in the HTML.
        for match in re.finditer(r"(?:kalender\.php[^\"'\s<>]+)", html, re.I):
            href = unescape(match.group(0))
            parsed = urlparse(href if href.startswith("http") else urljoin(SPH_BASE + "/", href))
            query = parse_qs(parsed.query)
            if query.get("a", [""])[0].lower() in {"ical", "ics"}:
                candidates.append(parsed.geturl())

        # Prefer a tokenized personal export. Do not log the token itself.
        candidates = list(dict.fromkeys(candidates))
        candidates.sort(key=lambda url: ("t=" not in url, len(url)))
        if candidates:
            chosen = candidates[0]
            _LOGGER.debug(
                "SPH: persönlicher iCal-Export gefunden (tokenisiert=%s)",
                "t=" in chosen,
            )
            return chosen

        _LOGGER.debug("SPH: Kein iCal-Link auf kalender.php gefunden; verwende Fallback ohne Token")
        return f"{SPH_BASE}/kalender.php?i={self.school_id}&a=ical"

    def get_calendar(self, start: datetime, end: datetime):
        self.login()
        url = self._calendar_export_url()
        response = self.session.get(url, allow_redirects=True, timeout=30)
        _LOGGER.debug(
            "SPH: iCal-Export HTTP %s, URL=%s, Content-Type=%s, Bytes=%s",
            response.status_code,
            response.url.split("?", 1)[0],
            response.headers.get("Content-Type"),
            len(response.content),
        )
        response.raise_for_status()
        text = response.content.decode("utf-8-sig", errors="replace")
        if "BEGIN:VCALENDAR" not in text:
            text = self._decrypt_tags(response.text)
        if "BEGIN:VCALENDAR" not in text:
            snippet = re.sub(r"\s+", " ", text[:300])
            _LOGGER.debug("SPH: iCal-Antwort enthält kein VCALENDAR: %s", snippet)
            raise RuntimeError("Der persönliche Schulkalender konnte nicht als iCal abgerufen werden.")
        events = self._parse_ical(text)
        return [e for e in events if self._event_overlaps(e, start, end)]

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
            elif name == "DTEND": current["end"] = cls._parse_ical_datetime(value)
            elif name == "SUMMARY": current["summary"] = cls._ical_unescape(value)
            elif name == "DESCRIPTION": current["description"] = cls._ical_unescape(value)
            elif name == "LOCATION": current["location"] = cls._ical_unescape(value)
            elif name == "UID": current["uid"] = value
        for event in events:
            event.setdefault("end", event["start"])
            event.setdefault("description", "")
            event.setdefault("location", "")
            event.setdefault("uid", "")
        return events

    @staticmethod
    def _ical_unescape(value):
        return unescape(value.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")).strip()

    @staticmethod
    def _parse_ical_datetime(value):
        value = value.strip()
        if len(value) == 8 and value.isdigit():
            return datetime.strptime(value, "%Y%m%d").isoformat()
        if value.endswith("Z"):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").isoformat() + "+00:00"
        return datetime.strptime(value[:15], "%Y%m%dT%H%M%S").isoformat()

    @staticmethod
    def _parse(tbody):
        rows = tbody.find_all("tr", recursive=False)
        if not rows:
            return []
        day_count = max(0, len(rows[0].find_all(["td", "th"], recursive=False)) - 1)
        result = [[] for _ in range(day_count)]
        occupied = [[False] * day_count for _ in range(len(rows) + 32)]
        slots = []
        for row in rows:
            element = row.select_one(".VonBis")
            if element:
                parts = [x.strip() for x in element.get_text(" ", strip=True).split(" - ")]
                if len(parts) == 2:
                    slots.append((parts[0], parts[1]))
        first = rows[0].find_all(["td", "th"], recursive=False)
        offset = bool(first and first[0].get_text(strip=True))
        for y, row in enumerate(rows):
            if y == 0:
                continue
            for x, cell in enumerate(row.find_all(["td", "th"], recursive=False)):
                if x == 0:
                    continue
                span = int(cell.get("rowspan", "1") or "1")
                day = x - 1
                while day < day_count and occupied[y][day]:
                    day += 1
                if day >= day_count:
                    continue
                for i in range(span):
                    if y + i < len(occupied):
                        occupied[y + i][day] = True
                for lesson in cell.select(".stunde"):
                    b, sm, bd = lesson.select_one("b"), lesson.select_one("small"), lesson.select_one(".badge")
                    subject = b.get_text(" ", strip=True) if b else None
                    teacher = sm.get_text(" ", strip=True) if sm else None
                    badge = bd.get_text(" ", strip=True) if bd else None
                    room = unescape(" ".join(n.strip() for n in lesson.find_all(string=True, recursive=False) if n.strip()))
                    duration = int(lesson.parent.get("rowspan", "1") or "1")
                    si, ei = (y if offset else y - 1), (y if offset else y - 1) + duration - 1
                    start = slots[si][0] if 0 <= si < len(slots) else "00:00"
                    end = slots[ei][1] if 0 <= ei < len(slots) else "00:00"
                    result[day].append({"day": day, "subject": subject, "teacher": teacher, "room": room, "badge": badge, "duration": duration, "start": start, "end": end, "index": y})
        return result
