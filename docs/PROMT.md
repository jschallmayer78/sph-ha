# Aufgabe: Home-Assistant-Integration „Schulportal Hessen (SPH)“

Entwickle eine vollständige Home-Assistant-Custom-Integration für das Schulportal Hessen unter:

https://start.schulportal.hessen.de/

Repository-Ziel:
https://github.com/leonsio/sph-ha

Die Integration soll HACS-kompatibel sein und modular aufgebaut werden.

## 1. Ziel der Integration

Die Integration ruft Daten aus dem Schulportal Hessen ab und stellt sie als Home-Assistant-Sensoren und Lovelace-Karten bereit.

Aktuell sollen folgende Module existieren:

- Stundenplan
- Schulkalender
- Mein Unterricht

Zusätzlich existieren spezielle KFG-Lovelace-Karten für das Kaiserin-Friedrich-Gymnasium in Bad Homburg.

Wichtig: Die normale SPH-Funktionalität darf durch KFG-Sonderfunktionen nicht verändert werden.

## 2. Repository-Architektur

Die Integration soll modular strukturiert sein:

```text
custom_components/sph/
├── api/
│   ├── Auth-/Session-Funktionen
│   └── übergreifende API-Funktionen
├── module/
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
│   ├── sph-stundenplan-card.js
│   ├── sph-stundenplan-tag-card.js
│   ├── sph-stundenplan-grid-card.js
│   ├── kfg-stundenplan-card.js
│   ├── kfg-stundenplan-tag-card.js
│   └── kfg-stundenplan-grid-card.js
├── brand/
├── translations/
├── __init__.py
├── config_flow.py
├── const.py
└── sensor.py
```

Grundregel: Fachliche Funktionen gehören in das jeweilige Modul. Stundenplan nach `module/stundenplan/`, Kalender nach `module/kalender/`, Mein Unterricht nach `module/meinunterricht/`. Nur Funktionen, die mehrere Module benötigen, gehören unter `api/`.

## 3. Authentifizierung / Session

Die Anmeldung erfolgt über das Schulportal Hessen. Schulnummer, Benutzername und Passwort müssen konfigurierbar sein.

Die HTTP-Session soll zwischen Stundenplan, Kalender und Mein Unterricht wiederverwendet werden. Nicht bei jedem Modul separat anmelden.

Die Session muss erkennen können, wenn sie abgelaufen ist. Bei einer abgelaufenen Session:

1. Session/Login erneuern
2. ursprünglichen Abruf erneut versuchen

Die Integration darf nicht davon ausgehen, dass ein Login dauerhaft gültig ist.

## 4. Robustheit

Die Integration muss gegen temporäre Fehler robust sein.

Wenn keine Internetverbindung besteht, Schulportal Hessen nicht erreichbar ist, ein einzelner Bereich des Schulportals nicht funktioniert, ein CSV-/iCal-Export temporär nicht verfügbar ist oder eine Session abgelaufen ist, dürfen bereits vorhandene Daten nicht durch leere Daten ersetzt werden.

Stattdessen:

- letzten erfolgreichen Datenstand behalten
- Fehler loggen
- beim nächsten Update erneut versuchen

Ein Ausfall des Kalenders darf beispielsweise nicht verhindern, dass der Stundenplan weiterhin funktioniert. Ein Ausfall von „Mein Unterricht“ darf ebenfalls nicht die anderen Module deaktivieren.

## 5. Aktualisierung

Standard-Aktualisierungsintervall: **60 Minuten**.

Das Intervall muss nach der Ersteinrichtung konfigurierbar sein.

## 6. Config Flow

Folgende Parameter müssen konfigurierbar bzw. nachträglich änderbar sein:

- Schulnummer / SchulID
- Benutzername
- Passwort
- Name des Kindes
- Kürzel des Kindes
- Aktualisierungsintervall

Die nachträgliche Änderung darf nicht nur bei einer Neuinstallation möglich sein.

Der Name und das Kürzel werden für die Entity-ID verwendet.

Beispiele:

- `sensor.stundenplan_maxim_mk`
- `sensor.schulkalender_maxim_mk`
- `sensor.mein_unterricht_maxim_mk`

## 7. Stundenplan

Der Stundenplan wird aus `stundenplan.php` ausgelesen. Die Daten enthalten unter anderem:

- Fach
- Fachkürzel
- Lehrer
- Raum
- Beginn
- Ende
- Stunde
- Dauer
- badge
- Tag

Zusätzlich soll die Klasse des Schülers erkannt werden.

Beispiel:

`stundenplan.php?a=detail_klasse&e=1&k=7n`

