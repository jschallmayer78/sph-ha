from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, CONF_CHILD_NAME, CONF_CHILD_SHORTCUT

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_URL = f"/api/{DOMAIN}/static/sph-stundenplan-card.js?v=0.2.6"


async def _register_lovelace_resource(hass: HomeAssistant) -> None:
    """Register the custom card as a Lovelace module resource."""
    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return

    resources = lovelace_data.resources
    if not hasattr(resources, "async_create_item"):
        return

    await resources.async_load()

    # Remove/normalize all previous versions of our card resource. This also
    # handles resources left behind by older releases using a different URL
    # or cache-busting query parameter.
    for resource in list(resources.async_items()):
        url = resource.get("url", "")
        base_url = url.split("?", 1)[0]
        if not base_url.endswith("/sph-stundenplan-card.js"):
            continue
        if url != CARD_URL or resource.get("res_type") != "module":
            await resources.async_update_item(
                resource["id"],
                {"url": CARD_URL, "res_type": "module"},
            )

    if not any(resource.get("url") == CARD_URL for resource in resources.async_items()):
        await resources.async_create_item({"res_type": "module", "url": CARD_URL})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    static_dir = Path(__file__).parent / "static"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"/api/{DOMAIN}/static", str(static_dir), False
            )
        ]
    )

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
