"""Setup screen: CL7 email and password, checked by logging in."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CarLinkAuthError, CarLinkClient, CarLinkError
from .const import DOMAIN

SCHEMA = vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str})


class CarLinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()
            client = CarLinkClient(async_get_clientsession(self.hass), username, user_input[CONF_PASSWORD])
            try:
                await client.login()
            except CarLinkAuthError:
                errors["base"] = "invalid_auth"
            except (CarLinkError, Exception):  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=username, data={CONF_USERNAME: username, CONF_PASSWORD: user_input[CONF_PASSWORD]})
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        return await self.async_step_user()
