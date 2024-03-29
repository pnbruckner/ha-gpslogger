"""Support for the GPSLogger device tracking."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import logging
from typing import Any, cast

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_BATTERY_CHARGING,
    ATTR_BATTERY_LEVEL,
    ATTR_GPS_ACCURACY,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import DOMAIN as GPL_DOMAIN, TRACKER_UPDATE
from .const import (
    ATTR_ACTIVITY,
    ATTR_ALTITUDE,
    ATTR_DIRECTION,
    ATTR_LAST_SEEN,
    ATTR_PROVIDER,
    ATTR_SPEED,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Configure a dispatcher connection based on a config entry."""

    @callback
    def _receive_data(
        device: str,
        gps: tuple[float, float],
        battery: float,
        accuracy: float,
        attrs: dict[str, Any],
    ) -> None:
        """Receive set location."""
        if device in hass.data[GPL_DOMAIN]["devices"]:
            return

        hass.data[GPL_DOMAIN]["devices"].add(device)

        async_add_entities([GPSLoggerEntity(device, gps, battery, accuracy, attrs)])

    entry.async_on_unload(async_dispatcher_connect(hass, TRACKER_UPDATE, _receive_data))

    # Restore previously loaded devices
    ent_reg = er.async_get(hass)
    dev_ids = {
        entity.unique_id
        for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    }
    if not dev_ids:
        return

    entities = []
    for dev_id in dev_ids:
        hass.data[GPL_DOMAIN]["devices"].add(dev_id)
        entity = GPSLoggerEntity(dev_id)
        entities.append(entity)

    async_add_entities(entities)


class GPSLoggerEntity(TrackerEntity, RestoreEntity):
    """Represent a tracked device."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        device: str,
        location: tuple[float, float] | None = None,
        battery: float | None = None,
        accuracy: float | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Set up GPSLogger entity."""
        self._accuracy = round(accuracy or 0)
        self._attributes = attributes or {}
        self._name = device
        self._battery = None if battery is None else int(battery)
        self._location = location
        self._unique_id = device
        self._prv_seen = cast(datetime | None, self._attributes.get(ATTR_LAST_SEEN))

    @property
    def battery_level(self) -> int | None:
        """Return battery value of the device."""
        return self._battery

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return device specific attributes."""
        return self._attributes

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self._location and self._location[0]

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self._location and self._location[1]

    @property
    def location_accuracy(self) -> int:
        """Return the gps accuracy of the device."""
        return self._accuracy

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID."""
        return self._unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(GPL_DOMAIN, self._unique_id)},
            name=self._name,
        )

    @property
    def source_type(self) -> SourceType | str:
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    async def async_added_to_hass(self) -> None:
        """Register state update callback."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, TRACKER_UPDATE, self._async_receive_data
            )
        )

        # don't restore if we got created with data
        if self._location is not None:
            return

        if (state := await self.async_get_last_state()) is None:
            self._location = None
            self._accuracy = 0
            self._attributes = {
                ATTR_ACTIVITY: None,
                ATTR_ALTITUDE: None,
                ATTR_BATTERY_CHARGING: None,
                ATTR_DIRECTION: None,
                ATTR_LAST_SEEN: None,
                ATTR_PROVIDER: None,
                ATTR_SPEED: None,
            }
            self._battery = None
            self._prv_seen = None
            return

        attr = state.attributes
        lat = cast(float | None, attr.get(ATTR_LATITUDE))
        lon = cast(float | None, attr.get(ATTR_LONGITUDE))
        if lat is not None and lon is not None:
            self._location = (lat, lon)
        else:
            self._location = None
        self._accuracy = round(attr.get(ATTR_GPS_ACCURACY) or 0)
        # Python datetime objects are saved/restored as strings.
        # Convert back to datetime object.
        restored_last_seen = cast(str | None, attr.get(ATTR_LAST_SEEN))
        if isinstance(restored_last_seen, str):
            last_seen = dt_util.parse_datetime(restored_last_seen)
        else:
            last_seen = None
        self._prv_seen = last_seen
        self._attributes = {
            ATTR_ACTIVITY: attr.get(ATTR_ACTIVITY),
            ATTR_ALTITUDE: attr.get(ATTR_ALTITUDE),
            ATTR_BATTERY_CHARGING: attr.get(ATTR_BATTERY_CHARGING),
            ATTR_DIRECTION: attr.get(ATTR_DIRECTION),
            ATTR_LAST_SEEN: last_seen,
            ATTR_PROVIDER: attr.get(ATTR_PROVIDER),
            ATTR_SPEED: attr.get(ATTR_SPEED),
        }
        battery = attr.get(ATTR_BATTERY_LEVEL)
        self._battery = None if battery is None else round(battery)

    @callback
    def _async_receive_data(
        self,
        device: str,
        location: tuple[float, float],
        battery: float,
        accuracy: float,
        attributes: dict[str, Any],
    ) -> None:
        """Mark the device as seen."""
        if device != self._name:
            return

        last_seen = cast(datetime | None, attributes.get(ATTR_LAST_SEEN))
        if self._prv_seen and last_seen and last_seen < self._prv_seen:
            _LOGGER.debug(
                "%s: Skipping update because last_seen went backwards: %s < %s",
                self.entity_id,
                last_seen,
                self._prv_seen,
            )
            return

        self._location = location
        self._battery = round(battery)
        self._accuracy = round(accuracy)
        self._attributes.update(attributes)
        self._prv_seen = last_seen
        self.async_write_ha_state()