Dabei bedeutet `k=7n` → Klasse 7n.

Die erkannte Klasse soll als Datenfeld gespeichert werden und später für weitere Funktionen verfügbar sein.

## 8. Wochenkennung / A-B-Wochen

Der Stundenplan kann eine `wochenkennung` enthalten, z. B. `A` oder `B`.

Bei einer Unterrichtsstunde kann zusätzlich `badge` vorhanden sein.

Regeln:

- `badge = null` → Unterricht findet unabhängig von der Wochenkennung statt.
- `badge = A` → Stunde nur anzeigen, wenn `wochenkennung = A`.
- `badge = B` → Stunde nur anzeigen, wenn `wochenkennung = B`.

Es können zur gleichen Uhrzeit zwei unterschiedliche Fächer existieren. Beispiel: Physik → Woche B, Chemie → Woche A. Dann darf nur das für die aktuelle Wochenkennung passende Fach angezeigt werden.

## 9. Schulkalender

Der Schulkalender wird aus `kalender.php` abgerufen. Bevorzugt soll der CSV-Export verwendet werden:

`https://start.schulportal.hessen.de/kalender.php?a=export&export=csv&year=2026`

Für 2026/2027 ist `year=2026`, für 2027/2028 `year=2027`.

Das Schuljahr darf nicht einfach anhand des Kalenderjahres bestimmt werden. Es muss das aktuelle hessische Schuljahr erkannt werden. Dazu sollen die offiziellen Ferientermine des Hessischen Kultusministeriums berücksichtigt werden:

https://kultus.hessen.de/schulsystem/ferien/ferientermine

Das aktuell laufende Schuljahr ist entscheidend. Das nächste Schuljahr ist für die normale Anzeige irrelevant.

## 10. Kalenderdaten

Jeder Termin soll möglichst folgende Felder besitzen:

- `start`
- `end`
- `all_day`
- `summary`
- `description`
- `location`
- `art`
- `verantwortlich`
- `uid`

Besonders wichtig sind `art` und `verantwortlich`, da sie später als Filterkriterien verwendet werden.

Textwerte müssen korrekt escaped/serialisiert werden. Keine manuelle YAML-Erzeugung, bei der beispielsweise `art: Ferien` statt eines korrekt serialisierten Strings entsteht.

## 11. Kalender-Sensor

Der Kalender-Sensor enthält die Termine als Liste.

Home Assistant begrenzt die Größe von State Attributes auf 16384 Bytes. Es darf deshalb nicht versucht werden, eine unbegrenzt große Terminliste als State Attribute zu speichern.

Die Implementierung muss mit dieser Grenze sinnvoll umgehen, z. B. durch Begrenzung oder Priorisierung relevanter Termine bzw. alternative Datenhaltung.

## 12. Mein Unterricht

Neues Modul: `module/meinunterricht/`

Die Seite `https://start.schulportal.hessen.de/meinunterricht.php#aktuell` soll ausgelesen werden.

Ziel: Alle aktuellen Hausaufgaben erfassen.

Pro Aufgabe möglichst:

- Datum
- Wochentag
- Fach
- Kurs
- Lehrer
- Thema
- Aufgabe
- erledigt

Zusätzlich:

- Anzahl Aufgaben
- Anzahl erledigt
- Anzahl nicht erledigt

Die Darstellung des Status soll später visuell möglich sein.

Die bestehende Auth-/Session-Logik muss verwendet werden.

## 13. Bestehende Implementierungen analysieren

Vor der Implementierung von Mein Unterricht soll geprüft werden, ob bestehende Open-Source-Implementierungen existieren, insbesondere Lanis-Mobile:

https://github.com/lanis-mobile/lanis

Erkenntnisse dürfen zur Verbesserung des Parsings verwendet werden, aber die Integration soll direkt das Schulportal Hessen auslesen.

## 14. Lovelace-Karten

Normale SPH-Karten:

- `sph-stundenplan-card`
- `sph-stundenplan-tag-card`
- `sph-stundenplan-grid-card`

KFG-Karten:

- `kfg-stundenplan-card`
- `kfg-stundenplan-tag-card`
- `kfg-stundenplan-grid-card`

Die KFG-Karten sind eigenständige Varianten der normalen Karten. Die normalen SPH-Karten dürfen nicht durch KFG-Funktionen verändert werden.

## 15. Tageskarte

Die Tageskarte soll automatisch auf den nächsten Tag wechseln, wenn die letzte Unterrichtsstunde des aktuellen Tages beendet ist.

Beispiel: Dienstag Unterricht bis 15:20 → nach 15:20 Mittwoch anzeigen.

Wochenendlogik muss erhalten bleiben.

