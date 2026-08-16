from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.helpers import selector

from .const import CONF_SOURCE_ENTRY, DOMAIN


class SphCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        entries = self.hass.config_entries.async_entries("sph_stundenplan")
        if not entries:
            return self.async_abort(reason="no_timetable_account")

        if user_input is not None:
            source_id = user_input[CONF_SOURCE_ENTRY]
            source = self.hass.config_entries.async_get_entry(source_id)
            if source is None:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._schema(entries, source_id),
                    errors={"base": "invalid_account"},
                )

            await self.async_set_unique_id(f"calendar_{source_id}")
            self._abort_if_unique_id_configured()
            child = source.data.get("child_name") or source.title
            shortcut = source.data.get("child_shortcut", "")
            title = f"Schulkalender {child}"
            if shortcut:
                title += f" ({shortcut})"
            return self.async_create_entry(
                title=title,
                data={CONF_SOURCE_ENTRY: source_id},
            )

        return self.async_show_form(step_id="user", data_schema=self._schema(entries))

    @staticmethod
    def _schema(entries: list[ConfigEntry], current: str | None = None):
        options = [
            selector.SelectOptionDict(
                value=entry.entry_id,
                label=entry.title,
            )
            for entry in entries
        ]
        default = current or entries[0].entry_id
        return vol.Schema(
            {
                vol.Required(
                    CONF_SOURCE_ENTRY,
                    default=default,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SphCalendarOptionsFlow()


class SphCalendarOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        entries = self.hass.config_entries.async_entries("sph_stundenplan")
        if not entries:
            return self.async_abort(reason="no_timetable_account")
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={CONF_SOURCE_ENTRY: user_input[CONF_SOURCE_ENTRY]},
            )
            return self.async_create_entry(title="", data={})
        return self.async_show_form(
            step_id="init",
            data_schema=SphCalendarConfigFlow._schema(
                entries, self.config_entry.data.get(CONF_SOURCE_ENTRY)
            ),
        )
