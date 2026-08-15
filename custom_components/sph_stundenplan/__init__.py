from .const import DOMAIN

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    from .coordinator import SphTimetableCoordinator
    coordinator = SphTimetableCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass, entry):
    unload = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload
