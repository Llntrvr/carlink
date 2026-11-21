"""Engine running, doors / trunk / hood open, module online. (The cloud's lock reading is left out: its
Status_Lock didn't match the car.)"""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import CarLinkEntity

# key, name, status field, device class, icon, invert, diagnostic
SENSORS = (
    ("engine", "Engine", "Status_Engine", BinarySensorDeviceClass.RUNNING, "mdi:engine", False, False),
    ("doors", "Doors", "Status_Doors", BinarySensorDeviceClass.DOOR, None, False, False),
    ("trunk", "Trunk", "Status_Trunk", BinarySensorDeviceClass.OPENING, "mdi:car-back", False, False),
    ("hood", "Hood", "Status_Hood", BinarySensorDeviceClass.OPENING, "mdi:car-select", False, False),
    ("online", "Module online", "IsOffline", BinarySensorDeviceClass.CONNECTIVITY, None, True, True),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    add(CarLinkBinarySensor(coordinator, vid, *s) for vid in coordinator.data for s in SENSORS)


class CarLinkBinarySensor(CarLinkEntity, BinarySensorEntity):
    def __init__(self, coordinator, vehicle_id, key, name, field, device_class, icon, invert, diagnostic) -> None:
        super().__init__(coordinator, vehicle_id, key)
        self._attr_name = name
        self._attr_device_class = device_class
        if icon:
            self._attr_icon = icon
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._field, self._invert = field, invert

    @property
    def is_on(self) -> bool | None:
        if self._field == "Status_Engine" and self.status.get("StartEvent") == "ENGINE_SHUTDOWN":
            return False                                  # the engine flag lags behind a shutdown
        value = self.status.get(self._field)
        if value is None:
            return None
        return (not value) if self._invert else bool(value)
