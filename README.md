# Schulportal Hessen Stundenplan und Kalender für Home Assistant

Home Assistant Custom Integration für den persönlichen Stundenplan und Schulkalender aus dem **Schulportal Hessen (SPH)**.

Die Integration basiert technisch auf den Open-Source-Projekten von [lanis-mobile](https://github.com/lanis-mobile), insbesondere `liblanis`, `LanisAPI` und `Lanis-mobile`.

## Installation über HACS

In **HACS → Integrationen → Benutzerdefinierte Repositories** dieses Repository hinzufügen:

```text
https://github.com/leonsio/sph-ha
```

Kategorie: `Integration`

Das Repository enthält mehrere Home-Assistant-Integrationen. HACS installiert sie gemeinsam; die Komponenten können anschließend unabhängig voneinander konfiguriert werden.

## Stundenplan

Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Schulportal Hessen Stundenplan** suchen.

Für jedes Schülerkonto werden benötigt:

- Schulnummer
- SPH-Benutzername
- SPH-Passwort
- Kind / Anzeigename
- Kind-Kürzel
- Aktualisierungsintervall

Eine Angabe der Klasse ist **nicht erforderlich**. Das Schülerkonto ist im Schulportal bereits einem persönlichen Stundenplan zugeordnet.

Beispiel:

```text
sensor.stundenplan_maxim_mk
```

Die Karte zeigt ausschließlich `eigener_plan`.

```yaml
type: custom:sph-stundenplan-card
entity: sensor.stundenplan_maxim_mk
title: Stundenplan Maxim
```

Die Integration löst Fachkürzel auf, berücksichtigt Badges in Klammern und kann alternative A/B-Wochenstunden nebeneinander darstellen.

## Schulkalender

Zusätzlich enthält das Repository die eigenständige Integration **Schulportal Hessen Kalender** (`sph_kalender`). Sie erzeugt einen Sensor mit den persönlichen Schulkalender-Terminen des Kindes.

Wichtig: **Die Zugangsdaten werden für den Kalender nicht erneut abgefragt oder gespeichert.** Beim Einrichten des Kalenders wird ein bereits eingerichtetes **Schulportal Hessen Stundenplan-Konto** ausgewählt. Dadurch werden dessen Schulnummer, Benutzername und Passwort wiederverwendet. Wenn die Stundenplan-Komponente bereits läuft, verwendet der Kalender außerdem deren `SphClient` und damit dieselbe Sitzung.

### Einrichtung

1. Zuerst mindestens ein Kind unter **Schulportal Hessen Stundenplan** einrichten.
2. Danach **Schulportal Hessen Kalender** als neue Integration hinzufügen.
3. Das gewünschte vorhandene Schulportal-Konto auswählen.
4. Home Assistant erzeugt den persönlichen Kalender-Sensor für dieses Kind.

Beispiel:

```text
sensor.schulkalender_maxim
```

Die Sensorattribute enthalten die normalisierten Termine:

```yaml
kind: Maxim
termine:
  - uid: ...
    summary: Elternabend
    description: ...
    location: Raum 153
    start: "2026-08-20T19:00:00"
    end: "2026-08-20T20:30:00"
    all_day: false
```

Der Sensorzustand ist die Anzahl der aktuell abgerufenen Termine. Der Zeitraum umfasst standardmäßig die vergangenen 31 Tage bis 365 Tage in die Zukunft.

### Warum iCalendar?

Der Schulkalender bietet einen iCal/ICS-Export. Dieser wird verwendet, damit der Kalender nicht aus der visuellen Monatsansicht rekonstruiert werden muss und die vom Schulportal für das Benutzerkonto bereitgestellte Auswahl an Terminen erhalten bleibt.

## Lovelace-Ressourcen

Die Stundenplan-Karten werden für **Home Assistant 2026.2+** automatisch über `add_extra_js_url()` bereitgestellt und zusätzlich in der Lovelace-Ressourcensammlung verwaltet. Eine manuelle `/local/...`-Ressource ist nicht erforderlich.

## Technische Umsetzung

Die SPH-Kommunikation orientiert sich an den genannten Lanis-Projekten:

- Login über das aktuelle SPH-Login-System
- RSA/AES-Handschlag
- Entschlüsselung von `<encoded>`-Bereichen
- Stundenplan über `stundenplan.php`
- persönlicher Stundenplan über `#own`
- persönlicher Schulkalender über den authentifizierten iCal-Export von `kalender.php`
- Parsing von iCalendar-Events einschließlich Ganztagsterminen, Beschreibung und Ort
- Netzwerkzugriffe laufen außerhalb des Home-Assistant-Event-Loops

## Mehrere Kinder

Für mehrere Kinder werden mehrere Stundenplan-Konten eingerichtet. Für jedes Konto kann anschließend ein eigener Kalender angelegt werden. Der Kalender speichert nur die Referenz auf den zugehörigen Stundenplan-Config-Entry und damit **keine zusätzlichen Zugangsdaten**.

## Fehlerbehebung

### „Custom element not found: sph-stundenplan-card“

Integration vollständig laden, Home Assistant neu starten und Browser/App neu laden. Die Karten-Ressourcen werden durch die Integration registriert; keine zusätzliche manuelle Ressource anlegen.

### Kalender lässt sich nicht einrichten

Es muss zuerst mindestens ein **Schulportal Hessen Stundenplan**-Eintrag existieren. Der Kalender verwendet bewusst ein bestehendes Konto, damit die Zugangsdaten nicht doppelt gespeichert werden.

### „Der persönliche Schulkalender konnte nicht als iCal abgerufen werden“

Prüfe, ob das ausgewählte Konto den Schulkalender im Schulportal öffnen kann. Der Schulkalender ist ein separates PaedOrg-Modul und kann schulabhängig aktiviert bzw. konfiguriert sein.

## Sicherheit

SPH-Zugangsdaten werden als Config-Entry-Daten des Stundenplan-Kontos gespeichert und nicht als Sensorattribute veröffentlicht. Der Kalender legt keine Kopie des Passworts an.

Bitte niemals Zugangsdaten oder vollständige Debug-Logs in Issues veröffentlichen.

## Hinweis

Dieses Projekt ist ein unabhängiges Community-Projekt und steht nicht in offizieller Verbindung mit dem Schulportal Hessen.
