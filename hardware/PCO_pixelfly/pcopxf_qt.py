import pyqtgraph as pg
QtGui=pg.QtGui
from hardware.qt import CameraWidget
from hardware.PCO_pixelfly.pcopxf_driver import PCOpxfCamera

class PCOpxfWidget(CameraWidget):

    def __init__(self,parent=None):
        CameraWidget.__init__(self,parent=parent)
        self.binning_modes= (1,1),(1,2),(1,4), (2,1),(2,2),(2,4), (4,1),(4,2),(4,4)
        vbox=QtGui.QVBoxLayout()
        hbox=QtGui.QHBoxLayout()
        #self.setLayout(hbox)
        #pb=QtGui.QPushButton("Init")
        #pb.clicked.connect(self.scan_cameras)
        #hbox.addWidget(pb)
        #cb=QtGui.QComboBox()
        #self.camera_list=cb
        #hbox.addWidget(cb)
        cb=QtGui.QCheckBox("Open")
        self.opened=cb
        cb.stateChanged.connect(self.respond_open)
        hbox.addWidget(cb)
        cb=QtGui.QCheckBox("Arm")
        self.armedcb=cb
        cb.stateChanged.connect(self.respond_arm)
        hbox.addWidget(cb)
        vbox.addLayout(hbox)
        hbox=QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Exposure (us):"))
        self.exposure = QtGui.QSpinBox()
        self.exposure.setRange(0,1000000000)
        self.exposure.valueChanged.connect(self.respond_exposure)
        hbox.addWidget(self.exposure)
        #hbox.addWidget(QtGui.QLabel("Gain:"))
        #self.gain = QtGui.QSpinBox()
        #self.gain.setRange(0,23)
        #self.gain.valueChanged.connect(self.respond_gain)
        #hbox.addWidget(self.gain)
        self.binning = QtGui.QComboBox()
        for mode in self.binning_modes:
            self.binning.addItem('%dx%d'%mode)
        self.binning.currentIndexChanged.connect(self.respond_binning)
        hbox.addWidget(self.binning)
        #self.pixelformat = QtGui.QComboBox()
        #for fo in self.pixel_formats:
        #    self.pixelformat.addItem('%s'%fo)
        #self.pixelformat.currentIndexChanged.connect(self.respond_pixelformat)
        #hbox.addWidget(self.pixelformat)

        vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.setContentsMargins(0,0,0,0)
        self.driver=PCOpxfCamera()


    def respond_open(self,state):
        if state:
            # opening
            self.driver.open()
            #self.camera_list.setEnabled(False)
            #self.roi.set_max_width(self.driver.cam.properties['WidthMax'])
            #self.roi.set_max_height(self.driver.cam.properties['HeightMax'])
            self.exposure.setValue(self.driver.exposure_us)
            #mode=self.driver.binning_x,self.driver.binning_y
            #mode_index=self.binning_modes.index(mode)
            #self.binning.setCurrentIndex(mode_index)
            #fmt_ix = self.pixel_formats.index(self.driver.pixelformat)
            #self.pixelformat.setCurrentIndex(fmt_ix)
        else:
            # closing
            #self.camera_list.setEnabled(True)
            self.driver.close()
        self.online_changed.emit(self.online)
    
    def respond_arm(self,state):
        if state:   
            self.driver.preparerecording()
        else:
            self.driver.disarm_camera()
            
            
    def trigger(self):
        self.driver.trigger()
        
    def wait(self,timeout=5000):
        #self.driver.wait(timeout)
        #self.driver.trigger()
        self.driver.wait()
        self.image_acquired.emit()
        return True

    def respond_exposure(self):
        usms =1
        self.driver.set_exposure(self.exposure.value(),usms)
        
    
    def respond_binning(self,ix):
        x,y=self.binning_modes[ix]
        #self.driver.set_binning_x(x)
        #self.driver.set_binning_y(y)
        #self.set_roimax()
        #self.respond_roi()
        
   
        
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
    def armed(self):
        return self.driver is not None and self.driver.armed

        
    @property
    def datetime(self):
        return self.driver.datetime
        
if __name__=="__main__":
    w=PCOpxfWidget()
    w.show()
    #w.online
    
    if 0:
        ##
        w.acquire_image()
        import matplotlib.pyplot as plt
        plt.imshow(w.image)
        plt.show()
        ##
