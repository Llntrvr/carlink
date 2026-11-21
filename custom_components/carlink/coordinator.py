"""Polls the vehicle list and each vehicle's last reported status."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CarLinkAuthError, CarLinkClient, CarLinkError
from .const import DOMAIN, SCAN_INTERVAL, SCAN_INTERVAL_RUNNING

_LOGGER = logging.getLogger(__name__)


class CarLinkCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """data = {vehicle_id: {"vehicle": {...}, "status": {...}}}"""

    def __init__(self, hass: HomeAssistant, client: CarLinkClient) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.client = client
        self._vehicles: list[dict[str, Any]] = []
        self._vehicles_age = 0

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            # The vehicle list rarely changes: refresh it every 20th poll.
            if not self._vehicles or self._vehicles_age >= 20:
                self._vehicles = await self.client.vehicles()
                self._vehicles_age = 0
            self._vehicles_age += 1
            data: dict[str, dict[str, Any]] = {}
            for v in self._vehicles:
                data[v["Id"]] = {"vehicle": v, "status": await self.client.status(v["Id"])}
        except CarLinkAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CarLinkError as err:
            raise UpdateFailed(str(err)) from err
        running = any(d["status"].get("Status_Engine") and d["status"].get("StartEvent") != "ENGINE_SHUTDOWN"
                      for d in data.values())
        self.update_interval = SCAN_INTERVAL_RUNNING if running else SCAN_INTERVAL
        return data
