"""Support for Prana fan."""

from . import prana, DOMAIN, CONF_DEVICES, CONF_NAME, CLIENT, CONFIG, SIGNAL_UPDATE_PRANA

from datetime import datetime, timedelta
import logging
from homeassistant.components.fan import (
    SPEED_HIGH,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_OFF,
    SUPPORT_SET_SPEED,
    SUPPORT_DIRECTION,
    FanEntity,
)

from homeassistant.const import STATE_OFF
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect

_LOGGER = logging.getLogger(__name__)

SPEED_AUTO = "auto"
FAN_SPEEDS = [STATE_OFF, SPEED_AUTO, "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
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
    def speed(self) -> str:
        """Return the current speed."""
        speed = self.device.speed
        if speed == 0:
            return STATE_OFF
        else:
            return str(speed)

    @property
    def speed_list(self) -> list:
        """Get the list of available speeds."""
        return FAN_SPEEDS

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_SET_SPEED | SUPPORT_DIRECTION

    def turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn on the entity."""
        if speed is None:
            self.device.powerOn()
        else:
            self.set_speed(speed)
        dispatcher_send(self.hass, SIGNAL_UPDATE_PRANA + self.device.mac)

    def turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        self.set_speed(SPEED_OFF)
        dispatcher_send(self.hass, SIGNAL_UPDATE_PRANA + self.device.mac)

    def set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        if speed == STATE_OFF:
            self.device.powerOff()
        elif speed == SPEED_AUTO:
            self.device.setAutoMode()
        else:
            self.device.setSpeed(int(speed))
        
        dispatcher_send(self.hass, SIGNAL_UPDATE_PRANA + self.device.mac)



    def set_direction(self, direction: str):
        """Set the direction of the fan."""
        if direction == 'reverse':
            if not self.device.isAirInOn:
                self.device.toogleAirInOff()

            self.device.toogleAirOutOff()
        elif direction == 'forward':
            if not self.device.isAirOutOn:
                self.device.toogleAirOutOff()

            self.device.toogleAirInOff()

        dispatcher_send(self.hass, SIGNAL_UPDATE_PRANA + self.device.mac)

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

    # @staticmethod
    # def _int_to_speed(speed: int):
    #     hex_speed = SPEED_OFF
    #     if speed > 7:
    #         hex_speed = SPEED_HIGH
    #     elif speed > 3:
    #         hex_speed = SPEED_MEDIUM
    #     elif speed > 0:
    #         hex_speed = SPEED_LOW
    #     return hex_speed



