# Schulportal Hessen

Home-Assistant-Custom-Integration für Daten aus dem **Schulportal Hessen (SPH)**.

Die Integration wird einmalig installiert und konfiguriert und umfasst aktuell:

- persönlichen Stundenplan
- persönlichen Schulkalender
- Lovelace-Karten für den Stundenplan

## Installation

Die Installation erfolgt über HACS als Integration:

```text
https://github.com/leonsio/sph-ha
```

Anschließend in Home Assistant unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Schulportal Hessen** suchen.

## Konfiguration

Für jedes Kind wird ein eigener Eintrag angelegt. Benötigt werden:

- Schulnummer
- SPH-Benutzername
- SPH-Passwort
- Name des Kindes
- Kürzel des Kindes
- Aktualisierungsintervall

Das Standardintervall beträgt **60 Minuten**. Die Konfiguration kann später geändert werden, einschließlich Zugangsdaten, Schulnummer, Name, Kürzel und Aktualisierungsintervall.

## Sensoren

Beispiel für Maxim (`Mk`):

```text
sensor.stundenplan_maxim_mk
sensor.schulkalender_maxim_mk
```

Der Stundenplan enthält den persönlichen Plan einschließlich Fach, Lehrkraft, Raum, Uhrzeit und Badge. Der Kalender enthält Termine mit Feldern wie `start`, `end`, `summary`, `art` und `verantwortlich`.

Das aktuelle hessische Schuljahr wird automatisch ermittelt. Der Kalender verwendet bevorzugt den CSV-Export des Schulportals und kann auf iCal zurückfallen.

Bei kurzfristigen Verbindungsproblemen bleiben die zuletzt erfolgreich abgerufenen Daten erhalten.

## Lovelace

```yaml
type: custom:sph-stundenplan-card
entity: sensor.stundenplan_maxim_mk
title: Stundenplan Maxim
```

Für die Tagesansicht:

```yaml
type: custom:sph-stundenplan-tag-card
entity: sensor.stundenplan_maxim_mk
title: Heute – Maxim
```

Die benötigten JavaScript-Ressourcen werden von der Integration automatisch registriert.

## Hinweis

Dieses Projekt ist ein unabhängiges Community-Projekt und steht nicht in offizieller Verbindung mit dem Schulportal Hessen.

Die technische Quelltextstruktur ist separat unter [`docs/ARCHITEKTUR.md`](docs/ARCHITEKTUR.md) dokumentiert.