Die Karte soll Wochentag und Datum anzeigen, z. B.:

`Dienstag 18.08.2026`

bzw.:

`Dienstag 18.08. Woche B`

Die Aktualisierung des Tageswechsels soll über einen Timer erfolgen.

## 16. Grid-Karten

Die Grid-Karten sollen den Stundenplan über die gesamte verfügbare Breite darstellen.

Raster:

```text
         Montag Dienstag Mittwoch Donnerstag Freitag
1.
2.
3.
...
```

Zeilen entsprechen Unterrichtsstunden. Doppelstunden sollen sinnvoll dargestellt werden.

Neben dem Raum soll explizit stehen: `Raum: 123`.

## 17. KFG-Karten

Die KFG-Karten sind für das Kaiserin-Friedrich-Gymnasium Bad Homburg gedacht.

Sie verwenden zusätzlich:

- `sensor.kfg_kollegium`
- `sensor.vertretungsplan`

Die Karten dürfen aber nicht voraussetzen, dass diese Sensoren vorhanden sind. Wenn sie fehlen, soll die normale SPH-Darstellung verwendet werden.

## 18. Lehrerauflösung

`sensor.kfg_kollegium` enthält beispielsweise:

`DRG: S.Düring`

Die Auflösung muss unabhängig von Groß-/Kleinschreibung sein. `Drg`, `DRG` und `drg` sollen alle zu `S.Düring` führen.

## 19. Vertretungsplan

`sensor.vertretungsplan` enthält Vertretungen.

Eine Vertretung darf nur auf eine Schülerstunde angewendet werden, wenn das Fach tatsächlich im Stundenplan dieses Schülers existiert.

Beispiel: 7./8. Stunde Schüler A → Ethik, Schüler B → Religion. Eine Religion-Vertretung darf nur Schüler B ändern.

Besonders wichtig: Zuerst mit den originalen Kürzeln arbeiten. Beispiel Stundenplan `F2`, Vertretungsplan `F2`; erst nach der Zuordnung `F2 → Französisch 2`. Gleiches gilt für Lehrer. Nicht `Französisch 2` gegen `F2` vergleichen.

## 20. Vertretungsarten

Abkürzungen sollen lesbar dargestellt werden:

- Betr → Betreuung
- Vertr → Vertretung
- Entf → Entfall
- Taus → Tausch
- Freis → Freistunde
- Raum → Raumänderung
- Statt-Vertretung → Statt-Vertretung
- Paus → Pausenaufsicht
- SES → Sonderunterricht
- Vtr. ohne Lehrer → Vertretung ohne Lehrer

Die verschiedenen Arten sollen farblich unterschiedlich dargestellt werden. Entfall soll z. B. durchgestrichen erscheinen.

## 21. Nachricht des Tages

`sensor.vertretungsplan` kann Nachrichten enthalten:

```yaml
weekday: Dienstag
date: 18.8.
news:
  - ...
```

Die Nachricht soll in `kfg-stundenplan-card` und `kfg-stundenplan-tag-card` angezeigt werden, aber nicht in `kfg-stundenplan-grid-card`.

Die Nachricht muss anhand von Wochentag und Datum zugeordnet werden. Der Vertretungsplan kann Daten für mehrere Wochen enthalten. Beim Wechsel auf die nächste Woche muss die passende Nachricht dieser Woche verwendet werden.

Wenn keine Nachricht vorhanden ist, darf kein leerer Nachrichtenblock angezeigt werden.

## 22. KFG Grid

Die KFG Grid Karte soll:

- Woche A/B anzeigen
- Vertretungen anzeigen
- Lehrer auflösen
- Fachkürzel korrekt zuordnen
- Raum anzeigen
- Kalenderinformationen anzeigen

Die Nachricht des Tages wird nicht angezeigt.

## 23. Arbeiten und Klausuren

Beide Grid-Karten sollen den Schulkalender auswerten.

Wenn in der aktuellen Woche ein Kalendereintrag mit `art = Arbeiten` oder `art = Klausuren` existiert, soll dessen `summary` im passenden Unterrichtsfach / Tag / Stunde angezeigt werden.

Beispiel: `Arbeit in Englisch 7n`.

Die Zuordnung muss auf den passenden Tag und möglichst auf das passende Fach bzw. die Unterrichtsstunde erfolgen.

Vorschlag für Farben:

- Arbeiten → orange
- Klausuren → rot

Die Funktion soll sowohl in `sph-stundenplan-grid-card` als auch `kfg-stundenplan-grid-card` funktionieren.

## 24. Title

