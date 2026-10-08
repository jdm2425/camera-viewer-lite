"""Extremely bare-bones driver for the Ocean Optics ADC1000USB spectrometer 
inside the APE SPIDER.

The ADC1000USB is pretty ancient, and the only driver that works (that I know of)
is in OmniDriver.jar. Java is a pain to access from Python. The solution I came
up with is to use py4j. This works, but is very slow. The driver runs as a separate
Java process. If the program is not exited normally, then it may leave the driver
running, in which case the program won't be able to access the spectrometer upon
restart. The solution is to kill this process - it is called java.exe in
Windows task manager.

This was written very quickly. TODOs:
* remove the hard-coded locations of py4j and OmniDriver.
* better handling of integration time and consistency between device and GUI
* more robust killing of the gateway process
"""
import subprocess,os,atexit,logging
from datetime import datetime
import numpy as np
import py4j
from py4j.java_gateway import JavaGateway
from scipy.io import loadmat
import hardware,hardware.qt
logger=logging.getLogger(__name__)
py4j_path='C:\ProgramData\Miniconda3\envs\lab\share\py4j\py4j0.10.4.jar'
omnidriver_path=r'C:\Program Files\Ocean Optics\OmniDriverSPAM\OOI_HOME\OmniDriver.jar'
path=os.path.dirname(__file__)
gateway_process=None

def ensure_gateway_process_started():
    global gateway_process
    if gateway_process is None:
        # Start gateway
        gateway_process=subprocess.Popen(('java','-cp',path+os.pathsep+py4j_path+os.pathsep+omnidriver_path,'ADC1000USBGateway'))
        # Kill gateway when Python exits. Note this doesn't work when it quits 
        # due to an exception.
        atexit.register(gateway_process.kill)
    
def compile_gateway():
    """Compile the Java gateway program. Java SDK must be installed."""
    subprocess.run((r'C:\Program Files\Java\jdk1.8.0_121\bin\javac.exe',
        '-cp',py4j_path+os.pathsep+omnidriver_path,os.path.join(path,'ADC1000USBGateway.java')))        

class SetupException(Exception):
    pass
    
suggestions_str='Check that: 1. Spectrometer is connected and its green LED is on. 2. It appears in devices manager. 3. java.exe is not running i.e. in Task Manager - kill it if it is (see %s for more info).'%__file__

class ADC1000USB(hardware.Spectrometer):
    def __init__(self):
        ensure_gateway_process_started()
        gateway=JavaGateway()
        app=gateway.entry_point
        try:
            self.driver=app.getDriver()
        except py4j.protocol.Py4JNetworkError:
            raise SetupException('Unable to create ADC1000USB spectrometer driver. '+suggestions_str)
        # Sometimes e.g. after unplug and replug it increments the spectrometer
        # number. Try them in sequence...
        spectrometer_num=0
        max_spectrometer_num=99
        while True:
            try:
                logger.info('Attempting openSpectrometer(%d)'%spectrometer_num)
                self.driver.openSpectrometer(spectrometer_num)
            except py4j.protocol.Py4JJavaError:
                # openSpectrometer failed
                spectrometer_num+=1
                if spectrometer_num>max_spectrometer_num:
                    raise SetupException('Unable to open any spectrometer. '+suggestions_str)
            else:
                break
        # openSpectrometer succeeeded
        self.serial=self.driver.getSerialNumber()
        self.saturation_intensity=self.driver.getMaxIntensity()
        self.wavelengths=loadmat(os.path.join(os.path.dirname(__file__),'spec_calib150224_1848.mat'))['lambda'].squeeze()
        self.online=True
        
    @property
    def integration_time(self):
        """Integration time in ms"""
        return self.driver.getActualIntegrationTime()/1000
        
    def set_integration_time(self,ms):
        """Set integration time in ms"""
        self.driver.setIntegrationTime(int(ms*1000))
    
    def close(self):
        self.driver.closeSpectrometer()
        
    def trigger(self):
        self.spectrum=np.asarray(list(self.driver.getSpectrum().getSpectrum()))
        self.datetime=datetime.now()
        
    def wait(self,timeout=1000):
        return True
        
# todo separate file
from PyQt5 import QtGui, QtWidgets
class ADC1000USBWidget(ADC1000USB,hardware.qt.SpectrometerWidget):
    def __init__(self,config={},parent=None):
        ADC1000USB.__init__(self)
        hardware.qt.SpectrometerWidget.__init__(self,parent)
        hbox=QtGui.QHBoxLayout()
        self.setLayout(hbox)
        hbox.addWidget(QtGui.QLabel('Integration time (ms):'))
        sb=QtGui.QDoubleSpinBox()
        sb.setRange(0.001,10000)
        integration_time=config.pop('integration_time',10)
        sb.setValue(integration_time)
        self.set_integration_time(integration_time)
        self.integration_time_widget=sb
        sb.valueChanged.connect(self.set_integration_time)
        hbox.addWidget(sb)
        if len(config)>0:
            logger.warning('Unused config keys %s'%str(config.keys()))
        
    def get_config(self):
        return dict(integration_time=self.integration_time)
        
        
    
        
        


