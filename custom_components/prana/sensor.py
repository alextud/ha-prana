"""Support for Prana sensor."""
from datetime import timedelta
import logging

from . import prana, DOMAIN, CONF_DEVICES, CONF_NAME, CONF_MEDIAN, CLIENT, CONFIG, SIGNAL_UPDATE_PRANA, SENSOR_TYPES, CONF_MONITORED_CONDITIONS

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

# SCAN_INTERVAL = timedelta(seconds=300)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Prana sensor."""

    entities = []
    for device in hass.data[DOMAIN][CONF_DEVICES]:
        config = device[CONFIG]

        for parameter in config[CONF_MONITORED_CONDITIONS]:
            name = SENSOR_TYPES[parameter][0]
            unit = SENSOR_TYPES[parameter][1]
            icon = SENSOR_TYPES[parameter][2]
            median = config.get(CONF_MEDIAN)
            prefix = config.get(CONF_NAME)
            if prefix:
                name = f"{prefix} {name}"

            entities.append(
                PranaSensor(device[CLIENT], parameter, name, unit, icon, median)
            )

    async_add_entities(entities)


class PranaSensor(Entity):
    """Implementing the Prana sensor."""

    def __init__(self, device, parameter, name, unit, icon, median):
        """Initialize the sensor."""
        self.device = device
        self.parameter = parameter
        self._unit = unit
        self._icon = icon
        self._name = name
        self._state = None
        self._available = False
        self.data = []
        # Median is used to filter out outliers. median of 3 will filter
        # single outliers, while  median of 5 will filter double outliers
        # Use median_count = 1 if no filtering is required.
        self.median_count = median

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon

    async def async_update(self):
        """
        Update current conditions.

        This uses a rolling median over 3 values to filter out outliers.
        """
        data = self.device.sensorValue(self.parameter)

        if data is not None:
            _LOGGER.debug("%s = %s", self.name, data)
            self._available = True
            self.data.append(data)
        else:
            _LOGGER.info("Did not receive any data from Prana sensor %s", self.name)
            # Remove old data from median list or set sensor value to None
            # if no data is available anymore
            if self.data:
                self.data = self.data[1:]
            else:
                self._state = None
            return

        if len(self.data) > self.median_count:
            self.data = self.data[1:]

        if len(self.data) == self.median_count:
            median = sorted(self.data)[int((self.median_count - 1) / 2)]
            # _LOGGER.debug("Median is: %s", median)
            self._state = median
        elif self._state is None:
            # _LOGGER.debug("Set initial state")
            self._state = self.data[0]
        else:
            _LOGGER.debug("Not yet enough data for median calculation")

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