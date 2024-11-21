"""Support for GPSLogger."""
from http import HTTPStatus
import logging

from aiohttp import web
import voluptuous as vol

from homeassistant.components import webhook
from homeassistant.components.device_tracker import ATTR_BATTERY
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_BATTERY_CHARGING,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_WEBHOOK_ID,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import (
    config_entry_flow,
    config_validation as cv,
    entity_registry as er,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ACCURACY,
    ATTR_ACTIVITY,
    ATTR_ALTITUDE,
    ATTR_DEVICE,
    ATTR_DIRECTION,
    ATTR_LAST_SEEN,
    ATTR_PROVIDER,
    ATTR_SPEED,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER]
TRACKER_UPDATE = f"{DOMAIN}_tracker_update"

DEFAULT_ACCURACY = 200
DEFAULT_BATTERY = -1


def _id(value: str) -> str:
    """Coerce id by removing '-'."""
    return value.replace("-", "")


WEBHOOK_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE): _id,
        vol.Required(ATTR_LATITUDE): cv.latitude,
        vol.Required(ATTR_LONGITUDE): cv.longitude,
        vol.Optional(ATTR_ACCURACY, default=DEFAULT_ACCURACY): vol.Coerce(float),
        vol.Optional(ATTR_ACTIVITY): cv.string,
        vol.Optional(ATTR_ALTITUDE): vol.Coerce(float),
        vol.Optional(ATTR_BATTERY, default=DEFAULT_BATTERY): vol.Coerce(float),
        vol.Optional(ATTR_BATTERY_CHARGING): cv.boolean,
        vol.Optional(ATTR_DIRECTION): vol.Coerce(float),
        vol.Optional(ATTR_LAST_SEEN): cv.datetime,
        vol.Optional(ATTR_PROVIDER): cv.string,
        vol.Optional(ATTR_SPEED): vol.Coerce(float),
    }
)


async def async_setup(hass: HomeAssistant, _: ConfigType) -> bool:
    """Set up integration."""
    hass.data[DOMAIN] = {"devices": set(), "warned_no_last_seen": False}
    ent_reg = er.async_get(hass)

    async def device_work_around(event: Event) -> None:
        """Work around for device tracker component deleting devices.

        Applies to HA versions prior to 2024.5:

        The device tracker component level code, at startup, deletes devices that are
        associated only with device_tracker entities. Not only that, it will delete
        those device_tracker entities from the entity registry as well. So, when HA
        shuts down, remove references to devices from our device_tracker entity registry
        entries. They'll get set back up automatically the next time our config is
        loaded (i.e., setup.)
        """
        for c_entry in hass.config_entries.async_entries(DOMAIN):
            for r_entry in er.async_entries_for_config_entry(ent_reg, c_entry.entry_id):
                ent_reg.async_update_entity(r_entry.entity_id, device_id=None)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, device_work_around)
    return True


async def handle_webhook(
    hass: HomeAssistant, webhook_id: str, request: web.Request
) -> web.Response:
    """Handle incoming webhook with GPSLogger request."""
    try:
        data = WEBHOOK_SCHEMA(dict(await request.post()))
    except vol.MultipleInvalid as error:
        return web.Response(
            text=error.error_message, status=HTTPStatus.UNPROCESSABLE_ENTITY
        )

    if ATTR_LAST_SEEN not in data and not hass.data[DOMAIN]["warned_no_last_seen"]:
        _LOGGER.warning(
            "HTTP Body does not contain %s. Consider adding it for better results. See "
            "https://github.com/pnbruckner/ha-gpslogger/blob/master/README.md",
            ATTR_LAST_SEEN,
        )
        hass.data[DOMAIN]["warned_no_last_seen"] = True

    attrs = {
        ATTR_ACTIVITY: data.get(ATTR_ACTIVITY),
        ATTR_ALTITUDE: data.get(ATTR_ALTITUDE),
        ATTR_BATTERY_CHARGING: data.get(ATTR_BATTERY_CHARGING),
        ATTR_DIRECTION: data.get(ATTR_DIRECTION),
        ATTR_LAST_SEEN: data.get(ATTR_LAST_SEEN),
        ATTR_PROVIDER: data.get(ATTR_PROVIDER),
        ATTR_SPEED: data.get(ATTR_SPEED),
    }

    device = data[ATTR_DEVICE]

    async_dispatcher_send(
        hass,
        TRACKER_UPDATE,
        device,
        (data[ATTR_LATITUDE], data[ATTR_LONGITUDE]),
        data[ATTR_BATTERY],
        data[ATTR_ACCURACY],
        attrs,
    )

    return web.Response(text=f"Setting location for {device}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure based on config entry."""
    webhook.async_register(
        hass, DOMAIN, "GPSLogger", entry.data[CONF_WEBHOOK_ID], handle_webhook
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async_remove_entry = config_entry_flow.webhook_async_remove_entry
