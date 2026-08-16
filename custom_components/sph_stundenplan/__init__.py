from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, CONF_CHILD_NAME, CONF_CHILD_SHORTCUT

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_URL = f"/api/{DOMAIN}/static/sph-stundenplan-card.js"
DAILY_CARD_URL = f"/api/{DOMAIN}/static/sph-stundenplan-tag-card.js"
CARD_URLS = (CARD_URL, DAILY_CARD_URL)


async def _register_lovelace_resource(hass: HomeAssistant) -> None:
    """Register the custom cards in the dashboard resource collection.

    add_extra_js_url() makes the JavaScript available globally, but it does
    not create an entry under Settings > Dashboards > Resources. For HA
    2026.2+ we additionally register the files in Lovelace's storage-backed
    resource collection so they are visible and managed there as module
    resources.
    """
    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return

    resources = lovelace_data.resources
    if not hasattr(resources, "async_create_item"):
        return

    # ResourceStorageCollection is lazy-loaded in HA 2026.2. Loading it
    # before async_items()/async_create_item() prevents existing resources
    # from being lost or overwritten.
    if not getattr(resources, "loaded", True):
        await resources.async_load()
        resources.loaded = True

    existing = {}
    for resource in resources.async_items() or []:
        url = resource.get("url", "")
        base_url = url.split("?", 1)[0]
        for card_url in CARD_URLS:
            if base_url == card_url or base_url.endswith(card_url.rsplit("/", 1)[-1]):
                existing[card_url] = resource
                break

    for card_url in CARD_URLS:
        resource = existing.get(card_url)
        if resource is None:
            await resources.async_create_item({"url": card_url, "res_type": "module"})
            continue

        # Stored Lovelace resources use "type" while the create/update API
        # uses "res_type". Normalize old entries without creating duplicates.
        if resource.get("url") != card_url or resource.get("type") != "module":
            await resources.async_update_item(
                resource["id"],
                {"url": card_url, "res_type": "module"},
            )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    static_dir = Path(__file__).parent / "static"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(f"/api/{DOMAIN}/static", str(static_dir), False)]
    )

    # Keep this because it makes the cards available even before the Lovelace
    # resource collection has been initialized.
    add_extra_js_url(hass, CARD_URL)
    add_extra_js_url(hass, DAILY_CARD_URL)

    # Lovelace may not have initialized its resource collection yet when the
    # integration is set up. Register after startup in that case.
    if hass.is_running:
        hass.async_create_task(_register_lovelace_resource(hass))
    else:
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            lambda _event: hass.async_create_task(_register_lovelace_resource(hass)),
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import SphTimetableCoordinator
    coordinator = SphTimetableCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate entries and retain the new child identity fields."""
    if config_entry.version < 3:
        data = dict(config_entry.data)
        data.pop("class_name", None)
        data.setdefault(CONF_CHILD_NAME, "")
        data.setdefault(CONF_CHILD_SHORTCUT, "")
        hass.config_entries.async_update_entry(config_entry, data=data, version=3)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload
