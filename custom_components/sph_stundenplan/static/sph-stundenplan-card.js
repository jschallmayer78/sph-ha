class SphStundenplanCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.config || !this.shadowRoot) return;

    const entityId = this.config.sensor || this.config.entity || "sensor.schulportal_hessen_stundenplan";
    const entity = hass.states[entityId];
    const attrs = entity?.attributes || {};

    // The SPH sensor contains both the complete class timetable ("tage")
    // and the timetable assigned to the logged-in student ("eigener_plan").
    // This card deliberately displays only the student's personal timetable.
    const days = Array.isArray(attrs.eigener_plan) ? attrs.eigener_plan : [];
    const names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"];

    this.shadowRoot.innerHTML = `<style>
      :host{display:block} .content{padding:12px 16px} section{margin-bottom:16px} h3{margin:0 0 8px}.lesson{display:flex;gap:12px;padding:8px 0;border-bottom:1px solid var(--divider-color)}.time{min-width:92px;color:var(--secondary-text-color);white-space:nowrap}.main{display:flex;flex-direction:column;gap:2px}.main small{color:var(--secondary-text-color)}.empty{color:var(--secondary-text-color)}
    </style><ha-card header="${this.config.title || "Stundenplan"}"><div class="content">${days.slice(0,5).map((day,i)=>`<section><h3>${names[i]}</h3>${day.length ? day.map(x=>`<div class="lesson"><span class="time">${this._escape(x.start)}–${this._escape(x.end)}</span><span class="main"><b>${this._escape(x.subject || "Unterricht")}</b><small>${this._escape(x.teacher || "")}${x.room ? " · " + this._escape(x.room) : ""}</small></span></div>`).join("") : `<span class="empty">Kein Unterricht</span>`}</section>`).join("")}</div></ha-card>`;
  }

  _escape(value) {
    const d = document.createElement("div");
    d.textContent = String(value ?? "");
    return d.innerHTML;
  }

  getCardSize() { return 6; }
}

customElements.define("sph-stundenplan-card", SphStundenplanCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "sph-stundenplan-card",
  name: "SPH Stundenplan",
  description: "Persönlicher Stundenplan aus dem Schulportal Hessen",
});
