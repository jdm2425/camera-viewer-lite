import win32com.client
import numpy as np
import time

"""
Documentation:

1. Run DAQer() to obtain full data set, or AveragePower() for averaged (i.e. more stable) readings
2. If using DAQer(), run starter() beforehand, and stopper() afterwards
3. Use closer() to close comms with the individual powermeter
4. Use closecomm to completely stop and close connection with powermeter
5. Use newloader() to load a different device, if the one you want is not automatically selected
"""

class powermeterreader():

    def __init__(self):
        self.found_devices = []
        self.meter = win32com.client.Dispatch("OphirLMMeasurement.CoLMMeasurement")
        """scan for devices"""
        serials = self.meter.ScanUSB()
        for serial in serials: self.found_devices.append(serial)
        for device in self.found_devices:
            devicehandle = self.meter.OpenUSBDevice(device)
            exists = self.meter.IsSensorExists(devicehandle, 0)
            if exists:
                self.handle = devicehandle
                print("Valid Ophir power meter detected")
                self.closer()


    def singleopener(self,idnum=0):
        self.meter.OpenUSBDevice(self.found_devices[idnum])
        self.starter()
        print("Connected to sensor ",self.found_devices[idnum])


    def reader(self):
        """scan for devices"""
        self.found_devices = []
        serials = self.meter.ScanUSB()
        for serial in serials: self.found_devices.append(serial)

    def load_default(self):
        """Load the first found Juno Power Meter"""
        for device in self.found_devices:
            devicehandle = self.meter.OpenUSBDevice(device)
            exists = self.meter.IsSensorExists(devicehandle, 0)
            self.handle = devicehandle
            print("Power meter connected")
    
    def newloader(self,serial):
        """Read in a device handle from elsewhere to connect to"""
        devicehandle = self.meter.OpenUSBDevice(serial)
        exists = self.meter.IsSensorExists(devicehandle, 0)
        if exists:
            self.handle = devicehandle
            print("Ophir power meter successfully loaded")
                
    def closer(self):
        self.meter.Close(self.handle)

    def starter(self):
        self.meter.StartStream(self.handle, 0)

    def stopper(self):
        self.meter.StopStream(self.handle, 0)

    def DAQer(self):
        data = self.meter.GetData(self.handle, 0)
        if len(data[0]) > 0:
            result = data
        else:
            result = 'no data available'
        return result
        
    def AveragePower(self,IntTime=0.1):
        time.sleep(IntTime)
        data = self.DAQer()
        if data == 'no data available':
            return data
        else:
            average = []
            for i in np.nditer(np.asarray(data[0][:])):
                average.append(i)
            averaged = np.mean(np.array(average))
            return averaged
            
    def MaxPower(self,IntTime=0.1):
        time.sleep(IntTime)
        data = self.DAQer()
        if data == 'no data available':
            return data
        else:
            values = []
            for i in np.nditer(np.asarray(data[0][:])):
                values.append(i)
            maxvlaue = max(np.array(values).astype(float))
            return maxvlaue

    def closecom(self):
        self.meter.StopAllStreams()
        self.meter.CloseAll()
        self.meter = None

def individual_power_measurement(IntTime=2):
    reader=powermeterreader()
    reader.load_default()
    reader.starter()
    data=reader.AveragePower(IntTime)
    reader.stopper()
    reader.closer()
    return data
