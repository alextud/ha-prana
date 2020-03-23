"""Support for Prana fan."""

from . import prana, DOMAIN, CONF_DEVICES, CLIENT, CONFIG

from datetime import timedelta
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
from homeassistant.const import (
    CONF_FORCE_UPDATE,
    CONF_MAC,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    EVENT_HOMEASSISTANT_START,
)


from homeassistant.const import STATE_OFF
from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)

SPEED_AUTO = "auto"
FAN_SPEEDS = [STATE_OFF, SPEED_AUTO, "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
SCAN_INTERVAL = timedelta(seconds=60)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the PRANA device class for the hass platform."""
    # config.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL).total_seconds()
    # device = prana.Prana(config.get(CONF_MAC))
    # async_add_entities([PranaFan(device, "Prana")], update_before_add=True)

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
    def device_state_attributes(self):
        """Provide attributes for display on device card."""
        attributes = { 
            "co2": self.device.co2,
            "voc": self.device.voc,
            "auto mode": self.device.isAutoMode,
            "night mode": self.device.isNightMode,
            "thaw on": self.device.isThawOn,
            "heater on": self.device.isHeaterOn,
            "speed in & out": self.device.speedInOut,
            "speed in": self.device.speedIn,
            "speed out": self.device.speedOut,
            "air in on": self.device.isAirInOn,
            "air out on": self.device.isAirOutOn,
        }
        return attributes

    @property
    def speed(self) -> str:
        """Return the current speed."""
        # return self._int_to_speed(self.device.parameter_value("speed"))
        speed = self.device.speed
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
            speed = SPEED_AUTO
        self.set_speed(speed)

    def turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        self.set_speed(SPEED_OFF)

    def set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        if speed == STATE_OFF:
            self.device.powerOff()
        elif speed == SPEED_AUTO:
            self.device.toogleAuto()
        else:
            self.device.setSpeed(int(speed))




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

    def update(self):
        """Update state."""
        _LOGGER.debug("Updating fan state")
        self.device.getStatusDetails()

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



