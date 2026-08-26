// Compatibility and shared week-selection logic for KFG timetable cards.
//
// KFG A/B week rules:
// - A/B badges describe the week in which that lesson is active.
// - An unbadged lesson is the counterpart/fallback for the other week when
//   it shares a time slot with an explicitly badged lesson.
// - A lesson with a non-matching badge is never shown.
//
// Examples:
//   A + unbadged -> week A: A only, week B: unbadged only
//   B + unbadged -> week B: B only, week A: unbadged only
//   A + B        -> week A: A only, week B: B only
//   A only       -> week A: A, week B: nothing
//   B only       -> week B: B, week A: nothing
//   unbadged only -> shown in both weeks
(() => {
  const CARD_TAGS = [
    "kfg-stundenplan-card",
    "kfg-stundenplan-tag-card",
    "kfg-stundenplan-grid-card",
  ];

  const badgeValues = (badge) => {
    if (badge === null || badge === undefined || badge === "") return [];
    const values = Array.isArray(badge)
      ? badge
      : String(badge).split(/[,;/|]+/);
    return values
      .map((value) => String(value).trim().replace(/[()]/g, "").toUpperCase())
      .filter(Boolean);
  };

  const slotKey = (lesson) => {
    const start = String(lesson?.start || "").trim();
    const end = String(lesson?.end || "").trim();
    if (start || end) return `${start}|${end}`;
    return `${lesson?.index ?? ""}|${lesson?.duration ?? 1}`;
  };

  const filterDayForWeek = (day, week) => {
    const lessons = Array.isArray(day) ? day : [];
    const wanted = String(week || "").trim().toUpperCase();
    if (!wanted) return lessons.slice();

    const groups = new Map();
    const order = [];

    for (const lesson of lessons) {
      const key = slotKey(lesson);
      if (!groups.has(key)) {
        groups.set(key, []);
        order.push(key);
      }
      groups.get(key).push(lesson);
    }

    const result = [];
    for (const key of order) {
      const group = groups.get(key) || [];
      const matching = group.filter((lesson) => badgeValues(lesson?.badge).includes(wanted));
      const unbadged = group.filter((lesson) => badgeValues(lesson?.badge).length === 0);
      const hasExplicitBadges = group.some((lesson) => badgeValues(lesson?.badge).length > 0);

      if (matching.length) {
        // Current week has an explicit lesson. It replaces an unbadged
        // counterpart at this time slot.
        result.push(...matching);
      } else if (hasExplicitBadges) {
        // There are explicit A/B alternatives, but none for the current
        // week. In this case an unbadged lesson is the counterpart for the
        // other week. If there is no unbadged counterpart, the slot is empty.
        result.push(...unbadged);
      } else {
        // Purely generic lesson: active in every week.
        result.push(...unbadged);
      }
    }

    return result;
  };

  const filterDaysForWeek = (days, week) =>
    (Array.isArray(days) ? days : []).map((day) => filterDayForWeek(day, week));

  const findTimetableEntity = (card, hass) => {
    const configured = card?.config?.sensor || card?.config?.entity;
    if (configured && hass?.states?.[configured]) return hass.states[configured];

    const child = String(card?.config?.child || "").trim().toLowerCase();
    if (child) {
      const byChild = Object.values(hass?.states || {}).find((state) =>
        state?.entity_id?.startsWith("sensor.") &&
        String(state?.attributes?.kind_kürzel || "").trim().toLowerCase() === child
      );
      if (byChild) return byChild;
    }

    return Object.values(hass?.states || {}).find((state) =>
      state?.entity_id?.startsWith("sensor.stundenplan") &&
      Array.isArray(state?.attributes?.eigener_plan)
    );
  };

  const hassWithFilteredTimetable = (card, hass) => {
    const entity = findTimetableEntity(card, hass);
    if (!entity) return hass;

    const attrs = entity.attributes || {};
    const days = attrs.eigener_plan;
    const week = attrs.wochenkennung;
    if (!Array.isArray(days) || !week) return hass;

    const filteredDays = filterDaysForWeek(days, week);
    const filteredEntity = {
      ...entity,
      attributes: {
        ...attrs,
        eigener_plan: filteredDays,
      },
    };

    const states = {
      ...(hass.states || {}),
      [entity.entity_id]: filteredEntity,
    };

    const patchedHass = Object.create(Object.getPrototypeOf(hass));
    Object.assign(patchedHass, hass);
    patchedHass.states = states;
    return patchedHass;
  };

  const patchCard = (tagName) => {
    const apply = () => {
      const Card = customElements.get(tagName);
      if (!Card || Card.prototype.__kfgWeekSelectionPatched) return;

      // Keep the old alias required by kfg-stundenplan-card.
      if (
        tagName === "kfg-stundenplan-card" &&
        !Card.prototype._entity &&
        typeof Card.prototype._findEntity === "function"
      ) {
        Card.prototype._entity = Card.prototype._findEntity;
      }

      const descriptor = Object.getOwnPropertyDescriptor(Card.prototype, "hass");
      const originalSetter = descriptor?.set;
      if (typeof originalSetter !== "function") return;

      Object.defineProperty(Card.prototype, "hass", {
        configurable: descriptor.configurable !== false,
        enumerable: descriptor.enumerable === true,
        get: descriptor.get,
        set(hass) {
          originalSetter.call(this, hassWithFilteredTimetable(this, hass));
        },
      });

      Card.prototype.__kfgWeekSelectionPatched = true;
    };

    if (customElements.get(tagName)) {
      apply();
    } else {
      customElements.whenDefined(tagName).then(apply);
    }
  };

  CARD_TAGS.forEach(patchCard);
})();
