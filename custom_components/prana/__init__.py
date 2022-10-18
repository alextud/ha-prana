"""The prana component."""

import asyncio
from . import prana
import voluptuous as vol
import logging
from datetime import timedelta
import threading

DOMAIN = "prana"
CLIENT = "client"
CONFIG = "config"
SENSOR_TYPES = {
    "voc": ["VOC", "ppb", "mdi:gauge"],
    "co2": ["CO2", "ppm", "mdi:gauge"],
    
    # "temperature": ["Temperature", "°C", "mdi:thermometer"],
    # "humidity": ["Humidity", "%", "mdi:water-percent"],
    "speed": ["Speed", "level", "mdi:gauge"],
}


SCAN_INTERVAL = timedelta(seconds=60)
DEFAULT_MEDIAN = 1
CONF_MEDIAN = "median"
SIGNAL_UPDATE_PRANA = "prana_update"

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import load_platform, async_load_platform
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_track_time_interval, call_later
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
        device[CLIENT] = prana.Prana(hass, mac)
        device[CONFIG] = device_conf

    for platform in ["fan", "sensor"]:
        load_platform(hass, platform, DOMAIN, {}, conf)

    for device in prana_data[CONF_DEVICES]:
        prana_client = device[CLIENT]

    async def device_update():
        """Update Prana device."""
        while True:
            for device in prana_data[CONF_DEVICES]:
                prana_client = device[CLIENT]

                _LOGGER.debug("Updating Prana device... %s", prana_client.mac)
                if await prana_client.getStatusDetails():
                    _LOGGER.debug("Update success...")
                    dispatcher_send(hass, SIGNAL_UPDATE_PRANA + prana_client.mac)
                else:
                    _LOGGER.debug("Update failed...")

            await asyncio.sleep(scan_interval)
    
    def poll_devices(time):
        hass.async_create_task(device_update())
    call_later(hass, 1, poll_devices) #trigger update now

    return True