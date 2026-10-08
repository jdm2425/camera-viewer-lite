import logging
import serial
from serial.tools.list_ports import comports
from time import time, sleep

logger = logging.getLogger(__name__)


class OmegaPressureGauge:
    def __init__(self):
        self.serial = None
        self.rescan()

    def rescan(self):
        self.ports_available = [port[0] for port in comports()]

    def open(self, port=None):
        if port is None:
            # cannot be COM1 on most PCs since
            # that is the actual serial port, not a USB virtual serial
            if len(self.ports_available) > 1:
                port = self.ports_available[1]
            elif len(self.ports_available) == 1:
                port = self.ports_available[0]
            else:
                raise Exception('No serial ports found')
        self.serial = serial.Serial(port)
        self.serial.baudrate = 115200
        self.serial.flushInput()
        # set readout rate to 1000 per second
        self.serial.write('RATE 8\r'.encode('ascii'))
        now = time()
        while self.serial.inWaiting() < 13:
            sleep(0.1)
            if time() - now > 5:
                self.serial.close()
                raise Exception(
                    'Setting read out rate failed.\
                     Have you selected the correct COM port?')
        self.serial.flushInput()

    def close(self):
        self.serial.close()

    def acquire_pressure(self, timeout=2):
        self.serial.flushInput()
        self.serial.write('P\r'.encode('ascii'))
        now = time()
        while self.serial.inWaiting() < 14:
            sleep(0.01)
            if time() - now > timeout:
                raise IOError('Reading from pressure gauge timed out')
        tmp = self.serial.read(self.serial.inWaiting()).decode('ascii')
        p_psi = float(tmp.split('PSI')[0])
        return p_psi * 0.0689476 + 1.013

    @property
    def online(self):
        return (False if self.serial is None
                else self.serial.isOpen())


if __name__ == "__main__":
    o = OmegaPressureGauge()
    o.open()
