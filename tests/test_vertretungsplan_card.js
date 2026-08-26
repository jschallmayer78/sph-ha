/**
 * Offline-Test der Vertretungsplan-Karte.
 *
 * Die Karte läuft im Browser, lässt sich aber ohne Browser prüfen: HTMLElement,
 * customElements und document werden hier minimal nachgebaut, dann wird gegen
 * echte Sensor-Attribute gerendert und das erzeugte HTML geprüft.
 *
 * Ausführen:  node tests/test_vertretungsplan_card.js
 */

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const CARD = path.join(
  __dirname,
  "..",
  "custom_components",
  "sph",
  "static",
  "sph-vertretungsplan-card.js"
);

function makeSandbox() {
  const registry = new Map();
  const escapeElement = {
    set textContent(value) {
      this._text = value;
    },
    get innerHTML() {
      return String(this._text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    },
  };

  class HTMLElement {
    attachShadow() {
      this.shadowRoot = { innerHTML: "" };
      return this.shadowRoot;
    }
  }

  const sandbox = {
    HTMLElement,
    document: { createElement: () => Object.create(escapeElement) },
    customElements: {
      get: (name) => registry.get(name),
      define: (name, cls) => registry.set(name, cls),
    },
    window: {},
    Intl,
    Date,
    Number,
    Array,
    Object,
    String,
    console,
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  return { sandbox, registry };
}

const PLAN = {
  kind: "Nias",
  "kind_kürzel": "Nias",
  aktualisiert: "2026-08-26T07:11:02",
  wird_aktualisiert: false,
  tage: [
    {
      datum: "2026-08-26",
      datum_de: "26.08.2026",
      wochentag: "Mittwoch",
      relativ: "heute",
      woche: "35. Woche",
      hinweise: ["Der Schulhof ist gesperrt."],
      eintraege: [
        {
          stunde: "5",
          klasse: "05cG",
          vertreter: "NN",
          lehrer: "",
          art: "Vertr",
          art_lang: "Vertretung",
          fach: "ETH",
          fach_lang: "Ethik",
          raum: "Spie",
          raum_alt: "b302",
          hinweis: "Spieleraum Ethikgruppe",
          stunden: [5],
          von_stunde: 5,
          bis_stunde: 5,
          entfall: false,
        },
        {
          stunde: "1 - 2",
          klasse: "05cG",
          vertreter: "",
          lehrer: "MUE",
          art: "Entf.",
          art_lang: "Entfall",
          fach: "M",
          fach_lang: "Mathematik",
          raum: "",
          raum_alt: "",
          hinweis: "",
          stunden: [1, 2],
          von_stunde: 1,
          bis_stunde: 2,
          entfall: true,
        },
      ],
    },
    {
      datum: "2026-08-27",
      datum_de: "27.08.2026",
      wochentag: "Donnerstag",
      relativ: "morgen",
      woche: "35. Woche",
      hinweise: [],
      eintraege: [],
    },
  ],
};

function buildCard(config, states) {
  const { sandbox, registry } = makeSandbox();
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(CARD, "utf8"), sandbox);
  const Card = registry.get("sph-vertretungsplan-card");
  const card = new Card();
  card.setConfig(config);
  card.hass = { states };
  return { card, html: card.shadowRoot.innerHTML, sandbox };
}

const failures = [];
function check(label, condition) {
  if (!condition) failures.push(`  ${label}`);
}

const states = {
  "sensor.vertretungsplan_nias_nias": { entity_id: "sensor.vertretungsplan_nias_nias", attributes: PLAN },
};

// --- Standardfall -------------------------------------------------------
{
  const { html, card } = buildCard(
    { entity: "sensor.vertretungsplan_nias_nias", title: "Vertretungsplan Nias" },
    states
  );
  check('Titel landet im ha-card header', html.includes('header="Vertretungsplan Nias"'));
  check("Beide Tage gerendert", html.includes("26.08.2026") && html.includes("27.08.2026"));
  check("Relativ-Badge", html.includes(">heute<") && html.includes(">morgen<"));
  check("Fach ausgeschrieben", html.includes(">Ethik<") && html.includes(">Mathematik<"));
  check("Stundenbereich 1.–2.", html.includes("1.–2."));
  check("Einzelstunde 5.", html.includes(">5.<"));
  check("Entfall markiert", html.includes('class="entry cancelled"') && html.includes('badge art out'));
  check("Ausgeschriebene Art statt Kürzel", html.includes(">Vertretung<") && !html.includes(">Vertr<"));
  check("Entfall durchgestrichen", html.includes(".entry.cancelled .subject{text-decoration:line-through"));
  check("Alter Raum durchgestrichen", html.includes('class="was">statt b302'));
  check("Hinweis der Schule", html.includes("Der Schulhof ist gesperrt."));
  check("Leerer Tag", html.includes("Keine Einträge"));
  check("Stand-Fußzeile", html.includes("Stand: 26.08.2026"));
  check("getCardSize > 1", card.getCardSize() > 1);
}

// --- only_cancellations -------------------------------------------------
{
  const { html } = buildCard(
    { entity: "sensor.vertretungsplan_nias_nias", only_cancellations: true },
    states
  );
  check("Nur Entfälle: Mathematik bleibt", html.includes("Mathematik"));
  check("Nur Entfälle: Ethik gefiltert", !html.includes("Ethik"));
}

// --- hide_empty ---------------------------------------------------------
{
  const { html } = buildCard(
    { entity: "sensor.vertretungsplan_nias_nias", hide_empty: true },
    states
  );
  check("hide_empty entfernt den leeren Tag", !html.includes("27.08.2026"));
}

// --- Automatische Sensorwahl über child --------------------------------
{
  const { html } = buildCard({ child: "Nias" }, states);
  check("Sensor über child gefunden", html.includes("26.08.2026"));
}

// --- Kein Sensor --------------------------------------------------------
{
  const { html } = buildCard({ entity: "sensor.gibt_es_nicht" }, states);
  check("Fehlender Sensor wird sauber gemeldet", html.includes("Kein Vertretungsplan-Sensor gefunden."));
}

// --- XSS ----------------------------------------------------------------
{
  const evil = JSON.parse(JSON.stringify(PLAN));
  evil.tage[0].eintraege[0].hinweis = '<img src=x onerror="alert(1)">';
  const { html } = buildCard(
    { entity: "sensor.vertretungsplan_nias_nias" },
    { "sensor.vertretungsplan_nias_nias": { entity_id: "x", attributes: evil } }
  );
  check("HTML aus Portaldaten wird escaped", !html.includes("<img src=x") && html.includes("&lt;img"));
}

if (failures.length) {
  console.log("FEHLGESCHLAGEN:");
  console.log(failures.join("\n"));
  process.exit(1);
}
console.log("OK — Vertretungsplan-Karte rendert Tage, Entfälle, Filter und Escaping korrekt.");
