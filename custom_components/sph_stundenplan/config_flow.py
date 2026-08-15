import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import DOMAIN, CONF_SCHOOL_ID, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL


class SphConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            if not user_input[CONF_SCHOOL_ID].isdigit():
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._schema(user_input),
                    errors={"base": "invalid_school_id"},
                )
            return self.async_create_entry(
                title=f"SPH {user_input[CONF_USERNAME]}",
                data=user_input,
            )
        return self.async_show_form(step_id="user", data_schema=self._schema())

    def _schema(self, values=None):
        values = values or {}
        return vol.Schema(
            {
                vol.Required(CONF_SCHOOL_ID, default=values.get(CONF_SCHOOL_ID, "")): str,
                vol.Required(CONF_USERNAME, default=values.get(CONF_USERNAME, "")): str,
                vol.Required(CONF_PASSWORD, default=values.get(CONF_PASSWORD, "")): str,
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=values.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
            }
        )
