"""Offline tests for the calendar event conversion and plan helpers.

Home Assistant is not installable in every dev environment, so the few HA
symbols that are actually used get minimal stand-ins here. The code under test
is loaded from source, exactly as it ships.

Run with:  python3 tests/test_calendar_events.py
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
BERLIN = timezone(timedelta(hours=2))


def _install_homeassistant_stubs() -> None:
    """Register the minimal HA surface the modules under test import."""
    if "homeassistant" in sys.modules:
        return

    @dataclass
    class CalendarEvent:
        start: object
        end: object
        summary: str
        description: str | None = None
        location: str | None = None
        uid: str | None = None

    ha = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    calendar = types.ModuleType("homeassistant.components.calendar")
    class _CalendarEntity:
        """Stand-in base class."""

    class _CoordinatorEntity:
        """Stand-in base class; must differ from CalendarEntity."""

    calendar.CalendarEvent = CalendarEvent
    calendar.CalendarEntity = _CalendarEntity

    helpers = types.ModuleType("homeassistant.helpers")
    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")
    update_coordinator.CoordinatorEntity = _CoordinatorEntity

    util = types.ModuleType("homeassistant.util")
    dt_util = types.ModuleType("homeassistant.util.dt")
    dt_util.DEFAULT_TIME_ZONE = BERLIN
    dt_util.now = lambda: datetime(2026, 8, 26, 9, 0, tzinfo=BERLIN)
    dt_util.as_local = lambda value: value.astimezone(BERLIN)
    util.dt = dt_util

    for name, module in (
        ("homeassistant", ha),
        ("homeassistant.components", components),
        ("homeassistant.components.calendar", calendar),
        ("homeassistant.helpers", helpers),
        ("homeassistant.helpers.update_coordinator", update_coordinator),
        ("homeassistant.util", util),
        ("homeassistant.util.dt", dt_util),
    ):
        sys.modules[name] = module


def _load(path: pathlib.Path, name: str, replacements: dict[str, str] | None = None):
    source = path.read_text(encoding="utf-8")
    for old, new in (replacements or {}).items():
        source = source.replace(old, new)
    namespace: dict = {"__name__": name}
    exec(compile(source, str(path), "exec"), namespace)
    return namespace


def main() -> int:
    _install_homeassistant_stubs()
    failures: list[str] = []

    def check(label, actual, expected):
        if actual != expected:
            failures.append(f"  {label}: erwartet {expected!r}, war {actual!r}")

    calendar_ns = _load(
        ROOT / "custom_components/sph/module/kalender/calendar.py",
        "sph_calendar",
        {"from ..stundenplan.sensor import child_label": "child_label = lambda entry: 'Test'"},
    )
    to_calendar_event = calendar_ns["to_calendar_event"]

    # All-day event: SPH marks the last day itself, HA expects an exclusive end.
    allday = to_calendar_event(
        {
            "start": "2026-09-01T00:00:00",
            "end": "2026-09-03T23:59:59.999999",
            "all_day": True,
            "summary": "Klassenfahrt",
            "art": "Fahrt",
            "verantwortlich": "KLM",
        }
    )
    check("Ganztag Start", allday.start, date(2026, 9, 1))
    check("Ganztag Ende exklusiv", allday.end, date(2026, 9, 4))
    check("Ganztag Beschreibung", allday.description, "Art: Fahrt\nVerantwortlich: KLM")

    # Single all-day event must still span one day.
    single = to_calendar_event(
        {"start": "2026-09-01T00:00:00", "end": "2026-09-01T00:00:00",
         "all_day": True, "summary": "Wandertag"}
    )
    check("Einzelner Ganztag", (single.start, single.end),
          (date(2026, 9, 1), date(2026, 9, 2)))

    # Timed event without timezone must be interpreted as local time.
    timed = to_calendar_event(
        {"start": "2026-09-02T18:00:00", "end": "2026-09-02T20:00:00",
         "all_day": False, "summary": "Elternabend", "location": "Aula"}
    )
    check("Zeit-Termin Start", timed.start, datetime(2026, 9, 2, 18, 0, tzinfo=BERLIN))
    check("Zeit-Termin Ende", timed.end, datetime(2026, 9, 2, 20, 0, tzinfo=BERLIN))
    check("Zeit-Termin Ort", timed.location, "Aula")

    # Zero-length timed events get a sane fallback duration.
    zero = to_calendar_event(
        {"start": "2026-09-02T18:00:00", "end": "2026-09-02T18:00:00",
         "all_day": False, "summary": "Ausgabe Zeugnisse"}
    )
    check("Null-Dauer korrigiert", zero.end, datetime(2026, 9, 2, 19, 0, tzinfo=BERLIN))

    check("Unparsbarer Termin verworfen", to_calendar_event({"summary": "x"}), None)

    # --- helpers ----------------------------------------------------------
    helpers = _load(ROOT / "custom_components/sph/module/vertretung/helpers.py", "sph_helpers")
    plan = {
        "tage": [
            {"datum": "2026-08-26", "eintraege": [
                {"entfall": True, "stunden": [1, 2]},
                {"entfall": False, "stunden": [4]},
            ]},
            {"datum": "2026-08-27", "eintraege": [
                {"entfall": True, "stunden": [3]},
            ]},
        ]
    }
    check("Entfall 1. Stunde heute",
          helpers["first_lesson_cancelled"](plan, date(2026, 8, 26), 1), True)
    check("Kein Entfall 1. Stunde morgen",
          helpers["first_lesson_cancelled"](plan, date(2026, 8, 27), 1), False)
    check("Tag ohne Plan liefert None",
          helpers["first_lesson_cancelled"](plan, date(2026, 8, 28), 1), None)
    check("Einträge eines Tages",
          len(helpers["entries_for"](plan, date(2026, 8, 26))), 2)
    check("Heute aus dt_util", helpers["today"](), date(2026, 8, 26))
    check("Morgen aus dt_util", helpers["tomorrow"](), date(2026, 8, 27))

    if failures:
        print("FEHLGESCHLAGEN:")
        print("\n".join(failures))
        return 1
    print("OK — Kalender-Konvertierung und Vertretungs-Helfer verhalten sich wie erwartet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
