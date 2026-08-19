/*
 * Preserve horizontal scrolling for SPH/KFG grid cards.
 *
 * The grid cards rebuild their shadow DOM whenever Home Assistant supplies a
 * new hass object. Replacing the .table-wrap element resets scrollLeft to 0.
 * This small compatibility layer keeps the user's horizontal position across
 * those renders without changing the card implementations themselves.
 */
(() => {
  const patch = (tagName) => {
    const apply = (CardClass) => {
      if (!CardClass || CardClass.prototype.__sphScrollPreserverPatched) return;

      const originalRender = CardClass.prototype._render;
      if (typeof originalRender !== "function") return;

      CardClass.prototype._render = function (...args) {
        const oldWrap = this.shadowRoot?.querySelector?.(".table-wrap");
        const scrollLeft = oldWrap ? oldWrap.scrollLeft : 0;

        originalRender.apply(this, args);

        const newWrap = this.shadowRoot?.querySelector?.(".table-wrap");
        if (newWrap && scrollLeft > 0) {
          newWrap.scrollLeft = scrollLeft;
        }
      };

      CardClass.prototype.__sphScrollPreserverPatched = true;
    };

    const existing = customElements.get(tagName);
    if (existing) {
      apply(existing);
      return;
    }

    customElements.whenDefined(tagName).then(() => {
      apply(customElements.get(tagName));
    });
  };

  patch("sph-stundenplan-grid-card");
  patch("kfg-stundenplan-grid-card");
})();
