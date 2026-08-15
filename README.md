# Schulportal Hessen Stundenplan für Home Assistant

Home Assistant Custom Integration für den Stundenplan aus dem **Schulportal Hessen (SPH)**.

Die Integration basiert technisch auf den Open-Source-Projekten von [lanis-mobile](https://github.com/lanis-mobile), insbesondere `liblanis`, `LanisAPI` und `Lanis-mobile`.

## Installation über HACS

### 1. Repository zu HACS hinzufügen

In Home Assistant **HACS → Integrationen** öffnen und über das Drei-Punkte-Menü **Benutzerdefinierte Repositories** auswählen.

Repository:

```text
https://github.com/leonsio/sph-ha
```

Kategorie:

```text
Integration
```

Danach **Schulportal Hessen Stundenplan** installieren und Home Assistant neu starten.

### 2. Integration konfigurieren

Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Schulportal Hessen** suchen.

Benötigt werden nur:

- **Schulnummer**
- **SPH-Benutzername**
- **SPH-Passwort**
- **Aktualisierungsintervall**

Eine Angabe der Klasse ist **nicht erforderlich**. Das Schülerkonto im Schulportal ist bereits einer Klasse zugeordnet. Die Integration liest den Stundenplan direkt aus `stundenplan.php` und übernimmt die vom SPH für dieses Konto bereitgestellten Pläne.

## Lovelace-Karte

Die Lovelace-JavaScript-Ressource wird bei Home Assistant 2026.2+ automatisch durch die Integration registriert bzw. aktualisiert. Eine manuelle `/local/...`-Ressource ist nicht erforderlich.

Beispiel:

```yaml
type: custom:sph-stundenplan-card
entity: sensor.schulportal_hessen_stundenplan
title: Stundenplan
```

## Stundenplanquelle

Die Implementierung folgt dem aktuellen Vorgehen von `liblanis`: Nach der Authentifizierung wird `https://start.schulportal.hessen.de/stundenplan.php` aufgerufen. Der Parser wertet dort die Tabellen `#all` und `#own` aus. Die aktuelle Referenzimplementierung macht ebenfalls keine Klassenangabe beim Abruf des Stundenplans. citeturn35file0turn36file0

Damit ist die Klasse keine zusätzliche Filterinformation der Home-Assistant-Integration.

## Technische Umsetzung

Die SPH-Kommunikation orientiert sich an `lanis-mobile/liblanis`:

- SPH-Login über die Login-Bootstrap-URL
- RSA-Public-Key-Handschlag
- RSA/PKCS#1-Verschlüsselung des Sitzungsschlüssels
- AES-CBC/PKCS7 für verschlüsselte SPH-Inhalte
- Stundenplanparser für die SPH-Tabellen
- Unterstützung von `#all` und `#own`
- Berücksichtigung von Unterrichtsfach, Lehrkraft, Raum, Badge, Uhrzeiten und Doppelstunden/`rowspan`

Die aktuelle `liblanis`-Implementierung ruft den Stundenplan ebenfalls direkt über `stundenplan.php` ab und prüft anschließend auf `#all` bzw. `#own`. citeturn35file0turn36file0

Referenzprojekte:

- https://github.com/lanis-mobile/liblanis
- https://github.com/lanis-mobile/LanisAPI
- https://github.com/lanis-mobile/Lanis-mobile

## Home Assistant

Die Integration ist für **Home Assistant 2026.2 und neuer** vorgesehen.

## Sicherheit

Das SPH-Passwort wird als Config-Entry-Daten von Home Assistant gespeichert und nicht als Sensorattribut veröffentlicht.

Bitte niemals Zugangsdaten oder vollständige Login-/Debug-Logs in Issues veröffentlichen.

## Hinweis

Dieses Projekt ist ein unabhängiges Community-Projekt und steht nicht in offizieller Verbindung mit dem Schulportal Hessen.
