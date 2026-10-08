import logging
import numpy as np
from datetime import datetime
import ctypes
from ctypes import byref
from hardware import Spectrometer

logger = logging.getLogger(__name__)


class PhotonControlSpectrometer(Spectrometer):
    def __init__(self, path_to_dll=None):
        self.path_to_dll = (
            'C:\\Program Files (x86)\\Photon Control\\SPM Spectrometer\\'
            'SpecSoft V4.0\\data\\PhotonSpectr.dll'
            if path_to_dll is None else path_to_dll)
        self.lib = ctypes.cdll.LoadLibrary(self.path_to_dll)
        self.found_device = False
        self.rescan()
        self.spectrum = None
        self.wavelengths = None
        self.datetime = None
        self.online = False

    def rescan(self):
        ret = self.lib.PHO_EnumerateDevices()
        self.found_device = bool(ret)
        return bool(ret)

    def open(self):
        ret = self.lib.PHO_Open(0)
        num_pix = ctypes.c_int()
        self.lib.PHO_GetPn(0, byref(num_pix))
        self.num_pix = num_pix.value
        coeffs = (ctypes.c_float*4)()
        self.lib.PHO_GetLut(0, byref(coeffs), 4)
        self.wavelengths = np.polyval(coeffs[::-1], np.arange(0, self.num_pix))
        self._buffer = (ctypes.c_ushort * self.num_pix)()

        if ret:
            self.online = True
        else:
            logger.warning('Failed to open spectrometer')
            self.online = False

    def close(self):
        ret = self.lib.PHO_Close(0)
        self.online = False
        if not ret:
            logger.warning('Error occurred when closing spectrometer')

    def trigger(self):
        pass

    def wait(self, timeout=1000):
        ret = self.lib.PHO_Acquire(0, 0, self.num_pix, byref(self._buffer))
        if not ret:
            return False
        self.datetime = datetime.now()
        self.spectrum = np.int32(np.ctypeslib.as_array(self._buffer))
        return True

    def set_exposure_time(self, exposure_time_ms):
        if not self.online:
            logger.warning('Tried to set exposure time but not online')
            return
        self.lib.PHO_SetTime(0, ctypes.c_float(exposure_time_ms))

    @property
    def exposure_time(self):
        if not self.online:
            return None
        buf = ctypes.c_float()
        ret = self.lib.PHO_GetTime(0, byref(buf))
        if not ret:
            raise Exception('Failed to get exposure time')
        return buf.value

    @property
    def serial_no(self):
        if not self.online:
            return None
        buf = (ctypes.c_char*9)()
        self.lib.PHO_GetSn(0, byref(buf), 9)
        return buf.value.decode('ascii')


if __name__ == '__main__':
    o = PhotonControlSpectrometer()
    o.open()
