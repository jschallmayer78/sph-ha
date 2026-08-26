"""Offline-Tests für Fachableitung und Fächer-Übersicht aus "Mein Unterricht".

Ausführen:  python3 tests/test_meinunterricht_overview.py
Braucht weder Home Assistant noch Netzzugriff.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(relative: str, name: str):
    path = ROOT / "custom_components" / "sph" / relative
    namespace: dict = {"__name__": name}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
    return namespace


subjects = load("api/subjects.py", "sph_subjects")
helpers = load("module/meinunterricht/helpers.py", "sph_mu_helpers")

subject_from_course = subjects["subject_from_course"]
subject_overview = helpers["subject_overview"]

failures: list[str] = []


def check(label, actual, expected):
    if actual != expected:
        failures.append(f"  {label}: erwartet {expected!r}, war {actual!r}")


# --- Fach aus Kursnamen ---------------------------------------------------
# Echte Kursnamen aus dem Portal.
check("Biologie 05cg", subject_from_course("Biologie 05cg"), "Biologie")
check("D 05cG", subject_from_course("D 05cG"), "Deutsch")
check("M 05cG", subject_from_course("M 05cG"), "Mathematik")
check("Englisch 05cg", subject_from_course("Englisch 05cg"), "Englisch")
check("Ethik 5", subject_from_course("Ethik 5"), "Ethik")
check("Musik 05cg", subject_from_course("Musik 05cg"), "Musik")
check("Klasse voran", subject_from_course("7c, 7n Ethik"), "Ethik")
check("Deutsch 7n", subject_from_course("Deutsch 7n"), "Deutsch")
check("Mehrwortfach", subject_from_course("Politik und Wirtschaft 10b"), "Politik und Wirtschaft")
check("Nur Klasse bleibt roh", subject_from_course("05cG"), "05cG")
check("Leer", subject_from_course(""), "")

# D und Deutsch landen im selben Topf – der Kern der Gruppierung.
check("D == Deutsch", subject_from_course("D 05cG"), subject_from_course("Deutsch 7n"))

# --- Übersicht ------------------------------------------------------------
AUFGABEN = [
    {"fach": "Deutsch", "kurs": "D 05cG", "lehrer": "JÄF", "datum": "2026-08-26",
     "thema": "Lesetexte", "erledigt": True},
    {"fach": "Deutsch", "kurs": "D 05cG", "lehrer": "JÄF", "datum": "2026-08-20",
     "thema": "Rechtschreibung", "erledigt": False},
    {"fach": "Mathematik", "kurs": "M 05cG", "lehrer": "SUL", "datum": "2026-08-24",
     "thema": "Diagramme", "erledigt": False},
    {"fach": "Mathematik", "kurs": "M 05cG", "lehrer": "NN", "datum": "2026-08-18",
     "thema": "Zahlenstrahl", "erledigt": False},
    {"fach": "Musik", "kurs": "Musik 05cg", "lehrer": "ABS", "datum": "2026-08-21",
     "thema": "Moorhexe", "erledigt": True},
]

uebersicht = subject_overview(AUFGABEN)

check("Drei Fächer", [f["fach"] for f in uebersicht], ["Mathematik", "Deutsch", "Musik"])
check("Sortierung: meiste offene zuerst", uebersicht[0]["offen"], 2)

mathe = uebersicht[0]
check("Mathe gesamt", mathe["anzahl"], 2)
check("Mathe erledigt", mathe["erledigt"], 0)
check("Mathe Status", mathe["status"], "offen")
check("Mathe Lehrer gesammelt", mathe["lehrer"], ["SUL", "NN"])
check("Mathe letzter Eintrag", mathe["letzter_eintrag"], "2026-08-24")
check("Mathe offene Themen", mathe["offene_themen"], ["Diagramme", "Zahlenstrahl"])

musik = uebersicht[2]
check("Musik ohne offene", musik["offen"], 0)
check("Musik Status", musik["status"], "erledigt")
check("Musik keine offenen Themen", musik["offene_themen"], [])

check("Leere Eingabe", subject_overview([]), [])
check("Fach fehlt -> Kurs", subject_overview([{"kurs": "AG Schulband"}])[0]["fach"], "AG Schulband")
check("Weder Fach noch Kurs", subject_overview([{}])[0]["fach"], "Ohne Fach")

if failures:
    print("FEHLGESCHLAGEN:")
    print("\n".join(failures))
    sys.exit(1)
print(f"OK — Fachableitung und Übersicht über {len(uebersicht)} Fächer korrekt.")
