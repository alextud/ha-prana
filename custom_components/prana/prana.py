import asyncio
from bleak import BleakClient

import binascii
import logging
import time
import struct
from datetime import datetime, timedelta
import threading
from multiprocessing import Process

_LOGGER = logging.getLogger(__name__)

DEFAULT_RETRY_COUNT = 2
DEFAULT_RETRY_TIMEOUT = .2

HANDLE = '0000cccc-0000-1000-8000-00805f9b34fb'
UUID = '0000baba-0000-1000-8000-00805f9b34fb'

deviceStatus = 'BEEF0501000000005A'
deviceDetails = 'BEEF0502000000005A'
powerOff     = "BEEF0401"
luminosity   = "BEEF0402"
heater       = "BEEF0405"
nightMode    = "BEEF0406"
maxSpeed     = "BEEF0407"
airOutOff    = "BEEF0410"
speedLocked  = "BEEF0409"
powerOn      = "BEEF040A"
speedDown    = "BEEF040B"
speedUp      = "BEEF040C"
airInOff     = "BEEF040D"
speedInUp    = "BEEF040E"
speedInDown  = "BEEF040F"
speedOutUp   = "BEEF0411"
speedOutDown = "BEEF0412"
thaw         = "BEEF0416"
autoMode     = "BEEF0418"

class Prana:
    """Representation of Prana."""

    def __init__(self, mac):
        self.mac = mac
        self.lastRead = None
        self.speed = None #calculated
        self.speedInOut = None
        self.speedIn = None
        self.speedOut = None
        self.co2 = None
        self.voc = None
        self.isAutoMode = None
        self.isNightMode = None
        self.isSpeedLocked = None
        self.isOn = None
        self.isHeaterOn = None
        self.isThawOn = None
        self.isAirInOn = None
        self.isAirOutOn = None

    def handleNotification (self, cHandle, data):
        #print (data)
        voc = int(struct.unpack_from(">h", data, 63)[0] & 0b0011_1111_1111_1111)
        co2 = int(struct.unpack_from(">h", data, 61)[0] & 0b0011_1111_1111_1111)
        #if (voc > 10000 or co2 > 15000):
        #	return #ingore invalid data

        self.voc = voc
        self.co2 = co2
        self.speedInOut = int(data[26] / 10)
        self.speedIn = int(data[30] / 10)
        self.speedOut = int(data[34] / 10)
        self.isAutoMode = bool(data[20])
        self.isNightMode = bool(data[16])
        self.isSpeedLocked = bool(data[22])
        self.isOn = bool(data[10])
        self.isHeaterOn = bool(data[14])
        self.isThawOn = bool(data[42])
        self.isAirInOn = bool(data[28])
        self.isAirOutOn = bool(data[32])

        if not self.isOn:
            self.speed = 0
        elif self.isAutoMode:
            self.speed = self.speedIn #same as self.speedOut
        elif self.isSpeedLocked:
            self.speed = self.speedInOut
        elif self.isAirInOn and self.isAirOutOn:
            self.speed = int((self.speedIn + self.speedOut) / 2)
        elif self.isAirInOn:
            self.speed = self.speedIn
        elif self.isAirOutOn:
            self.speed = self.speedOut

        _LOGGER.debug("speed: %d CO2: %d VOC: %d, AUTO_MODE: %d, HEATER: %d, THAW: %d", self.speed, self.co2, self.voc, self.isAutoMode, self.isHeaterOn, self.isThawOn)
        self.lastRead = datetime.now()

    async def sendCommand(self, command, repeat = 0, retry = DEFAULT_RETRY_COUNT) -> bool:
        sendSuccess = True
        _LOGGER.debug("Sending command %s to prana %s", command, self.mac)

        try:
            async with BleakClient(self.mac) as device:
                _LOGGER.debug("Connected")
                await device.start_notify(HANDLE, self.handleNotification)

                while repeat >= 0:
                    await device.write_gatt_char(HANDLE, binascii.a2b_hex(command))
                    repeat = repeat - 1

                if command != deviceStatus: # trigger a notifications
                    await device.write_gatt_char(HANDLE, binascii.a2b_hex(deviceStatus))
                    await asyncio.sleep(0.7)

        except:
            _LOGGER.debug("Error talking to prana.", exc_info=True)
            sendSuccess = False
        finally:
            pass

        if sendSuccess:
            return True
        if retry < 1:
            _LOGGER.error("Prana communication failed. Stopping trying.")
            return False

        _LOGGER.debug("Cannot connect to Prana. Retrying (remaining: %d)...", retry)
        await asyncio.sleep(DEFAULT_RETRY_TIMEOUT)

        return await self.sendCommand(command, 0, retry - 1)

    def sensorValue(self, name):
        # if (self.lastRead is None) or (datetime.now() - timedelta(seconds=3) > self.lastRead):
        #     self.sendCommand(deviceStatus)

        values = {
            "co2":      self.co2,
            "voc":      self.voc,
            "speed":    self.speed,
        }
        return values.get(name, None)

    async def getStatusDetails(self) -> bool:
        return await self.sendCommand(deviceStatus)

    async def powerOff(self):
        await self.sendCommand(powerOff)

    async def powerOn(self):
        await self.sendCommand(powerOn)

    async def toogleAutoMode(self):
        await self.sendCommand(autoMode)
    async def setAutoMode(self):
        if not self.isAutoMode:
            await self.sendCommand(autoMode)

    async def toogleAirInOff(self):
        await self.sendCommand(airInOff)
    async def toogleAirOutOff(self):
        await self.sendCommand(airOutOff)

    async def setSpeed(self, speed, maxStack = 5):
        if (maxStack < 0): # break any loops on error
            return

        if not self.isOn:
            await self.powerOn()

        up = speedUp
        down = speedDown
        if not self.isAirOutOn:
            up = speedInUp
            down = speedInDown
        if not self.isAirInOn:
            up = speedOutUp
            down = speedOutDown

        if speed > self.speed:
            await self.sendCommand(up, speed - self.speed - 1)
            await self.setSpeed(speed, maxStack - 1)
        elif (speed < self.speed):
            await self.sendCommand(down, self.speed - speed - 1)
            await self.setSpeed(speed, maxStack - 1)
        elif speed == self.speed and self.isAutoMode: # disable auto mode
            await self.toogleAutoMode()
            await self.setSpeed(speed, maxStack - 1)
        elif speed == self.speed and self.isHeaterOn: # disable heater
            await self.sendCommand(heater)
