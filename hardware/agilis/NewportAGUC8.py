import logging
import numpy as np
from datetime import datetime
from time import sleep
import serial
from serial.tools.list_ports import comports
from hardware import RelativeStage, MotorisedMirror

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


class NewportAGUC8(RelativeStage):
    def __init__(self):
        self.com_port = None
        self.found_devices = None
        self.serial = None
        self.position = [0 for i in range(7)]

    def rescan(self):
        # find virtual COM ports created by AGUC8 devices
        self.found_devices = [port[0] for port in comports()
                              if 'UC8' in port[1]]

    def open(self, com_port=None):
        if not self.found_devices:
            logger.warning('Tried to open but no devices found')
            return
        if com_port is None:
            com_port = self.found_devices[0]
        self.serial = serial.Serial()
        self.serial.port = com_port
        if self.serial.isOpen():
            logger.warning('Serial port already opened')
            if not all([self.serial.baudrate == 921600,
                        self.serial.bytesize == 8,
                        self.serial.stopbits == 1,
                        self.serial.parity == 'N']):
                raise IOError(
                    'Serial port is already open but with incorrect settings')
        else:
            self.serial.open()
        self.serial.baudrate = 921600
        self.serial.parity = 'N'
        self.serial.timeout = 1
        self.com_port = com_port
        self.serial.write('MR\n'.encode('ascii'))
        self.serial.flush()

    def close(self):
        if not self.online:
            return
        self.serial.close()

    def trigger(self, dist, axis):
        if not self.online:
            logger.warning('Tried to move but not online')
            return
        channel = np.floor(axis/2) + 1
        self._set_channel(channel)
        axis_in_channel = np.mod(axis, 2)+1
        logger.debug('Writing trigger signal: {0:.0f}PR{1:.0f}'.format(
            axis_in_channel, dist))
        self.serial.write('{0:.0f}PR{1:.0f}\n'.format(
            axis_in_channel, dist).encode('ascii'))
        self.position[axis] += dist

    def wait(self, axis, timeout=5000):
        if not self.online:
            return False
        logger.debug('Waiting for movement to stop')
        channel = np.floor(axis/2) + 1
        logger.debug('Setting channel...')
        ret = self._set_channel(channel)
        if not ret:
            logger.debug('Setting channel failed')
            return False
        logger.debug('Channel set. Waiting for channel to finish')
        return self._wait_channel()

    def is_moving(self, axis):
        channel = np.floor(axis/2) + 1
        axis_in_channel = np.mod(axis, 2)+1
        ret = self._set_channel(channel)
        if ret is False:
            # this means we're waiting for another channel
            # to stop moving before we can check the one we actually want
            return True
        logger.debug('is_moving: writing status request')
        self.serial.write('{0:.0f}TS\n'.format(
            axis_in_channel).encode('ascii'))
        ret = self._read_serial()
        status = ret[3:]
        if status == '0':
            return False
        else:
            return True

    def move(self, dist, axis, timeout=5000):
        self.trigger(dist, axis)
        sleep(0.01)
        return self.wait(axis, timeout=timeout)

    def _set_channel(self, channel):
        """Set controller channel
        Args:
            channel (int):  Required channel (1-4)
        Returns:
            bool:   True if channel set successfully or already set correctly,
                    False if tried to set but failed"""
        if not self.online:
            return False
        logger.debug('_set_channel: writing channel request')
        self.serial.write('CC?\n'.encode('ascii'))
        ret = self._read_serial()
        current_channel = int(ret[2:])
        if current_channel == channel:
            logger.debug('Channel already set correctly')
            return True
        if self._wait_channel() is True:
            logger.debug('_set_channel: writing channel change command')
            self.serial.write('CC{0:.0f}\n'.format(channel).encode('ascii'))
            ret = self._get_error()
            if ret == '0':
                return True
        return False

    def set_step_amplitude(self, axis, dir, amp):
        """Set step amplitude for motor
        Args:
            axis (int): axis for which to set amplitude. Range: 0 to 7
            dir (int): If dir>0, set positive step amplitude,
                       if dir<0, set negative
            amp (int):    Value to which the amplitude is set.
                        Range: -50 to 50 excluding 0
        """
        if not ((-50 < amp < 50) and amp != 0):
            raise ValueError('Invalid amplitude value {0}.\
                Amplitude needs to be between -50 and 50,\
                excluding 0'.format(amp))
        channel = np.floor(axis/2) + 1
        axis_in_channel = np.mod(axis, 2)+1
        ret = self._set_channel(channel)
        if not ret:
            raise Exception('Could not set step amplitude -\
                             could not set channel')
        logger.debug('set_step_amplitude: writing set command\
                     {0:.0f}SU{1:.0f}'.format(
            axis_in_channel, np.sign(dir)*amp))
        self.serial.write('{0:.0f}SU{1:.0f}\n'.format(
            axis_in_channel, np.sign(dir)*amp
        ).encode('ascii'))
        ret = self._get_error()
        if ret != '0':
            raise Exception('Could not set step amplitude -\
                set command failed with error code: {0}'.format(ret))

    def get_step_amplitude(self, axis, dir):
        channel = np.floor(axis/2) + 1
        axis_in_channel = np.mod(axis, 2)+1
        ret = self._set_channel(channel)
        if not ret:
            raise Exception('Could not set step amplitude -\
                could not set channel')
        self.serial.write('{0:.0f}SU{1}?\n'.format(
            axis_in_channel, ('+' if dir > 0 else '-')
        ).encode('ascii'))
        ret = self._read_serial()
        return np.abs(int(ret[3:]))

    def _wait_channel(self, timeout=5000):
        start = datetime.now()
        timed_out = False
        while not timed_out and not self._channel_ready():
            logger.debug('Waiting for current channel to be ready')
            timed_out = (datetime.now()-start).total_seconds() > timeout/1000
            sleep(0.001)
        return not timed_out

    def _channel_ready(self):
        logger.debug('_channel_ready: writing first status request')
        self.serial.write('{0:.0f}TS\n'.format(1).encode('ascii'))
        ret_1 = self._read_serial()
        logger.debug('_channel_ready: writing second status request')
        self.serial.write('{0:.0f}TS\n'.format(2).encode('ascii'))
        ret_2 = self._read_serial()
        return all([ret_1[3:] == '0', ret_2[3:] == '0'])

    def _read_serial(self):
        logger.debug('Reading serial port')
        start = datetime.now()
        timed_out = False
        while not timed_out and not self.serial.inWaiting():
            logger.debug('Waiting for available bytes')
            timed_out = (datetime.now()-start).total_seconds() > 0.5
            sleep(0.001)
        if not timed_out:
            raw = self.serial.read(self.serial.inWaiting())
            ret = raw[:-2].decode('ascii')
            logger.debug('Read data: {0}'.format(ret))
            return ret
        else:
            raise Exception('NewportAGUC8: Reading serial timed out')
            return None

    def _get_error(self):
        logger.debug('Getting error')
        if not self.online:
            return 'not online'
        logger.debug('Requesting error code')
        self.serial.write('TE\n'.encode('ascii'))
        ret = self._read_serial()
        if ret is None:
            return 'no response'
        return ret[2:]

    @property
    def online(self):
        if self.serial is None:
            return False
        return self.serial.isOpen()


