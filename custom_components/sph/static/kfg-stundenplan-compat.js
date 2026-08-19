// Compatibility patch for older cached versions of kfg-stundenplan-card.
// The current card contains _findEntity(), while some generated/cached
// versions still call _entity(). Keep the alias outside the card itself so
// the existing card implementation remains untouched.
(() => {
  const patch = () => {
    const Card = customElements.get("kfg-stundenplan-card");
    if (!Card || Card.prototype._entity) return;
    if (typeof Card.prototype._findEntity === "function") {
      Card.prototype._entity = Card.prototype._findEntity;
    }
  };

  if (customElements.get("kfg-stundenplan-card")) {
    patch();
  } else {
    customElements.whenDefined("kfg-stundenplan-card").then(patch);
  }
})();
