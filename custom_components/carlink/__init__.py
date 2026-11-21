"""Unofficial CarLink (VOXX CL7) integration: remote start / stop and status. Never touches the door locks.

Talks to the same cloud as the CL7 app (AWS Cognito login, api.mybrandedapp.com). Remote start is a lock
entity (unlock = start, carCommand 3; lock = stop, 4); sensors read the module's last reported status.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CarLinkAuthError, CarLinkClient, CarLinkError
from .const import DOMAIN
from .coordinator import CarLinkCoordinator

PLATFORMS = [Platform.LOCK, Platform.BINARY_SENSOR, Platform.SENSOR, Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = CarLinkClient(async_get_clientsession(hass), entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    try:
        await client.login()
    except CarLinkAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except CarLinkError as err:
        raise ConfigEntryNotReady(str(err)) from err
    coordinator = CarLinkCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
