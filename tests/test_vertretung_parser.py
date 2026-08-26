"""Offline tests for the Vertretungsplan HTML parser.

Run with:  python3 tests/test_vertretung_parser.py
Only needs beautifulsoup4 — no Home Assistant installation required.
"""

from __future__ import annotations

import pathlib
import sys

from bs4 import BeautifulSoup

CLIENT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "custom_components" / "sph" / "module" / "vertretung" / "client.py"
)


def _load_client():
    """Load the parser without pulling in Home Assistant.

    client.py only needs SphAuthClient for the live requests, not for parsing,
    so the two package-relative imports are replaced by stubs here.
    """
    source = CLIENT_PATH.read_text(encoding="utf-8")
    source = source.replace("from ...api.client import SphAuthClient", "SphAuthClient = object")
    source = source.replace("from ...const import SPH_BASE", 'SPH_BASE = "https://start.schulportal.hessen.de"')
    namespace: dict = {"__name__": "sph_vertretung_client"}
    exec(compile(source, str(CLIENT_PATH), "exec"), namespace)
    return namespace["SphVertretungClient"]


SphVertretungClient = _load_client()

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "vertretungsplan.html"


def parse():
    soup = BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "html.parser")
    return SphVertretungClient._parse_page(soup)


def main() -> int:
    data = parse()
    failures = []

    def check(label, actual, expected):
        if actual != expected:
            failures.append(f"  {label}: erwartet {expected!r}, war {actual!r}")

    days = data["tage"]
    check("Anzahl Tage", len(days), 3)
    check("Sortierung", [d["datum"] for d in days],
          ["2026-08-26", "2026-08-27", "2026-08-28"])
    check("Letzte Aktualisierung", data["aktualisiert"], "2026-08-26T07:12:44")
    check("wird_aktualisiert", data["wird_aktualisiert"], False)

    heute = days[0]
    check("Wochentag", heute["wochentag"], "Mittwoch")
    check("Relativ", heute["relativ"], "heute")
    check("Woche", heute["woche"], "A-Woche")
    check("Einträge heute", heute["anzahl"], 3)
    check("Entfälle heute", heute["entfaelle"], 2)
    check("Hinweise heute", heute["hinweise"], [
        "Der Schulhof ist wegen Bauarbeiten gesperrt.",
        "Die Mensa öffnet erst ab 12:00 Uhr.",
    ])

    first = heute["eintraege"][0]
    check("Stundenbereich 1-2", first["stunden"], [1, 2])
    check("von_stunde", first["von_stunde"], 1)
    check("bis_stunde", first["bis_stunde"], 2)
    check("Lehrer", first["lehrer"], "MUE")
    check("Art", first["art"], "Entfall")
    check("Fach", first["fach"], "M")
    check("Hinweis", first["hinweis"], "Aufgaben im Lernraum")
    check("Entfall erkannt", first["entfall"], True)

    second = heute["eintraege"][1]
    check("Einzelstunde", second["stunden"], [4])
    check("Vertreter", second["vertreter"], "SCH")
    check("Raum", second["raum"], "B204")
    check("Kein Entfall", second["entfall"], False)
    check("Abkürzung Vertr aufgelöst", second["art_lang"], "Vertretung")
    check("Rohwert der Art bleibt erhalten", second["art"], "Vertr")

    third = heute["eintraege"][2]
    check("Abkürzung Entf. erkannt", third["art_lang"], "Entfall")
    check("Abgekürzter Entfall zählt als Entfall", third["entfall"], True)
    check("Stundenbereich 7-8", third["stunden"], [7, 8])

    morgen = days[1]
    check("Fach_alt gelesen", morgen["eintraege"][0]["fach_alt"], "D")
    check("Freisetzung ist Entfall", morgen["eintraege"][0]["entfall"], True)
    check("Langform bleibt Langform", morgen["eintraege"][0]["art_lang"], "Freisetzung")

    arten = SphVertretungClient._art_long
    check("Betr", arten("Betr"), "Betreuung")
    check("taus klein", arten("taus"), "Tausch")
    check("Raum", arten("Raum"), "Raumänderung")
    check("Unbekannte Art bleibt unverändert", arten("Wandertag"), "Wandertag")
    check("Leere Art", arten(None), "")

    check("Leerer Tag ohne Einträge", days[2]["anzahl"], 0)

    # helpers
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from datetime import date

    def day_for(target):
        return next((d for d in days if d["datum"] == target.isoformat()), None)

    lesson_one_cancelled = any(
        e["entfall"] and 1 in e["stunden"]
        for e in day_for(date(2026, 8, 27))["eintraege"]
    )
    check("Erste Stunde entfällt morgen", lesson_one_cancelled, True)

    if failures:
        print("FEHLGESCHLAGEN:")
        print("\n".join(failures))
        return 1
    print(f"OK — {len(days)} Tage, "
          f"{sum(d['anzahl'] for d in days)} Einträge, "
          f"{sum(d['entfaelle'] for d in days)} Entfälle korrekt geparst.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
