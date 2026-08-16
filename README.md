# Schulportal Hessen für Home Assistant

Eine gemeinsame Home-Assistant-Custom-Integration für Daten aus dem **Schulportal Hessen (SPH)**.

Die Installation erfolgt **einmalig** als Integration **Schulportal Hessen**. Unter dieser Integration werden die fachlichen Module gebündelt:

```text
custom_components/
└── sph/
    ├── api/          # gemeinsamer SPH-Client und technische Kommunikation
    ├── stundenplan/  # Stundenplan-Modul
    └── kalender/     # Schulkalender-Modul
```

Weitere SPH-Module können später ergänzt werden, ohne eine weitere HACS-Integration anzulegen.

## Installation über HACS

Repository in HACS als benutzerdefiniertes Repository hinzufügen:

```text
https://github.com/leonsio/sph-ha
```

Kategorie: `Integration`.

Danach unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Schulportal Hessen** suchen.

## Einrichtung

Für jedes Kind wird ein Config-Entry der gemeinsamen Integration angelegt. Benötigt werden:

- Schulnummer
- SPH-Benutzername
- SPH-Passwort
- Name des Kindes
- Kürzel des Kindes
- Aktualisierungsintervall

Eine Klassenangabe ist nicht erforderlich: Das Schülerkonto ist im Schulportal bereits seinem persönlichen Stundenplan zugeordnet.

Die Zugangsdaten werden innerhalb des Config-Entries gemeinsam von allen aktivierten Modulen verwendet. Dadurch muss der Kalender nicht separat angemeldet werden.

Mehrere Kinder sind möglich, indem für jedes Kind ein weiterer Config-Entry angelegt wird.

## Module

### Stundenplan

Der Sensor heißt beispielsweise:

```text
sensor.stundenplan_maxim_mk
```

Die Attribute enthalten `tage` und `eigener_plan`. Die Darstellung verwendet ausschließlich den persönlichen Stundenplan. Fachkürzel werden aufgelöst und Badges als `(A)` bzw. `(B)` dargestellt. Gleichzeitige A/B-Alternativen können in der Lovelace-Karte nebeneinander erscheinen.

### Schulkalender

Für dasselbe Kind wird zusätzlich ein Sensor bereitgestellt, beispielsweise:

```text
sensor.schulkalender_maxim_mk
```

Die Attribute `termine` enthalten normalisierte persönliche Kalendertermine einschließlich Beginn, Ende, Ganztag, Beschreibung, Ort und UID. Der Kalender wird über den authentifizierten iCalendar-Export des Schulportals abgerufen.

## Lovelace

Die vorhandenen Karten bleiben erhalten:

```yaml
type: custom:sph-stundenplan-card
entity: sensor.stundenplan_maxim_mk
title: Stundenplan Maxim
```

und:

```yaml
type: custom:sph-stundenplan-tag-card
entity: sensor.stundenplan_maxim_mk
title: Heute – Maxim
```

Für Home Assistant 2026.2+ registriert die gemeinsame Integration die JavaScript-Dateien mit `add_extra_js_url()` und trägt sie zusätzlich in die Lovelace-Ressourcensammlung ein. Eine manuelle `/local/...`-Ressource ist nicht erforderlich.

## Technische Architektur

Der gemeinsame Bereich `api/` kapselt die SPH-Kommunikation:

- Login und Session
- RSA/AES-Handshake
- Entschlüsselung von `<encoded>`-Bereichen
- HTTP-Kommunikation
- Stundenplanabruf
- iCalendar-Abruf und Parsing

Die Module verwenden denselben `SphClient`. Netzwerkzugriffe werden über Home Assistants Executor ausgeführt, damit keine blockierenden `requests`- oder Kryptografie-Aufrufe im Event Loop stattfinden.

## Migration von älteren Versionen

Ab Version 0.3.x ist **`sph` die einzige Integration**. Die früheren Domains `sph_stundenplan` und `sph_kalender` werden nicht mehr als separate HACS-Integrationen geführt.

Nach dem Update müssen eventuell vorhandene alte Config-Entries entfernt und die gemeinsame Integration **Schulportal Hessen** neu eingerichtet werden. Die Lovelace-Kartentypen `sph-stundenplan-card` und `sph-stundenplan-tag-card` bleiben unverändert.

## Hinweis

Dieses Projekt ist ein unabhängiges Community-Projekt und steht nicht in offizieller Verbindung mit dem Schulportal Hessen.
