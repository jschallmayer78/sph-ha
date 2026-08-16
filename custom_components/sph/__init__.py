from __future__ import annotations

from pathlib import Path
import logging

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from .const import CONF_CHILD_NAME, CONF_CHILD_SHORTCUT, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_URLS = (
    f"/api/{DOMAIN}/static/sph-stundenplan-card.js",
    f"/api/{DOMAIN}/static/sph-stundenplan-tag-card.js",
)


async def _register_lovelace_resources(hass: HomeAssistant) -> None:
    data = hass.data.get(LOVELACE_DATA)
    if data is None:
        return
    resources = data.resources
    if not hasattr(resources, "async_create_item"):
        return
    if not getattr(resources, "loaded", True):
        await resources.async_load()
        resources.loaded = True
    items = resources.async_items() or []
    for url in CARD_URLS:
        found = next((r for r in items if r.get("url", "").split("?", 1)[0] == url), None)
        if found is None:
            await resources.async_create_item({"url": url, "res_type": "module"})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    static_dir = Path(__file__).parent / "static"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(f"/api/{DOMAIN}/static", str(static_dir), False)]
    )
    for url in CARD_URLS:
        add_extra_js_url(hass, url)

    if hass.is_running:
        hass.async_create_task(_register_lovelace_resources(hass))
    else:
        async def _on_started(_event):
            await _register_lovelace_resources(hass)

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)

    return True


async def _migrate_sensor_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Rename legacy generic sensor IDs to child-specific IDs.

    Older versions created sensor.stundenplan and sensor.schulkalender because
    the child was only stored as state attributes. Keep the same unique IDs but
    move those registry entries to the child-specific object IDs.
    """
    registry = er.async_get(hass)
    name = str(entry.data.get(CONF_CHILD_NAME, "")).strip()
    shortcut = str(entry.data.get(CONF_CHILD_SHORTCUT, "")).strip()
    child = "_".join(part for part in (name, shortcut) if part)
    suffix = slugify(child) if child else "schulportal_hessen"

    for unique_id, prefix in (
        (f"{entry.entry_id}_timetable", "stundenplan"),
        (f"{entry.entry_id}_calendar", "schulkalender"),
    ):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if not entity_id:
            continue
        desired = f"sensor.{prefix}_{suffix}"
        if entity_id == desired:
            continue
        if registry.async_get(desired):
            _LOGGER.warning(
                "Kann %s nicht in %s umbenennen, da die Ziel-Entity bereits existiert",
                entity_id,
                desired,
            )
            continue
        registry.async_update_entity(entity_id, new_entity_id=desired)
        _LOGGER.info("SPH: Entity %s in %s umbenannt", entity_id, desired)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import SphTimetableCoordinator
    from .kalender.coordinator import SphCalendarCoordinator

    timetable = SphTimetableCoordinator(hass, entry)
    try:
        await timetable.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.warning(
            "Schulportal Hessen Stundenplan für %s aktuell nicht verfügbar: %s",
            entry.title,
            err,
        )

    calendar = SphCalendarCoordinator(hass, entry, timetable.client)
    try:
        await calendar.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.warning(
            "Schulportal Hessen Kalender für %s aktuell nicht verfügbar: %s",
            entry.title,
            err,
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "timetable": timetable,
        "calendar": calendar,
    }
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    await _migrate_sensor_entity_ids(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
