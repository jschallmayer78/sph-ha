class SphStundenplanTagCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.config || !this.shadowRoot) return;

    const entity = this._findEntity(hass);
    const attrs = entity?.attributes || {};
    const days = Array.isArray(attrs.eigener_plan) ? attrs.eigener_plan : [];
    const child = attrs.kind_kürzel || attrs.kind || this.config.child || "";
    const title = this.config.title || (child ? `Heute – ${child}` : "Heute");
    const selected = this._getNextTeachingDay(days);

    this.shadowRoot.innerHTML = `<style>
      :host{display:block}.content{padding:12px 16px}.day-title{font-size:1.15rem;font-weight:600;margin-bottom:10px}.lesson{display:flex;gap:12px;padding:10px 0;border-bottom:1px solid var(--divider-color)}.lesson:last-child{border-bottom:0}.time{min-width:92px;color:var(--secondary-text-color);white-space:nowrap}.lesson-options{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;flex:1}.lesson-option{min-width:0}.main{display:flex;flex-direction:column;gap:2px}.main small{color:var(--secondary-text-color)}.badges{display:flex;gap:4px;flex-wrap:wrap;margin-top:3px}.badge{display:inline-flex;align-items:center;padding:1px 6px;border-radius:8px;background:var(--primary-color);color:var(--text-primary-color);font-size:.78rem;font-weight:600}.empty{color:var(--secondary-text-color)}.error{padding:16px;color:var(--error-color)}
    </style><ha-card header="${this._escape(title)}"><div class="content">${selected ? `<div class="day-title">${selected.name}</div>${this._renderDay(selected.lessons)}` : `<div class="empty">Kein Unterricht geplant.</div>`}</div></ha-card>`;
  }

  _getNextTeachingDay(days) {
    const now = new Date();
    const today = now.getDay();
    const currentIndex = today === 0 ? 6 : today - 1;
    for (let offset = 0; offset < 7; offset++) {
      const index = (currentIndex + offset) % 7;
      const lessons = Array.isArray(days[index]) ? days[index] : [];
      if (lessons.length) {
        const names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"];
        return { index, name: names[index], lessons };
      }
    }
    return null;
  }

  _renderDay(day) {
    if (!day || !day.length) return `<span class="empty">Kein Unterricht</span>`;
    const groups = [];
    const byTime = new Map();
    for (const lesson of day) {
      const key = `${lesson.start || ""}|${lesson.end || ""}`;
      if (!byTime.has(key)) {
        const group = { start: lesson.start || "", end: lesson.end || "", lessons: [] };
        byTime.set(key, group);
        groups.push(group);
      }
      byTime.get(key).lessons.push(lesson);
    }
    return groups.map((group) => {
      const options = group.lessons.map((x) => `<div class="lesson-option"><span class="main"><b>${this._escape(x.fach || x.subject || "Unterricht")}</b>${this._renderBadges(x.badge)}<small>${this._escape(x.teacher || "")}${x.room ? " · " + this._escape(x.room) : ""}</small></span></div>`).join("");
      return `<div class="lesson"><span class="time">${this._escape(group.start)}–${this._escape(group.end)}</span><div class="lesson-options">${options}</div></div>`;
    }).join("");
  }

  _renderBadges(value) {
    if (value === null || value === undefined || value === "") return "";
    const values = Array.isArray(value) ? value : String(value).split(/[,;/|]+/).map((item) => item.trim()).filter(Boolean);
    if (!values.length) return "";
    return `<span class="badges">${values.map((badge) => `<span class="badge">(${this._escape(badge)})</span>`).join("")}</span>`;
  }

  _findEntity(hass) {
    const configured = this.config.sensor || this.config.entity;
    if (configured && hass.states[configured]) return hass.states[configured];
    if (!this.config.child) return hass.states["sensor.schulportal_hessen_stundenplan"];
    const wanted = String(this.config.child).toLowerCase();
    return Object.values(hass.states).find((state) => state.entity_id.startsWith("sensor.") && state.attributes?.kind_kürzel?.toString().toLowerCase() === wanted);
  }

  _escape(value) {
    const d = document.createElement("div");
    d.textContent = String(value ?? "");
    return d.innerHTML;
  }

  getCardSize() { return 4; }
}

customElements.define("sph-stundenplan-tag-card", SphStundenplanTagCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "sph-stundenplan-tag-card", name: "SPH Tagesstundenplan", description: "Persönlicher Stundenplan für den aktuellen bzw. nächsten Unterrichtstag" });
