# Schulportal Hessen für Home Assistant

Home-Assistant-Custom-Integration für Daten aus dem **Schulportal Hessen (SPH)**.

Die Installation erfolgt einmalig als Integration **Schulportal Hessen**. Sie umfasst aktuell die Module **Stundenplan**, **Schulkalender**, **Mein Unterricht** und **Vertretungsplan**.

## Installation über HACS

In HACS das Repository hinzufügen:

```text
https://github.com/jschallmayer78/sph-ha
```

Kategorie: **Integration**.

Anschließend unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Schulportal Hessen** suchen.

## Einrichtung

Für jedes Kind wird ein eigener Eintrag der Integration angelegt. Benötigt werden:

- Schulnummer
- SPH-Benutzername
- SPH-Passwort
- Name des Kindes
- Kürzel des Kindes
- Aktualisierungsintervall

Das Standard-Aktualisierungsintervall beträgt **60 Minuten** und kann nach der Einrichtung geändert werden. Auch Zugangsdaten, Schulnummer, Name und Kürzel können über die Konfiguration angepasst werden.

Die Zugangsdaten werden von den Modulen gemeinsam verwendet. Mehrere Kinder können als separate Einträge eingerichtet werden.

## Sensoren

Für ein Kind mit Name `Maxim` und Kürzel `Mk` entstehen beispielsweise:

```text
sensor.stundenplan_maxim_mk
sensor.schulkalender_maxim_mk
sensor.mein_unterricht_maxim_mk
sensor.vertretungsplan_maxim_mk
binary_sensor.erste_stunde_entfallt_heute_maxim_mk
binary_sensor.erste_stunde_entfallt_morgen_maxim_mk
calendar.schulkalender_maxim_mk
```

### Stundenplan

Der Stundenplan enthält unter anderem persönliche Stunden, Fach, Lehrkraft, Raum, Uhrzeit und Badge. Badges wie `A` oder `B` kennzeichnen wochenabhängige Stunden.

### Schulkalender

Der Kalender verwendet automatisch das aktuelle **hessische Schuljahr** und bevorzugt den CSV-Export des Schulportals. iCal wird als Fallback verwendet.

Termine enthalten unter anderem:

- `start`
- `end`
- `all_day`
- `summary`
- `description`
- `location`
- `art`
- `verantwortlich`
- `uid`

`art` und `verantwortlich` bleiben erhalten und können später zur Filterung verwendet werden.

### Vertretungsplan

Der Sensor `sensor.vertretungsplan_...` liest `vertretungsplan.php` und gibt als Zustand die Gesamtzahl der veröffentlichten Einträge zurück. Wichtige Attribute:

- `tage` – alle veröffentlichten Tage mit `datum`, `wochentag`, `relativ` (`heute`/`morgen`), `woche` (`A`/`B`) und `eintraege`
- `heute` und `morgen` – die Einträge des jeweiligen Tages, direkt für Templates nutzbar
- `anzahl_heute`, `anzahl_morgen`, `entfaelle_heute`, `entfaelle_morgen`
- `hinweise` – die „Allgemein"-Kästen des Plans
- `aktualisiert` – Zeitpunkt der letzten Planänderung laut Schulportal
- `wird_aktualisiert` – ob das Portal den Plan gerade neu aufbaut

Jeder Eintrag enthält `stunde`, `stunden` (aufgelöster Bereich, z. B. `1 - 2` → `[1, 2]`), `von_stunde`, `bis_stunde`, `klasse`, `vertreter`, `lehrer`, `art`, `fach`, `fach_alt`, `raum`, `hinweis` sowie zwei abgeleitete Felder:

- `art_lang` – die ausgeschriebene Art. Schulen kürzen die Spalte ab (`Vertr`, `Entf.`, `Freis`); hier steht dann `Vertretung`, `Entfall`, `Freistunde`. Der Rohwert bleibt in `art` erhalten.
- `entfall` – ob in dieser Stunde kein Unterricht stattfindet. Ausgewertet wird die aufgelöste Langform, damit `Entf` und `Entfall` gleich behandelt werden.

Die Spalten werden anhand des `data-field`-Attributs der Tabellenköpfe zugeordnet, nicht anhand ihrer Position. Schulen, die Spalten anders anordnen oder weglassen, werden dadurch mitgelesen.

### Erste Stunde entfällt

Zwei Binärsensoren werten den Vertretungsplan aus:

```text
binary_sensor.erste_stunde_entfallt_heute_maxim_mk
binary_sensor.erste_stunde_entfallt_morgen_maxim_mk
```

