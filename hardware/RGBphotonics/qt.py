import os,logging,sys
from PyQt5 import QtGui, QtWidgets, QtCore
import numpy as np
from datetime import datetime
from hardware.RGBphotonics.rgb_spectrometers import RGBPhotonicsSpectrometer
from hardware.qt import SpectrometerWidget
from lab_apps.gui_elements import wrap_in_panel,auto_button_width

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class RGBSpectrometerWidget(SpectrometerWidget):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.controller = RGBPhotonicsSpectrometer()
        self.destroyed.connect(self.controller.close)
        ##Create control widgets
        self.dropdown_serials = QtGui.QComboBox()
        self.push_rescan = QtGui.QPushButton('Rescan')
        self.check_open = QtGui.QCheckBox('Open')
        self.spin_exposure = QtGui.QSpinBox()
        self.spin_average = QtGui.QSpinBox()
        
        self.spin_average.setRange(1,1000)
        self.spin_exposure.setRange(1,100000000)
        self.spin_exposure.setMinimumWidth(70)
        self.spin_average.setMinimumWidth(50)
        
        self.push_rescan.clicked.connect(self.rescan)
        self.check_open.toggled.connect(self.set_open)
        self.spin_exposure.valueChanged.connect(self.set_exposure)
        self.spin_average.valueChanged.connect(self.set_averaging)
        self.exposure_buttons = [QtGui.QPushButton(str(exp)) for exp in [1,3,5,10,50,100,1000]]
        self.average_buttons = [QtGui.QPushButton(str(avg)) for avg in [1,5,10,100]]
        for butt in self.exposure_buttons:
            auto_button_width(butt)
            butt.clicked.connect(lambda __,butt=butt: self.spin_exposure.setValue(int(butt.text())))
        for butt in self.average_buttons:
            auto_button_width(butt)
            butt.clicked.connect(lambda __,butt=butt: self.spin_average.setValue(int(butt.text())))
        
        self.check_nonlinearity = QtGui.QCheckBox('Correct Nonlinearity')
        self.check_nonlinearity.toggled.connect(lambda val: self.controller.set_processing(CorrectNonlinearity=val))
        self.check_spectral_calib = QtGui.QCheckBox('Correct Spectral Sensitivity')
        self.check_spectral_calib.toggled.connect(lambda val: self.controller.set_processing(SensitivityCalibration=val))
        self.check_normalise = QtGui.QCheckBox('Normalise to 1 s exposure')
        self.check_normalise.toggled.connect(lambda val: self.controller.set_processing(NormalizeExposureTime=val))
        ##Build GUI layout
        vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        lab = QtGui.QLabel('Serial:')
        lab.setMaximumWidth(35)
        hbox.addWidget(lab)
        hbox.addWidget(self.dropdown_serials)
        hbox.addWidget(self.push_rescan)
        hbox.addWidget(self.check_open)
        vbox.addLayout(hbox)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel('Exposure time [ms]:'))
        hbox.addWidget(self.spin_exposure)
        for butt in self.exposure_buttons:
            hbox.addWidget(butt)
        vbox.addLayout(hbox)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel('Averaging:'))
        hbox.addWidget(self.spin_average)
        for butt in self.average_buttons:
            hbox.addWidget(butt)
        vbox.addLayout(hbox)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.check_nonlinearity)
        hbox.addWidget(self.check_spectral_calib)
        hbox.addWidget(self.check_normalise)
        vbox.addLayout(hbox)
        self.setLayout(vbox)
        
        self._update_gui()
        
    def rescan(self):
        self.dropdown_serials.clear()
        self.controller.rescan()
        if not self.controller.found_devices:
            return
        serials = [dev.SerialNo for dev in self.controller.found_devices]
        self.dropdown_serials.addItems(serials)
        
    def set_open(self,val):
        if val is True:
            if not self.online:
                self._open()     
        else:
            if self.online:
                self._close()
        self.check_open.setChecked(val)
        
    def _open(self):
        serial = self.dropdown_serials.currentText()
        self.controller.open(serial)
        if not self.online:
            self.controller.close()
            return
        self._update_gui()
        self.online_changed.emit(True)
            
    def _close(self):
        self.controller.close()
        self._update_gui()
        self.online_changed.emit(False)
        
    def _update_gui(self):
        if self.online:
            for w in [self.spin_average,self.spin_exposure,self.check_spectral_calib,
                self.check_nonlinearity,self.check_normalise]+self.exposure_buttons+self.average_buttons: w.setEnabled(True)
            self.dropdown_serials.setEnabled(False)
            self.spin_average.setValue(self.averaging)
            self.spin_exposure.setValue(self.exposure_time)
            self.check_nonlinearity.setChecked(self.controller.processing_steps['CorrectNonlinearity'])
            self.check_spectral_calib.setChecked(self.controller.processing_steps['SensitivityCalibration'])
            self.check_normalise.setChecked(self.controller.processing_steps['NormalizeExposureTime'])
        else:
            for w in [self.spin_average,self.spin_exposure,self.check_spectral_calib,
                self.check_nonlinearity,self.check_normalise]+self.exposure_buttons+self.average_buttons: w.setEnabled(False)
            self.dropdown_serials.setEnabled(True)
        
    def set_exposure(self,val=None):
        if val is None:
            val=self.spin_exposure.value()
        if val != self.controller.exposure_time:
            self.controller.set_exposure_time(val)
        self.spin_exposure.setValue(val)
        
    def set_averaging(self,val=None):
        if val is None:
            val=self.spin_average.value()
        if val != self.controller.averaging:
            self.controller.set_averaging(val)
        self.spin_average.setValue(val)
        
    def trigger(self):
        self.controller.trigger()
        
    def wait(self,timeout=10000):
        ret = self.controller.wait(timeout=timeout)
        if ret:
            self.spectrum_acquired.emit()
        return ret
        
    def closeEvent(self,event):
        self._close()
        event.accept()
    
    def get_config(self):
        return dict(serial=self.dropdown_serials.currentText(),exposure_time=self.exposure_time,averaging=self.averaging,online=self.online,
                correct_nonlinear=self.controller.processing_steps['CorrectNonlinearity'], spectral_calib=self.controller.processing_steps['SensitivityCalibration'])
        
    def set_config(self,config):
        if 'serial' in config:
            self.dropdown_serials.setCurrentIndex(self.dropdown_serials.findText(config['serial']))
        if 'online' in config:
            self.check_open.setChecked(config['online'])
        if 'exposure_time' in config:
            self.spin_exposure.setValue(config['exposure_time'])
        if 'averaging' in config:
            self.spin_average.setValue(config['averaging'])
        if 'correct_nonlinear' in config:
            self.check_nonlinearity.setChecked(config['correct_nonlinear'])
        if 'spectral_calib' in config:
            self.check_spectral_calib.setChecked(config['spectral_calib'])
        
        
    @property
    def online(self):
        return self.controller.online
    @property
    def averaging(self):
        return self.controller.averaging
    @property
    def exposure_time(self):
        return self.controller.exposure_time
    @property
    def spectrum(self):
        return self.controller.spectrum
    @property
    def wavelengths(self):
        return self.controller.wavelengths
    @property
    def datetime(self):
        return self.controller.datetime
        
        
if __name__ == "__main__":
    widget = RGBSpectrometerWidget()
    widget.show()
