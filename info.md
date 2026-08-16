# Schulportal Hessen Stundenplan

Home Assistant Custom Integration für den persönlichen Stundenplan aus dem Schulportal Hessen.

Die Integration verwendet die Kommunikations- und Parserkonzepte aus den Open-Source-Projekten `lanis-mobile/liblanis`, `LanisAPI` und `Lanis-mobile`.

## Features

- SPH-Anmeldung über Schulnummer, Benutzername und Passwort
- RSA/AES-Handshake entsprechend dem Lanis-Mobile-Protokoll
- Auslesen des persönlichen SPH-Stundenplans
- Keine manuelle Klassenangabe erforderlich
- Mehrere Schüler/Kinder mit eigenen SPH-Zugangsdaten
- Kind-Name und Kind-Kürzel für die Zuordnung der Sensoren
- Fach, Lehrkraft, Raum, Uhrzeit und Dauer
- Auflösung gängiger Fachkürzel, z. B. `M` → Mathematik und `F2` → Französisch 2
- Darstellung von SPH-Badges zur Kennzeichnung eingeschränkter bzw. wochenabhängiger Stunden
- Badges werden in der Lovelace-Karte in Klammern dargestellt, z. B. `Französisch 2 (A)`
- Home-Assistant-Sensor mit persönlichem `eigener_plan`
- integrierte Lovelace-Karte `custom:sph-stundenplan-card`
- automatische Lovelace-Ressourcenverwaltung über `add_extra_js_url()` für Home Assistant 2026.2+
- Installation und Updates über HACS

## Lovelace-Karte

Beispiel:

```yaml
type: custom:sph-stundenplan-card
entity: sensor.stundenplan_maxim_mk
title: Stundenplan Maxim
```

Die Karte zeigt ausschließlich den persönlichen Stundenplan (`eigener_plan`).

## Mehrere Kinder

Für jedes Schülerkonto kann ein eigener Config-Entry angelegt werden. Kind-Name und Kind-Kürzel werden zur eindeutigen Zuordnung verwendet. Dadurch können beispielsweise folgende Sensoren entstehen:

```text
sensor.stundenplan_maxim_mk
sensor.stundenplan_lena_lk
```

## Unterstützung

Dieses Projekt ist nicht offiziell mit dem Schulportal Hessen verbunden.

Bei Problemen bitte ein Issue im GitHub-Repository mit Home-Assistant-Version und relevanten Logmeldungen erstellen. Keine Passwörter oder Zugangsdaten veröffentlichen.
