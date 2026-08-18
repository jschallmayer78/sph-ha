class SphStundenplanTagCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._timer = this._timer || null;
  }
  connectedCallback() { this._startTimer(); }
  disconnectedCallback() { this._stopTimer(); }
  set hass(hass) { this._hass = hass; this._render(); }
  _startTimer() { this._stopTimer(); this._timer = window.setInterval(() => this._render(), 30000); }
  _stopTimer() { if (this._timer !== null) { window.clearInterval(this._timer); this._timer = null; } }
  _render() {
    const hass = this._hass;
    if (!hass || !this.config || !this.shadowRoot) return;
    const entity = this._findEntity(hass), attrs = entity?.attributes || {}, days = Array.isArray(attrs.eigener_plan) ? attrs.eigener_plan : [], child = attrs.kind_kürzel || attrs.kind || this.config.child || "", title = this.config.title || "", header = title ? ` header="${this._escape(title)}"` : "", selected = this._getNextTeachingDay(days);
    this.shadowRoot.innerHTML = `<style>:host{display:block}.content{padding:12px 16px}.day-title{font-size:1.15rem;font-weight:600;margin-bottom:10px}.lesson{display:flex;gap:12px;padding:10px 0;border-bottom:1px solid var(--divider-color)}.lesson-options{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;flex:1}.time{min-width:92px;color:var(--secondary-text-color);white-space:nowrap}.main{display:flex;flex-direction:column;gap:2px}.main small{color:var(--secondary-text-color)}.badges{display:flex;gap:4px;flex-wrap:wrap;margin-top:3px}.badge{display:inline-flex;align-items:center;padding:1px 6px;border-radius:8px;background:var(--primary-color);color:var(--text-primary-color);font-size:.78rem;font-weight:600}.empty{color:var(--secondary-text-color)}</style><ha-card${header}><div class="content">${selected?`<div class="day-title">${this._formatDate(selected.date)}</div>${this._renderDay(selected.lessons)}`:`<div class="empty">Kein Unterricht geplant.</div>`}</div></ha-card>`;
  }
  _getNextTeachingDay(days) {
    const now = new Date(), today = now.getDay(), current = today === 0 ? 6 : today - 1, todayLessons = Array.isArray(days[current]) ? days[current] : [];
    if (today === 0 || today === 6 || !todayLessons.length) { for (let offset = 1; offset <= 7; offset++) { const index = (current + offset) % 7, lessons = Array.isArray(days[index]) ? days[index] : []; if (lessons.length) return this._selectionFor(index, lessons, now, offset); } return null; }
    const lastEnd = todayLessons.reduce((latest, lesson) => { const end = this._timeToMinutes(lesson?.end); return end !== null && (latest === null || end > latest) ? end : latest; }, null), nowMinutes = now.getHours() * 60 + now.getMinutes();
    if (lastEnd === null || nowMinutes < lastEnd) return this._selectionFor(current, todayLessons, now, 0);
    for (let offset = 1; offset <= 7; offset++) { const index = (current + offset) % 7, lessons = Array.isArray(days[index]) ? days[index] : []; if (lessons.length) return this._selectionFor(index, lessons, now, offset); }
    return null;
  }
  _selectionFor(index, lessons, now, offset) { const date = new Date(now.getFullYear(), now.getMonth(), now.getDate()); date.setDate(date.getDate() + offset); return { index, date, lessons }; }
  _formatDate(date) { return new Intl.DateTimeFormat("de-DE", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" }).format(date); }
  _timeToMinutes(value) { if (typeof value !== "string") return null; const match = value.trim().match(/^(\d{1,2}):(\d{2})/); if (!match) return null; const hours = Number(match[1]), minutes = Number(match[2]); if (hours > 23 || minutes > 59) return null; return hours * 60 + minutes; }
  _renderDay(day) { if (!day || !day.length) return `<span class="empty">Kein Unterricht</span>`; const groups = [], byTime = new Map(); for (const lesson of day) { const key = `${lesson.start || ""}|${lesson.end || ""}`; if (!byTime.has(key)) { const group = { start: lesson.start || "", end: lesson.end || "", lessons: [] }; byTime.set(key, group); groups.push(group); } byTime.get(key).lessons.push(lesson); } return groups.map(group => `<div class="lesson"><span class="time">${this._escape(group.start)}–${this._escape(group.end)}</span><div class="lesson-options">${group.lessons.map(lesson => `<div><span class="main"><b>${this._escape(lesson.fach || lesson.subject || "Unterricht")}</b>${this._renderBadges(lesson.badge)}<small>${this._escape(lesson.teacher || "")}${lesson.room ? " · " + this._escape(lesson.room) : ""}</small></span></div>`).join("")}</div></div>`).join(""); }
  _renderBadges(value) { if (value === null || value === undefined || value === "") return ""; const values = Array.isArray(value) ? value : String(value).split(/[,;/|]+/).map(x => x.trim()).filter(Boolean); return values.length ? `<span class="badges">${values.map(x => `<span class="badge">(${this._escape(x)})</span>`).join("")}</span>` : ""; }
  _findEntity(hass) { const configured = this.config.sensor || this.config.entity; if (configured && hass.states[configured]) return hass.states[configured]; if (!this.config.child) return hass.states["sensor.schulportal_hessen_stundenplan"]; const wanted = String(this.config.child).toLowerCase(); return Object.values(hass.states).find(state => state.entity_id.startsWith("sensor.") && state.attributes?.kind_kürzel?.toString().toLowerCase() === wanted); }
  _escape(value) { const div = document.createElement("div"); div.textContent = String(value ?? ""); return div.innerHTML; }
  getCardSize() { return 4; }
}
customElements.define("sph-stundenplan-tag-card", SphStundenplanTagCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "sph-stundenplan-tag-card", name: "SPH Tagesstundenplan", description: "Persönlicher Stundenplan für den aktuellen bzw. nächsten Unterrichtstag" });
