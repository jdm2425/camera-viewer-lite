from PyQt5 import QtWidgets, QtCore
from hardware.qt import CameraWidget
import cv2
import numpy as np
import scipy.ndimage
import mathx
import logging
import pickle,os
import copy
from datetime import datetime
from functools import partial
logger = logging.getLogger(__name__)
# logger.setLevel(logger.debug)

class Image:
    def __init__(self,x=None,y=None,image=None,datetime=None,info=None):
        self.x = x
        self.y = y
        self.image = image
        self.datetime = datetime
        self.info = info

class ImageProcessorStd(CameraWidget):
    """
    Standard image processing unit with most common processors added
    Listens to the actual camera controller. When this acquires an image:
        1. Feeds image into first processor unit
        2. When last processor unit emits its "changed" signal, takes the result and updates its own image
        3. Then emits "image_acquired" signal to notify that an image has been acquired
    """
    def __init__(self,camera,parent=None):
        super().__init__(parent=parent)
        self.camera = camera
        vbox = QtWidgets.QVBoxLayout()
        vbox.setSpacing(1)
        self.setLayout(vbox)
        self.processors = []
        self.addProcessor(ChannelSelector())
        self.addProcessor(FixedBGRmvr())
        self.addProcessor(EdgeBGRmvr())
        self.addProcessor(Thresholder())
        self.addProcessor(Exponentiator())
        self.addProcessor(GaussianBlurrer())
        self.addProcessor(MedianFilter())
        self.addProcessor(Cropper())
        self.addProcessor(Transposer())
        
        #If the camera sends its "acquired" signal, feed the camera image into the first image processor
        self.camera.image_acquired.connect(lambda:self.processors[0].set_input(Image(self.camera.x,self.camera.y,self.camera.image,self.camera.datetime)))
        #When the last processor has finished, make this the current image (set_image)
        self.processors[-1].changed.connect(lambda:self.set_image(self.processors[-1].output))
        
        self.setMaximumHeight(300)
        
    def addProcessor(self,processor):
        self.processors.append(processor)
        setattr(self,type(processor).__name__,processor)
        self.layout().addWidget(processor)
        #processor.layout().setMargin(1)
        if len(self.processors) >1:
            last_added = self.processors[-2]
            last_added.changed.connect(lambda:processor.set_input(last_added.output))
            last_added.changed.connect(lambda:logger.debug("%s changed" % last_added))
            logger.debug("Connected %s to %s" % (last_added,processor))
    def set_image(self,input):
        if input is None:
            self.image = None
            self.x = None
            self.y = None
            self.datetime = None
        else:
            self.image = input.image
            self.x = input.x
            self.y = input.y
            self.datetime = input.datetime
            logger.debug('ImageProcessorStd: emit image_acquired')
            self.image_acquired.emit()   
    def trigger(self):
        self.camera.trigger()
    def wait(self,timeout):
        self.camera.wait(timeout)
    def acquire_image(self,timeout=1000):
        self.camera.acquire_image(timeout)
    def get_config(self):
        return {type(self.processors[ii]).__name__ : self.processors[ii].get_config() for ii in range(len(self.processors))}
    def set_config(self,config):
        for ii in range(len(self.processors)):
            if type(self.processors[ii]).__name__ in config:
                self.processors[ii].set_config(config[type(self.processors[ii]).__name__])
        
class ImageProcessorStd_Compact(CameraWidget):
    """
    Compact version of ImageProcessorStd. Just shows a button for settings, which then shows the actual processing window. This can be closed and opened again
    """
    def __init__(self,camera,text='Image Processing',parent=None):
        super().__init__(parent=parent)
        self.camera = camera
        self.processorStd = ImageProcessorStd(camera)
        self.processorStd.image_acquired.connect(self.image_acquired.emit)
        self.processorStd.setWindowTitle('Image Processing settings')
        hbox = QtWidgets.QHBoxLayout()
        self.showButton = QtWidgets.QPushButton(text)
        self.showButton.clicked.connect(self.processorStd.show)
        hbox.addWidget(self.showButton)
        self.setLayout(hbox)
    def acquire_image(self,timeout=1000):
        self.processorStd.acquire_image(timeout)
    def get_config(self):
        return self.processorStd.get_config()
    def set_config(self,config):
        self.processorStd.set_config(config)
    @property
    def x(self):
        return self.processorStd.x
    @property
    def y(self):
        return self.processorStd.y
    @property
    def datetime(self):
        return self.processorStd.datetime
    @property
    def image(self):
        return self.processorStd.image
    

