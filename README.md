# Schulportal Hessen Stundenplan für Home Assistant

Home Assistant Custom Integration für den persönlichen Stundenplan aus dem **Schulportal Hessen (SPH)**.

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

Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Schulportal Hessen Stundenplan** suchen.

Für jedes Schülerkonto werden benötigt:

- **Schulnummer**
- **SPH-Benutzername**
- **SPH-Passwort**
- **Kind / Anzeigename** – frei wählbarer Name, z. B. `Maxim`
- **Kind-Kürzel** – kurzes eindeutiges Kürzel, z. B. `Mk`
- **Aktualisierungsintervall**

Eine Angabe der Klasse ist **nicht erforderlich**. Jedes Schülerkonto ist im Schulportal bereits genau einer Klasse bzw. einem persönlichen Stundenplan zugeordnet. Die Integration liest den Stundenplan direkt aus `stundenplan.php` und übernimmt den vom SPH für dieses Konto bereitgestellten persönlichen Plan.

Es können **mehrere Schülerkonten/Kinder** eingerichtet werden. Für jedes Konto wird ein eigener Sensor angelegt, dessen Entity-ID den Kind-Namen bzw. das Kind-Kürzel enthält, z. B.:

```text
sensor.stundenplan_maxim_mk
```

Damit können mehrere Kinder mit unterschiedlichen SPH-Zugangsdaten unabhängig voneinander in einem Home-Assistant-System verwendet werden.

## Lovelace-Karte

Die Lovelace-JavaScript-Ressource wird bei Home Assistant **2026.2+** automatisch durch die Integration registriert bzw. aktualisiert. Die Ressource verwendet die von Home Assistant bereitgestellte `add_extra_js_url()`-Methode. Eine manuelle `/local/...`-Ressource ist daher nicht erforderlich.

Die Karte zeigt ausschließlich den **persönlichen Stundenplan** aus `eigener_plan`.

### Beispiel

```yaml
type: custom:sph-stundenplan-card
entity: sensor.stundenplan_maxim_mk
title: Stundenplan Maxim
```

`entity` ist optional, wenn die Karte über ein Kind-Kürzel konfiguriert werden soll. Die explizite Angabe des Sensors wird empfohlen, insbesondere wenn mehrere Kinder eingerichtet sind.

### Kartenparameter

| Parameter | Erforderlich | Beschreibung |
|---|---|---|
| `type` | ja | Muss `custom:sph-stundenplan-card` sein |
| `entity` | empfohlen | Sensor des gewünschten Kindes, z. B. `sensor.stundenplan_maxim_mk` |
| `title` | nein | Eigener Titel der Karte |
| `child` | nein | Kind-Kürzel zur automatischen Auswahl des passenden Sensors |

### Darstellung von Fächern und Gruppen

Die Integration versucht, die SPH-Fachkürzel in verständliche Fachnamen umzuwandeln. Beispiele:

- `M` → **Mathematik**
- `D` → **Deutsch**
- `E1` → **Englisch 1**
- `F2` → **Französisch 2**
- `L2` → **Latein 2**
- `GE` → **Geschichte**
- `PH` → **Physik**
- `CH` → **Chemie**
- `BIO` → **Biologie**
- `PW` → **Politik und Wirtschaft**
- `ETH` → **Ethik**
- `RKA` → **Religion katholisch**
- `REV` → **Religion evangelisch**
- `SP` → **Sport**

Dabei wird eine Zahl am Fachkürzel als mögliche Fach-/Gruppenkennung beibehalten. `F2` wird beispielsweise zu **Französisch 2**.

Zusätzlich können die vom SPH gelieferten **Badges** wichtige Angaben zur Gültigkeit einer Stunde enthalten, etwa bei einem Unterricht, der nur in einer bestimmten Woche stattfindet. Diese werden in der Karte **in Klammern** angezeigt, damit sie eindeutig von der Fach-/Gruppenbezeichnung unterschieden werden:

```text
Französisch 2 (A)
```

Ohne Badge erscheint lediglich:

```text
Französisch 2
```

Die Karte zeigt außerdem Uhrzeit, Lehrkraft und Raum an.

## Sensorattribute

Der jeweilige Stundenplansensor enthält unter anderem:

```yaml
kind: Maxim
kind_kürzel: Mk
wochenkennung: A
tage: ...
eigener_plan: ...
```

`tage` enthält den vom SPH bereitgestellten Stundenplan, während `eigener_plan` den **persönlichen Stundenplan des Schülerkontos** enthält. Die Lovelace-Karte verwendet ausschließlich `eigener_plan`.

Ein einzelner Unterrichtseintrag kann beispielsweise so aussehen:

```yaml
- day: 0
  subject: F2
  fach: Französisch 2
  teacher: Drg
  room: "157"
  badge: A
  duration: 2
  start: "07:55"
  end: "09:25"
  index: 1
```

Das Badge `A` wird in der Karte als **(A)** dargestellt.

## Stundenplanquelle

Die Implementierung folgt dem aktuellen Vorgehen von `liblanis`: Nach der Authentifizierung wird `https://start.schulportal.hessen.de/stundenplan.php` aufgerufen. Der Parser wertet dort die Tabellen `#all` und `#own` aus. Die Klasse wird dabei nicht als zusätzlicher Parameter benötigt.

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
- persönlicher Stundenplan über `#own`

Referenzprojekte:

- https://github.com/lanis-mobile/liblanis
- https://github.com/lanis-mobile/LanisAPI
- https://github.com/lanis-mobile/Lanis-mobile

## Home Assistant

Die Integration ist für **Home Assistant 2026.2 und neuer** vorgesehen.

Die Lovelace-Ressource wird automatisch verwaltet. Nach einer Aktualisierung der Integration kann ein Neustart von Home Assistant erforderlich sein, damit die aktuelle Version der Karte geladen wird.

## Fehlerbehebung

### „Custom element not found: sph-stundenplan-card“

Prüfe zunächst, ob die Integration vollständig geladen wurde und die Lovelace-Ressource automatisch registriert wurde. Danach Home Assistant neu starten und den Browser bzw. die Home-Assistant-App neu laden.

Eine zusätzliche manuelle Lovelace-Ressource sollte **nicht** angelegt werden, da die Integration die Ressource selbst über `add_extra_js_url()` registriert.

### „Kein Stundenplan für dieses Konto verfügbar“

Die Integration benötigt keine Klassenangabe. Prüfe stattdessen:

1. ob die SPH-Anmeldung erfolgreich ist,
2. ob das verwendete Konto ein Schülerkonto ist,
3. ob der Stundenplan im Schulportal für dieses Konto angezeigt wird,
4. ob Schulnummer, Benutzername und Passwort korrekt sind.

### Mehrere Kinder

Für jedes Kind sollte eine eigene Integration bzw. ein eigener Config-Entry mit dessen SPH-Zugangsdaten angelegt werden. Verwende unterschiedliche Kind-Namen und Kürzel. Dadurch entstehen separate Sensoren, beispielsweise:

```text
sensor.stundenplan_maxim_mk
sensor.stundenplan_lena_lk
```

In der Karte wird anschließend der gewünschte Sensor über `entity` angegeben.

## Sicherheit

Das SPH-Passwort wird als Config-Entry-Daten von Home Assistant gespeichert und nicht als Sensorattribut veröffentlicht.

Bitte niemals Zugangsdaten oder vollständige Login-/Debug-Logs in Issues veröffentlichen.

## Hinweis

Dieses Projekt ist ein unabhängiges Community-Projekt und steht nicht in offizieller Verbindung mit dem Schulportal Hessen.
