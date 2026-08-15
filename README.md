# Schulportal Hessen Stundenplan für Home Assistant

Home Assistant Custom Integration für den Stundenplan aus dem **Schulportal Hessen (SPH)**.

Die Integration basiert technisch auf den Open-Source-Projekten von [lanis-mobile](https://github.com/lanis-mobile), insbesondere `liblanis`, `LanisAPI` und `Lanis-mobile`.

## Installation über HACS

### 1. Repository zu HACS hinzufügen

In Home Assistant **HACS → Integrationen** öffnen und über das Drei-Punkte-Menü **Benutzerdefinierte Repositories** auswählen.

Als Repository eintragen:

```text
https://github.com/leonsio/sph-ha
```

Kategorie:

```text
Integration
```

Danach nach **Schulportal Hessen Stundenplan** suchen und die Integration installieren.

Anschließend Home Assistant neu starten.

### 2. Integration konfigurieren

Nach dem Neustart unter:

**Einstellungen → Geräte & Dienste → Integration hinzufügen**

nach **Schulportal Hessen** suchen.

Benötigt werden:

- **Schulnummer**
- **SPH-Benutzername**
- **SPH-Passwort**
- **Klasse**
- **Aktualisierungsintervall**

## Lovelace-Karte

Die Lovelace-JavaScript-Ressource wird bei Home Assistant 2026.2+ automatisch durch die Integration registriert bzw. aktualisiert.

Eine manuelle `/local/...`-Ressource ist daher **nicht erforderlich**.

Die Karte kann anschließend beispielsweise so verwendet werden:

```yaml
type: custom:sph-stundenplan-card
entity: sensor.schulportal_hessen_stundenplan
title: Stundenplan
```

Die Ressource wird intern über den statischen Pfad der Integration bereitgestellt.

## Technische Umsetzung

Die SPH-Kommunikation orientiert sich an `lanis-mobile/liblanis`:

- SPH-Login und Session-Cookies
- RSA-Public-Key-Handschlag
- RSA/PKCS#1-Verschlüsselung des Sitzungsschlüssels
- AES-CBC/PKCS7 für verschlüsselte SPH-Inhalte
- Stundenplanparser für die SPH-Tabellen
- Unterstützung von `#all` und `#own`
- Berücksichtigung von Unterrichtsfach, Lehrkraft, Raum, Badge, Uhrzeiten und Doppelstunden/`rowspan`

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