class FixedBGRmvr(QtWidgets.QWidget):
    responded=QtCore.pyqtSignal()
    changed=QtCore.pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.output = None
        self.input = None
        self.BG = None
        hbox = QtWidgets.QHBoxLayout()
        self.on = QtWidgets.QCheckBox('Constant Background removal')
        hbox.addWidget(self.on)
        self.readBG = QtWidgets.QPushButton('Read')
        hbox.addWidget(self.readBG)
        self.clearBG = QtWidgets.QPushButton('Clear')
        hbox.addWidget(self.clearBG)
        self.setLayout(hbox)
        self.readBG.clicked.connect(self.clickedRead)
        self.clearBG.clicked.connect(self.clickedClear)
        self.on.stateChanged.connect(self.respond_on)
    def respond_on(self):
        self.proc()
        self.responded.emit()
    def clickedRead(self):
        self.BG = copy.copy(self.input)
        self.proc()
        self.responded.emit()
    def clickedClear(self):
        self.BG = None
        self.proc()
        self.responded.emit()
    def proc(self):
        logger.debug('Fixed BG processing')    
        if self.on.isChecked() and (self.input is not None) and (self.BG is not None) and (self.BG.image.shape==self.input.image.shape):
            self.output = copy.copy(self.input)
            self.output.image = self.input.image - self.BG.image
        else:
            self.output = self.input
        self.changed.emit()
    def set_input(self,input):
        logger.debug('Fixed BG remover input set')
        self.input = input
        self.proc()
    def get_config(self):
        if self.BG is not None:
            pth = os.path.join(os.path.expanduser('~'),'Saved_Backgrounds')
            if not os.path.isdir(pth):
                os.makedirs(pth)
            fname = 'img_BG_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.bg'
            fpath=os.path.join(pth,fname)
            with open(os.path.join(pth,fpath),'wb') as file:
                pickle.dump(self.BG,file)
        else:
            fpath=None
        return dict(on=self.on.isChecked(),BGfile=fpath)
    def set_config(self,config):
        if config['BGfile'] is not None:
            with open(config['BGfile'],'rb') as file:
                self.BG = pickle.load(file)
        self.on.setChecked(config['on'])
        

class Exponentiator(QtWidgets.QWidget):
    responded=QtCore.pyqtSignal()
    changed=QtCore.pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.output = None
        self.input = None
        hbox = QtWidgets.QHBoxLayout()
        self.on = QtWidgets.QCheckBox('Exponent')
        hbox.addWidget(self.on)
        self.exponent = QtWidgets.QDoubleSpinBox()
        self.exponent.setRange(1,100)
        hbox.addWidget(self.exponent)
        self.setLayout(hbox)
        self.on.stateChanged.connect(self.respond_on)
        self.exponent.valueChanged.connect(self.respond_exponent)
    def respond_on(self):
        self.proc()
        self.responded.emit()
    def respond_exponent(self):
        if self.on.isChecked():
            self.proc()
            self.responded.emit()
    def proc(self):
        logger.debug('Exponentiator processing')
        if self.on.isChecked() and (self.input is not None):
            self.output = copy.copy(self.input)
            exponent = self.exponent.value()
            max = np.max(self.input.image)
            tmp = np.power(self.input.image,exponent)
            self.output.image = np.sign(self.input.image)*tmp/(np.power(max,exponent-1))
        else:
            self.output = self.input
        self.changed.emit()
    def set_input(self,input):
        logger.debug('Exponentiator input set')
        self.input=input
        self.proc()
    def get_config(self):
        return dict(on=self.on.isChecked(),exponent=self.exponent.value())
    def set_config(self,config):
        self.exponent.setValue(config['exponent'])
        self.on.setChecked(config['on'])


