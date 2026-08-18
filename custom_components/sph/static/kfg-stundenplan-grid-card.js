const KFG_CHANGE_LABELS = {
  Betr: "Betreuung",
  Vertr: "Vertretung",
  Entf: "Entfall",
  Taus: "Tausch",
  Freis: "Freistunde",
  Raum: "Raumänderung",
  "Statt-Vertretung": "Statt-Vertretung",
  Paus: "Pausenaufsicht",
  SES: "Sonderunterricht",
  "Vtr. ohne Lehrer": "Vertretung ohne Lehrer"
};

class KfgStundenplanGridCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    const hass = this._hass;
    if (!hass || !this.config || !this.shadowRoot) return;

    const entity = this._findEntity(hass);
    const attrs = entity?.attributes || {};
    const sourceDays = Array.isArray(attrs.eigener_plan) ? attrs.eigener_plan.slice(0, 5) : [];
    const week = String(attrs.wochenkennung || "").trim().toUpperCase();
    const ctx = this._context(hass, attrs);
    const aliases = this._subjectAliases(sourceDays);
    const calendarEvents = this._calendarEvents(hass);
    const monday = this._monday(new Date());
    const names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"];
    const title = this.config.title || "";
    const header = title ? ` header="${this._esc(title)}"` : "";

    if (!entity) {
      this.shadowRoot.innerHTML = `<ha-card${header}><div class="error">Kein passender Stundenplan gefunden.</div></ha-card>`;
      return;
    }

    const days = sourceDays.map((day, dayIndex) =>
      (Array.isArray(day) ? day : []).filter(lesson => this._active(lesson, week))
        .map(lesson => this._applySubstitution(lesson, dayIndex, monday, ctx, aliases))
    );

    const maxPeriod = Math.max(8, ...days.flatMap(day =>
      day.map(lesson => this._periodEnd(lesson))
    ));
    const slots = this._buildSlots(days, maxPeriod);
    const table = this._renderTable(days, names, slots, monday, week, calendarEvents);

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; width: 100%; box-sizing: border-box; }
        ha-card { width: 100%; overflow: hidden; }
        .table-wrap { width: 100%; overflow-x: auto; }
        table { width: 100%; min-width: 1050px; border-collapse: collapse; table-layout: fixed; }
        th, td { border: 1px solid var(--divider-color); text-align: center; vertical-align: middle; box-sizing: border-box; }
        thead th { background: var(--secondary-background-color); padding: 8px 6px; font-weight: 700; }
        thead th:first-child { width: 15%; }
        .day-name { display: block; font-size: 1.05rem; }
        .day-date { display: block; margin-top: 2px; font-size: .8rem; color: var(--secondary-text-color); font-weight: 500; }
        .week { color: var(--primary-color); font-weight: 800; }
        tbody th { padding: 7px 4px; background: var(--secondary-background-color); }
        .period { display: block; font-size: 1rem; }
        .slot-time { display: block; margin-top: 4px; font-size: .82rem; font-weight: 400; white-space: nowrap; }
        td { padding: 8px 6px; }
        .lessons { display: flex; flex-direction: column; gap: 7px; width: 100%; }
        .lesson { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 52px; line-height: 1.25; }
        .subject { font-size: 1.05rem; font-weight: 700; }
        .teacher { margin-top: 3px; font-size: .9rem; color: var(--secondary-text-color); }
        .badge { display: inline-block; margin-left: 4px; padding: 2px 7px; border-radius: 999px; color: #fff; font-size: .72rem; font-weight: 700; white-space: nowrap; }
        .change-vertretung { background: var(--info-color, #2196f3); }
        .change-entfall { background: var(--error-color, #f44336); }
        .change-fachwechsel, .change-tausch { background: var(--warning-color, #ff9800); }
        .change-betreuung { background: #4caf50; }
        .change-freistunde { background: #757575; }
        .change-raumanderung { background: #9c27b0; }
        .change-statt-vertretung { background: #03a9f4; }
        .change-pausenaufsicht { background: #009688; }
        .change-sonderunterricht { background: #00acc1; }
        .change-vertretung-ohne-lehrer { background: #607d8b; }
        .changed { border-left: 4px solid var(--warning-color, #ff9800); padding-left: 7px; }
        .changed.change-vertretung { border-left-color: var(--info-color, #2196f3); }
        .changed.change-betreuung { border-left-color: #4caf50; }
        .changed.change-tausch { border-left-color: #ff9800; }
        .changed.change-raumanderung { border-left-color: #9c27b0; }
        .changed.change-statt-vertretung { border-left-color: #03a9f4; }
        .changed.change-pausenaufsicht { border-left-color: #009688; }
        .changed.change-sonderunterricht { border-left-color: #00acc1; }
        .changed.change-vertretung-ohne-lehrer { border-left-color: #607d8b; }
        .calendar-event { display: inline-block; margin-top: 5px; padding: 3px 7px; border-radius: 6px; color: #fff; font-size: .74rem; font-weight: 700; line-height: 1.2; max-width: 100%; box-sizing: border-box; }
        .calendar-arbeiten { background: var(--warning-color, #ff9800); }
        .calendar-klausuren { background: var(--error-color, #e53935); }
        .cancelled { text-decoration: line-through; opacity: .62; }
        .empty { color: var(--secondary-text-color); }
        .error { padding: 16px; color: var(--error-color); }
        @media (max-width: 700px) { table { min-width: 900px; } .subject { font-size: .95rem; } }
      </style>
      <ha-card${header}><div class="table-wrap">${table}</div></ha-card>`;
  }

  _renderTable(days, names, slots, monday, week, calendarEvents) {
    const covered = Array.from({ length: 5 }, () => new Set());
    let html = "<table><thead><tr><th>Stunde</th>";

    names.forEach((name, dayIndex) => {
      const date = new Date(monday);
      date.setDate(date.getDate() + dayIndex);
      html += `<th><span class="day-name">${this._esc(name)}</span><span class="day-date">${this._esc(this._date(date))}${week ? ` · Woche <span class="week">${this._esc(week)}</span>` : ""}</span></th>`;
    });
    html += "</tr></thead><tbody>";

    for (const slot of slots) {
      html += "<tr>";
      html += `<th><span class="period">${slot.index}.</span><span class="slot-time">${this._esc(slot.start || "")}${slot.end ? ` – ${this._esc(slot.end)}` : ""}</span></th>`;

      for (let dayIndex = 0; dayIndex < 5; dayIndex++) {
        if (covered[dayIndex].has(slot.index)) continue;
        const lessons = this._lessonsAt(days[dayIndex], slot.index);
        const span = this._spanFor(lessons, slot.index);
        for (let p = slot.index + 1; p < slot.index + span; p++) covered[dayIndex].add(p);
        const date = new Date(monday);
        date.setDate(date.getDate() + dayIndex);
        html += `<td${span > 1 ? ` rowspan="${span}"` : ""}>`;
        html += lessons.length ? this._renderLessons(lessons, date, calendarEvents) : '<span class="empty">–</span>';
        html += "</td>";
      }
      html += "</tr>";
    }

    return html + "</tbody></table>";
  }

  _renderLessons(lessons, date, calendarEvents) {
    return `<div class="lessons">${lessons.map(lesson => {
      const changeClass = lesson.changeClass || "";
      const classes = [changeClass ? `changed ${changeClass}` : "", lesson.cancelled ? "cancelled" : ""].filter(Boolean).join(" ");
      const events = this._calendarEventsForLesson(calendarEvents, date, lesson);
      return `<div class="lesson ${classes}"><div class="subject">${this._esc(lesson.displaySubject || lesson.fach || lesson.subject || "Unterricht")}</div>${lesson.changeLabel ? `<span class="badge ${changeClass}">${this._esc(lesson.changeLabel)}</span>` : ""}${events.map(event => `<span class="calendar-event ${event.cssClass}">${this._esc(event.summary)}</span>`).join("")}<div class="teacher">${this._esc(lesson.displayTeacher || lesson.teacher || "")}${lesson.room ? ` <span>· Raum: ${this._esc(lesson.room)}</span>` : ""}</div></div>`;
    }).join("")}</div>`;
  }

  _calendarEvents(hass) {
    const entity = Object.values(hass.states).find(state => state.entity_id.startsWith("sensor.schulkalender_") && Array.isArray(state.attributes?.termine));
    const events = entity?.attributes?.termine;
    if (!Array.isArray(events)) return [];
    return events.filter(event => ["arbeiten", "klausuren"].includes(this._norm(event.art)));
  }

  _calendarEventsForLesson(events, date, lesson) {
    return events.filter(event => {
      if (!this._eventOnDate(event, date)) return false;
      const summary = this._norm(event.summary);
      const subjects = [lesson.subject, lesson.fach, lesson.displaySubject].filter(Boolean).map(value => this._norm(value));
      const subjectMatch = subjects.some(subject => subject && (summary.includes(subject) || this._subjectWordsMatch(summary, subject)));
      if (subjectMatch) return true;
      if (event.all_day || !lesson.start || !lesson.end) return false;
      return this._eventOverlapsLesson(event, lesson);
    });
  }

  _subjectWordsMatch(summary, subject) {
    const words = String(subject).split(/\s+/).map(word => this._norm(word)).filter(word => word.length >= 2);
    return words.length > 0 && words.every(word => summary.includes(word));
  }

  _eventOnDate(event, date) {
    const start = this._dateValue(event.start), end = this._dateValue(event.end || event.start);
    if (!start) return false;
    const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const dayEnd = new Date(dayStart); dayEnd.setDate(dayEnd.getDate() + 1);
    return start < dayEnd && (end ? end > dayStart : start >= dayStart && start < dayEnd);
  }

  _eventOverlapsLesson(event, lesson) {
    const start = this._dateValue(event.start), end = this._dateValue(event.end || event.start);
    if (!start || !lesson.start || !lesson.end) return false;
    const lessonStart = this._timeToMinutes(lesson.start), lessonEnd = this._timeToMinutes(lesson.end);
    if (lessonStart === null || lessonEnd === null) return false;
    const eventStart = start.getHours() * 60 + start.getMinutes();
    const eventEnd = end ? end.getHours() * 60 + end.getMinutes() : eventStart;
    return eventStart < lessonEnd && eventEnd > lessonStart;
  }

  _dateValue(value) {
    if (!value) return null;
    const raw = String(value).trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      const [year, month, day] = raw.split("-").map(Number);
      return new Date(year, month - 1, day);
    }
    const date = new Date(raw);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  _applySubstitution(lesson, dayIndex, monday, ctx, aliases) {
    const base = { ...lesson, displaySubject: lesson.fach || lesson.subject || "Unterricht", displayTeacher: this._teacher(lesson.teacher, ctx.teachers), room: lesson.room || "" };
    if (!ctx.available || !ctx.entries.length || !lesson?.subject) return base;
    const date = new Date(monday);
    date.setDate(date.getDate() + dayIndex);
    const candidates = ctx.entries.filter(item => this._class(item, ctx.childClass) && this._dateMatch(item, date, dayIndex) && this._period(item.stunde, lesson) && this._subjectMatches(item, lesson, aliases));
    if (!candidates.length) return base;
    const item = candidates[0];
    const art = String(item.art || "").trim();
    const low = art.toLowerCase();
    const cancelled = low.includes("entfall") || low.includes("ausfall") || low.includes("frei");
    const changedSubject = item.fach || item.subject || lesson.fach || lesson.subject || "";
    const originalSubject = item.fach_original || item.subject_original || lesson.subject || lesson.fach || "";
    const fachwechsel = !cancelled && this._norm(changedSubject) !== this._norm(originalSubject);
    const changeLabel = fachwechsel ? "Fachwechsel" : (KFG_CHANGE_LABELS[art] || art || "Vertretung");
    const changeClass = this._className(changeLabel);
    return { ...base, displaySubject: cancelled ? base.displaySubject : this._displaySubject(changedSubject, aliases, lesson), displayTeacher: item.vertreter || item.lehrer_nach || item.teacher ? this._teacher(item.vertreter || item.lehrer_nach || item.teacher, ctx.teachers) : base.displayTeacher, room: item.raum || item.room || base.room, cancelled, changeLabel, changeClass };
  }

  _subjectMatches(item, lesson, aliases) {
    const values = [item.fach_original, item.subject_original, item.fach, item.subject].filter(Boolean).map(value => this._norm(value));
    const own = [lesson.subject, lesson.fach].filter(Boolean).flatMap(value => { const key = this._norm(value); return [key, ...(aliases[key]?.matches || [])]; });
    return values.some(value => own.includes(value));
  }

  _displaySubject(value, aliases, lesson) {
    const target = this._norm(value);
    if (target === this._norm(lesson.subject) && lesson.fach) return lesson.fach;
    if (aliases[target]?.label) return aliases[target].label;
    return String(value || lesson.fach || lesson.subject || "");
  }

  _subjectAliases(days) {
    const aliases = {};
    for (const day of days || []) for (const lesson of Array.isArray(day) ? day : []) {
      const subject = this._norm(lesson.subject), fach = this._norm(lesson.fach);
      if (!subject || !fach) continue;
      const label = String(lesson.fach || lesson.subject).trim();
      aliases[subject] = { matches: Array.from(new Set([...(aliases[subject]?.matches || []), subject, fach])), label };
      aliases[fach] = { matches: Array.from(new Set([...(aliases[fach]?.matches || []), subject, fach])), label };
    }
    return aliases;
  }

  _context(hass, attrs) {
    const plan = hass.states["sensor.vertretungsplan"], collegium = hass.states["sensor.kfg_kollegium"];
    return { available: !!(plan || collegium), entries: this._entries(plan?.attributes || {}), teachers: collegium?.attributes?.lehrer && typeof collegium.attributes.lehrer === "object" ? collegium.attributes.lehrer : {}, childClass: String(attrs.klasse || "").trim() };
  }

  _entries(attributes) {
    const result = [], walk = value => { if (Array.isArray(value)) return value.forEach(walk); if (!value || typeof value !== "object") return; if (this._looksLikeEntry(value)) result.push(value); Object.values(value).forEach(walk); };
    walk(attributes); return result;
  }

  _looksLikeEntry(value) { return !!(value && (value.fach || value.fach_original || value.subject) && (value.stunde || value.datum || value.art || value.vertreter || value.lehrer_nach)); }

  _active(lesson, week) {
    const badge = lesson?.badge;
    if (badge === null || badge === undefined || badge === "" || !week) return true;
    const values = Array.isArray(badge) ? badge : String(badge).split(/[,;/|]+/);
    return values.some(value => String(value).trim().toUpperCase() === week);
  }

  _lessonsAt(day, period) { return (Array.isArray(day) ? day : []).filter(lesson => { const index = Number(lesson?.index), duration = Math.max(1, Number(lesson?.duration) || 1); return Number.isFinite(index) && index <= period && period < index + duration; }); }
  _spanFor(lessons, period) { const starting = lessons.filter(lesson => Number(lesson?.index) === period); return starting.length ? Math.max(1, ...starting.map(lesson => Number(lesson.duration) || 1)) : 1; }
  _periodEnd(lesson) { const index = Number(lesson?.index), duration = Math.max(1, Number(lesson?.duration) || 1); return Number.isFinite(index) ? index + duration - 1 : 1; }

  _buildSlots(days, maxPeriod) {
    const byPeriod = new Map();
    for (const day of days) for (const lesson of Array.isArray(day) ? day : []) {
      const index = Number(lesson?.index), duration = Math.max(1, Number(lesson?.duration) || 1);
      if (!Number.isFinite(index)) continue;
      const start = this._timeToMinutes(lesson.start), end = this._timeToMinutes(lesson.end);
      if (start !== null && end !== null && end > start && duration > 1) {
        const length = (end - start) / duration;
        for (let offset = 0; offset < duration; offset++) { const period = index + offset; if (!byPeriod.has(period)) byPeriod.set(period, { start: this._minutesToTime(start + length * offset), end: this._minutesToTime(start + length * (offset + 1)) }); }
      } else if (!byPeriod.has(index)) byPeriod.set(index, { start: lesson.start || "", end: lesson.end || "" });
    }
    const slots = [];
    for (let index = 1; index <= maxPeriod; index++) { const current = byPeriod.get(index) || { start: "", end: "" }; slots.push({ index, start: current.start, end: current.end }); }
    return slots;
  }

  _timeToMinutes(value) { if (typeof value !== "string") return null; const match = value.trim().match(/^(\d{1,2}):(\d{2})/); return match ? Number(match[1]) * 60 + Number(match[2]) : null; }
  _minutesToTime(value) { const minutes = Math.round(value); return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`; }

  _dateMatch(item, date, dayIndex) {
    if (!item?.datum) return false;
    const value = String(item.datum).trim().toLowerCase();
    const names = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag"];
    const weekdayIndex = names.indexOf(value);
    if (weekdayIndex >= 0) return weekdayIndex === dayIndex + 1;
    const match = value.match(/(\d{1,2})[.\/-](\d{1,2})(?:[.\/-](\d{2,4}))?/);
    if (!match) return false;
    if (Number(match[1]) !== date.getDate() || Number(match[2]) !== date.getMonth() + 1) return false;
    return !match[3] || Number(match[3]) === date.getFullYear() || Number(match[3]) === date.getFullYear() % 100;
  }

  _period(value, lesson) {
    if (!value || !lesson) return true;
    const numbers = String(value).match(/\d+/g)?.map(Number).filter(number => number > 0 && number < 20) || [], index = Number(lesson.index);
    if (!numbers.length || !Number.isFinite(index)) return true;
    if (numbers.length === 2 && /[-–—]/.test(String(value))) { const range = []; for (let number = numbers[0]; number <= numbers[1]; number++) range.push(number); return range.includes(index); }
    return numbers.includes(index);
  }

  _class(item, childClass) { if (!childClass || !item?.klasse) return false; const wanted = this._norm(childClass); return String(item.klasse).split(/[,;/|]+/).some(value => this._norm(value) === wanted); }

  _teacher(value, map) {
    if (!value) return "";
    const raw = String(value).trim(), wanted = raw.toLocaleLowerCase("de-DE");
    const key = Object.keys(map || {}).find(item => String(item).trim().toLocaleLowerCase("de-DE") === wanted);
    return key ? map[key] : raw;
  }

  _className(value) { return this._norm(value).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }
  _norm(value) { return String(value ?? "").trim().toLowerCase().replace(/ä/g, "a").replace(/ö/g, "o").replace(/ü/g, "u").replace(/ß/g, "ss").replace(/[^a-z0-9]+/g, ""); }
  _monday(date) { const result = new Date(date.getFullYear(), date.getMonth(), date.getDate()), day = result.getDay(); result.setDate(result.getDate() + (day === 0 ? -6 : 1 - day)); return result; }
  _date(date) { return new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date); }

  _findEntity(hass) {
    const configured = this.config.sensor || this.config.entity;
    if (configured && hass.states[configured]) return hass.states[configured];
    if (!this.config.child) return hass.states["sensor.stundenplan"];
    const wanted = String(this.config.child).toLowerCase();
    return Object.values(hass.states).find(state => state.entity_id.startsWith("sensor.") && state.attributes?.kind_kürzel?.toString().toLowerCase() === wanted);
  }

  _esc(value) { const div = document.createElement("div"); div.textContent = String(value ?? ""); return div.innerHTML; }
  getCardSize() { return 10; }
  getGridOptions() { return { columns: "full", min_columns: 12, rows: 8, min_rows: 5 }; }
}

if (!customElements.get("kfg-stundenplan-grid-card")) customElements.define("kfg-stundenplan-grid-card", KfgStundenplanGridCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "kfg-stundenplan-grid-card")) window.customCards.push({ type: "kfg-stundenplan-grid-card", name: "KFG Stundenplan Raster (KFG Anpassung)", description: "Breiter Wochenstundenplan im Rasterformat mit KFG-Vertretungsplan" });
