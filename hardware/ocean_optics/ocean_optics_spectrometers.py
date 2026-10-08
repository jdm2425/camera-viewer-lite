import os, logging, sys
from datetime import datetime
from time import sleep
import numpy as np
import clr #python .NET
from hardware import Spectrometer
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

class OceanOpticsSpectrometer(Spectrometer):
    """Interface class for ocean optics spectrometers using OmniDriver"""
    ##Load .NET DLL
    path_to_dll = r'C:\Program Files\Ocean Optics\OmniDriver\OOI_HOME\NETOmniDriver-NET40.dll'
    clr.AddReference(path_to_dll)
    import OmniDriver
    lib = OmniDriver.CCoWrapper()
      
    def __init__(self):
        self.found_devices = []
        self.wavelengths = None
        self.spectrum = None
        self.datetime = None
        self.device_index = None
        self.online = False
        
    def open_all(self):
        num = self.lib.openAllSpectrometers()
        #create a list of devices in the format "[Model number] ([Serial number])"
        self.found_devices = ['{0} ({1})'.format(self.lib.getFirmwareModel(i),self.lib.getSerialNumber(i)) for i in range(num)]
        
    def close_all(self):
        self.lib.closeAllSpectrometers()
        self.online = False
    
    def set_device(self,serial=None,index=0):
        """Choose which device to acquire spectra from. Since all spectrometers
        are opened when open_all() is called, no connection needs to be created
        
        args:
            serial (string):    Serial number of the spectrometer we want to open
            index (int):        Index within the list of found devices for the
                                spectrometer we want to open. serial takes precedence over this
        """
        if serial is not None:
            tmp = [i for i,v in enumerate(self.found_devices) if serial in v] #find index of spectrometer in list
            if not tmp:
                raise ValueError('No device with serial no. {0} found'.format(serial))
            index = tmp[0]
        self.device_index = index
        self.wavelengths = np.fromiter(self.lib.getWavelengths(self.device_index),float)
        self.online = True
        
    def trigger(self):
        """Trigger acquisition. Since OmniDriver does not provide triggering functionality,
        this function does nothing"""
        pass
        
    def wait(self,timeout=2000):
        """Wait for spectrum to finish acquiring."""
        tmp = self.lib.getSpectrum(self.device_index)
        self.spectrum = np.fromiter(tmp,float)
        return True
        
    def set_exposure_time(self,exposure_time_ms):
        if not self.online:
            logger.warning('Tried to set exposure time but not online')
            return
        self.lib.setIntegrationTime(self.device_index,exposure_time_ms*1000) #convert from ms to us
    
    def set_averaging(self,avg):
        if not self.online:
            logger.warning('Tried to set averaging but not online')
            return
        self.lib.setScansToAverage(self.device_index,avg)
        
    def set_correct_nonlinear(self,val):
        if not self.online:
            logger.warning('Tried to set nonlinearity correction but not online')
            return
        self.lib.setCorrectForDetectorNonlinearity(self.device_index,int(val))
        
    def get_correct_nonlinear(self):
        if not self.online:
            logger.warning('Tried to get nonlinearity correction status but not online')
            return
        return self.lib.getCorrectForDetectorNonlinearity(self.device_index)
        
    def set_correct_electronic_dark(self,val):
        if not self.online:
            logger.warning('Tried to set electric dark current correction but not online')
            return
        self.lib.setCorrectForElectricalDark(self.device_index,int(val))
        
    def get_correct_electronic_dark(self):
        if not self.online:
            logger.warning('Tried to get electric dark current correction status but not online')
            return
        return self.lib.getCorrectForElectricalDark(self.device_index)
        
    def get_saturation_intensity(self):
        if not self.online:
            logger.warning('Tried to get saturation intensity but not online')
            return
        return self.lib.getMaximumIntensity(self.device_index)
    
    @property
    def exposure_time(self):
        if not self.online:
            return None
        return self.lib.getIntegrationTime(self.device_index)/1000
    
    @property
    def averaging(self):
        if not self.online:
            return None
        else:
            return self.lib.getScansToAverage(self.device_index)
            
if __name__ == "__main__":
    o = OceanOpticsSpectrometer()
    o.open_all()
    o.set_device()