class ChannelSelector(QtWidgets.QWidget):
    responded = QtCore.pyqtSignal()
    changed = QtCore.pyqtSignal()
    def __init__(self,parent = None):
        super().__init__(parent=parent)
        self.output = None
        self.input=None
        hbox = QtWidgets.QHBoxLayout()
        self.R = QtWidgets.QCheckBox('R')
        self.R.setChecked(True)
        self.G = QtWidgets.QCheckBox('G')
        self.B = QtWidgets.QCheckBox('B')
        hbox.addWidget(self.R)
        hbox.addWidget(self.G)
        hbox.addWidget(self.B)
        self.setLayout(hbox)
        self.R.stateChanged.connect(self.respond)
        self.G.stateChanged.connect(self.respond)
        self.B.stateChanged.connect(self.respond)
    def respond(self):
        self.proc()
        self.responded.emit()
    def proc(self):
        logger.debug('Channel selector processing')
        if self.input is not None:
            self.output = copy.copy(self.input)
            self.input.image = self.input.image.squeeze()
            if len(self.input.image.shape)==3 and (self.input.image.shape[2] == 3):
                self.output.image = self.input.image[:,:,np.array([self.R.isChecked(),self.G.isChecked(),self.B.isChecked()])].sum(2)
            elif len(self.input.image.shape)==2:
                self.output = self.input
            else:
                raise Exception("Too many or too few dimensions in image")
        self.changed.emit()
    def set_input(self,input):
        logger.debug('Channel selector input set')
        self.input=input
        self.proc()
    def get_config(self):
        return dict(R=self.R.isChecked(),G=self.G.isChecked(),B=self.B.isChecked())
    def set_config(self,config):
        self.R.setChecked(config['R'])
        self.G.setChecked(config['G'])
        self.B.setChecked(config['B'])
        

class Cropper(QtWidgets.QWidget):
    responded  = QtCore.pyqtSignal()
    changed=QtCore.pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.output = None
        self.input = None
        hbox = QtWidgets.QHBoxLayout()
        self.on = QtWidgets.QCheckBox('Crop')
        hbox.addWidget(self.on)
        grid = QtWidgets.QGridLayout()
        hbox.addLayout(grid)
        grid.addWidget(QtWidgets.QLabel('Xmin:'),0,0)
        self.xmin = QtWidgets.QSpinBox()
        grid.addWidget(self.xmin,0,1)
        grid.addWidget(QtWidgets.QLabel('Xmax:'),1,0)
        self.xmax = QtWidgets.QSpinBox()
        grid.addWidget(self.xmax,1,1)
        grid.addWidget(QtWidgets.QLabel('Ymin:'),0,2)
        self.ymin = QtWidgets.QSpinBox()
        grid.addWidget(self.ymin,0,3)
        grid.addWidget(QtWidgets.QLabel('Ymax:'),1,2)
        self.ymax = QtWidgets.QSpinBox()
        grid.addWidget(self.ymax,1,3)
        self.current = QtWidgets.QPushButton('Current') #this has to be connected from the outside, since the processor does not know anything about display axes
        self.current.setEnabled(False)
        hbox.addWidget(self.current)
        self.setLayout(hbox)
        self.xmin.setRange(0,100000)
        self.xmax.setRange(0,100000)
        self.ymin.setRange(0,100000)
        self.ymax.setRange(0,100000)
        self.xmin.valueChanged.connect(self.respond)
        self.xmax.valueChanged.connect(self.respond)
        self.ymin.valueChanged.connect(self.respond)
        self.ymax.valueChanged.connect(self.respond)
        self.on.stateChanged.connect(self.respond)
    def respond(self):
        self.proc()
        self.responded.emit()
    def proc(self):
        logger.debug('Cropper processing')
        if self.input is None:
            self.output = self.input
            self.changed.emit()
            return
        if self.on.isChecked():
            self.output = copy.copy(self.input)
            x_logical = np.logical_and(self.input.x>=self.xmin.value(),self.input.x<=self.xmax.value()).squeeze()
            y_logical = np.logical_and(self.input.y>=self.ymin.value(),self.input.y<=self.ymax.value()).squeeze()
            self.output.image = self.input.image[np.ix_(x_logical,y_logical)]
            self.output.x = self.input.x[x_logical]
            self.output.y = self.input.y[y_logical]    
            if not (self.output.image.shape[1]>1 and self.output.image.shape[0]>1):
                self.output.x = None
                self.output.x = None
                self.output.image = None
        else:
            self.output = self.input
        self.changed.emit()
    def set_input(self,input):
        logger.debug('Cropper input set')
        self.input=input
        self.proc()
    def get_config(self):
        return dict(on=self.on.isChecked(),xmin=self.xmin.value(),xmax=self.xmax.value(),ymin=self.ymin.value(),ymax=self.ymax.value())
    def set_config(self,config):
        self.xmax.setValue(config['xmax'])
        self.xmin.setValue(config['xmin'])
        self.ymin.setValue(config['ymin'])
        self.ymax.setValue(config['ymax'])
        self.on.setChecked(config['on'])
    def set_lims(self,xmin,xmax,ymin,ymax):
        self.xmax.setValue(xmax)
        self.xmin.setValue(xmin)
        self.ymin.setValue(ymin)
        self.ymax.setValue(ymax)
        
