"""Requires RGB Photonics drivers to be installed on the computer. Easiest is to
install the QWave software from their website."""
import os, logging, sys
from datetime import datetime
from time import sleep
import numpy as np
import clr #python .NET
import System #System namespace from .NET for data types
from hardware import Spectrometer

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

class RGBPhotonicsSpectrometer(Spectrometer):
    """Interface class to work with an RGB Photonics Spectrometer (Qwave, Qmini etc)
        Supports settings for built-in processing of the spectrometer if available, the available options are listed in processing_steps_codes"""
    ##Load .NET DLL
    path_to_dll = os.path.join(os.path.dirname(__file__),'RgbDriverKit.dll')
    clr.AddReference(path_to_dll)
    import RgbDriverKit as lib
    status_codes = {'0': 'Idle', '1': 'Waiting for trigger', '2': 'Taking spectrum','-1':'Not Ready','-2':'Busy','-3':'Error during exposure','-4':'Connection closed'}
    processing_steps_codes = ['ScaleTo16BitRange','AdditionalFiltering','SensitivitySmoothing','SensitivityCalibration','NormalizeExposureTime','CompensateStraylight',
            'RemoveTemporaryBadPixels','SubtractDark','RemovePermanentBadPixels','CorrectNonlinearity','AdjustOffset']
    
    def __init__(self):
        self.found_devices = []
        self.device = None
        self.spectrum = None
        self.wavelengths = None
        self.datetime = None
        
    def rescan(self):
        """Scan for devices."""
        self.found_devices = []
        qseries = self.lib.Qseries.SearchDevices()
        rgbspec = self.lib.RgbSpectrometer.SearchDevices() #older spectrometer models use a different class
        for dev in qseries: self.found_devices.append(dev)
        for dev in rgbspec: self.found_devices.append(dev)
        
    def open(self,serial_no=None,indx=0):
        """Open spectrometer specified by either serial no. or index in list of found devices, 
            or the first one found if neither are given"""
        if serial_no is not None and type(serial_no) is not str:
            raise ValueError('serial needs to be a string, got {0} instead.'.format(type(serial_no).__name__))
        if not self.found_devices:
            logger.warning("Tried to open but no devices found. Have you rescan()ed before opening?")
            return
        if serial_no is not None: #if serial no is specified, use that
            tmp = [dev for dev in self.found_devices if dev.serialNo == serial_no]
            if tmp:
                self.device = tmp[0]
            else:
                logger.warning('Tried to open device with serial no. {0} but no such device found'.format(serial_no))
                return
        else: #if serial no. not specified, use index (if that is not supplied either, it defaults to 0)
            self.device = self.found_devices[indx]
        self.device.Open()
        if self.device.CheckDeviceRemoved(): #Check that the object just created refers to a spectrometer that is still connected
            logger.warning('Opened spectrometer object but spectromer is disconnected. Closing.')
            self.device.Close()
            return
        self.wavelengths = np.fromiter(self.device.GetWavelengths(),float) #convert from System.Double[] to numpy array
    
    def close(self):
        """Close device connection"""
        if self.device is None:
            return
        self.device.Close()
        self.device = None
    
    def trigger(self):
        """Start acquisition"""
        if not self.online:
            logger.warning('Tried to trigger spectrometer but not online')
            return
        if self.device.Status != 0:
            logger.warning('Spectrometer is not ready to be triggered, status:'.format(
                self.status_codes[str(self.device.Status)] if str(self.device.Status) in self.status_codes else 'unknown' ) )
            return
        self.device.StartExposure()
        
    def wait(self,timeout=10000):
        """Wait for current acquisition to finish or time out after exposure time + timeout
            Spectrometer needs to have been triggered before this, otherwise returns False and no spectrum
            Use acquire_spectrum() (from Specrometer superclass) to trigger and then wait"""
        if not self.online:
            logger.warning('Tried to wait for spectrum but not online')
            return False
        #need to make sure we wait for at least the amount of time it takes to get a spectrum
        timeout += self.averaging*self.exposure_time 
        timed_out = False
        logger.debug('Waiting for exposure to finish, timeout {0} ms'.format(timeout))
        start = datetime.now()
        while self.device.Status != 0 and not timed_out:
            timed_out = (datetime.now()-start).total_seconds() > timeout/1000
            sleep(0.01)
        logger.debug('Waiting for spectrum '+('timed out.' if timed_out else 'finished.'))
        if not timed_out:
            try:
                d = self.device.GetSpectrumData()
            except System.InvalidOperationException:
                logger.warning('Tried to get spectrum but no data available. Have you triggered the spectrometer?')
                return
            self.spectrum = np.fromiter(d.Spectrum,float) #convert from System.Double[] to numpy array
            self.datetime = datetime(d.TimeStamp.Year,d.TimeStamp.Month,d.TimeStamp.Day,
                d.TimeStamp.Hour,d.TimeStamp.Minute,d.TimeStamp.Second,d.TimeStamp.Millisecond*1000)
        return not timed_out
        
    def set_exposure_time(self,exposure_time_ms):
        if not self.online:
            logger.warning('Tried to set exposure time but not online')
            return
        logger.debug('Setting exposure to {0} ms'.format(exposure_time_ms))
        self.device.ExposureTime = exposure_time_ms/1000
        
    def set_averaging(self,avg):
        if not self.online:
            logger.warning('Tried to set averaging but not online')
            return
        logger.debug('Setting averaging to {0} frames'.format(avg))
        self.device.Averaging = avg
        
    def get_processing_dict(self):
        """Get dictionary of current internal processing steps"""
        proc = bin(self.device.ProcessingSteps)[2:].zfill(11)
        proc_bit_list = [int(i) for i in proc]
        return {self.processing_steps_codes[i]: bool(proc_bit_list[i]) for i in range(len(proc_bit_list))}
        
    def set_processing(self,**kwargs):
        """Set internal processing steps as given by keyword arguments.
            Example: set_processing(NormalizeExposureTime=True,SensitivityCalibration=False)
            The argument to device.ProcessingSteps is an integer whose individual bits stand for specific processing steps.
            This function creates this number from a keyword arg list by retrieving the current settings and applying bitwise OR operations"""
        current = self.get_processing_dict()
        proc_bit_list = [0 for i in range(11)]
        for key,value in current.items():
            proc_bit_list[self.processing_steps_codes.index(key)] = int(value)
        for key,value in kwargs.items():
            if key not in self.processing_steps_codes:
                raise ValueError('Passed invalid processing option {0}'.format(key))
            proc_bit_list[self.processing_steps_codes.index(key)] = int(value)
        proc = 0
        for bit in proc_bit_list:
            proc = (proc << 1) | bit #bit-shift to access next bit in the number and set to 1 if the current bit is 1, otherwise unchanged
        self.device.ProcessingSteps=proc
        
    @property
    def online(self):
        return self.device is not None and self.device.isOpen and not self.device.CheckDeviceRemoved()
        
    @property
    def exposure_time(self):
        if not self.online:
            return None
        else:
            return self.device.ExposureTime*1000
            
    @property
    def averaging(self):
        if not self.online:
            return None
        else:
            return self.device.Averaging
            
    @property
    def processing_steps(self):
        return self.get_processing_dict()
            
        
        
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    o = RGBPhotonicsSpectrometer()
    o.rescan()
    o.open()
    
