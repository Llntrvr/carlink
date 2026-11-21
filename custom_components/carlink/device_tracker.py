"""The car's last GPS position, from the module's status reports."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import CarLinkEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    add(CarLinkTracker(coordinator, vid) for vid in coordinator.data)


class CarLinkTracker(CarLinkEntity, TrackerEntity):
    _attr_name = "Location"
    _attr_icon = "mdi:car"

    def __init__(self, coordinator, vehicle_id) -> None:
        super().__init__(coordinator, vehicle_id, "location")

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        return self.status.get("GpsLocationLatitude")

    @property
    def longitude(self) -> float | None:
        return self.status.get("GpsLocationLongitude")

    @property
    def location_accuracy(self) -> int:
        return 20

    @property
    def extra_state_attributes(self) -> dict:
        s = self.status
        return {"speed": s.get("GpsSpeed"), "heading": s.get("GpsHeading"), "gps_time_utc": s.get("GpsDateTime")}