class Transposer(QtWidgets.QWidget):
    responded  = QtCore.pyqtSignal()
    changed=QtCore.pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.output = None
        self.input = None
        hbox = QtWidgets.QHBoxLayout()
        self.swap_XY = QtWidgets.QCheckBox('Swap XY')
        hbox.addWidget(self.swap_XY)
        self.flip_h = QtWidgets.QCheckBox('Flip H')
        hbox.addWidget(self.flip_h)
        self.flip_v = QtWidgets.QCheckBox('Flip V')
        hbox.addWidget(self.flip_v)
        self.setLayout(hbox)
        
        self.swap_XY.toggled.connect(self.respond)
        self.flip_h.toggled.connect(self.respond)
        self.flip_v.toggled.connect(self.respond)
        
    def respond(self):
        self.proc()
        self.responded.emit()
        
    def proc(self):
        logger.debug('Transposer processing')
        if (not any([self.swap_XY.isChecked(),self.flip_h.isChecked(),self.flip_v.isChecked()])) or self.input is None:
            self.output = self.input
            self.changed.emit()
            return
        else:
            self.output = copy.copy(self.input)
        if self.swap_XY.isChecked():
            dims = np.arange(self.output.image.ndim)
            dims[0], dims[1] = (1, 0)
            self.output.image = self.output.image.transpose(dims)
            self.output.x = self.input.y.transpose()
            self.output.y = self.input.x.transpose()
            logger.debug('Transposer: XY swapped')
        if self.flip_h.isChecked():
            self.output.image = np.flipud(self.output.image)
            logger.debug('Transposer: Flipped Horizontally')
        if self.flip_v.isChecked():
            self.output.image = np.fliplr(self.output.image)
            logger.debug('Transposer: Flipped Vertically')
        self.changed.emit()
    def set_input(self,input):
        logger.debug('Transposer input set')
        self.input=input
        self.proc()
    def get_config(self):
        return dict(swap_XY=self.swap_XY.isChecked(),flip_h=self.flip_h.isChecked(),flip_v=self.flip_v.isChecked())
    def set_config(self,config):
        self.swap_XY.setChecked(config['swap_XY'])
        self.flip_h.setChecked(config['flip_h'])
        self.flip_v.setChecked(config['flip_v'])

class Thresholder(QtWidgets.QWidget):
    responded  = QtCore.pyqtSignal()
    changed=QtCore.pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.output = None
        self.input = None
        hbox = QtWidgets.QHBoxLayout()
        self.on = QtWidgets.QCheckBox('Threshold')
        hbox.addWidget(self.on)
        self.thrValue = QtWidgets.QDoubleSpinBox()
        self.thrValue.setRange(-100000000,100000000)
        hbox.addWidget(self.thrValue)
        self.thrAsPercent = QtWidgets.QCheckBox('% of peak')
        hbox.addWidget(self.thrAsPercent)
        self.setLayout(hbox)
        self.on.stateChanged.connect(self.respond)
        self.thrAsPercent.stateChanged.connect(self.respond)
        self.thrValue.valueChanged.connect(self.respond)
    def respond(self):
        self.proc()
        self.responded.emit()
    def proc(self):
        logger.debug('Thresholder processing')
        if self.on.isChecked() and (self.input is not None):
            self.output = copy.copy(self.input)
            if self.thrAsPercent.isChecked():
                thr = self.thrValue.value()/100 * np.max(self.input.image)
            else:
                thr = self.thrValue.value()
            low_val_indices = self.output.image < thr
            self.output.image[low_val_indices] = 0
        else:
            self.output=self.input
        self.changed.emit()
    def set_input(self,input):
        logger.debug('Thresholder input set')
        self.input=input
        self.proc()
    def get_config(self):
        return dict(on=self.on.isChecked(),thrValue=self.thrValue.value(),thrAsPercent=self.thrAsPercent.isChecked())
    def set_config(self,config):
        self.thrValue.setValue(config['thrValue'])
        self.thrAsPercent.setChecked(config['thrAsPercent'])
        self.on.setChecked(config['on'])
            
