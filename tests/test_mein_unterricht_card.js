/**
 * Offline-Test der Mein-Unterricht-Karte.
 *
 * HTMLElement, customElements und document werden minimal nachgebaut, damit die
 * Karte ohne Browser gegen echte Sensor-Attribute gerendert werden kann.
 *
 * Ausführen:  node tests/test_mein_unterricht_card.js
 */

const fs=require("fs"),path=require("path"),vm=require("vm");
const CARD=path.join(process.cwd(),"custom_components/sph/static/sph-mein-unterricht-card.js");
const esc={set textContent(v){this._t=v},get innerHTML(){return String(this._t).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}};
class HTMLElement{attachShadow(){this.shadowRoot={innerHTML:""};return this.shadowRoot}}
const reg=new Map();
const sb={HTMLElement,document:{createElement:()=>Object.create(esc)},customElements:{get:n=>reg.get(n),define:(n,c)=>reg.set(n,c)},window:{},Number,Array,Object,String,console};
sb.window=sb;sb.globalThis=sb;vm.createContext(sb);vm.runInContext(fs.readFileSync(CARD,"utf8"),sb);
const Card=reg.get("sph-mein-unterricht-card");
const ATTRS={kind:"Nias",anzahl:6,unerledigt:5,erledigt:1,faecher_offen:2,
 faecher:[{fach:"Mathematik",offen:2,erledigt:0,anzahl:2,lehrer:["SUL"],letzter_eintrag:"2026-08-24",offene_themen:["Diagramme"],status:"offen"},
          {fach:"Musik",offen:0,erledigt:1,anzahl:1,lehrer:["ABS"],letzter_eintrag:"2026-08-21",offene_themen:[],status:"erledigt"}],
 aufgaben:[{fach:"Mathematik",datum:"2026-08-24",thema:"Diagramme",aufgabe:"S. 26 Nr. 3",erledigt:false},
           {fach:"Musik",datum:"2026-08-21",thema:"Moorhexe",aufgabe:"<b>unterschreiben</b>",erledigt:true}]};
const states={"sensor.mein_unterricht_nias_nias":{entity_id:"sensor.mein_unterricht_nias_nias",attributes:ATTRS}};
function build(cfg,st){const c=new Card();c.setConfig(cfg);c.hass={states:st||states};return c}
const f=[];const ck=(l,c)=>{if(!c)f.push("  "+l)};
let h=build({entity:"sensor.mein_unterricht_nias_nias",title:"Mein Unterricht Nias"}).shadowRoot.innerHTML;
ck("Titel",h.includes('header="Mein Unterricht Nias"'));
ck("Zusammenfassung",h.includes("5 von 6 Einträgen offen")&&h.includes("2 Fächer betroffen"));
ck("Fächer",h.includes(">Mathematik<")&&h.includes(">Musik<"));
ck("Offen-Badge",h.includes('badge open">2 offen'));
ck("Erledigt-Badge",h.includes('badge done">erledigt'));
ck("Meta mit Lehrer und Datum",h.includes("SUL")&&h.includes("zuletzt 24.08."));
ck("Offene Themen",h.includes("Diagramme"));
ck("Erledigtes Fach abgeblendet",h.includes('class="subject complete"'));
h=build({entity:"sensor.mein_unterricht_nias_nias",only_open:true}).shadowRoot.innerHTML;
ck("only_open filtert Musik",!h.includes(">Musik<")&&h.includes(">Mathematik<"));
h=build({entity:"sensor.mein_unterricht_nias_nias",details:true}).shadowRoot.innerHTML;
ck("details zeigt Aufgabentext",h.includes("S. 26 Nr. 3"));
ck("details verbirgt Erledigte",!h.includes("Moorhexe"));
h=build({entity:"sensor.mein_unterricht_nias_nias",details:true,show_done:true}).shadowRoot.innerHTML;
ck("show_done zeigt Erledigte",h.includes("Moorhexe"));
ck("HTML escaped",!h.includes("<b>unterschreiben")&&h.includes("&lt;b&gt;"));
h=build({entity:"sensor.mein_unterricht_nias_nias"},{"sensor.mein_unterricht_nias_nias":{entity_id:"x",attributes:{anzahl:0}}}).shadowRoot.innerHTML;
ck("Alte Version ohne faecher wird gemeldet",h.includes("noch keine Fächer-Übersicht"));
h=build({entity:"sensor.gibt_es_nicht"}).shadowRoot.innerHTML;
ck("Fehlender Sensor",h.includes("Kein Mein-Unterricht-Sensor gefunden."));
if(f.length){console.log("FEHLGESCHLAGEN:\n"+f.join("\n"));process.exit(1)}
console.log("OK — Mein-Unterricht-Karte rendert Fächer, Status, Filter und Escaping korrekt.");
