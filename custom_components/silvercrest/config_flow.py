from typing import override
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
import voluptuous as vol

from .const import DOMAIN


class SilvercrestSwsA1FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION: int = 1
    CONNECTION_CLASS: str = config_entries.CONN_CLASS_LOCAL_POLL
    _errors: dict[str, str]

    def __init__(self):
        self._errors = {}

    @override
    async def async_step_user(self, user_input: dict[str, str] | None = None):
        self._errors = {}

        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_NAME): str, vol.Required(CONF_HOST): str}
            ),
            errors=self._errors,
        )
