import pyqtgraph as pg
QtGui=pg.QtGui
from hardware.qt import CameraWidget,CameraROIChooser
from hardware.basler_pypylon_gige.driver import BaslerCamera

class BaslerWidget(CameraWidget):
    binning_modes=(1,1),(2,2),(4,4),(1,4)
    pixel_formats='Mono8','Mono16'
    
    def __init__(self,parent=None):
        CameraWidget.__init__(self,parent=parent)
        vbox=QtGui.QVBoxLayout()
        
        hbox=QtGui.QHBoxLayout()
        #self.setLayout(hbox)
        pb=QtGui.QPushButton("Scan")
        pb.clicked.connect(self.scan_cameras)
        hbox.addWidget(pb)
        cb=QtGui.QComboBox()
        self.camera_list=cb
        hbox.addWidget(cb)
        cb=QtGui.QCheckBox("Open")
        self.opened=cb
        cb.stateChanged.connect(self.open_or_close)
        hbox.addWidget(cb)
        vbox.addLayout(hbox)
        
        hbox=QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Exp(us):"))
        self.exposure = QtGui.QSpinBox()
        self.exposure.setRange(40,40949)
        self.exposure.valueChanged.connect(self.respond_exposure)
        hbox.addWidget(self.exposure)
        hbox.addWidget(QtGui.QLabel("Gain:"))
        self.gain = QtGui.QSpinBox()
        self.gain.setRange(192,511)
        self.gain.valueChanged.connect(self.respond_gain)
        hbox.addWidget(self.gain)
        self.binning = QtGui.QComboBox()
        for mode in self.binning_modes:
            self.binning.addItem('%dx%d'%mode)
        self.binning.currentIndexChanged.connect(self.respond_binning)
        hbox.addWidget(self.binning)
        self.pixelformat = QtGui.QComboBox()
        for fo in self.pixel_formats:
            self.pixelformat.addItem('%s'%fo)
        self.pixelformat.currentIndexChanged.connect(self.respond_pixelformat)
        hbox.addWidget(self.pixelformat)
        
        
        vbox.addLayout(hbox)
        
        self.roi=CameraROIChooser()
        self.roi.set_horizontal_increment(8)
        self.roi.set_vertical_increment(8)
        self.roi.changed.connect(self.respond_roi)
        vbox.addWidget(self.roi)
        
        # hbox=QtGui.QHBoxLayout()
        # hbox.addWidget(QtGui.QLabel("binx:"))
        # self.binx = QtGui.QSpinBox()
        # self.binx.setRange(0,4)
        # self.binx.valueChanged.connect(self.respond_binning_x)
        # hbox.addWidget(self.binx)
        # hbox.addWidget(QtGui.QLabel("biny:"))
        # self.biny = QtGui.QSpinBox()
        # self.biny.setRange(0,4)
        # self.biny.valueChanged.connect(self.respond_binning_y)
        # hbox.addWidget(self.biny)

       ##   vbox.addLayout(hbox)
        
        self.setLayout(vbox)
        
        self.setContentsMargins(0,0,0,0)
        
        self.driver=BaslerCamera()
        self.scan_cameras()
        
    def scan_cameras(self):
        cameras=self.driver.get_available_cameras()
        self.camera_list.clear()
        for camera in cameras:
            self.camera_list.addItem(camera.friendly_name)
        
    def open_or_close(self,state):
        if state:
            # opening
            self.driver.open(self.camera_list.currentIndex())
            self.camera_list.setEnabled(False)
            #self.roi.set_max_width(self.driver.cam.properties['WidthMax'])
            #self.roi.set_max_height(self.driver.cam.properties['HeightMax'])
            self.exposure.setValue(self.driver.exposure_us)
            self.gain.setValue(self.driver.gain) 
            self.set_roimax()
            self.roi.set_roi(self.driver.roi)
            mode=self.driver.binning_x,self.driver.binning_y
            mode_index=self.binning_modes.index(mode)
            self.binning.setCurrentIndex(mode_index)
            fmt_ix = self.pixel_formats.index(self.driver.pixelformat)
            self.pixelformat.setCurrentIndex(fmt_ix)
            
        else:
            # closing
            self.camera_list.setEnabled(True)
            self.driver.close()
        self.online_changed.emit(self.online)
    
    def trigger(self):
        pass
        
    def wait(self,timeout=5000):
        self.driver.wait(timeout)
        self.image_acquired.emit()
        return True

    def respond_exposure(self):
        self.driver.set_exposure(self.exposure.value())
        
    def respond_gain(self):
        self.driver.set_gain(self.gain.value())
    
    def respond_roi(self,roi):
        self.driver.set_roi(roi)
        self.roi.set_roi(self.driver.roi)
    
    def set_roimax(self):
        self.roi.set_max_width(self.driver.cam.properties['WidthMax'])
        self.roi.set_max_height(self.driver.cam.properties['HeightMax'])
    
    def respond_binning(self,ix):
        x,y=self.binning_modes[ix]
        self.driver.set_binning_x(x)
        self.driver.set_binning_y(y)
        self.set_roimax()
        self.respond_roi(self.roi)
        
    def respond_pixelformat(self,ix):
        pixformat = self.pixel_formats[ix]
        self.driver.set_pixelformat(pixformat)
        
    def get_config(self):
        pass
        
    @property
    def image(self):
        return self.driver.image
        
    @property
    def x(self):
        return self.driver.x
        
    @property
    def y(self):
        return self.driver.y
    
    @property
    def online(self):
        return self.driver is not None and self.driver.online
        
    @property
    def datetime(self):
        return self.driver.datetime
        
if __name__=="__main__":
    w=BaslerWidget()
    w.show()
    w.online
    
    if 0:
        ##
        w.acquire_image()
        import matplotlib.pyplot as plt
        plt.imshow(w.image)
        plt.show()
        ##
