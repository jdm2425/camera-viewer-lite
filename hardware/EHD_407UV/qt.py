from PyQt5 import QtGui, QtWidgets, QtCore
import numpy as np
import sys, os, logging
from datetime import datetime
import hardware.qt
from hardware.qt import CameraWidget, CameraROIChooser
from hardware.EHD_407UV import EHDCamController


class EHDCamWidget(CameraWidget):
    """
    Qt widget controlling an EHD UV camera. Usual controls for camera, exposure time and gain
    Acquisition average is only applied for acquire_image(), NOT for trigger() and wait() 
    """
    def __init__(self):
        super().__init__()
        self.controller = EHDCamController()
        vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        self.open_close_button = QtGui.QPushButton("Open")
        hbox.addWidget(self.open_close_button)
        hbox.addWidget(QtGui.QLabel("Exp. time (ms):"))
        self.exposure_time_spinner = QtGui.QSpinBox()
        self.exposure_time_spinner.setMinimum(1)
        self.exposure_time_spinner.setMaximum(80)
        hbox.addWidget(self.exposure_time_spinner)
        self.real_exposure_time = QtGui.QLabel('n/a')
        self.real_exposure_time.setMinimumWidth(60)
        hbox.addWidget(self.real_exposure_time)
        hbox.addWidget(QtGui.QLabel("Gain (0-1023):"))
        self.gain_spinner = QtGui.QSpinBox()
        self.gain_spinner.setMinimum(0)
        self.gain_spinner.setMaximum(1023)
        hbox.addWidget(self.gain_spinner)
        hbox  = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Acq. average:"))
        self.acq_avg_spinner = QtGui.QSpinBox()
        self.acq_avg_spinner.setMaximum(100)
        self.acq_avg_spinner.setMinimum(1)
        self.acq_avg_spinner.setValue(1)
        hbox.addWidget(self.acq_avg_spinner)
        vbox.addLayout(hbox)
        
        self.setLayout(vbox)
        
        self.online = False
        self.acq_avg = 1
        
        self.exposure_time_spinner.valueChanged.connect(lambda: self.set_exposure_time(None))
        self.gain_spinner.valueChanged.connect(lambda: self.set_gain(self.gain_spinner.value()))
        self.acq_avg_spinner.valueChanged.connect(lambda: self.set_acq_avg(self.acq_avg_spinner.value()))
        self.open_close_button.clicked.connect(lambda: self.set_open(not self.online))
        
    
    def _open(self):
        self.controller.open()
        if self.controller.online:
            self.open_close_button.setText("Close")
            self.online = True
            self.exposure_time_spinner.setValue(5)
            self.gain_spinner.setValue(self.controller.gain)
            self.online_changed.emit(True)
    
    def _close(self):
        self.controller.close()
        self.open_close_button.setText("Open")
        self.online = False
        self._update_exposure()
        self.online_changed.emit(False)
        
    def set_open(self,val):
        if val is True:
            if not self.online:
                self._open()     
        else:
            if self.online:
                self._close()
                
    def acquire_image(self,timeout=1000):
        if not self.online:
            return False
        ret = self.controller.acquire_image(timeout)
        if self.acq_avg==1 and ret:
            self.image = self.controller.image
            self.image_acquired.emit()
            return ret
        elif ret:
            buf = np.empty_like(self.controller.image)
            for i in range(self.acq_avg-1):
                ret = self.controller.acquire_image(timeout)
                assert ret
                buf += self.controller.image
            self.image = buf/self.acq_avg
            self.image_acquired.emit()
            return True
        else:
            return False
        
    def trigger(self):
        self.controller.trigger()
        
    def wait(self,timeout=1000):
        ret = self.controller.wait(timeout)
        if ret:
            self.image_acquired.emit()
        return ret
                
    def set_exposure_time(self,exposure_time_ms=None):
        if exposure_time_ms is not None:
            self.exposure_time_spinner.setValue(exposure_time_ms)
            return
        if self.online:
            self.controller.set_exposure_time(self.exposure_time_spinner.value())
            self._update_exposure()
    
    def _update_exposure(self):
        self.real_exposure_time.setText( str(self.exposure_time_ms)+' ms' if self.exposure_time_ms is not None else 'n/a')
        
    def set_gain(self,gain):
        self.controller.set_gain(gain)
    
    def set_acq_avg(self,avg):
        if avg != self.acq_avg:
            self.acq_avg = avg
        self.acq_avg_spinner.setValue(avg)
        
    def get_config(self):
        return dict(exposure_time_ms=self.exposure_time_ms,
                    gain = self.gain,
                    acq_avg = self.acq_avg,
                    online=self.online)
                    
    def set_config(self,config):
        if 'exposure_time' in config:
            self.set_exposure_time(config['exposure_time_ms'])
        if 'gain' in config:
            self.set_gain(config['gain'])
        if 'acq_avg' in config:
            self.set_acq_avg(config['acq_avg'])
        if 'online' in config:
            self.set_open(config['online'])
        
    @property
    def exposure_time_ms(self):
        return self.controller.exposure_time_ms
    @property
    def gain(self):
        return self.controller.gain
    @property
    def x(self):
        return self.controller.x
    @property
    def y(self):
        return self.controller.y
    @property
    def datetime(self):
        return self.controller.datetime
        
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    widget=EHDCamWidget()
    widget.setWindowTitle('EHD UV Cam Controller')
    widget.show()
    widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    sys.exit(app.exec_())
