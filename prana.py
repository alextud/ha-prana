from bluepy import btle

import binascii
import logging
import time
import struct
from datetime import datetime, timedelta
import threading

_LOGGER = logging.getLogger(__name__)

DEFAULT_RETRY_COUNT = 2
DEFAULT_RETRY_TIMEOUT = .2

HANDLE = '0000cccc-0000-1000-8000-00805f9b34fb'
UUID = '0000baba-0000-1000-8000-00805f9b34fb'

deviceStatus = 'BEEF0501000000005A'
deviceDetails = 'BEEF0502000000005A'
powerOff     = "BEEF0401"
heater       = "BEEF0405"
nightMode    = "BEEF0406"
maxSpeed     = "BEEF0407"
airOutOff    = "BEEF0410"
speedLocked  = "BEEF0409"
speedDown    = "BEEF040B"
speedUp      = "BEEF040C"
airInOff     = "BEEF040D"
speedInUp    = "BEEF040E"
speedInDown  = "BEEF040F"
speedOutUp   = "BEEF0411"
speedOutDown = "BEEF0412"
thaw         = "BEEF0416"
autoMode     = "BEEF0418"

class Prana (btle.DefaultDelegate):
    """Representation of Prana."""

    def __init__(self, mac):
        self.mac = mac
        self.device = None
        self.lastRead = None
        self.characteristics = None
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
        self.lock = threading.RLock()

    def handleNotification (self, cHandle, data):
        #print (data)
        self.speedInOut = int(data[26] / 10)
        self.speedIn = int(data[30] / 10)
        self.speedOut = int(data[34] / 10)
        self.co2 = int(struct.unpack_from(">h", data, 61)[0] & 0b0011_1111_1111_1111)
        self.voc = int(struct.unpack_from(">h", data, 63)[0] & 0b0011_1111_1111_1111)
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


    def connect(self) -> None:
        if self.device is not None:
            return
        try:
            _LOGGER.debug("Connecting to Prana... %s", self.mac)
            self.device = btle.Peripheral(self.mac)
            self.device.setDelegate(self)
            self.device.setMTU(200) #increase MTU

            _LOGGER.debug("Connected to Prana.")

            service = self.device.getServiceByUUID(UUID)
            characteristics = service.getCharacteristics(HANDLE)[0]
            # print(characteristics.uuid, characteristics.propertiesToString(), characteristics.getHandle())

            desc = characteristics.getDescriptors(forUUID = 0x2902)[0]
            desc.write(binascii.a2b_hex('0100')) #subscribe to notifications
            self.characteristics = characteristics

        except:
            _LOGGER.debug("Failed connecting to Prana.", exc_info=True)
            self.device = None
            raise

    def disconnect(self) -> None:
        if self.device is None:
            return
        _LOGGER.debug("Disconnecting")
        try:
            self.device.disconnect()
        except:
            _LOGGER.warning("Error disconnecting from Prana.", exc_info=True)
        finally:
            self.device = None
            self.characteristics = None

    def writeKey(self, key, wait, timeout = 0.6) -> bool:
        writeResult = self.characteristics.write(binascii.a2b_hex(key), withResponse = True)

        if writeResult and wait:
            self.device.waitForNotifications(timeout)

        return writeResult

    def sendCommand(self, command, retry = DEFAULT_RETRY_COUNT) -> bool:
        sendSuccess = False
        _LOGGER.debug("Sending command to prana %s", command)
        
        try:
            self.connect()
            isGetStatus = command == deviceStatus
            sendSuccess = self.writeKey(command, wait = isGetStatus)
            if not isGetStatus: #get status
                self.writeKey(deviceStatus, wait = True)

        except:
            _LOGGER.warning("Error talking to prana.", exc_info=True)
        finally:
            self.disconnect()

        if sendSuccess:
            return True
        if retry < 1:
            _LOGGER.error("Prana communication failed. Stopping trying.", exc_info=True)
            return False
        _LOGGER.warning("Cannot connect to Prana. Retrying (remaining: %d)...", retry - 1)
        time.sleep(DEFAULT_RETRY_TIMEOUT)

        return self.sendCommand(command, retry - 1)

    def sensorValue(self, name): 
        if (self.lastRead is None) or (datetime.now() - timedelta(seconds=3) > self.lastRead):
            self.sendCommand(deviceStatus)

        values = { 
            "co2":      self.co2, 
            "voc":      self.voc,
            "speed":    self.speed,
        }
        
        return values.get(name, None)

    def getStatusDetails(self) -> bool:
        return self.sendCommand(deviceStatus)

    def powerOff(self): 
        self.sendCommand(powerOff)

    def toogleAuto(self): 
        self.sendCommand(autoMode)

    def toogleAirInOff(self): 
        self.sendCommand(airInOff)
    def toogleAirOutOff(self): 
        self.sendCommand(airOutOff)

    def setSpeed(self, speed): 
        self.sendCommand(deviceStatus)

        up = speedUp
        down = speedDown
        if not self.isAirOutOn:
            up = speedInUp
            down = speedInDown
        if not self.isAirInOn:
            up = speedOutUp
            down = speedOutDown

        if speed > self.speed:
            self.sendCommand(up)
            self.setSpeed(speed)
        elif (speed < self.speed):
            self.sendCommand(down)
            self.setSpeed(speed)