class GaussianBlurrer(QtWidgets.QWidget):
    responded=QtCore.pyqtSignal()
    changed=QtCore.pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.output = None
        self.input = None
        hbox = QtWidgets.QHBoxLayout()
        self.on = QtWidgets.QCheckBox('Gaussian Blur')
        hbox.addWidget(self.on)
        hbox.addWidget(QtWidgets.QLabel('Amount:'))
        self.amount = QtWidgets.QSpinBox()
        self.amount.setEnabled(False)
        self.amount.setRange(1,10000)
        hbox.addWidget(self.amount)
        self.setLayout(hbox)
        self.on.stateChanged.connect(self.respond_on)
        self.amount.valueChanged.connect(self.respond_amount)
    def respond_on(self):
        self.amount.setEnabled(self.on.isChecked())
        self.proc()
        self.responded.emit()
    def respond_amount(self):
        if self.on.isChecked():
            self.proc()
            self.responded.emit()
    def proc(self):
        logger.debug('Gaussian Blurrer processing')
        if self.on.isChecked() and (self.input is not None):
            amount = self.amount.value()
            self.output = copy.copy(self.input)
            self.output.image=scipy.ndimage.gaussian_filter(self.input.image,amount)
        else:
            self.output=self.input
        self.changed.emit()
    def set_input(self,input):
        logger.debug('Gaussian Blurrer input set')
        self.input=input
        self.proc()
    def get_config(self):
        return dict(on=self.on.isChecked(),amount=self.amount.value())
    def set_config(self,config):
        self.amount.setValue(config['amount'])
        self.on.setChecked(config['on'])

class MedianFilter(QtWidgets.QGroupBox):
    responded=QtCore.pyqtSignal()
    changed=QtCore.pyqtSignal()
    def __init__(self,parent=None):
        QtWidgets.QGroupBox.__init__(self,'Median Filter:',parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.output = None
        self.input = None
        hbox=QtWidgets.QHBoxLayout()
        lab=QtWidgets.QLabel('Size:')
        lab.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        hbox.addWidget(lab)
        self.size=QtWidgets.QSpinBox()
        self.size.setMinimum(2)
        self.size.setMaximum(10)
        hbox.addWidget(self.size)
        self.setLayout(hbox)
        # signals
        self.toggled.connect(self.respond_on)
        self.size.valueChanged.connect(self.respond_size)
    def proc(self):
        logger.debug('Median Filter processing')
        size=self.size.value()
        if self.isChecked() and (self.input is not None):
            self.output = copy.copy(self.input)
            self.output.image=scipy.ndimage.filters.median_filter(self.input.image,size)
            # tried this, much slower and froze:
            #self.output=scipy.signal.medfilt(self.input,size*2-1)
        else:
            self.output=self.input
        self.changed.emit()
    def set_input(self,input):
        self.input=input
        logger.debug('Median Filter input set')
        self.proc()
    def respond_size(self):
        if self.isChecked():
            self.proc()
            self.responded.emit()
    def respond_on(self):
        self.proc()
        self.responded.emit()
    def get_config(self):
        return dict(on=self.isChecked(),size=self.size.value())
    def set_config(self,config):
        self.size.setValue(config['size'])
        self.setChecked(config['on'])

def border(x):
    return np.c_[x[[0,-1],0:],x[1:-1,[0,-1]].T]
class EdgeBGRmvr(QtWidgets.QWidget):
    responded=QtCore.pyqtSignal()
    changed=QtCore.pyqtSignal()
    def __init__(self,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.output = None
        self.input = None
        self.on=QtWidgets.QCheckBox('Edge BG remover',self)
        hbox=QtWidgets.QHBoxLayout()
        hbox.addWidget(self.on)
        self.setLayout(hbox)
        #signals
        self.on.stateChanged.connect(self.respond_on)
    def respond_on(self):
        self.proc()
        self.responded.emit()
    def proc(self):
        logger.debug('Edge BG processing')
        if self.on.isChecked() and (self.input is not None):
            self.output = copy.copy(self.input)
            self.output.image=self.input.image-np.mean(border(self.input.image))
        else:
            self.output=self.input
        self.changed.emit()
    def set_input(self,input):
        logger.debug('Edge BG remover input set')
        self.input=input
        self.proc()
    def get_config(self):
        return dict(on=self.on.isChecked())
    def set_config(self,config):
        self.on.setChecked(config['on'])
