import logging, sys
import numpy as np
from PyQt5 import QtGui, QtWidgets,QtCore
from hardware.qt import CameraWidget
from hardware.webcam import webcam_opencv

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


class WebcamWidget(CameraWidget):
    """
    Qt Widget for an opencv webcam controller
    For ROI functionality, use an ImageProcessor (opencv only offers post-acquisition cropping anyway)
    """
    def __init__(self,parent = None):
        super().__init__(parent = parent)
        self.controller = webcam_opencv.WebcamController()
        self.name_settings = QtCore.QSettings('CameraViewerLite', 'CameraNames')
        self.camera_settings = QtCore.QSettings('CameraViewerLite', 'CameraSettings')
        self._loading_settings = False
        self.destroyed.connect(self.controller.close)
        vbox=QtGui.QVBoxLayout() #main vbox
        ## First row: Select cam, open,running, rescan
        hbox = QtGui.QHBoxLayout()
        self.cam_chooser = QtGui.QComboBox()
        hbox.addWidget(self.cam_chooser)
        self.rename_button = QtWidgets.QPushButton('Rename...')
        self.rename_button.clicked.connect(self.rename_camera)
        self.rename_button.setToolTip('Names are saved on this PC by camera number; check them after reconnecting devices.')
        hbox.addWidget(self.rename_button)
        self.rescanbutton = QtGui.QPushButton("Rescan")
        self.rescanbutton.clicked.connect(self.rescan)
        hbox.addWidget(self.rescanbutton)
        self.connect_button = QtWidgets.QPushButton('Connect')
        self.connect_button.setCheckable(True)
        self.connect_button.setToolTip(
            'Connect to the selected camera and start its frame stream.')
        self.connect_button.toggled.connect(self.set_connected)
        hbox.addWidget(self.connect_button)
        vbox.addLayout(hbox)
        ## Second row: Resolution, Exposure time, Gain
        hbox = QtGui.QHBoxLayout()
        self.format_chooser = QtGui.QComboBox()
        self.format_chooser.addItems(webcam_opencv.image_format_names)
        self.format_chooser.setCurrentIndex(webcam_opencv.image_format_names.index('Native'))
        self.format_chooser.currentIndexChanged.connect(lambda indx: self.setFormat(val=self.format_chooser.currentText()))
        hbox.addWidget(self.format_chooser)
        hbox.addWidget(QtGui.QLabel('Exposure:'))
        self.exposure_spinner = QtGui.QSpinBox()
        self.exposure_spinner.setRange(-15,0)
        self.exposure_spinner.setValue(-5)
        self.exposure_spinner.setKeyboardTracking(False)
        self.exposure_spinner.valueChanged.connect(lambda val: self.setExposure(val))
        hbox.addWidget(self.exposure_spinner)
        hbox.addWidget(QtGui.QLabel('Gain:'))
        self.gain_spinner = QtGui.QSpinBox()
        self.gain_spinner.setRange(2,255)
        self.gain_spinner.setValue(128)
        self.gain_spinner.setKeyboardTracking(False)
        self.gain_spinner.valueChanged.connect(lambda val: self.setGain(val))
        hbox.addWidget(self.gain_spinner)
        vbox.addLayout(hbox)
        self.setLayout(vbox)
        exposure_buttons = QtWidgets.QHBoxLayout()
        self.auto_exposure = QtWidgets.QPushButton('Camera auto')
        self.auto_exposure.setCheckable(True)
        self.auto_exposure.setEnabled(False)
        self.auto_exposure.setToolTip(
            'Use the camera driver\'s fast automatic exposure.')
        self.auto_exposure.toggled.connect(self.setAutoExposure)
        exposure_buttons.addWidget(self.auto_exposure)
        self.safe_exposure = QtWidgets.QPushButton('Safe exposure scan')
        self.safe_exposure.setEnabled(False)
        self.safe_exposure.setToolTip(
            'Slower optional scan for the brightest setting without clipping.')
        self.safe_exposure.clicked.connect(self.run_safe_exposure)
        exposure_buttons.addWidget(self.safe_exposure)
        vbox.addLayout(exposure_buttons)
        
        self.setWindowTitle('Webcam settings')
        
        self.rescan()
        self.control_timer = QtCore.QTimer(self)
        self.control_timer.timeout.connect(self.refresh_camera_controls)
        self.control_timer.start(250)
        self.refresh_camera_controls()

    @property
    def display_name(self):
        return self.cam_chooser.currentText() or 'No camera'

    @property
    def reference_key(self):
        device = self.cam_chooser.currentData()
        return self._camera_name_key(device) if device is not None else None

    def _camera_name_key(self, device):
        import socket
        return '{}/camera_{}'.format(socket.gethostname(), device)

    def rename_camera(self):
        device = self.cam_chooser.currentData()
        if device is None:
            return
        key = self._camera_name_key(device)
        name, accepted = QtWidgets.QInputDialog.getText(
            self, 'Rename camera',
            'Name for camera #{} on this PC (blank resets it):'.format(device),
            text=self.name_settings.value(key, '', type=str))
        if accepted:
            self.name_settings.setValue(key, name.strip())
            self.name_settings.sync()
            if self.name_settings.status() != QtCore.QSettings.NoError:
                QtWidgets.QMessageBox.warning(self, 'Name not saved', 'Could not store the camera name on this PC.')
            self._update_camera_names()

    def _update_camera_names(self):
        for index in range(self.cam_chooser.count()):
            device = self.cam_chooser.itemData(index)
            name = self.name_settings.value(self._camera_name_key(device), '', type=str)
            self.cam_chooser.setItemText(index, '{} [#{}]'.format(name, device) if name else 'Webcam #{}'.format(device))

    def refresh_camera_controls(self):
        opened = self.opened
        blocker = QtCore.QSignalBlocker(self.connect_button)
        self.connect_button.setChecked(opened)
        del blocker
        self.connect_button.setText('Disconnect' if opened else 'Connect')
        self.connect_button.setEnabled(opened or self.cam_chooser.count() > 0)
        self.rescanbutton.setEnabled(not opened)
        self.rename_button.setEnabled(self.cam_chooser.count() > 0)
        self.format_chooser.setEnabled(opened)
        self.gain_spinner.setEnabled(opened)
        self.auto_exposure.setEnabled(opened)
        self.safe_exposure.setEnabled(opened and self.online)
        self.exposure_spinner.setEnabled(
            opened and not self.auto_exposure.isChecked())
        
    def rescan(self):
        if self.opened:
            return
        previous = self.cam_chooser.currentData()
        self.controller.rescan()
        self.cam_chooser.clear()
        for device in self.controller.cams_found:
            self.cam_chooser.addItem('Webcam #{}'.format(device), device)
        index = self.cam_chooser.findData(previous)
        if index >= 0:
            self.cam_chooser.setCurrentIndex(index)
        self._update_camera_names()
    
    def set_open(self,val):
        try:
            if val is True:
                if not self.opened:
                    self._open()     
            else:
                if self.opened:
                    self._close()
        finally:
            blocker = QtCore.QSignalBlocker(self.connect_button)
            self.connect_button.setChecked(self.opened)
            del blocker
            self.auto_exposure.setEnabled(self.opened)

    def set_connected(self, connected):
        """Open and start, or stop and close, using one connection control."""
        try:
            if connected:
                self.set_open(True)
                if self.opened:
                    self.set_online(True)
            else:
                self.set_open(False)
        finally:
            blocker = QtCore.QSignalBlocker(self.connect_button)
            self.connect_button.setChecked(self.opened)
            del blocker
            self.refresh_camera_controls()
        
    def set_online(self,val):
        if val is True:
            if (not self.online) and self.opened:
                self._start()
        else:
            if self.online:
                self._stop()
    
    def _open(self,ext=None):
        #ext: externally supplied camera index
        logger.debug('Opening camera')
        if ext is not None:
            self.cam_chooser.setCurrentIndex(ext)
        indx = self.cam_chooser.currentIndex()
        self.controller.open(indx)
        if self.opened:
            self._load_camera_settings()
            self.cam_chooser.setEnabled(False)
    
    def _close(self):
        self.set_online(False)
        self.controller.close()
        self.cam_chooser.setEnabled(True)
        
    def _start(self):
        self.controller.start()
        self.online_changed.emit(self.online)
        
    def _stop(self):
        self.controller.stop()
        self.online_changed.emit(self.online)
    
    def setFormat(self,val=None):
        if not self.opened:
            logger.debug('Camera not opened, cannot set format.')
            return
        if val is None:
            val = self.format_chooser.currentText()
            logger.debug('setFormat: No external value supplied, taking GUI value {0}'.format(val))
        else:
            logger.debug('setFormat: Using externally supplied value {0}.'.format(val))
        format = webcam_opencv.image_formats[val]
        if format != self.controller.image_size:
            logger.debug('Setting format to {0}'.format(val))
            self.controller.set(format=val)
        self.format_changed.emit()
        self.format_chooser.setCurrentIndex(self.format_chooser.findText(val))
        if not self._loading_settings:
            self._save_camera_settings()
        
    def setAutoExposure(self, enabled):
        previous = self.controller.nominal_settings.get(
            'auto_exposure', False)
        try:
            accepted = self.controller.set_auto_exposure(enabled)
        except Exception:
            logger.exception('Could not change camera auto exposure')
            accepted = False
        blocker = QtCore.QSignalBlocker(self.auto_exposure)
        self.auto_exposure.setChecked(enabled if accepted else previous)
        del blocker
        self.exposure_spinner.setEnabled(
            self.opened and not self.auto_exposure.isChecked())
        if not accepted:
            QtWidgets.QMessageBox.warning(
                self, 'Auto exposure unavailable',
                'The camera driver could not change exposure mode. '
                'The previous setting has been kept.')
        else:
            self._save_camera_settings()

    def run_safe_exposure(self):
        """Select the brightest exposure with no meaningful pixel clipping."""
        if not self.opened or not self.online:
            return
        self.safe_exposure.setEnabled(False)
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        chosen = self.exposure_spinner.minimum()
        found_safe = False
        try:
            self.setAutoExposure(False)
            if self.auto_exposure.isChecked():
                return
            for exposure in range(self.exposure_spinner.minimum(),
                                  self.exposure_spinner.maximum() + 1):
                self.setExposure(exposure, save=False)
                for _ in range(2):
                    if not self.acquire_image(1500):
                        raise RuntimeError(
                            'Timed out waiting for a camera frame.')
                image = np.asarray(self.image)
                if not self._exposure_is_safe(image):
                    break
                chosen = exposure
                found_safe = True
            self.setExposure(chosen)
            if not found_safe:
                QtWidgets.QMessageBox.warning(
                    self, 'Exposure remains saturated',
                    'The image still contains clipped pixels at the minimum '
                    'camera exposure. Reduce the light level or add attenuation.')
        except Exception as error:
            logger.exception('Automatic exposure failed')
            QtWidgets.QMessageBox.warning(
                self, 'Auto exposure failed', str(error))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.safe_exposure.setEnabled(self.opened and self.online)

    @staticmethod
    def _exposure_is_safe(image):
        image = np.asarray(image)
        return (float(np.percentile(image, 99.9)) < 245.0
                and float(np.mean(image >= 254.0)) <= 0.0005)

    def setExposure(self,val=None,save=True):
        if val is None:
            val=self.exposure_spinner.value()
        if val != self.controller.exposure_time:
            self.controller.set(exposure_time=val)
        self.exposure_spinner.setValue(int(val))
        if save:
            self._save_camera_settings()
        
    def setGain(self,val=None):
        if val is None:
            val = self.gain_spinner.value()
        if val != self.controller.gain:
            self.controller.set(gain=val)
        self.gain_spinner.setValue(int(val))
        self._save_camera_settings()

    def _load_camera_settings(self):
        key = self.reference_key
        if not key:
            return
        fmt = self.camera_settings.value(
            key + '/format', self.format_chooser.currentText(), type=str)
        exposure = self.camera_settings.value(
            key + '/exposure', self.exposure_spinner.value(), type=int)
        gain = self.camera_settings.value(
            key + '/gain', self.gain_spinner.value(), type=int)
        auto = (self.camera_settings.value(
            key + '/auto_exposure', False, type=bool)
                if self.camera_settings.contains(
                    key + '/auto_exposure') else None)
        self._loading_settings = True
        try:
            if self.format_chooser.findText(fmt) >= 0:
                self.setFormat(fmt)
            self.setExposure(exposure, save=False)
            blocker = QtCore.QSignalBlocker(self.gain_spinner)
            self.gain_spinner.setValue(gain)
            del blocker
            if gain != self.controller.gain:
                self.controller.set(gain=gain)
            if auto is not None:
                self.setAutoExposure(auto)
        finally:
            self._loading_settings = False

    def _save_camera_settings(self):
        key = self.reference_key
        if not key or not self.opened:
            return
        self.camera_settings.setValue(
            key + '/format', self.format_chooser.currentText())
        self.camera_settings.setValue(
            key + '/exposure', self.exposure_spinner.value())
        self.camera_settings.setValue(
            key + '/gain', self.gain_spinner.value())
        self.camera_settings.setValue(
            key + '/auto_exposure', self.auto_exposure.isChecked())
        self.camera_settings.sync()
    
    def acquire_image(self,timeout=1000):
        ret = self.controller.acquire_image(timeout)
        if ret:
            self.image_acquired.emit()
        return ret
        
    def trigger(self):
        self.controller.trigger()
        
    def wait(self,timeout=1000):
        ret = self.controller.wait(timeout)
        if ret:
            self.image_acquired.emit()
        return ret
        
    def get_config(self):
        return dict(exposure_time=self.exposure_time,
                    camera_name=self.display_name,
                    auto_exposure=self.auto_exposure.isChecked(),
                    format=self.format,
                    opened=self.opened,
                    online=self.online,
                    gain=self.gain,
                    cam_indx=self.cam_chooser.currentIndex())
    def set_config(self,config):
        if self.auto_exposure.isChecked() and 'exposure_time' in config:
            self.setAutoExposure(False)
        if 'cam_indx' in config:
            self.cam_chooser.setCurrentIndex(config['cam_indx'])
        if 'opened' in config:
            self.set_open(config['opened'])
        if 'format' in config:
            self.setFormat(config['format'])
        if 'exposure_time' in config:
            self.setExposure(config['exposure_time'])
        if 'gain' in config:
            self.setGain(config['gain'])
        if 'auto_exposure' in config and self.opened:
            self.setAutoExposure(config['auto_exposure'])
        if 'online' in config:
            self.set_online(config['online'])
        
    @property
    def online(self):
        return self.controller.online
    @property
    def opened(self):
        return self.controller.opened
    @property
    def image(self):
        return self.controller.image
    @property
    def x(self):
        return self.controller.x
    @property
    def y(self):
        return self.controller.y
    @property
    def datetime(self):
        return self.controller.datetime
    @property
    def exposure_time(self):
        return self.controller.exposure_time
    @property
    def gain(self):
        return self.controller.gain
    @property
    def format(self):
        return self.format_chooser.currentText()
        
if __name__=="__main__":
    # Standard 'boilerplate' code, common to all applications
    app = QtGui.QApplication(sys.argv)
    # Create widget
    widget=WebcamWidget()
    widget.setWindowTitle('Webcam Controller')
    widget.show()
    widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    # More boilerplate
    sys.exit(app.exec_())
