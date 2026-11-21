"""Shared base: one Home Assistant device per vehicle."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CarLinkCoordinator


class CarLinkEntity(CoordinatorEntity[CarLinkCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: CarLinkCoordinator, vehicle_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.vehicle_id = vehicle_id
        self._attr_unique_id = f"{vehicle_id}_{key}"
        v = self.vehicle
        info = v.get("VehicleImageInfo") or {}
        model = " ".join(x for x in (info.get("Year"), info.get("Make"), info.get("Model")) if x) or None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vehicle_id)},
            name=v.get("Name") or model or "Car",
            manufacturer="VOXX CarLink",
            model=model or v.get("ProductCode"),
            serial_number=v.get("SerialNumber"),
            sw_version=self.status.get("FWVersion"),
        )

    @property
    def vehicle(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get(self.vehicle_id, {}).get("vehicle", {})

    @property
    def status(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get(self.vehicle_id, {}).get("status", {})

    @property
    def aux(self) -> list[dict[str, Any]]:
        """Accessories set up in the CL7 app: [{"AuxilliaryOptionId", "CarCommand", "Position", "Label", "Icon"}]."""
        return [a for a in self.vehicle.get("Aux") or [] if isinstance(a.get("CarCommand"), int)]

    async def _command(self, command: int) -> None:
        await self.coordinator.client.send_command(
            self.vehicle_id, command, frozenset(a["CarCommand"] for a in self.aux))

    @property
    def available(self) -> bool:
        return super().available and self.vehicle_id in (self.coordinator.data or {})
