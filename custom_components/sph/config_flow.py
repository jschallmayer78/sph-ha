from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import (
    CONF_CHILD_NAME,
    CONF_CHILD_SHORTCUT,
    CONF_SCHOOL_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)


class SphConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            if not user_input[CONF_SCHOOL_ID].isdigit():
                return self.async_show_form(step_id="user", data_schema=self._schema(user_input), errors={"base": "invalid_school_id"})
            user_input[CONF_CHILD_NAME] = user_input[CONF_CHILD_NAME].strip()
            user_input[CONF_CHILD_SHORTCUT] = user_input[CONF_CHILD_SHORTCUT].strip()
            if not user_input[CONF_CHILD_NAME] or not user_input[CONF_CHILD_SHORTCUT]:
                return self.async_show_form(step_id="user", data_schema=self._schema(user_input), errors={"base": "invalid_child"})
            return self.async_create_entry(
                title=f"Schulportal Hessen – {user_input[CONF_CHILD_NAME]} ({user_input[CONF_CHILD_SHORTCUT]})",
                data=user_input,
            )
        return self.async_show_form(step_id="user", data_schema=self._schema())

    def _schema(self, values: dict[str, Any] | None = None):
        values = values or {}
        return vol.Schema({
            vol.Required(CONF_CHILD_NAME, default=values.get(CONF_CHILD_NAME, "")): str,
            vol.Required(CONF_CHILD_SHORTCUT, default=values.get(CONF_CHILD_SHORTCUT, "")): str,
            vol.Required(CONF_SCHOOL_ID, default=values.get(CONF_SCHOOL_ID, "")): str,
            vol.Required(CONF_USERNAME, default=values.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD, default=values.get(CONF_PASSWORD, "")): str,
            vol.Required(CONF_UPDATE_INTERVAL, default=values.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
        })

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SphOptionsFlow()


class SphOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            data = dict(self.config_entry.data)
            data[CONF_CHILD_NAME] = user_input[CONF_CHILD_NAME].strip()
            data[CONF_CHILD_SHORTCUT] = user_input[CONF_CHILD_SHORTCUT].strip()
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=data,
                title=f"Schulportal Hessen – {data[CONF_CHILD_NAME]} ({data[CONF_CHILD_SHORTCUT]})",
            )
            return self.async_create_entry(title="", data={})
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required(CONF_CHILD_NAME, default=self.config_entry.data.get(CONF_CHILD_NAME, "")): str,
            vol.Required(CONF_CHILD_SHORTCUT, default=self.config_entry.data.get(CONF_CHILD_SHORTCUT, "")): str,
        }))