Wenn in YAML kein `title:` angegeben ist, darf kein automatischer Titel wie `Tagesstundenplan MK` angezeigt werden. Nur bei explizitem `title` soll ein Titel erscheinen.

## 25. Installation / HACS

Die Integration muss HACS-kompatibel sein.

Wichtig:

- korrekte Version in `manifest.json`
- vollständige MIT-Lizenz
- `README.md`
- `info.md`
- HACS-relevante Repository-Struktur
- korrekte Releases/Tags
- Lovelace-JavaScript-Dateien korrekt registrieren
- keine fehlerhaften oder nicht unterstützten Dateien im Repository

Vor Abschluss:

- Git-Status prüfen
- Repository-Struktur prüfen
- Python-Syntax prüfen
- JavaScript-Syntax prüfen
- HACS-Validierung durchführen
- GitHub Actions prüfen

## 26. Dokumentation

`README.md` / `info.md`: nur wesentliche Informationen zu Installation, Konfiguration, Voraussetzungen, Sensoren und Lovelace-Karten.

Technische Architektur gehört in `docs/ARCHITEKTUR.md`.

KFG-spezifische Dokumentation gehört in `README-KFG.md` und beschreibt Voraussetzungen, `sensor.kfg_kollegium`, `sensor.vertretungsplan`, Konfiguration der kfg-* Karten und KFG-spezifische Funktionen.

Verweis auf:

https://github.com/leonsio/kfg-vertretungsplan

## 27. Coding-Regeln

Keine monolithische `client.py`.

Gemeinsame Funktionen → `api/`.

Stundenplan → `module/stundenplan/`.

Kalender → `module/kalender/`.

Mein Unterricht → `module/meinunterricht/`.

Sensorlogik möglichst in den jeweiligen Modulen. Coordinator ebenfalls im jeweiligen Modul. Lovelace-Karten getrennt halten. KFG-Code darf normale SPH-Karten nicht beeinflussen.

Keine manuellen YAML-Strings erzeugen, wenn strukturierte Daten serialisiert werden können. Alle Benutzer-/Schulportal-Daten korrekt escapen. Fehler abfangen. Bestehende erfolgreiche Daten bei temporären Fehlern erhalten.

## 28. Fehlerbehandlung

Folgende Fälle müssen sauber behandelt werden:

- Login fehlgeschlagen
- Login erfolgreich, aber Seite enthält keine erwarteten Daten
- Schulportal HTTP-Fehler
- Internet nicht erreichbar
- Session abgelaufen
- CSV leer
- iCal leer
- HTML-Struktur geändert
- Kalender nicht verfügbar
- Mein Unterricht nicht verfügbar
- KFG-Sensoren nicht vorhanden
- Sensorattribute zu groß
- ungültige/fehlende Termine
- ungültige Lehrer-/Fachkürzel

Ein Fehler in einem Modul darf andere Module nicht unbrauchbar machen.

## 29. Vorgehensweise

Arbeite inkrementell.

Vor jeder größeren Änderung:

1. bestehende Architektur analysieren
2. betroffene Dateien identifizieren
3. Änderung minimal halten
4. bestehende Funktionen nicht unnötig verändern
5. Tests/Validierungen durchführen

Nach jeder Änderung:

- Python-Syntax prüfen
- JavaScript-Syntax prüfen
- Imports prüfen
- Entity-Namen prüfen
- HACS-Kompatibilität prüfen
- Git-Diff kontrollieren

Besonders wichtig: Bestehende Funktionen wie Stundenplan, Kalender, Wochenkennung, KFG-Vertretungsplan und Lovelace-Karten dürfen durch neue Module nicht regressieren.

## 30. Anweisung für eine Coding-KI mit Repository-Zugriff

Arbeite direkt im vorhandenen Repository und analysiere zuerst den aktuellen Stand des Codes. Verwende nicht automatisch die oben beschriebene Struktur als Ersatz für den vorhandenen Code. Die beschriebene Struktur und Funktionalität dient als Soll-Zustand.

Vor Änderungen:

- Repository-Struktur untersuchen
- aktuelle Version feststellen
- bestehende Module und Imports prüfen
- aktuelle Lovelace-Karten prüfen
- vorhandene Tests und CI prüfen
- aktuelle README und `docs/ARCHITEKTUR.md` lesen

Bestehende Implementierungen haben Vorrang vor Annahmen aus diesem Prompt. Wenn der aktuelle Repository-Stand von der Beschreibung abweicht, analysiere die Abweichung und erhalte die bereits funktionierenden Funktionen.

Führe Änderungen direkt im Repository durch und erstelle nach erfolgreicher Validierung einen Commit mit einer aussagekräftigen Commit-Nachricht.
