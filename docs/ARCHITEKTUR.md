# Schulportal Hessen – Architektur

Die Home-Assistant-Integration ist modular aufgebaut. Gemeinsame technische Funktionen liegen unter `api/`. Fachliche Funktionen werden in den jeweiligen Modulen unter `module/` gekapselt.

## Quelltextstruktur

```text
custom_components/sph/
├── __init__.py
├── config_flow.py
├── const.py
├── coordinator.py
├── sensor.py
├── api/
│   ├── __init__.py
│   ├── auth_client.py
│   └── client.py
├── module/
│   ├── __init__.py
│   ├── stundenplan/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── coordinator.py
│   │   └── sensor.py
│   ├── kalender/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── coordinator.py
│   │   └── sensor.py
│   └── meinunterricht/
│       ├── __init__.py
│       ├── client.py
│       ├── coordinator.py
│       └── sensor.py
├── static/
│   └── Lovelace-Karten und weitere Frontend-Dateien
└── translations/
```

## Integrationsebene

Die Dateien direkt unter `custom_components/sph/` bilden die Integrations- und Home-Assistant-Ebene:

- `__init__.py` – Initialisierung der Integration und Aufbau der gemeinsamen Laufzeitdaten.
- `config_flow.py` – Einrichtung und Konfiguration der Integration.
- `const.py` – integrationsweite Konstanten.
- `sensor.py` – Sensor-Dispatcher. Erzeugt die Sensoren aus den fachlichen Modulen und enthält selbst möglichst keine fachliche Datenverarbeitung.
- `coordinator.py` – Kompatibilitätsschicht für den Stundenplan-Coordinator; die eigentliche Implementierung befindet sich im Stundenplan-Modul.

## `api/` – gemeinsame technische Funktionen

`api/` enthält Funktionen, die von mehreren fachlichen Modulen benötigt werden und nicht speziell zu Kalender, Stundenplan oder Mein Unterricht gehören.

Dazu zählen insbesondere:

- Authentifizierung beim Schulportal Hessen.
- Verwaltung der gemeinsamen HTTP-Kommunikation und Session.
- Login-/Session-Verarbeitung.
- Gemeinsame technische Hilfsfunktionen für die Kommunikation mit SPH.

Fachliche Verarbeitung soll nicht in `api/` abgelegt werden, wenn sie ausschließlich für ein einzelnes Modul benötigt wird.

## `module/stundenplan/`

Das Modul kapselt die komplette fachliche Verarbeitung des Stundenplans.

- `client.py` – Abruf und fachliche Verarbeitung der Stundenplandaten von `stundenplan.php`.
- `coordinator.py` – Home-Assistant DataUpdateCoordinator für den Stundenplan.
- `sensor.py` – Sensorimplementierung für die Stundenplandaten.
- `__init__.py` – Moduldefinition und öffentliche Modul-Schnittstellen.

Zum fachlichen Datenmodell gehören unter anderem:

- Unterrichtsstunden und Tageszuordnung.
- Fach, Lehrkraft und Raum.
- `badge` bzw. Wochenkennungen für A/B-Stunden.
- Erkennung bzw. Bereitstellung der Schülerklasse.
- Aufbereitung der Daten für den Stundenplan-Sensor.

## `module/kalender/`

Das Modul kapselt die komplette fachliche Verarbeitung des Schulkalenders.

- `client.py` – Abruf und Parsing der Kalenderdaten.
- `coordinator.py` – Home-Assistant DataUpdateCoordinator für den Kalender.
- `sensor.py` – Sensorimplementierung für die Kalenderdaten.
- `__init__.py` – Moduldefinition und öffentliche Modul-Schnittstellen.

Zum fachlichen Datenmodell gehören unter anderem:

- Ermittlung des aktuell gültigen hessischen Schuljahres.
- Abruf des SPH-Kalenderexports.
- CSV-Verarbeitung und iCal-Fallback.
- Normalisierung der Termine.
- Kalenderfelder wie `summary`, `description`, `location`, `art` und `verantwortlich`.

## `module/meinunterricht/`

Das Modul kapselt die fachliche Verarbeitung der Aufgaben aus „Mein Unterricht“.

- `client.py` – Abruf von `meinunterricht.php` und Parsing der aktuellen Kurs-/Hausaufgabeneinträge.
- `coordinator.py` – Home-Assistant DataUpdateCoordinator für die Aufgaben.
- `sensor.py` – Sensorimplementierung mit Aufgabenliste und Erledigungsstatistik.
- `__init__.py` – Moduldefinition und öffentliche Modul-Schnittstellen.

Das Datenmodell enthält insbesondere:

- Datum und daraus abgeleiteten Wochentag.
- Fach und Kurs.
- Thema und Hausaufgabe.
- Lehrer-Kürzel.
- Erledigt-/Nicht-erledigt-Status.
- SPH-interne Kurs-/Eintragskennungen zur eindeutigen Zuordnung.

Das Modul verwendet dieselbe authentifizierte SPH-Session wie Stundenplan und Kalender. Dadurch wird bei einer Aktualisierung nicht für jedes Modul ein eigener Login-Handshake benötigt.

## Datenfluss

Die fachliche Trennung folgt grundsätzlich diesem Ablauf:

```text
Home Assistant
      │
      ▼
custom_components/sph/__init__.py
      │
      ├──────────────► api/                    Gemeinsame Anmeldung/HTTP-Kommunikation
      │
      ├──────────────► module/stundenplan/
      │                    ├── client.py
      │                    ├── coordinator.py
      │                    └── sensor.py
      │
      ├──────────────► module/kalender/
      │                    ├── client.py
      │                    ├── coordinator.py
      │                    └── sensor.py
      │
      └──────────────► module/meinunterricht/
                           ├── client.py
                           ├── coordinator.py
                           └── sensor.py
```

Der `sensor.py`-Dispatcher auf Integrationsebene verbindet die fachlichen Sensorimplementierungen mit Home Assistant. Die fachliche Logik bleibt in den jeweiligen Modulen.

## Grundprinzip für weitere Entwicklung

Neue Funktionen sollen möglichst dort implementiert werden, wo sie fachlich hingehören:

1. **Nur Stundenplan:** `module/stundenplan/`
2. **Nur Kalender:** `module/kalender/`
3. **Nur Mein Unterricht:** `module/meinunterricht/`
4. **Von mehreren Modulen benötigt:** `api/`
5. **Nur Home-Assistant-Integration bzw. Konfiguration:** Ebene `custom_components/sph/`

Dadurch bleiben die fachlichen Module unabhängig voneinander und die gemeinsame API wird auf tatsächlich übergreifende Funktionen beschränkt.

Bei einer Erweiterung eines bestehenden Moduls sollen zunächst dessen `client.py`, `coordinator.py` und `sensor.py` geprüft werden, bevor neue Logik auf Integrationsebene ergänzt wird.
