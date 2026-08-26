#!/usr/bin/env python3
"""Live-Check für den Vertretungsplan-Parser.

Ruft den Vertretungsplan mit echten Zugangsdaten ab und zeigt an, was der
Parser daraus macht. Damit lässt sich prüfen, ob die eigene Schule die Tabelle
so ausliefert, wie die Integration sie erwartet — ohne Home Assistant.

    pip install requests pycryptodome beautifulsoup4
    python3 tools/sph_vertretung_check.py

Die Zugangsdaten werden abgefragt und nirgends gespeichert. Mit --dump-html
wird die rohe (entschlüsselte) Seite zusätzlich in eine Datei geschrieben —
nützlich, wenn etwas nicht erkannt wird und ein Fixture gebaut werden soll.
"""

from __future__ import annotations

import argparse
import getpass
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPH = ROOT / "custom_components" / "sph"


def _load(path: pathlib.Path, name: str, replacements: dict[str, str] | None = None) -> dict:
    source = path.read_text(encoding="utf-8")
    for old, new in (replacements or {}).items():
        source = source.replace(old, new)
    namespace: dict = {"__name__": name}
    exec(compile(source, str(path), "exec"), namespace)
    return namespace


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--school", help="Schulnummer")
    parser.add_argument("--user", help="SPH-Benutzername")
    parser.add_argument("--dump-html", metavar="DATEI", help="Rohe Seite zusätzlich speichern")
    args = parser.parse_args()

    school = args.school or input("Schulnummer: ").strip()
    username = args.user or input("Benutzername: ").strip()
    password = getpass.getpass("Passwort: ")

    api = _load(SPH / "api" / "client.py", "sph_api", {
        "from ..const import SPH_BASE, SPH_CONNECT, SPH_LOGIN":
            'SPH_BASE = "https://start.schulportal.hessen.de"\n'
            'SPH_LOGIN = "https://login.schulportal.hessen.de/"\n'
            'SPH_CONNECT = "https://connect.schulportal.hessen.de/"',
    })
    vertretung = _load(SPH / "module" / "vertretung" / "client.py", "sph_vertretung", {
        "from ...api.client import SphAuthClient": "SphAuthClient = object",
        "from ...const import SPH_BASE": 'SPH_BASE = "https://start.schulportal.hessen.de"',
    })

    auth = api["SphAuthClient"](school, username, password)
    client = vertretung["SphVertretungClient"](auth)

    try:
        auth.login()
    except Exception as err:  # noqa: BLE001 — this is a diagnostic tool
        print(f"Anmeldung fehlgeschlagen: {err}", file=sys.stderr)
        return 1
    print("Anmeldung erfolgreich.\n")

    if args.dump_html:
        response = auth.get("https://start.schulportal.hessen.de/vertretungsplan.php", timeout=20)
        pathlib.Path(args.dump_html).write_text(
            auth._decrypt_tags(response.text), encoding="utf-8"
        )
        print(f"Rohe Seite geschrieben nach {args.dump_html}\n")

    try:
        data = client.get_substitutions()
    except Exception as err:  # noqa: BLE001
        print(f"Abruf/Parsing fehlgeschlagen: {err}", file=sys.stderr)
        return 1

    days = data["tage"]
    if not days:
        print("Der Parser hat keine Tage gefunden.")
        print("Das kann bedeuten: aktuell kein Plan veröffentlicht (Ferien) —")
        print("oder die Schule liefert ein abweichendes HTML. Mit --dump-html prüfen.")
        return 2

    print(f"Letzte Aktualisierung: {data['aktualisiert'] or 'unbekannt'}")
    print(f"Plan wird gerade aktualisiert: {'ja' if data['wird_aktualisiert'] else 'nein'}\n")

    for day in days:
        print(f"── {day['wochentag']}, {day['datum_de']} "
              f"{('(' + day['relativ'] + ') ') if day['relativ'] else ''}"
              f"{day['woche']}".rstrip())
        if day["hinweise"]:
            for note in day["hinweise"]:
                print(f"   Hinweis: {note}")
        if not day["eintraege"]:
            print("   keine Einträge")
        for entry in day["eintraege"]:
            marker = "ENTFALL" if entry["entfall"] else entry["art"] or "—"
            print(f"   Std {entry['stunde'] or '?':<8} {marker:<12} "
                  f"{entry['fach'] or '':<6} {entry['lehrer'] or '':<5} "
                  f"→ {entry['vertreter'] or '—':<5} Raum {entry['raum'] or '—'}"
                  f"{'  | ' + entry['hinweis'] if entry['hinweis'] else ''}")
        print()

    empty_fields = [
        key for key in ("stunde", "art", "fach", "lehrer")
        if all(not entry.get(key) for day in days for entry in day["eintraege"])
    ]
    if empty_fields:
        print(f"Achtung: diese Felder waren überall leer: {', '.join(empty_fields)}.")
        print("Möglicherweise benennt die Schule die Spalten anders — bitte melden.")

    print("\nRohdaten des ersten Tages:")
    print(json.dumps(days[0], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
