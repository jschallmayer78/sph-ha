from __future__ import annotations

from html import unescape
import logging
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from ..api.client import SphAuthClient
from ..const import SPH_BASE

_LOGGER = logging.getLogger(__name__)


class SphTimetableClient:
    """Schulportal Hessen timetable access and HTML parsing."""

    def __init__(self, auth: SphAuthClient):
        self.auth = auth

    @property
    def session(self):
        return self.auth.session

    def get_timetable(self):
        """Fetch the timetable and recover once from an expired session."""
        for attempt in range(2):
            try:
                self.auth.login(force=attempt == 1)
                response = self.session.get(
                    f"{SPH_BASE}/stundenplan.php",
                    allow_redirects=False,
                    timeout=20,
                )
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
                soup = BeautifulSoup(self.auth._decrypt_tags(response.text), "html.parser")
                all_table = soup.select_one("#all tbody")
                own_table = soup.select_one("#own tbody")
                if all_table is None and own_table is None:
                    raise RuntimeError(
                        "Kein Stundenplan für dieses Konto verfügbar. Die SPH-Anmeldung war erfolgreich, "
                        "aber stundenplan.php enthält weder #all noch #own."
                    )
                badge = soup.select_one("#aktuelleWoche")
                return {
                    "week_badge": badge.get_text(" ", strip=True) if badge else None,
                    "all": self._parse(all_table) if all_table else [],
                    "own": self._parse(own_table) if own_table else [],
                    "klasse": self._extract_student_class(soup, response.url),
                }
            except RuntimeError:
                if attempt == 0:
                    _LOGGER.warning("SPH: Stundenplan-Abruf fehlgeschlagen; erneuere Anmeldung und versuche es erneut")
                    continue
                raise

    @staticmethod
    def _extract_student_class(soup: BeautifulSoup, page_url: str = "") -> str:
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

        heading = soup.find("h1")
        if heading:
            text = heading.get_text(" ", strip=True)
            if text and len(text) <= 20 and text[0].isdigit():
                return text
        return ""

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
                    bold = lesson.select_one("b")
                    small = lesson.select_one("small")
                    badge = lesson.select_one(".badge")
                    subject = bold.get_text(" ", strip=True) if bold else None
                    teacher = small.get_text(" ", strip=True) if small else None
                    badge_value = badge.get_text(" ", strip=True) if badge else None
                    room = unescape(
                        " ".join(
                            node.strip()
                            for node in lesson.find_all(string=True, recursive=False)
                            if node.strip()
                        )
                    )
                    duration = int(lesson.parent.get("rowspan", "1") or "1")
                    si = y if offset else y - 1
                    ei = si + duration - 1
                    start = slots[si][0] if 0 <= si < len(slots) else "00:00"
                    end = slots[ei][1] if 0 <= ei < len(slots) else "00:00"
                    result[day].append(
                        {
                            "day": day,
                            "subject": subject,
                            "teacher": teacher,
                            "room": room,
                            "badge": badge_value,
                            "duration": duration,
                            "start": start,
                            "end": end,
                            "index": y,
                        }
                    )
        return result
