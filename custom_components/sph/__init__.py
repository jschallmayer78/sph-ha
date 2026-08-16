from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

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
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            lambda _event: hass.async_create_task(_register_lovelace_resources(hass)),
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import SphTimetableCoordinator
    from .kalender.coordinator import SphCalendarCoordinator

    timetable = SphTimetableCoordinator(hass, entry)
    await timetable.async_config_entry_first_refresh()
    calendar = SphCalendarCoordinator(hass, entry, timetable.client)
    await calendar.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "timetable": timetable,
        "calendar": calendar,
    }
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
