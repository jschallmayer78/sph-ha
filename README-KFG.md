# KFG-Anpassung – Kaiserin Friedrich Gymnasium Bad Homburg

Diese Dokumentation beschreibt die **KFG-spezifischen Lovelace-Karten** der Schulportal-Hessen-Integration für das **Kaiserin Friedrich Gymnasium (KFG) in Bad Homburg**.

Die KFG-Karten sind eine zusätzliche Anpassung. Die normalen `sph-*`-Karten bleiben davon unberührt.

## Voraussetzungen

### 1. Schulportal-Hessen-Integration

Die Integration **Schulportal Hessen** muss über HACS installiert und eingerichtet sein.

Für das jeweilige Kind wird insbesondere ein Stundenplan-Sensor benötigt, beispielsweise:

```text
sensor.stundenplan_maxim_mk
```

Der Sensor sollte unter anderem die persönlichen Stunden, `wochenkennung`, `badge` sowie die Angaben zum Kind enthalten.

Die Klasse des Kindes wird von der Schulportal-Hessen-Integration aus dem Stundenplan übernommen und kann von den KFG-Karten zur Zuordnung von Vertretungen verwendet werden.

### 2. KFG-Vertretungsplan – optional

Für die erweiterten KFG-Funktionen kann zusätzlich die Erweiterung **KFG Vertretungsplan** installiert werden.

urlKFG Vertretungsplan – GitHub Repositoryhttps://github.com/leonsio/kfg-vertretungsplan

Wenn die Erweiterung installiert ist und die folgenden Sensoren bereitstellt, können die KFG-Karten zusätzliche Informationen einblenden:

```text
sensor.kfg_kollegium
sensor.vertretungsplan
```

Sind diese Sensoren nicht vorhanden oder nicht verfügbar, zeigen die KFG-Karten weiterhin den normalen persönlichen Stundenplan an.

## Installation

Die KFG-Karten werden zusammen mit der Schulportal-Hessen-Integration installiert und automatisch als Lovelace-Ressourcen registriert.

Es müssen daher keine zusätzlichen JavaScript-Dateien manuell als Ressource eingetragen werden.

Die beiden Karten heißen:

```text
custom:kfg-stundenplan-card
custom:kfg-stundenplan-tag-card
```

## Konfiguration

### Wochenkarte

```yaml
type: custom:kfg-stundenplan-card
entity: sensor.stundenplan_maxim_mk
title: Stundenplan Maxim
```

### Tageskarte

```yaml
type: custom:kfg-stundenplan-tag-card
entity: sensor.stundenplan_maxim_mk
title: Tagesplan Maxim
```

### Verfügbare Kartenparameter

| Parameter | Pflicht | Beschreibung |
|---|---:|---|
| `type` | Ja | `custom:kfg-stundenplan-card` oder `custom:kfg-stundenplan-tag-card` |
| `entity` | Nein | Stundenplan-Sensor des Kindes, z. B. `sensor.stundenplan_maxim_mk` |
| `sensor` | Nein | Alternative Bezeichnung für `entity` |
| `title` | Nein | Eigene Überschrift der Karte |
| `child` | Nein | Kürzel des Kindes als Fallback, wenn kein Sensor über `entity` angegeben ist |

Wird `entity` angegeben, sollte diese bevorzugt verwendet werden. Dadurch ist eindeutig festgelegt, welcher persönliche Stundenplan dargestellt wird.

## Funktionalität der KFG-Karten

### Kennzeichnung „KFG Anpassung"

Die KFG-Karten kennzeichnen ihre zusätzliche Funktionalität sichtbar mit **„KFG Anpassung“**.

### A-/B-Wochen

Die KFG-Karten berücksichtigen die `wochenkennung` des persönlichen Stundenplans.

Bei einer Unterrichtsstunde mit `badge` wird geprüft, ob die Stunde zur aktuellen Woche gehört. Beispielsweise:

```yaml
wochenkennung: B
```

und:

```yaml
badge: A
```

führt dazu, dass diese Stunde ausgeblendet wird.

Existieren zur gleichen Uhrzeit unterschiedliche Fächer für A- und B-Woche, wird ausschließlich das zur aktuellen Wochenkennung passende Fach dargestellt.

Stunden ohne `badge` gelten als reguläre Stunden und werden unabhängig von A/B angezeigt.

### Anzeige von Badges

Vorhandene Badges werden in Klammern dargestellt, damit sie nicht mit einer möglichen Gruppenzuordnung des Fachs verwechselt werden:

```text
Französisch 2 (A)
```

### Wochentag, Datum und Woche

Die Tages- und Wochenansicht zeigen die Wochenkennung zusammen mit dem Datum bzw. der Wochenüberschrift.

Beispiel:

```text
Dienstag 18.08.2026 · Woche B
```

### Nachricht des Tages

Die KFG-Karten können zusätzlich die **Nachricht des Tages** aus `sensor.vertretungsplan` oberhalb des Stundenplans anzeigen.

Die Nachricht wird nicht einfach anhand des Wochentags übernommen. Da der Vertretungsplan mehrere Wochen enthalten kann, werden **Wochentag und Datum gemeinsam** ausgewertet.

Beispiel eines Eintrags im Vertretungsplan:

```yaml
weekday: Dienstag
date: 18.8.
news:
  - JS E: 7.55 Uhr - Vorstellung der Jura-AG und Wirtschafts-AG
```

Die Nachricht erscheint damit nur am passenden Datum, beispielsweise am **Dienstag, 18.08.2026**. Nachrichten eines anderen Dienstags aus einer anderen Woche werden nicht übernommen.

