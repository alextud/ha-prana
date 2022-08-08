"""Support for Prana fan."""

from . import prana, DOMAIN, CONF_DEVICES, CONF_NAME, CLIENT, CONFIG, SIGNAL_UPDATE_PRANA

from datetime import datetime, timedelta
import logging
import math
from homeassistant.components.fan import (
    SUPPORT_SET_SPEED,
    SUPPORT_DIRECTION,
    SUPPORT_PRESET_MODE,
    FanEntity,
)

from homeassistant.const import STATE_OFF
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect
from homeassistant.util.percentage import (
    int_states_in_range,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)


_LOGGER = logging.getLogger(__name__)

SPEED_AUTO = "auto"
SPEED_MANUAL = "manual"
SPEED_RANGE = (1, 10)
#FAN_SPEEDS = [STATE_OFF, SPEED_AUTO, "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
# SCAN_INTERVAL = timedelta(seconds=60)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the PRANA device class for the hass platform."""
    entities = []
    for device in hass.data[DOMAIN][CONF_DEVICES]:
        name = device[CONFIG].get(CONF_NAME)
        entities.append(PranaFan(device[CLIENT], name))

    async_add_entities(entities, update_before_add=True)


class PranaFan(FanEntity):
    """Representation of a Prana fan."""
    def __init__(self, device, name):
        """Initialize the sensor."""
        self.device = device
        self._name = name
        self._state = None
        self._available = False

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return self.device.mac.replace(":", "")

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return state of the fan."""
        return self.device.isOn

    @property
    def available(self):
        """Return state of the fan."""
        return self.device.lastRead != None and (self.device.lastRead > datetime.now() - timedelta(minutes=5))

    @property
    def device_state_attributes(self):
        """Provide attributes for display on device card."""
        attributes = { 
            "co2": self.device.co2,
            "voc": self.device.voc,
            "auto_mode": self.device.isAutoMode,
            "night_mode": self.device.isNightMode,
            "thaw_on": self.device.isThawOn,
            "heater_on": self.device.isHeaterOn,
            "speed_in&out": self.device.speedInOut,
            "speed_in": self.device.speedIn,
            "speed_out": self.device.speedOut,
            "air_in": self.device.isAirInOn,
            "air_out": self.device.isAirOutOn,
            "last_updated": self.device.lastRead,
        }
        return attributes

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_SET_SPEED | SUPPORT_DIRECTION | SUPPORT_PRESET_MODE

    async def async_turn_on(self, speed: str = None, percentage=None, preset_mode=None, **kwargs) -> None:
        """Turn on the entity."""
        await self.device.powerOn()
        dispatcher_send(self.hass, SIGNAL_UPDATE_PRANA + self.device.mac)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        await self.device.powerOff()
        dispatcher_send(self.hass, SIGNAL_UPDATE_PRANA + self.device.mac)

    async def async_set_direction(self, direction: str):
        """Set the direction of the fan."""
        if direction == 'reverse':
            if not self.device.isAirInOn:
                await self.device.toogleAirInOff()

            await self.device.toogleAirOutOff()
        elif direction == 'forward':
            if not self.device.isAirOutOn:
                await self.device.toogleAirOutOff()

            await self.device.toogleAirInOff()

        dispatcher_send(self.hass, SIGNAL_UPDATE_PRANA + self.device.mac)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if preset_mode == SPEED_AUTO:
            await self.device.setAutoMode()
        else:
            await self.device.toogleAutoMode()

        dispatcher_send(self.hass, SIGNAL_UPDATE_PRANA + self.device.mac)

    @property
    def preset_modes(self):
        """Return state of the fan."""
        return [SPEED_MANUAL, SPEED_AUTO]

    @property
    def preset_mode(self) -> str:
        """Return preset mode of the fan."""
        if self.device.isAutoMode:
            return SPEED_AUTO
        else:
            return SPEED_MANUAL

    @property
    def percentage(self) -> int:
        """Return percentage of the fan."""
        return ranged_value_to_percentage(SPEED_RANGE, self.device.speed)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        _LOGGER.debug("Changing fan speed percentage to %s", percentage)

        if percentage == 0 or percentage == None:
            await self.device.powerOff()
        else:
            speed = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
            await self.device.setSpeed(speed)

        dispatcher_send(self.hass, SIGNAL_UPDATE_PRANA + self.device.mac)

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return int_states_in_range(SPEED_RANGE)

    @property
    def current_direction(self) -> str:
        """Fan direction."""
        if not self.device.speed:
            return None
        elif not self.device.isAirInOn:
            return "forward"
        elif not self.device.isAirOutOn:
            return "reverse"
        else:
            return "reverse & forward"

    @property
    def should_poll(self):
        """Do not poll."""
        return False

    async def async_added_to_hass(self):
        """Call to update fan."""
        async_dispatcher_connect(self.hass, SIGNAL_UPDATE_PRANA + self.device.mac, self._update_callback)

    @callback
    def _update_callback(self):
        """Call update method."""
        self.async_schedule_update_ha_state(True)


