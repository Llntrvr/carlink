"""Remote start as a lock: unlocked = engine running (remote started), locked = engine off.

Unlock sends carCommand 3 (remote start), lock sends 4 (stop). Modelled as a lock so starting the car is
treated as a sensitive action: Google Assistant asks for its PIN before unlocking, and dashboards confirm.
This never touches the car's door locks.
"""
from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CarLinkError
from .const import CMD_START, CMD_STOP, DOMAIN
from .entity import CarLinkEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    add(CarLinkRemoteStart(coordinator, vid) for vid in coordinator.data)


class CarLinkRemoteStart(CarLinkEntity, LockEntity):
    _attr_name = "Remote start"

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator, vehicle_id, "remote_start_lock")
        self._pending: str | None = None          # "unlocking" (starting) or "locking" (stopping)

    @property
    def _running(self) -> bool:
        s = self.status
        return bool(s.get("Status_Engine")) and s.get("StartEvent") != "ENGINE_SHUTDOWN"

    @property
    def is_locked(self) -> bool:
        return not self._running

    @property
    def is_unlocking(self) -> bool:
        return self._pending == "unlocking"

    @property
    def is_locking(self) -> bool:
        return self._pending == "locking"

    @property
    def icon(self) -> str:
        return "mdi:car-key" if self._running else "mdi:car-off"

    async def async_unlock(self, **kwargs: Any) -> None:
        await self._send(CMD_START, "unlocking", want_running=True)

    async def async_lock(self, **kwargs: Any) -> None:
        await self._send(CMD_STOP, "locking", want_running=False)

    async def _send(self, command: int, pending: str, want_running: bool) -> None:
        self._pending = pending
        self.async_write_ha_state()
        try:
            await self.coordinator.client.send_command(self.vehicle_id, command)
            # The module reports back within seconds; refresh until the engine state follows (up to ~1 min).
            for wait in (6, 8, 10, 15, 20):
                await asyncio.sleep(wait)
                await self.coordinator.async_request_refresh()
                if self._running == want_running:
                    break
        except CarLinkError as err:
            raise HomeAssistantError(f"CarLink: {err}") from err
        finally:
            self._pending = None
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