Dies gilt auch für die Tageskarte: Wenn diese nach Unterrichtsende, am Wochenende oder bei einem unterrichtsfreien Tag auf den nächsten Unterrichtstag wechselt, wird die Nachricht für **das tatsächlich ausgewählte Datum** gesucht.

In der Wochenkarte wird für jeden dargestellten Wochentag separat das zugehörige Datum ermittelt und die dazu passende Nachricht angezeigt.

### Tageskarte

Die `kfg-stundenplan-tag-card` zeigt den für die aktuelle Anzeige relevanten Unterrichtstag.

Dabei gilt:

- Am regulären Schultag wird der aktuelle Tag angezeigt.
- Nach Ende der letzten Unterrichtsstunde des Tages wird auf den nächsten Unterrichtstag gewechselt.
- Am Samstag und Sonntag wird der nächste Unterrichtstag verwendet.
- Tage ohne Unterricht werden übersprungen.
- Die Entscheidung basiert auf den im persönlichen Stundenplan tatsächlich vorhandenen und für die aktuelle A/B-Woche gültigen Stunden.
- Die Nachricht des Tages wird immer passend zum tatsächlich ausgewählten Datum gesucht.

Die Karte aktualisiert ihre zeitabhängige Darstellung selbstständig.

## Integration mit dem KFG-Vertretungsplan

Wenn `sensor.vertretungsplan` und `sensor.kfg_kollegium` vorhanden sind, versucht die KFG-Karte die zusätzlichen Informationen automatisch einzubeziehen.

### Lehrernamen

Die Abkürzungen der Lehrkräfte aus dem Vertretungsplan werden anhand von `sensor.kfg_kollegium` aufgelöst.

Die Auflösung ist **nicht von der Groß-/Kleinschreibung abhängig**. Beispielsweise können `Drg`, `DRG` oder `drg` dem Eintrag

```text
DRG: S.Düring
```

zugeordnet werden.

### Vertretungen nur für passende Schülerstunden

Eine Vertretung wird nicht pauschal für alle Schüler angezeigt.

Die Karte prüft, ob das betroffene Fach zur entsprechenden Zeit tatsächlich im persönlichen Stundenplan des Kindes vorhanden ist. Dadurch werden Vertretungen für andere Gruppen ignoriert.

Beispiel:

- Gruppe 1: Ethik
- Gruppe 2: Religion
- Vertretungsplan enthält eine Änderung für Ethik

Die Änderung wird nur bei einem Kind angezeigt, dessen persönlicher Stundenplan zu dieser Zeit **Ethik** enthält.

### Arten von Vertretungen

Je nach Art der Änderung wird die Unterrichtsstunde entsprechend gekennzeichnet.

Insbesondere:

- **Entfall / Ausfall / Frei:** Unterricht wird durchgestrichen dargestellt.
- **Vertretung:** Die geänderte Stunde wird hervorgehoben und der Vertretungshinweis angezeigt.
- **Fachwechsel:** Das neue Fach wird angezeigt; das ursprüngliche Fach kann als „statt …“ kenntlich gemacht werden.

Die genaue Darstellung hängt von den Daten ab, die der Vertretungsplan bereitstellt.

## Beispiel einer KFG-Konfiguration

```yaml
type: vertical-stack
cards:
  - type: custom:kfg-stundenplan-tag-card
    entity: sensor.stundenplan_maxim_mk
    title: Tagesplan Maxim

  - type: custom:kfg-stundenplan-card
    entity: sensor.stundenplan_maxim_mk
    title: Wochenplan Maxim
```

## Unterschied zu den normalen SPH-Karten

Die Karten

```text
custom:sph-stundenplan-card
custom:sph-stundenplan-tag-card
```

werden durch die KFG-Anpassungen **nicht verändert**.

Nur die Karten

```text
custom:kfg-stundenplan-card
custom:kfg-stundenplan-tag-card
```

verwenden die zusätzlichen KFG-Funktionen wie:

- A-/B-Wochenfilterung anhand von `badge` und `wochenkennung`
- KFG-Kennzeichnung
- Auflösung von Lehrerkürzeln über `sensor.kfg_kollegium`
- optionale Verarbeitung von `sensor.vertretungsplan`
- Anzeige der zum Datum passenden Nachricht des Tages
- Berücksichtigung der persönlichen Unterrichtsgruppe
- Kennzeichnung von Entfall, Vertretung und Fachwechsel
- automatische Auswahl des relevanten Tages in der Tageskarte

Damit bleiben bestehende allgemeine SPH-Dashboards unverändert.

## Fehler- und Fallback-Verhalten

Die KFG-Funktionen setzen die KFG-Vertretungsplan-Integration nicht voraus.

Fehlen `sensor.kfg_kollegium` oder `sensor.vertretungsplan`, wird der persönliche Stundenplan trotzdem dargestellt. Die zusätzlichen KFG-Informationen werden lediglich nicht ergänzt.

Auch unbekannte Lehrerkürzel werden nicht verworfen. Wenn keine Zuordnung gefunden wird, bleibt das vorhandene Kürzel erhalten.

## Hinweis

Diese KFG-Anpassungen sind auf die Verwendung am **Kaiserin Friedrich Gymnasium in Bad Homburg** ausgerichtet. Sie sind nicht Bestandteil des allgemeinen Schulportal-Hessen-Datenmodells und sollten entsprechend als standortspezifische Erweiterung betrachtet werden.
