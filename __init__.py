"""The prana component."""

from . import prana
import voluptuous as vol
import logging
from datetime import timedelta

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


SCAN_INTERVAL = timedelta(seconds=60)
DEFAULT_MEDIAN = 1
CONF_MEDIAN = "median"
SIGNAL_UPDATE_PRANA = "prana_update"

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import load_platform, async_load_platform
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import track_time_interval, call_later
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
        vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        ),
        vol.Optional(CONF_MEDIAN, default=DEFAULT_MEDIAN): cv.positive_int,
    })

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [CONNECTION_SCHEMA]), # array of mac, name
        vol.Optional(CONF_SCAN_INTERVAL): cv.time_period,
    })
}, extra=vol.ALLOW_EXTRA)


_LOGGER = logging.getLogger(__name__)

def setup(hass, config):

    prana_data = hass.data[DOMAIN] = {}
    prana_data[CONF_DEVICES] = []
    conf = config.get(DOMAIN)

    if CONF_DEVICES not in conf:
        return True

    scan_interval = conf.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL).total_seconds()

    for device_conf in conf[CONF_DEVICES]:
        prana_data[CONF_DEVICES].append({})
        device = prana_data[CONF_DEVICES][-1]
        mac = device_conf.get(CONF_MAC)
        device[CLIENT] = prana.Prana(mac)
        device[CONFIG] = device_conf

    for platform in ["fan", "sensor"]:
        load_platform(hass, platform, DOMAIN, {}, conf)

    for device in prana_data[CONF_DEVICES]:
        prana_client = device[CLIENT]

    def poll_device_update(event_time):
        """Update Prana device."""
        for device in prana_data[CONF_DEVICES]:
            prana_client = device[CLIENT]

            _LOGGER.debug("Updating Prana device... %s", prana_client.mac)
            if prana_client.getStatusDetails():
                _LOGGER.debug("Update success...")
                dispatcher_send(hass, SIGNAL_UPDATE_PRANA + prana_client.mac)
            else:
                _LOGGER.debug("Update failed...")

    track_time_interval(hass, poll_device_update, timedelta(seconds=scan_interval))
    call_later(hass, 0, poll_device_update) #trigger update now

    return True