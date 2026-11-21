"""Open trunk, plus one button per accessory set up in the CL7 app (the vehicle's "Aux" list), e.g. "Windows Roll Down".

Each press sends that accessory's own carCommand. Accessories added in the app show up after the integration
reloads. A button only sends the command; whether anything happens depends on how the module is wired.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CarLinkError
from .const import CMD_TRUNK, DOMAIN
from .entity import CarLinkEntity

# CL7 app icon names -> Material Design Icons
ICONS = {
    "config_windown": "mdi:arrow-down-bold-box-outline",
    "config_windup": "mdi:arrow-up-bold-box-outline",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = []
    for vid, data in coordinator.data.items():
        entities.append(CarLinkTrunkButton(coordinator, vid))
        for aux in data["vehicle"].get("Aux") or []:
            if isinstance(aux.get("CarCommand"), int):
                entities.append(CarLinkAuxButton(coordinator, vid, aux))
    add(entities)


class CarLinkAuxButton(CarLinkEntity, ButtonEntity):
    def __init__(self, coordinator, vehicle_id: str, aux: dict[str, Any]) -> None:
        key = aux.get("AuxilliaryOptionId") or f"cmd{aux['CarCommand']}"
        super().__init__(coordinator, vehicle_id, f"aux_{key}")
        self._car_command = aux["CarCommand"]
        self._attr_name = aux.get("Label") or f"Accessory {aux.get('Position', aux['CarCommand'])}"
        self._attr_icon = ICONS.get(aux.get("Icon"), "mdi:car-cog")
        self._attr_extra_state_attributes = {"car_command": self._car_command, "position": aux.get("Position")}

    @property
    def available(self) -> bool:
        # Gone from the app's list (removed there) -> unavailable until the integration reloads.
        return super().available and any(a.get("CarCommand") == self._car_command for a in self.aux)

    async def async_press(self) -> None:
        try:
            await self._command(self._car_command)
        except CarLinkError as err:
            raise HomeAssistantError(f"CarLink: {err}") from err


class CarLinkTrunkButton(CarLinkEntity, ButtonEntity):
    """Trunk / hatch release (carCommand 2), the CL7 app's trunk button."""

    _attr_name = "Open trunk"
    _attr_icon = "mdi:car-back"

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator, vehicle_id, "trunk_release")

    async def async_press(self) -> None:
        try:
            await self._command(CMD_TRUNK)
        except CarLinkError as err:
            raise HomeAssistantError(f"CarLink: {err}") from err
        await self.coordinator.async_request_refresh()
