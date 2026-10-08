import os,logging,sys
import numpy as np
from PyQt5 import QtGui, QtWidgets,QtCore
from hardware.photon_control import PhotonControlSpectrometer
from hardware.qt import SpectrometerWidget
from lab_apps.gui_elements import wrap_in_panel

logger = logging.getLogger(__name__)

class PhotonControlSpectrometerWidget(SpectrometerWidget):
    def __init__(self,controller=None,parent=None):
        super().__init__(parent=parent)
        self.controller = (PhotonControlSpectrometer() if controller is None else controller)
        self.destroyed.connect(self.controller.close)
        self.push_rescan = QtGui.QPushButton('Rescan')
        self.text_device = QtGui.QLabel('No device found')
        self.check_open = QtGui.QCheckBox('Open')
        self.spin_exposure = QtGui.QDoubleSpinBox()
        self.text_exposure = QtGui.QLabel('..... ms')
        
        self.push_rescan.clicked.connect(self.rescan)
        self.check_open.toggled.connect(self.set_open)
        self.check_open.setEnabled(False)
        self.spin_exposure.setRange(1,10000)
        self.spin_exposure.setValue(100)
        self.spin_exposure.valueChanged.connect(self.set_exposure)
        
        vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(self.push_rescan)
        hbox.addWidget(self.check_open)
        hbox.addWidget(self.text_device)
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(QtGui.QLabel('Exposure [ms]:'))
        hbox.addWidget(self.spin_exposure)
        hbox.addWidget(self.text_exposure)
        self.setLayout(vbox)
        
        self.rescan()
        
    def rescan(self):
        ret = self.controller.rescan()
        self.check_open.setEnabled(ret)
        if ret:
            self.text_device.setText('Found device')
        else:
            self.text_device.setText('No device found')
        
    def set_open(self,val):
        if val is True:
            if not self.online:
                self._open()     
        else:
            if self.online:
                self._close()
        self.check_open.setChecked(self.online)
        
    def _open(self):
        self.controller.open()
        if self.online:
            self.text_device.setText(self.controller.serial_no)
            self.online_changed.emit(True)
            self.spin_exposure.setValue(int(self.exposure_time))
            self._update_gui()
    
    def _close(self):
        self.controller.close()
        self.online_changed.emit(False)
        self.rescan()
        
    def set_exposure(self,val=None):
        if not self.online:
            return
        if val is None:
            val=self.spin_exposure.value()
        if np.abs(val - self.controller.exposure_time)>0.5:
            self.controller.set_exposure_time(val)
        self.spin_exposure.setValue(val)
        self._update_gui()
        
    def _update_gui(self):
        if not self.online:
            self.text_exposure.setText('..... ms')
        else:
            self.text_exposure.setText('{0:3.2f} ms'.format(self.exposure_time))
        
    def trigger(self):
        self.controller.trigger()
    
    def wait(self,timeout=1000):
        ret = self.controller.wait()
        self.spectrum_acquired.emit()
        return bool(ret)
        
    def get_config(self):
        return dict(online=self.online,exposure_time=self.exposure_time)
        
    def set_config(self,config):
        self.set_open(config.pop('online',False))
        self.set_exposure(config.pop('exposure_time',None))
        if len(config)>0:
            logger.warning('Found unused config keys: {0}'.format(config.keys()))
            
        
    @property
    def exposure_time(self):
        return self.controller.exposure_time
    @property
    def online(self):
        return self.controller.online
    @property
    def serial_no(self):
        return self.controller.serial_no
    @property
    def spectrum(self):
        return self.controller.spectrum
    @property
    def wavelengths(self):
        return self.controller.wavelengths
    @property
    def datetime(self):
        return self.controller.datetime
        
