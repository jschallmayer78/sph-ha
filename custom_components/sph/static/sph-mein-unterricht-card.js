class SphMeinUnterrichtCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  static getStubConfig(hass) {
    const entity = Object.values(hass?.states || {}).find((state) =>
      state.entity_id.startsWith("sensor.mein_unterricht_")
    );
    return { entity: entity ? entity.entity_id : "sensor.mein_unterricht" };
  }

  getCardSize() {
    const count = this._subjects().length;
    return count ? 1 + count : 3;
  }

  // ------------------------------------------------------------------
  // Data
  // ------------------------------------------------------------------

  _entity() {
    const hass = this._hass;
    if (!hass) return null;
    const configured = this.config.entity || this.config.sensor;
    if (configured) return hass.states[configured] || null;

    const candidates = Object.values(hass.states).filter(
      (state) =>
        state.entity_id.startsWith("sensor.mein_unterricht_") &&
        Array.isArray(state.attributes?.faecher)
    );
    if (!this.config.child) return candidates[0] || null;
    const wanted = this._norm(this.config.child);
    return (
      candidates.find(
        (state) =>
          this._norm(state.attributes?.kind_kürzel) === wanted ||
          this._norm(state.attributes?.kind) === wanted
      ) || null
    );
  }

  _subjects() {
    const attrs = this._entity()?.attributes || {};
    let subjects = Array.isArray(attrs.faecher) ? attrs.faecher.slice() : [];
    if (this.config.only_open) subjects = subjects.filter((subject) => subject.offen > 0);
    return subjects;
  }

  _tasksFor(subject) {
    const attrs = this._entity()?.attributes || {};
    const tasks = Array.isArray(attrs.aufgaben) ? attrs.aufgaben : [];
    return tasks.filter(
      (task) => (task.fach || task.kurs || "Ohne Fach") === subject.fach
    );
  }

  // ------------------------------------------------------------------
  // Rendering
  // ------------------------------------------------------------------

  _render() {
    if (!this._hass || !this.config || !this.shadowRoot) return;

    const entity = this._entity();
    const attrs = entity?.attributes || {};
    const subjects = this._subjects();
    const title = this.config.title || "";
    const header = title ? ` header="${this._escapeAttr(title)}"` : "";

    let body;
    if (!entity) {
      body = `<div class="empty">Kein Mein-Unterricht-Sensor gefunden.</div>`;
    } else if (!Array.isArray(attrs.faecher)) {
      body = `<div class="empty">Dieser Sensor liefert noch keine Fächer-Übersicht. Integration aktualisieren.</div>`;
    } else if (!subjects.length) {
      body = `<div class="empty">${this._escape(
        this.config.only_open ? "Nichts offen." : "Keine Einträge vorhanden."
      )}</div>`;
    } else {
      body = `${this._renderSummary(attrs)}${subjects.map((s) => this._renderSubject(s)).join("")}`;
    }

    this.shadowRoot.innerHTML = `<style>${this._styles()}</style><ha-card${header}><div class="content">${body}</div></ha-card>`;
  }

  _renderSummary(attrs) {
    const open = Number(attrs.unerledigt || 0);
    const total = Number(attrs.anzahl || 0);
    const subjectsOpen = Number(attrs.faecher_offen || 0);
    const text = open
      ? `${open} von ${total} Einträgen offen · ${subjectsOpen} ${subjectsOpen === 1 ? "Fach" : "Fächer"} betroffen`
      : `Alle ${total} Einträge erledigt`;
    return `<div class="summary${open ? "" : " done"}">${this._escape(text)}</div>`;
  }

  _renderSubject(subject) {
    const open = Number(subject.offen || 0);
    const badge = open
      ? `<span class="badge open">${open} offen</span>`
      : `<span class="badge done">erledigt</span>`;

    const meta = [];
    if (subject.lehrer?.length) meta.push(subject.lehrer.join(", "));
    if (subject.anzahl) meta.push(`${subject.anzahl} ${subject.anzahl === 1 ? "Eintrag" : "Einträge"}`);
    if (subject.letzter_eintrag) meta.push(`zuletzt ${this._formatDate(subject.letzter_eintrag)}`);

    let detail = "";
    if (this.config.details) {
      const tasks = this._tasksFor(subject).filter((task) => this.config.show_done || !task.erledigt);
      detail = tasks
        .map(
          (task) => `<div class="task${task.erledigt ? " is-done" : ""}">
            <div class="task-head">${this._escape(this._formatDate(task.datum))} · ${this._escape(task.thema || "Ohne Thema")}</div>
            ${task.aufgabe ? `<div class="task-body">${this._escape(task.aufgabe)}</div>` : ""}
          </div>`
        )
        .join("");
    } else if (subject.offene_themen?.length) {
      detail = `<div class="topics">${subject.offene_themen
        .map((topic) => this._escape(topic))
        .join(" · ")}</div>`;
    }

    return `<div class="subject${open ? "" : " complete"}">
      <div class="line">
        <span class="name">${this._escape(subject.fach || "Ohne Fach")}</span>
        ${badge}
      </div>
      ${meta.length ? `<div class="meta">${this._escape(meta.join(" · "))}</div>` : ""}
      ${detail}
    </div>`;
  }

  _formatDate(value) {
    const raw = String(value || "");
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    return match ? `${match[3]}.${match[2]}.` : raw;
  }

  _styles() {
    return `
      :host{display:block}
      .content{padding:12px 16px}
      .summary{margin-bottom:10px;color:var(--secondary-text-color);font-size:.88rem}
      .summary.done{color:var(--success-color,#43a047)}
      .subject{padding:8px 0;border-bottom:1px solid var(--divider-color)}
      .subject:last-child{border-bottom:0}
      .subject.complete{opacity:.72}
      .line{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
      .name{font-weight:600}
      .badge{display:inline-flex;align-items:center;padding:1px 7px;border-radius:9px;font-size:.75rem;font-weight:600;white-space:nowrap}
      .badge.open{background:var(--error-color,#e53935);color:#fff}
      .subject:not(.complete) .name{color:var(--error-color,#e53935)}
      .badge.done{background:var(--secondary-background-color);color:var(--secondary-text-color)}
      .meta{color:var(--secondary-text-color);font-size:.82rem;margin-top:2px}
      .topics{color:var(--error-color,#e53935);font-size:.85rem;font-style:italic;margin-top:4px}
      .task{margin-top:6px;padding-left:9px;border-left:2px solid var(--error-color,#e53935)}
      .task.is-done{opacity:.6;border-left-color:var(--divider-color)}
      .task-head{font-size:.85rem}
      .task-body{color:var(--secondary-text-color);font-size:.82rem;white-space:pre-line;margin-top:1px}
      .empty{color:var(--secondary-text-color)}
    `;
  }

  _norm(value) {
    return String(value ?? "")
      .trim()
      .toLowerCase()
      .replace(/ä/g, "a")
      .replace(/ö/g, "o")
      .replace(/ü/g, "u")
      .replace(/ß/g, "ss")
      .replace(/[^a-z0-9]+/g, "");
  }

  _escape(value) {
    const div = document.createElement("div");
    div.textContent = String(value ?? "");
    return div.innerHTML;
  }

  _escapeAttr(value) {
    return this._escape(value).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
}

if (!customElements.get("sph-mein-unterricht-card")) {
  customElements.define("sph-mein-unterricht-card", SphMeinUnterrichtCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "sph-mein-unterricht-card")) {
  window.customCards.push({
    type: "sph-mein-unterricht-card",
    name: "SPH Mein Unterricht",
    description: "Übersicht der Fächer mit offenen und erledigten Einträgen",
  });
}
