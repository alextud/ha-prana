from bluepy import btle

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

class Prana (btle.DefaultDelegate):
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

    def sendCommand(self, command, repeat = 0, retry = DEFAULT_RETRY_COUNT) -> bool:
        thread = threading.Thread(target=self.sendCommand_raw, args=(command, repeat, retry))
        thread.start()
        thread.join(timeout=30)
        if self.lastRead == None:
            didSucced = False
        else:
            didSucced = (datetime.now() - self.lastRead).total_seconds() < 29
        _LOGGER.debug("result = %d", didSucced)
        return didSucced

    def sendCommand_raw(self, command, repeat = 0, retry = DEFAULT_RETRY_COUNT) -> bool:
        sendSuccess = True
        _LOGGER.debug("Sending command %s to prana %s", command, self.mac)

        try:
            _LOGGER.debug("Connecting to Prana...",)
            device = btle.Peripheral(self.mac)
            device.setDelegate(self)
            device.setMTU(220) #increase MTU

            service = device.getServiceByUUID(UUID)
            characteristics = service.getCharacteristics(HANDLE)[0]
            # print(characteristics.uuid, characteristics.propertiesToString(), characteristics.getHandle())

            desc = characteristics.getDescriptors(forUUID = 0x2902)[0]
            desc.write(binascii.a2b_hex('0100')) #subscribe to notifications
            characteristics = characteristics
            _LOGGER.debug("Connected to Prana.")

            while sendSuccess and repeat >= 0:
                writeResult = characteristics.write(binascii.a2b_hex(command), withResponse = True)
                sendSuccess = writeResult != None
                repeat = repeat - 1
                #_LOGGER.debug("Command writen: %s", sendSuccess)

            if command != deviceStatus: # trigger a notifications
                writeResult = characteristics.write(binascii.a2b_hex(deviceStatus), withResponse = True)
                sendSuccess = writeResult != None
                #_LOGGER.debug("Notification Command writen: %s", sendSuccess)


            _LOGGER.debug("Command sent: %s", sendSuccess)
            device.waitForNotifications(0.6)
            device.disconnect()

            _LOGGER.debug("Disconnected.")

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
        time.sleep(DEFAULT_RETRY_TIMEOUT)

        return self.sendCommand_raw(command, 0, retry - 1)

    def sensorValue(self, name):
        # if (self.lastRead is None) or (datetime.now() - timedelta(seconds=3) > self.lastRead):
        #     self.sendCommand(deviceStatus)

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

    def powerOn(self):
        self.sendCommand(powerOn)

    def toogleAutoMode(self):
        self.sendCommand(autoMode)
    def setAutoMode(self):
        if not self.isAutoMode:
            self.sendCommand(autoMode)

    def toogleAirInOff(self):
        self.sendCommand(airInOff)
    def toogleAirOutOff(self):
        self.sendCommand(airOutOff)

    def setSpeed(self, speed, maxStack = 5):
        if (maxStack < 0): # break any loops on error
            return

        if not self.isOn:
            self.powerOn()

        up = speedUp
        down = speedDown
        if not self.isAirOutOn:
            up = speedInUp
            down = speedInDown
        if not self.isAirInOn:
            up = speedOutUp
            down = speedOutDown

        if speed > self.speed:
            self.sendCommand(up, speed - self.speed - 1)
            self.setSpeed(speed, maxStack - 1)
        elif (speed < self.speed):
            self.sendCommand(down, self.speed - speed - 1)
            self.setSpeed(speed, maxStack - 1)
        elif speed == self.speed and self.isAutoMode: # disable auto mode
            self.toogleAutoMode()
            self.setSpeed(speed, maxStack - 1)
        elif speed == self.speed and self.isHeaterOn: # disable heater
            self.sendCommand(heater)
