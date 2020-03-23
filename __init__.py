"""The prana component."""

from . import prana
import voluptuous as vol

DOMAIN = "prana"
CLIENT = "client"
CONFIG = "config"
SENSOR_TYPES = {
    "voc": ["VOC", "ppb", "mdi:gauge"],
    "co2": ["CO2", "ppm", "mdi:gauge"],
    
    # "temperature": ["Temperature", "°C", "mdi:thermometer"],
    # "humidity": ["Humidity", "%", "mdi:water-percent"],
    # "speed": ["Speed", None, "mdi:gauge"],
}
DEFAULT_MEDIAN = 3
CONF_MEDIAN = "median"

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.const import (
    CONF_MAC,
    CONF_DEVICES,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_SENSORS,
    CONF_SCAN_INTERVAL,
    EVENT_HOMEASSISTANT_START,
)


CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_NAME, default="Prana"): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL): cv.string,
        vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        ),
        vol.Optional(CONF_MEDIAN, default=DEFAULT_MEDIAN): cv.positive_int,
    })

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [CONNECTION_SCHEMA]), # array of mac, name
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):

    prana_data = hass.data[DOMAIN] = {}
    prana_data[CONF_DEVICES] = []

    conf = config.get(DOMAIN)

    if CONF_DEVICES not in conf:
        return True

    for device_conf in conf[CONF_DEVICES]:
        credentials = dict(device_conf)
        prana_data[CONF_DEVICES].append({})
        device = prana_data[CONF_DEVICES][-1]
        device[CLIENT] = prana.Prana(device_conf.get(CONF_MAC))
        device[CONFIG] = device_conf

    for platform in ["fan", "sensor"]:
        hass.async_create_task(
            async_load_platform(hass, platform, DOMAIN, {}, device_conf)
        )

    return True