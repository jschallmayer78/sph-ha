# Schulportal Hessen – Quelltextstruktur

Die Integration ist modular aufgebaut. Gemeinsame Funktionen liegen unter `api/`; fachliche Funktionen werden in den jeweiligen Modulen gekapselt.

```text
custom_components/sph/
├── __init__.py
├── sensor.py
├── api/
│   ├── __init__.py
│   ├── client.py
│   └── auth_client.py
├── stundenplan/
│   ├── __init__.py
│   ├── client.py
│   ├── coordinator.py
│   └── sensor.py
└── kalender/
    ├── __init__.py
    ├── client.py
    ├── coordinator.py
    └── sensor.py
```

## `api/`

Enthält Funktionen, die von mehreren Modulen benötigt werden, insbesondere:

- Authentifizierung und gemeinsame HTTP-Session
- Login-/Session-Verwaltung
- gemeinsame technische Kommunikation mit dem Schulportal
- gemeinsame Hilfsfunktionen für die Verarbeitung der SPH-Daten

## `stundenplan/`

Enthält die komplette fachliche Verarbeitung des Stundenplans:

- Abruf von `stundenplan.php`
- Parsing und Normalisierung der Stundenplandaten
- Erkennung der Schülerklasse
- Verarbeitung von Fach, Lehrkraft, Raum und Badge
- `SphTimetableCoordinator`
- `SphTimetableSensor`

## `kalender/`

Enthält die komplette fachliche Verarbeitung des Schulkalenders:

- Ermittlung des aktuellen hessischen Schuljahres
- CSV-Kalenderabruf und iCal-Fallback
- Parsing und Normalisierung der Termine
- Verarbeitung von `art` und `verantwortlich`
- `SphCalendarCoordinator`
- `SphCalendarSensor`

## Grundprinzip

Neue Funktionen sollen möglichst im fachlich passenden Modul implementiert werden. Nur Funktionen, die tatsächlich von mehreren Modulen benötigt werden, gehören in `api/`.

`sensor.py` auf Integrationsebene dient lediglich als Einstiegspunkt bzw. Dispatcher für die einzelnen Sensorplattformen.