class NewportAGUC8Mirror(MotorisedMirror):
    """Motorised mirror using a Newport AGUC8 8-axis controller as its controller

    Args:
        controller (NewportAGUC8):  Underlying controller.
                                    If none is provided, it is created
        axes (dict): Dict of axes settings:
                        h (int): Axis for horizontal movement
                        v (int): Axis for vertical movement
                        invert_h (bool): Whether to invert the horizontal axis
                        invert_v (bool): Whether to invert the vertical axis
    """

    def __init__(self,
                 controller=None,
                 axes=dict(h=0, v=1, invert_h=False, invert_v=False)):
        self.controller = (NewportAGUC8() if controller is None
                           else controller)
        self.axes = axes

    def set_axes(self, axis_h, axis_v, invert_h=False, invert_v=False):
        self.axes = dict(h=axis_h,
                         v=axis_v,
                         invert_h=invert_h,
                         invert_v=invert_v)

    def trigger(self, dir, dist):
        if ((dir == 'h' and self.axes['invert_h'])
                or (dir == 'v' and self.axes['invert_v'])):
            dist = -1*dist
        self.controller.trigger(dist, self.axes[dir])

    def move(self, dir, dist):
        if ((dir == 'h' and self.axes['invert_h'])
                or (dir == 'v' and self.axes['invert_v'])):
            dist = -1*dist
        return self.controller.move(dist, self.axes[dir])

    def wait_both(self, timeout=5000):
        for dir in ['h', 'v']:
            ret = self.controller.wait(self.axes[dir]['axis'])
            if not ret:
                return False
        return True

    @property
    def online(self):
        return self.controller.online

    @property
    def position(self):
        return {dir:
                self.controller.position[self.axes[dir]] for dir in ['h', 'v']}


if __name__ == "__main__":
    o = NewportAGUC8Mirror()
    o.controller.rescan()
    o.controller.open('COM4')
