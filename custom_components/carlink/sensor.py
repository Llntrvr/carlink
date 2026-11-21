"""Battery voltage, cabin temperature, remote-start time left, last start event, signal, last report."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfElectricPotential, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import CarLinkEntity


def _utc(value: Any) -> datetime | None:
    """The API's timestamps are UTC without a zone ("2026-11-21T01:34:44.95")."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:26]).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _volts(s: dict) -> float | None:
    mv = s.get("BatteryVoltage")
    return round(mv / 1000, 2) if isinstance(mv, (int, float)) else None


def _event(s: dict) -> str | None:
    e = s.get("StartEvent")
    if not isinstance(e, str) or e in ("", "0"):            # "0" = no start since the last report
        return None
    return e.replace("_", " ").capitalize()


# key, name, value, unit, device class, state class, icon, diagnostic
SENSORS: tuple[tuple[str, str, Callable[[dict], Any], Any, Any, Any, str | None, bool], ...] = (
    ("battery", "Battery", _volts, UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE,
     SensorStateClass.MEASUREMENT, "mdi:car-battery", False),
    ("cabin_temperature", "Cabin temperature", lambda s: s.get("InteriorTemperature"), UnitOfTemperature.CELSIUS,
     SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None, False),
    ("runtime_left", "Remote start time left",
     lambda s: 0 if s.get("StartEvent") == "ENGINE_SHUTDOWN" else s.get("Runtime_1s"), UnitOfTime.SECONDS,
     SensorDeviceClass.DURATION, None, "mdi:timer-outline", False),
    ("start_event", "Last start event", _event, None, None, None, "mdi:car-clock", False),
    ("signal", "Signal", lambda s: s.get("Rssi"), None, None, SensorStateClass.MEASUREMENT, "mdi:signal", True),
    ("last_report", "Last report", lambda s: _utc(s.get("CreatedDate")), None, SensorDeviceClass.TIMESTAMP,
     None, "mdi:update", True),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    add(CarLinkSensor(coordinator, vid, *s) for vid in coordinator.data for s in SENSORS)


class CarLinkSensor(CarLinkEntity, SensorEntity):
    def __init__(self, coordinator, vehicle_id, key, name, value, unit, device_class, state_class, icon, diagnostic):
        super().__init__(coordinator, vehicle_id, key)
        self._attr_name = name
        self._value = value
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        if icon:
            self._attr_icon = icon
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        return self._value(self.status)