Bewusst zwei getrennte Entitäten statt einer Automatik, die je nach Uhrzeit rät, welcher Tag gemeint ist. Für „Wecker aus, wenn morgen die erste Stunde ausfällt" ist der `morgen`-Sensor der richtige.

Welche Stunde geprüft wird, lässt sich in der Konfiguration einstellen (Standard: 1). Solange die Schule für den betreffenden Tag noch keinen Plan veröffentlicht hat, ist der Sensor `unavailable` – nicht `off`. `off` würde „Unterricht findet statt" bedeuten, und das ist etwas anderes als „es steht noch nichts fest".

Beispielautomation:

```yaml
automation:
  - alias: Wecker aus, wenn erste Stunde entfällt
    triggers:
      - trigger: time
        at: "21:30:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.erste_stunde_entfallt_morgen_maxim_mk
        state: "on"
    actions:
      - action: switch.turn_off
        target:
          entity_id: switch.wecker_maxim
```

### Kalender-Entity

Zusätzlich zum Kalender-Sensor entsteht eine echte `calendar`-Entity:

```text
calendar.schulkalender_maxim_mk
```

Sie erscheint in der Kalenderansicht von Home Assistant und lässt sich in Automationen mit `calendar.get_events` sowie den Kalender-Triggern verwenden. Ganztagestermine werden dabei auf das von Home Assistant erwartete exklusive Enddatum umgerechnet.

## Lovelace-Karten

Stundenplan:

```yaml
type: custom:sph-stundenplan-card
entity: sensor.stundenplan_maxim_mk
title: Stundenplan Maxim
```

Vertretungsplan:

```yaml
type: custom:sph-vertretungsplan-card
entity: sensor.vertretungsplan_maxim_mk
title: Vertretungsplan Maxim
```

Optionen der Vertretungsplan-Karte:

| Option | Standard | Wirkung |
| --- | --- | --- |
| `entity` | – | Sensor des Kindes. Ohne Angabe wird über `child` gesucht, sonst der erste gefundene Vertretungsplan-Sensor genommen. |
| `child` | – | Alternative zu `entity`: Name oder Kürzel des Kindes. |
| `title` | – | Kartenüberschrift. |
| `days` | alle | Maximale Anzahl angezeigter Tage. |
| `hide_empty` | `false` | Tage ohne Einträge ausblenden. |
| `only_cancellations` | `false` | Nur Ausfälle zeigen, Vertretungen und Raumwechsel ausblenden. |

Ausfälle bekommen einen roten Balken und ein `Entfall`-Badge, Raumwechsel zeigen den alten Raum durchgestrichen daneben, und die „Allgemein"-Hinweise der Schule stehen über den Einträgen des jeweiligen Tages.

Tagesansicht:

```yaml
type: custom:sph-stundenplan-tag-card
entity: sensor.stundenplan_maxim_mk
title: Heute – Maxim
```

Die Karten werden von der Integration automatisch als Lovelace-Ressourcen registriert. Für Home Assistant 2026.2+ ist keine manuelle `/local/...`-Ressource erforderlich.

## Diagnose

Ob die eigene Schule den Vertretungsplan so ausliefert, wie der Parser ihn erwartet, lässt sich ohne Home Assistant prüfen:

```bash
pip install requests pycryptodome beautifulsoup4
python3 tools/sph_vertretung_check.py
```

Das Skript fragt die Zugangsdaten ab, ruft den Plan ab und zeigt, was daraus gelesen wurde. Mit `--dump-html datei.html` wird zusätzlich die entschlüsselte Rohseite gespeichert.

Die Parser-Tests laufen offline gegen ein Beispiel-HTML:

```bash
python3 tests/test_vertretung_parser.py
python3 tests/test_calendar_events.py
node tests/test_vertretungsplan_card.js
```

## Verhalten bei Verbindungsproblemen

Bei einem fehlgeschlagenen Abruf bleiben die zuletzt erfolgreich geladenen Daten erhalten. Sobald das Schulportal wieder erreichbar ist, werden die Daten beim nächsten erfolgreichen Aktualisierungsversuch aktualisiert.

## Hinweis

Dieses Projekt ist ein unabhängiges Community-Projekt und steht nicht in offizieller Verbindung mit dem Schulportal Hessen.

Weitere Informationen zur Quelltextstruktur befinden sich unter [`docs/ARCHITEKTUR.md`](docs/ARCHITEKTUR.md).
