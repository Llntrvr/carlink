"""Two locks per car.

Remote start: unlocked = engine running (remote started), locked = engine off. Unlock sends carCommand 3
(remote start), lock sends 4 (stop). Modelled as a lock so starting the car is treated as a sensitive action:
Google Assistant asks for its PIN before unlocking, and dashboards confirm.

Doors: lock sends carCommand 0, unlock sends 1. The cloud's own lock reading (Status_Lock) didn't match the
car, so the state is the last command this integration sent (assumed state, kept across restarts).
"""
from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .api import CarLinkError
from .const import CMD_LOCK, CMD_START, CMD_STOP, CMD_UNLOCK, DOMAIN
from .entity import CarLinkEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[LockEntity] = []
    for vid in coordinator.data:
        entities += [CarLinkRemoteStart(coordinator, vid), CarLinkDoorLock(coordinator, vid)]
    add(entities)


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
            await self._command(command)
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


class CarLinkDoorLock(CarLinkEntity, LockEntity, RestoreEntity):
    _attr_name = "Doors"
    _attr_assumed_state = True

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator, vehicle_id, "door_lock")
        self._locked: bool | None = None
        self._pending: str | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state in ("locked", "unlocked"):
            self._locked = last.state == "locked"

    @property
    def is_locked(self) -> bool | None:
        return self._locked

    @property
    def is_locking(self) -> bool:
        return self._pending == "locking"

    @property
    def is_unlocking(self) -> bool:
        return self._pending == "unlocking"

    @property
    def icon(self) -> str:
        return "mdi:car-door-lock" if self._locked is not False else "mdi:car-door"

    async def async_lock(self, **kwargs: Any) -> None:
        await self._send(CMD_LOCK, "locking", locked=True)

    async def async_unlock(self, **kwargs: Any) -> None:
        await self._send(CMD_UNLOCK, "unlocking", locked=False)

    async def _send(self, command: int, pending: str, locked: bool) -> None:
        self._pending = pending
        self.async_write_ha_state()
        try:
            await self._command(command)
            self._locked = locked
        except CarLinkError as err:
            raise HomeAssistantError(f"CarLink: {err}") from err
        finally:
            self._pending = None
            self.async_write_ha_state()
