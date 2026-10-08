import logging
from PyQt5 import QtGui, QtWidgets,QtCore
from . import PymbaCamera,pixel_formats,get_available_camera,vimba
import hardware.qt
from hardware.qt import CameraWidget,CameraROIChooser

logger=logging.getLogger(__name__)
    
class PymbaCameraWidget(CameraWidget):
    """QWidget for controlling a camera through the Pymba Interface.
    """
    def __init__(self,parent=None):
        def make_label(string):
            label=QtGui.QLabel(string)
            label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
            return label
        """Setup GUI, no camera selected."""
        super().__init__(parent=parent)
        vbox=QtGui.QVBoxLayout()
        # Camera desc and choose button
        hbox=QtGui.QHBoxLayout()
        self.camera_desc=QtGui.QLabel('No camera selected')
        hbox.addWidget(self.camera_desc)
        choose_cam=QtGui.QPushButton('...')
        choose_cam.clicked.connect(self.choose_camera)
        hbox.addWidget(choose_cam)
        vbox.addLayout(hbox)
        # Exposure time and pixel format
        hbox=QtGui.QHBoxLayout()
        hbox.addWidget(make_label('Exposure (ms):'))
        self.exposure_time=QtGui.QSpinBox()
        self.exposure_time.setRange(0,10000)
        self.exposure_time.valueChanged.connect(self._exposure_time_changed)
        hbox.addWidget(self.exposure_time)
        hbox.addWidget(make_label('Pixel format:'))
        self.pixel_format=QtGui.QComboBox()
        for format in pixel_formats:
            self.pixel_format.addItem(format)
        self.pixel_format.activated.connect(self._pixel_format_changed)
        hbox.addWidget(self.pixel_format)
        vbox.addLayout(hbox)
        # Mode selector and description
        hbox=QtGui.QHBoxLayout()
        hbox.addWidget(make_label('Mode:'))
        self.iidc_mode=QtGui.QComboBox()
        for mode_num in range(7):
            self.iidc_mode.addItem(str(mode_num))
        self.iidc_mode.activated.connect(self.respond_iidc_mode)
        hbox.addWidget(self.iidc_mode)
        self.iidc_mode_description=QtGui.QLabel()
        hbox.addWidget(self.iidc_mode_description)
        vbox.addLayout(hbox)
        # ROI 
        self.roi=CameraROIChooser()
        self.roi.set_horizontal_increment(4)
        self.roi.set_vertical_increment(4)
        self.roi.changed.connect(self.respond_roi)
        vbox.addWidget(self.roi)
        
        self.setLayout(vbox)
        self.camera=None
        self.closed_camera_settings={}
        id=get_available_camera()
        if id is not None:
            self.open_camera(id)
        
    def choose_camera(self):
        """Presents user with dialog box allowing them to choose a camera. Sets
        a new camera (or no camera) if the user chooses to do so."""
        ids=vimba.getCameraIds(refresh=True)
        descs=[vimba.getCameraInfo(id).cameraName.decode()+' '+id for id in ids]+['none']
        desc,ok=QtGui.QInputDialog.getItem(self,'Choose camera','Camera:',descs,0)
        if not ok:
            return
        index=descs.index(desc)
        if index<len(ids):
            id=ids[index]
        else:
            id=None
        current_id=self.camera.id if self.camera is not None else None
        if id==current_id:
            return
        if self.camera is not None:
            self.close_camera()
        if id is not None:
            self.open_camera(id)
        
    def close_camera(self):
        assert self.camera is not None
        self.closed_camera_settings=self.get_settings()
        logger.info('Closing PymbaCamera')
        # this will cause self.online_changed to be emitted
        self.camera.close() 
        self.camera=None
        self.update_gui()
    
    def open_camera(self,id):
        """
        Args:
            id: shouldn't be None
        """
        logger.debug('Creating PymbaCamera id %s',id)
        self.camera=PymbaCamera(id)
        self.camera.open()
        self.camera.online_changed=self.online_changed.emit
        self.camera.format_changed=self.format_changed.emit
        self.update_gui()
        self.online_changed.emit(True)
        self.camera.check_validity()
            
    def _exposure_time_changed(self):
        self.camera.set(exposure_time=self.exposure_time.value()*1000)
        self.exposure_time.setValue(self.camera.exposure_time/1000)
        
    def _pixel_format_changed(self):
        self.camera.set(pixel_format=pixel_formats[self.pixel_format.currentIndex()])
        self.pixel_format.setCurrentIndex(pixel_formats.index(self.camera.pixel_format))
        
    def respond_iidc_mode(self,v):
        self.camera.set(iidc_mode_number=v)
        self.iidc_mode_description.setText(self.camera.iidc_mode_description)
        self.roi.set_max_width(self.camera.max_width)
        self.roi.set_max_height(self.camera.max_height)
        # Changing the mode can also change the ROI
        self.roi.set_roi(self.camera.roi,False)
        
    def respond_roi(self,roi):
        self.camera.set(roi=roi)
        
    def update_gui(self):
        for control in (self.exposure_time,self.pixel_format):
            control.setEnabled(self.camera is not None)
        if self.camera is not None:
            self.camera_desc.setText(self.camera.name+' '+self.camera.id)
            self.exposure_time.setValue(self.camera.exposure_time/1000)
            self.pixel_format.setCurrentIndex(pixel_formats.index(self.camera.pixel_format))
            self.iidc_mode.setCurrentIndex(self.camera.iidc_mode_number)
            self.iidc_mode_description.setText(self.camera.iidc_mode_description)
            self.roi.set_max_width(self.camera.max_width)
            self.roi.set_max_height(self.camera.max_height)
            self.roi.set_roi(self.camera.roi,False)
        else:
            self.camera_desc.setText('no camera selected')
            
    def trigger(self):
        self.camera.trigger()
        
    def wait(self,timeout=1000):
        return self.camera.wait(timeout)
        
    @property
    def image(self):
        return self.camera.image
        
    @property
    def x(self):
        return self.camera.x
        
    @property
    def y(self):
        return self.camera.y
    
    @property
    def online(self):
        return self.camera is not None and self.camera.online
        
    @property
    def datetime(self):
        return self.camera.datetime
#hardware.qt.widget_classes['pymbax']=PymbaCameraWidget
