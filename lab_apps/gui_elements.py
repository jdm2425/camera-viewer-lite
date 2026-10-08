from PyQt5 import QtWidgets, QtGui, QtCore
print("I AM NEW")


import sys
import os
from PyQt5 import QtWidgets, QtGui, QtCore

# ---- PyQt4 compatibility shim (MUST be before any class definitions) ----
QtGui.QWidget = QtWidgets.QWidget
QtGui.QApplication = QtWidgets.QApplication
QtGui.QMainWindow = QtWidgets.QMainWindow
QtGui.QDialog = QtWidgets.QDialog
QtGui.QVBoxLayout = QtWidgets.QVBoxLayout
QtGui.QHBoxLayout = QtWidgets.QHBoxLayout
QtGui.QGridLayout = QtWidgets.QGridLayout
QtGui.QPushButton = QtWidgets.QPushButton
QtGui.QLabel = QtWidgets.QLabel
QtGui.QCheckBox = QtWidgets.QCheckBox
QtGui.QComboBox = QtWidgets.QComboBox
QtGui.QSpinBox = QtWidgets.QSpinBox
QtGui.QGroupBox = QtWidgets.QGroupBox
QtGui.QTextEdit = QtWidgets.QTextEdit
QtGui.QFileDialog = QtWidgets.QFileDialog

from datetime import datetime
import numpy as np
from scipy import interpolate
from collections import deque, namedtuple
import pyqtgraph_extended as pg
import pyqtgraph_recipes
import fourier
from mathx.mathx import fwhm, moment


class CameraImageViewer(QtWidgets.QWidget):
    """A viewer for images from a camera. Image is shown in large plot, with plots left and below which show the vertical and horizontal marginals.
    Includes controls for commonly used axis functions (XY auto limits, change colormap,
    lock aspect ratio to 1:1), as well as buffer controls to temporarily save images, and ROI controls for the marginals.
    Args:
        lineout_num (int):  Number of buffer lineouts to allow. Default 3
        show_buffer_controls (bool):    True to show buffer controls, False to omit them. Default True
    """
    
    def __init__(self,parent=None,lineout_num=3,show_buffer_controls=True):
        super().__init__(parent = parent)
        vbox=QtWidgets.QVBoxLayout()  # main vbox
        self.mainplot = pyqtgraph_recipes.ImageWithProjsAligned()
        vbox.addWidget(self.mainplot.widget)
        self.setLayout(vbox)
        self.ax_cont = ImageAxisControls()
        vbox.addWidget(self.ax_cont)
        self.buffer_cont = ImageBufferControls(self)
        if show_buffer_controls:
            vbox.addWidget(self.buffer_cont)
        
        self.ax_cont.equal_aspect_ratio.stateChanged.connect(self._aspect_ratio_toggled)
        self.ax_cont.select_colormap.currentIndexChanged.connect(lambda:self.set_colormap(self.ax_cont.select_colormap.currentText()))
        self.ax_cont.auto_xy_limits.clicked.connect(self.auto_xy)
        self.ax_cont.auto_c_limits.clicked.connect(self.auto_c)
        
        self.set_colormap('flame')
        
    def setImage(self,x,y,img):
        self.buffer_cont.set_image(x,y,img)
        h,v = self.buffer_cont.get_projs()
        self.mainplot.set(x,y,img,horz_proj=h,vert_proj=v,
                          pen=pg.mkPen(getattr(self, 'projection_colour', 'k')))
        pg.QtWidgets.QApplication.processEvents()
        
    def _aspect_ratio_toggled(self):
        if self.ax_cont.equal_aspect_ratio.isChecked():
            self.mainplot.plots['image'].setAspectLocked(True,ratio=1)
        else:
            self.mainplot.plots['image'].setAspectLocked(False)
            
    def set_colormap(self,cm='grey'):
        if cm == 'parula':
            lut = pyqtgraph_recipes.parula()
        elif cm== 'parula_white':
            lut = pyqtgraph_recipes.parula_white()
        elif cm== 'jet_white_clip':
            lut = pyqtgraph_recipes.jet_white_clip()
        elif cm=='jet_white':
            lut = pyqtgraph_recipes.jet_white()
        else:
            lut = pg.get_colormap_lut(cm) 
        self.mainplot.image.setLookupTable(lut)
        
        if self.ax_cont.select_colormap.currentText != cm:
            cmaps = [self.ax_cont.select_colormap.itemText(i) for i in range(self.ax_cont.select_colormap.count())]
            self.ax_cont.select_colormap.setCurrentIndex(cmaps.index(cm))
        
    def auto_xy(self):
        self.mainplot.plots['image'].autoRange()

    def auto_c(self):
        mi = self.mainplot.image.image.min()
        ma = self.mainplot.image.image.max()
        self.mainplot.image.setLevels([mi,ma])
            
    def get_config(self):
        rect = self.mainplot.plots['image'].viewRect()
        return dict(ax_cont=self.ax_cont.get_config(),ax_lims=dict(xmin=rect.left(),xmax=rect.right(),ymin=rect.top(),ymax=rect.bottom()))
    def set_config(self,config):
        if 'ax_cont' in config:
            self.ax_cont.set_config(config['ax_cont'])
        if 'ax_lims' in config:
            self.mainplot.plots['image'].setRange(
                xRange=(config['ax_lims']['xmin'],config['ax_lims']['xmax']),
                yRange=(config['ax_lims']['ymin'],config['ax_lims']['ymax']))
        
class BeamRecorderImageViewer(QtWidgets.QWidget):
    """
    Same as CameraImageViewer but with extra axes for displaying historical images instead of buffer controls
    """
    def __init__(self,parent=None):
        super().__init__(parent = parent)
        vbox=QtWidgets.QVBoxLayout() #main vbox
        self.mainplot = pyqtgraph_recipes.ImageWithProjsAndLogAlignedPlot()
        vbox.addWidget(self.mainplot.widget)
        self.setLayout(vbox)
        self.ax_cont = ImageAxisControls()
        vbox.addWidget(self.ax_cont)
        self.vert_log_selector =pg.InfiniteLine(angle=90,pen=pg.mkPen('b',width=2),movable=False)
        self.mainplot.plots['vert_log'].addItem(self.vert_log_selector)
        self.horz_log_selector =pg.InfiniteLine(angle=0,pen=pg.mkPen('b',width=2),movable=False)
        self.mainplot.plots['horz_log'].addItem(self.horz_log_selector)
        self.vert_log_selector.sigDragged.connect(lambda:self.log_selector_update('v'))
        self.horz_log_selector.sigDragged.connect(lambda:self.log_selector_update('h'))
        self.log_selector_current_indx = None #saving the currently selected log entry, to avoid unnecessary re-draws
        self.log_img_override = False #allows the image showing currently selected log entry to be overriden (for instance by a reference image)
        
        self.ax_cont.equal_aspect_ratio.stateChanged.connect(self._aspectRatio_toggled)
        self.ax_cont.select_colormap.currentIndexChanged.connect(lambda:self.set_colormap(self.ax_cont.select_colormap.currentText()))
        self.ax_cont.auto_xy_limits.clicked.connect(self.auto_xy)
        
        self.set_colormap('flame')
        
    def setImage(self,x,y,img,datetimestr = None):
        """Update main image"""
        self.mainplot.set_image(x,y,img,datetimestr=datetimestr)
        pg.QtWidgets.QApplication.processEvents()
        
    def setLogImgOverride(self,x=None,y=None,img=None,datetimestr=None,on=True):
        """Override image in lower left plot to show custom input instead of historical image. 
        If on=False, re-sets image to be historical image"""
        if on is True:
            self.mainplot.set_log_img(x,y,img,datetimestr)
            self.log_img_override = True
        else:
            self.log_img_override = False
            self.log_selector_update(force_update=True)
            
    def setLog(self,x=None,y=None,log=None,datetime=None,indx=None):
        """Add historical images to plot"""
        if x is None:
            self.log = None
            self.log_x = None
            self.log_y = None
            self.log_datetime = None
            self.log_indcs = None
            self.vert_log_selector.setMovable(False)
            self.horz_log_selector.setMovable(False)
            self.mainplot.clear_log()
        else:
            self.log = log
            self.log_x = x
            self.log_y = y
            self.log_datetime = datetime
            self.log_indcs = np.arange(log.shape[0])
            self.mainplot.set_log(x,y,self.log_indcs,log.sum(2).transpose(),log.sum(1))
            self.vert_log_selector.setBounds((0,log.shape[0]-1))
            self.horz_log_selector.setBounds((0,log.shape[0]-1))
            self.vert_log_selector.setMovable(True)
            self.horz_log_selector.setMovable(True)
            self.log_selector_update(force_update=True)
        
    def log_selector_update(self,direction=None,force_update=False):
        """Called whenever either of the log selectors is moved.
        Args:
            direction (str):    'h' if the horizontal selector was dragged, 'v' for the vertical one
            force_update (bool):    If True, updates the plots even if the selected date and time has not changed"""
        if direction is 'h':
            self.vert_log_selector.setValue(self.horz_log_selector.value())
        elif direction is 'v':
            self.horz_log_selector.setValue(self.vert_log_selector.value())
        if self.log is None:
            self.mainplot.clear_log()
            return
        indx = self.vert_log_selector.value()
        indx_nearest = self.log_indcs[(np.abs(self.log_indcs-indx)).argmin()]
        if (not indx_nearest == self.log_selector_current_indx) or force_update:
            datetimestr = datetime.strptime(self.log_datetime[indx_nearest],'%Y%m%d_%H%M%S_%f').strftime('%Y%m%d %H:%M:%S')
            if not self.log_img_override:
                self.mainplot.set_log_img(self.log_x,self.log_y,self.log[indx_nearest],datetimestr)
            self.mainplot.set_log_lines(self.log_x,self.log_y,self.log[indx_nearest].sum(1),self.log[indx_nearest].sum(0))
            self.log_selector_current_indx = indx_nearest
            
    def setRef(self,x=None,y=None,hData=None,vData=None):
        if x is None:
            self.mainplot.clear_ref()
        else:
            self.mainplot.set_ref_lines(x,y,hData,vData)
        
    def _aspectRatio_toggled(self):
        if self.ax_cont.equal_aspect_ratio.isChecked():
            self.mainplot.plots['image'].setAspectLocked(True,ratio=1)
            self.mainplot.plots['log_image'].setAspectLocked(True,ratio=1)
            
        else:
            self.mainplot.plots['image'].setAspectLocked(False)
            self.mainplot.plots['log_image'].setAspectLocked(False)
            
    def set_colormap(self,cm='grey'):
        if cm == 'parula':
            lut = pyqtgraph_recipes.parula()
        elif cm== 'parula_white':
            lut = pyqtgraph_recipes.parula_white()
        elif cm== 'jet_white_clip':
            lut = pyqtgraph_recipes.jet_white_clip()
        elif cm=='jet_white':
            lut = pyqtgraph_recipes.jet_white()
        else:
            lut = pg.get_colormap_lut(cm) 
        self.mainplot.image.setLookupTable(lut)
        self.mainplot.logimg.setLookupTable(lut)
        self.mainplot.hlog.setLookupTable(lut)
        self.mainplot.vlog.setLookupTable(lut)
        
        if self.ax_cont.select_colormap.currentText != cm:
            cmaps = [self.ax_cont.select_colormap.itemText(i) for i in range(self.ax_cont.select_colormap.count())]
            self.ax_cont.select_colormap.setCurrentIndex(cmaps.index(cm))
        
    def auto_xy(self):
        self.mainplot.plots['image'].autoRange()
        
    def get_config(self):
        rect = self.mainplot.plots['image'].viewRect()
        return dict(ax_cont=self.ax_cont.get_config(),ax_lims=dict(xmin=rect.left(),xmax=rect.right(),ymin=rect.top(),ymax=rect.bottom()))
    def set_config(self,config):
        if 'ax_cont' in config:
            self.ax_cont.set_config(config['ax_cont'])
        if 'ax_lims' in config:
            self.mainplot.plots['image'].setRange(
                xRange=(config['ax_lims']['xmin'],config['ax_lims']['xmax']),
                yRange=(config['ax_lims']['ymin'],config['ax_lims']['ymax']))
        
class ImageAxisControls(QtWidgets.QWidget):
    """Basic set of controls for a set of axes containing an image.
        Does the following things:
            - Auto XY Limits
            - Lock aspect ratio to be equal
            - Select colourmap
    This just sets up the GUI, no actual setting is done.
    """
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        hbox = QtWidgets.QHBoxLayout()
        hbox.setSpacing(1)
        self.setLayout(hbox)
        self.auto_xy_limits = QtWidgets.QPushButton("XY Auto")
        hbox.addWidget(self.auto_xy_limits)
        self.equal_aspect_ratio = QtWidgets.QCheckBox("Equal aspect ratio")
        hbox.addWidget(self.equal_aspect_ratio)
        hbox.addWidget(QtWidgets.QLabel("Colormap:"))
        self.select_colormap = QtWidgets.QComboBox()
        self.select_colormap.addItems(['parula',
                                    'parula_white',
                                    'jet_white',
                                    'jet_white_clip',
                                    'thermal',
                                    'flame',
                                    'yellowy',
                                    'bipolar',
                                    'grey',
                                    'greyclip'])
        hbox.addWidget(self.select_colormap)
        self.auto_c_limits = QtWidgets.QPushButton("CLim Auto")
        hbox.addWidget(self.auto_c_limits)
                
    def get_config(self):
        return dict(colormap=self.select_colormap.currentText(),equal_aspect_ratio=self.equal_aspect_ratio.isChecked())
        
    def set_config(self,config):
        if 'colormap' in config:
            cm = config['colormap']
            cmaps = [self.select_colormap.itemText(i) for i in range(self.select_colormap.count())]
            self.select_colormap.setCurrentIndex(cmaps.index(cm))
        if 'equal_aspect_ratio' in config:
            self.equal_aspect_ratio.setChecked(config['equal_aspect_ratio'])
            
class ColormapSelector(QtWidgets.QComboBox):
    def __init__(self,images=[],parent=None):
        super().__init__(parent=parent)
        self.images = images
        self.addItems(['parula',
                        'parula_white',
                        'jet_white',
                        'jet_white_clip',
                        'thermal',
                        'flame',
                        'yellowy',
                        'bipolar',
                        'grey',
                        'greyclip'])
        self.currentIndexChanged.connect(lambda: self.set_colormap(self.currentText()))
        
    def set_colormap(self,cm='flame'):
        if cm == 'parula':
            lut = pyqtgraph_recipes.parula()
        elif cm== 'parula_white':
            lut = pyqtgraph_recipes.parula_white()
        elif cm== 'jet_white_clip':
            lut = pyqtgraph_recipes.jet_white_clip()
        elif cm=='jet_white':
            lut = pyqtgraph_recipes.jet_white()
        else:
            lut = pg.get_colormap_lut(cm) 
        for img in self.images:
            img.setLookupTable(lut)
        
        if self.currentText != cm:
            self.setCurrentIndex(self.findText(cm))
            
    def add_images(self,images):
        for img in images:
            self.images.append(img)
        
class ImageBufferControls(QtWidgets.QWidget):
    """Set of controls for image buffering (e.g. in CameraImageViewer)
    Offers three different ROI modes which determine how the coloured lineout (in the marginal plots) is obtained:
        Crosshair:  Single line of pixels for each horizontal and vertical direction, determined by draggable crosshair
        Rectangle:  Integrating over part of the image in each direction, region determined by a draggable and resizeable rectangle.
                    NOTE: Only one "direction" of the ROI given by the rectangle is used per direction of lineout. i.e. the horizontal lineout is
                    created by integrating over only parts of the y axis, but for ALL x, not just those in the rectangle
                    This is represented by lines continuing the rectangle sides to all sides which move with the rectangle
        Whole img:  Simply integrate the whole image along one direction, as is done when no buffer lineouts are shown at all. 
                    Effectively this simply adds coloured buffers to the already existing functionality of the CameraImageViewer's mainplot 
                    (see pyqtgraph_recipes::ImageWithProjsAligned)
    Lineouts are updated for both the current image and the buffered images (whole images are saved, not just projections) whenever the ROI changes
    
    Args:
            viewer:     An ImageViewer such as CameraImageViewer. Must have a method add_buffers that handles adding a number of buffer lines to a plot
                        Must also have a set_buffer_data method to set data based on the plot index returned by add_buffers
            num_colours:Number of coloured lines to be added. Changes number of buttons as well as lines added to the plot. Colour order is fixed as of time of writing
                        Defaults to 3 (red,green,blue). Maximum 6
            pen_style:  pen style to be used by the ROI and lines.
                        This can be used to add more than one instance of ImageBufferControls to a viewer and distinguish the lines
                        Defaults to a solid line (QtCore.Qt.SolidLine)
                        Other options include QtCore.Qt.[DashLine,DashDotLine...]
    """
                    
    button_colours = ['red','green','blue','magenta','cyan','yellow']
    def __init__(self,viewer,num_colours=3,pen_style = QtCore.Qt.SolidLine,parent=None):
        super().__init__(parent=parent)
        self.viewer = viewer
        if num_colours>3:
            raise ValueError('Maximum number of buffers is 6. Got {0}.'.format(num_colours))
        ##Set up GUI
        hbox = QtWidgets.QHBoxLayout()
        gbox = QtWidgets.QGroupBox()
        hbox_radio = QtWidgets.QHBoxLayout()
        self.radio_crosshair = QtWidgets.QRadioButton('Crosshair')
        self.radio_crosshair.setChecked(True)
        self.roi_style = 'crosshair'
        self.radio_rect = QtWidgets.QRadioButton('Rectangle')
        self.radio_all = QtWidgets.QRadioButton('Whole img')
        hbox_radio.addWidget(self.radio_crosshair)
        hbox_radio.addWidget(self.radio_rect)
        hbox_radio.addWidget(self.radio_all)
        gbox.setLayout(hbox_radio)
        hbox.addWidget(gbox)
        self.buttons_pick = []
        for i in range(num_colours):
            ##Add coloured buttons for buffer controls
            self.buttons_pick.append(QtWidgets.QPushButton())
            self.buttons_pick[i].setStyleSheet("background-color: "+ self.button_colours[i]+";")
            self.buttons_pick[i].setMinimumWidth(30)
            self.buttons_pick[i].clicked.connect(lambda checked,i=i:self._respond_pick(indx=i))
            hbox.addWidget(self.buttons_pick[i])
        self.check_show = QtWidgets.QCheckBox('Show')
        hbox.addWidget(self.check_show)
        self.setLayout(hbox)
        
        self.plot_indcs = viewer.mainplot.add_buffers(num_colours,pen_style=pen_style)
        
        pen = pg.mkPen('k', width=3, style=pen_style)
        self.crosshair = pg.CrosshairROI(pos=[50,50],size=[100000,10000],pen=pen)
        viewer.mainplot.plots['image'].addItem(self.crosshair)
        self.crosshair.sigRegionChanged.connect(lambda pos:self._update_lines())
        self.crosshair.hide()
        
        self.rect = pg.RectROI((50,50),(100,100),pen=pg.mkPen('k', width=3, style=pen_style))      
        viewer.mainplot.plots['image'].addItem(self.rect)
        self.rect.hide()
        self.rect_lines = {key : pg.InfiniteLine(pen=pg.mkPen('k', width=1, style=pen_style)) for key in ['left','right','top','bottom']}
        [viewer.mainplot.plots['image'].addItem(line) for line in self.rect_lines.values()]
        [line.hide() for line in self.rect_lines.values()]
        [self.rect_lines[key].setAngle(0) for key in ['top','bottom'] ]
        self.rect.sigRegionChanged.connect(lambda pos:self._update_lines())
        self.rect.sigRegionChanged.connect(self._update_rect_lines)
        self._update_rect_lines()
        
        [radio.toggled.connect(self._respond_radio) for radio in [self.radio_all,self.radio_crosshair,self.radio_rect] ]
        self.check_show.toggled.connect(self.set_show)
        
        self.current = dict(x=None,y=None,image=None)
        self.buffers = [dict(x=None,y=None,image=None) for i in range(num_colours)]
        
    def set_image(self,x,y,img):
        self.current['x'] = x.squeeze()
        self.current['y'] = y.squeeze()
        self.current['image'] = img
    
    def get_projs(self,x=None,y=None,image=None):
        """Get projections of image based on what ROI mode is active"""
        if not self.check_show.isChecked():
            return None,None
        if image is None:
            x = self.current['x']
            y = self.current['y']
            image = self.current['image']
        if self.roi_style == 'all':
            return image.sum(1),image.sum(0)
        elif self.roi_style == 'rect':
            pos = self.rect.pos()
            size = self.rect.size()
            xmin = pos[0]
            xmax = pos[0] + size[0]
            ymin = pos[1]
            ymax = pos[1] + size[1]
            x_logical = np.logical_and(x>=xmin,x<=xmax).squeeze()
            y_logical = np.logical_and(y>=ymin,y<=ymax).squeeze()
            return image[:,y_logical].sum(1),image[x_logical,:].sum(0)
        elif self.roi_style == 'crosshair':
            pos = self.crosshair.pos()
            x_nearest = x[np.abs(x-pos[0]).argmin()]
            y_nearest = y[np.abs(y-pos[1]).argmin()]
            x_logical = (x==x_nearest)
            y_logical = (y==y_nearest)
            return image[:,y_logical].squeeze(),image[x_logical,:].squeeze()
        else:
            return None,None #order: horz,vert
       
    def _respond_radio(self,val):
        if not val: #the "toggled" signal is emitted twice, both by the checked and unchecked radio button. only want this to execute once
            return
        if self.sender() is self.radio_all:
            self.roi_style = 'all'
        elif self.sender() is self.radio_rect:
            self.roi_style = 'rect'
        else:
            self.roi_style = 'crosshair'
        self._update_lines()
        self.set_show()
    
    def set_show(self,val=None):
        val = (self.check_show.isChecked() if val is None else val)
        if self.roi_style == 'crosshair' and val:
            self.crosshair.show()
            self.rect.hide()
            [line.hide() for line in self.rect_lines.values()]
        elif self.roi_style == 'rect' and val:
            self.rect.show()
            [line.show() for line in self.rect_lines.values()]
            self.crosshair.hide()
        else:
            self.rect.hide()
            [line.hide() for line in self.rect_lines.values()]
            self.crosshair.hide()
        [self.viewer.mainplot.hide_show_buffer(indx,val) for indx in self.plot_indcs]
        self._update_lines()
        
    def _respond_pick(self,indx):
        self.buffers[indx] = self.current.copy()
        self._update_lines(indx)
            
    def _update_lines(self,indx=None):
        #If no indx is given, update all
        if not self.check_show.isChecked():
            return
        if indx is None:
            for i in range(len(self.buffers)):
                if self.buffers[i]['x'] is not None:
                    h,v = self.get_projs(self.buffers[i]['x'],self.buffers[i]['y'],self.buffers[i]['image'])
                    self.viewer.mainplot.set_buffer_data(self.plot_indcs[i],self.buffers[i]['x'],self.buffers[i]['y'],h,v)
        else:
            if self.buffers[indx]['x'] is not None:
                h,v = self.get_projs(self.buffers[indx]['x'],self.buffers[indx]['y'],self.buffers[indx]['image'])
                self.viewer.mainplot.set_buffer_data(self.plot_indcs[indx],self.buffers[indx]['x'],self.buffers[indx]['y'],h,v)
                
    def _update_rect_lines(self):
        pos = self.rect.pos()
        size = self.rect.size()
        self.rect_lines['left'].setValue(pos[0])
        self.rect_lines['right'].setValue(pos[0] + size[0])
        self.rect_lines['bottom'].setValue(pos[1])
        self.rect_lines['top'].setValue(pos[1] + size[1])
        
class SpectrumViewer(QtWidgets.QWidget):
    """Viewer widget for spectra (e.g. from a spectrometer), with buffers and fourier transform options"""
    button_colours = ['red','green','blue','magenta','cyan','yellow']
    def __init__(self,parent=None,num_buffers=3):
        super().__init__(parent=parent)
        self.num_buffers = num_buffers
        ##Create plots
        self.plot_widgets = dict(spectrum=pg.GraphicsLayoutWidget(),ft=pg.GraphicsLayoutWidget())
        self.plot_items = dict(spectrum=self.plot_widgets['spectrum'].addAlignedPlot(),ft=self.plot_widgets['ft'].addAlignedPlot())
        self.plot_items['spectrum'].setLabels(bottom='Wavelength [nm]',left='Intensity')
        self.plot_items['ft'].setLabels(bottom='Pseudotime [fs]',left='Intensity')
        self.plot_lines = dict(spectrum=self.plot_items['spectrum'].plot(pen=pg.mkPen('k')),ft=self.plot_items['ft'].plot(pen=pg.mkPen('k')))
        ##Add plots to GUI
        vbox = QtWidgets.QVBoxLayout()
        vbox_plots = QtWidgets.QVBoxLayout()
        vbox_plots.addWidget(self.plot_widgets['spectrum'])
        vbox_plots.addWidget(self.plot_widgets['ft'])
        self.plot_widgets['ft'].hide()
        vbox.addLayout(vbox_plots)
        ##Add axis controls
        hbox = QtWidgets.QHBoxLayout()
        vbox.addLayout(hbox)
        self.push_XY_Auto = QtWidgets.QPushButton('XY Auto')
        self.push_XY_Auto.clicked.connect(self.xy_auto)
        hbox.addWidget(self.push_XY_Auto)
        hbox2 = QtWidgets.QHBoxLayout()
        self.check_log_spec = QtWidgets.QCheckBox('Spectrum')
        self.check_log_spec.toggled.connect(lambda val: self.plot_items['spectrum'].setLogMode(y=val))
        hbox2.addWidget(self.check_log_spec)
        self.check_log_ft = QtWidgets.QCheckBox('FT')
        self.check_log_ft.toggled.connect(lambda val: self.plot_items['ft'].setLogMode(y=val))
        hbox2.addWidget(self.check_log_ft)
        hbox.addWidget(wrap_in_panel(hbox2,'YLog'))
        hbox2 = QtWidgets.QHBoxLayout()
        self.check_show_ft = QtWidgets.QCheckBox('Show')
        self.check_show_ft.toggled.connect(self.set_show_ft)
        hbox2.addWidget(self.check_show_ft)
        self.check_thresh_ft = QtWidgets.QCheckBox('Threshold:')
        self.check_thresh_ft.toggled.connect(self.update_all)
        hbox2.addWidget(self.check_thresh_ft)
        self.spin_thresh_ft = QtWidgets.QSpinBox()
        self.spin_thresh_ft.setRange(-100000,100000)
        self.spin_thresh_ft.valueChanged.connect(self.update_all)
        hbox2.addWidget(self.spin_thresh_ft)
        self.check_sqrt_ft = QtWidgets.QCheckBox('Sqrt before FT')
        self.check_sqrt_ft.setChecked(True)
        self.check_sqrt_ft.toggled.connect(self.update_all)
        hbox2.addWidget(self.check_sqrt_ft)
        self.label_ft_fwhm = QtWidgets.QLabel('FWHM:          ')
        hbox2.addWidget(self.label_ft_fwhm)
        hbox.addWidget(wrap_in_panel(hbox2,'Fourier Transform'))
        
        ##Add buffer controls and buffer lines
        hbox = QtWidgets.QHBoxLayout()
        
        self.buttons_pick = []
        self.buttons_clear = []
        self.checks_show = []
        self.checks_normalise = []
        self.buffer_lines = dict(spectrum=[], ft=[])
        for i in range(num_buffers):
            hbox_inner = QtWidgets.QHBoxLayout()
            self.buttons_pick.append(QtWidgets.QPushButton('Pick'))
            self.buttons_pick[i].setStyleSheet("color: "+ self.button_colours[i]+";")
            self.buttons_pick[i].setMinimumWidth(30)
            self.buttons_pick[i].clicked.connect(lambda checked,i=i:self._respond_pick(indx=i))
            self.buttons_clear.append(QtWidgets.QPushButton('Clear'))
            self.buttons_clear[i].setStyleSheet("color: "+ self.button_colours[i]+";")
            self.buttons_clear[i].setMinimumWidth(30)
            self.buttons_clear[i].clicked.connect(lambda checked,i=i:self._respond_clear(indx=i))
            self.checks_show.append(QtWidgets.QCheckBox('Show'))
            self.checks_normalise.append(QtWidgets.QCheckBox('Normalise'))
            self.checks_show[i].toggled.connect(self._update_buffers)
            self.checks_normalise[i].toggled.connect(self._update_buffers)
            hbox_inner.addWidget(self.buttons_pick[i])
            hbox_inner.addWidget(self.buttons_clear[i])
            hbox_inner.addWidget(self.checks_show[i])
            hbox_inner.addWidget(self.checks_normalise[i])
            hbox.addWidget(wrap_in_panel(hbox_inner))
            self.buffer_lines['spectrum'].append(self.plot_items['spectrum'].plot(pen=pg.mkPen(self.button_colours[i][0])))
            self.buffer_lines['ft'].append(self.plot_items['ft'].plot(pen=pg.mkPen(self.button_colours[i][0])))
        vbox.addWidget(wrap_in_panel(hbox,'Buffers'))
        self.setLayout(vbox)
        
        self.current = dict(wavelengths=None,spectrum=None)
        self.buffers = [dict(wavelengths=None,spectrum=None) for i in range(num_buffers)]
        
    def _respond_pick(self,indx):
        self.buffers[indx] = self.current.copy()
        self._update_buffers()
        
    def _respond_clear(self,indx):
        self.buffers[indx] = dict(wavelengths=None,spectrum=None)
        self._update_buffers()
        
    def set_spectrum(self,wavelengths,spectrum):
        self.current['wavelengths'] = wavelengths
        self.current['spectrum'] = spectrum
        self._update_lines()
        
    def update_all(self):
        self._update_lines()
        self._update_buffers()
        
    def _update_lines(self):
        if self.current['spectrum'] is not None:
            self.plot_lines['spectrum'].setData(self.current['wavelengths'],self.current['spectrum'])
        if self.check_show_ft.isChecked():
            t,It = self._calc_ft(self.current)
            self.plot_lines['ft'].setData(t,It)
            self.label_ft_fwhm.setText('FWHM: {0:1.2f} fs'.format(fwhm(t,It)))
        if any([ check.isChecked() for check in self.checks_normalise]):
            self._update_buffers()
        QtWidgets.QApplication.processEvents()
            
    def _update_buffers(self):
        for i in range(self.num_buffers):
            if self.buffers[i]['spectrum'] is not None and self.checks_show[i].isChecked():
                if self.checks_normalise[i].isChecked():
                    spec = self.buffers[i]['spectrum']/self.buffers[i]['spectrum'].max()*self.current['spectrum'].max()
                else:
                    spec = self.buffers[i]['spectrum']
                self.buffer_lines['spectrum'][i].setData(self.buffers[i]['wavelengths'],spec)
                t,It = self._calc_ft(self.buffers[i])
                self.buffer_lines['ft'][i].setData(t,It)
            else:
                self.buffer_lines['spectrum'][i].clear()
                self.buffer_lines['ft'][i].clear()
            
    def _calc_ft(self,d):
        L = d['wavelengths']
        I = d['spectrum']
        omega = 2*np.pi*300/L
        omega_lin = np.linspace(2*np.pi*300/L.max(),2*np.pi*300/L.min(),len(L))
        indx = np.argsort(omega) #splrep needs sorted input arrays
        I = I[indx]
        omega = omega[indx]
        tck = interpolate.splrep(omega, I, s=0)
        I_lin = interpolate.splev(omega_lin, tck, der=0)
        if self.check_thresh_ft.isChecked():
            I_lin[I_lin < self.spin_thresh_ft.value()] = 0
        if self.check_sqrt_ft.isChecked():
            It = np.abs(np.fft.fftshift(np.fft.fft(np.sqrt(np.abs(I_lin)))))**2
        else:
            It = np.abs(np.fft.fftshift(np.fft.fft(I_lin)))
        t = fourier.conj_axis(omega_lin)
        return t,It     

    def set_show_ft(self, val):
        if val:
            self.plot_widgets['ft'].show()
        else:
            self.plot_widgets['ft'].hide()
        if val != self.check_show_ft.isChecked():
            self.check_show_ft.setChecked(val)
                
    def xy_auto(self):
        for item in self.plot_items.values(): item.autoRange()
        
class SpectrumLogViewer(QtWidgets.QWidget):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.plot_layout_widget = pg.GraphicsLayoutWidget()
        self.plot_items = dict(spectrum=self.plot_layout_widget.addAlignedPlot(0,0),log=None)
        self.plot_layout_widget.addVerticalSpacer(20,3,0)
        self.plot_items['log'] = self.plot_layout_widget.addAlignedPlot(4,0)
        self.cbar=pg.ColorBarItem()
        self.plot_layout_widget.addHorizontalSpacer(10,6,3)
        self.plot_layout_widget.addItem(self.cbar,6,4)
        for axis in ['right','top']:
            self.plot_items['spectrum'].showAxis(axis)
            self.plot_items['log'].showAxis(axis)
            self.plot_items['spectrum'].getAxis(axis).setStyle(showValues=False)
            self.plot_items['log'].getAxis(axis).setStyle(showValues=False)
        self.plot_items['spectrum'].getAxis('bottom').setStyle(showValues=False)
        self.plot_items['spectrum'].getAxis('bottom').setHeight(5)
        self.plot_items['spectrum'].setXLink(self.plot_items['log'])
        self.plot_layout_widget.setRowStretchFactor(5,2)
        self.plot_layout_widget.setRowStretchFactor(4,6)
        
        self.plot_lines = dict( current=self.plot_items['spectrum'].plot(pen=pg.mkPen('k')),
                                reference=self.plot_items['spectrum'].plot(pen=pg.mkPen('g')),
                                log=self.plot_items['spectrum'].plot(pen=pg.mkPen('b')))
        self.log_image = self.plot_items['log'].image()
        self.log_image.setLookupTable(pyqtgraph_recipes.jet_white())
        self.cbar.setImage(self.log_image)
        self.plot_items['spectrum'].setLabels(left='Intensity')
        self.plot_items['log'].setLabels(left='Index',bottom='Wavelength')
        self.log_selector = pg.InfiniteLine(angle=0,pen=pg.mkPen('b'))
        self.log_selector.sigDragged.connect(self.log_selector_update)
        self.plot_items['log'].addItem(self.log_selector)
        self.cornertexts = {key: pg.cornertext('none',self.plot_items['spectrum']) for key in ['current','reference','log']}
        self.cornertexts['reference'].anchor((0,0),(0,0),(0,15))
        self.cornertexts['log'].anchor((0,0),(0,0),(0,30))
        
        self.plot_items['spectrum'].setXRange(200,1500)
        
        self.log = dict()
             
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.plot_layout_widget)
        self.setLayout(vbox)
        
    def set_log(self,wavelengths=None,spectrum=None,datetime=None):
        if wavelengths is None:
            self.log_image.clear()
            self.plot_lines['log'].clear()
            self.log = dict(wavelengths=None,spectrum=None,datetime=None)
            self.cornertexts['log'].setText('...')
            self.log_selector.setMovable(False)
            return
        self.log['wavelengths'] = wavelengths.squeeze()
        self.log['spectrum'] = spectrum
        self.log['datetime'] = datetime
        self.log['indices'] = np.arange(spectrum.shape[0])
        if len(self.log['indices'])>1:
            self.log_image.setImage(self.log['spectrum'].squeeze().transpose())
            self.log_image.setRect(pg.axes_to_rect(self.log['wavelengths'],self.log['indices']))
        self.log_selector.setBounds((0,spectrum.shape[0]-1))
        self.log_selector.setMovable(True)
        self.log_selector_update()
        
    def log_selector_update(self):
        indx = self.log_selector.value()
        indx_nearest = self.log['indices'][(np.abs(self.log['indices']-indx)).argmin()]
        datetimestr = datetime.strptime(self.log['datetime'][indx_nearest],'%Y%m%d_%H%M%S_%f').strftime('%Y%m%d %H:%M:%S')
        self.cornertexts['log'].setText(datetimestr,color='0000FF')
        self.plot_lines['log'].setData(self.log['wavelengths'],self.log['spectrum'][indx_nearest].squeeze())
        
    def set_reference(self,wavelengths=None,spectrum=None,datetimestr=None,**kwargs):
        if wavelengths is None:
            self.plot_lines['reference'].clear()
            self.cornertexts['reference'].setText('...')
            self.reference=dict(wavelengths=None,spectrum=None,datetime=None)
            return
        datetimestr = datetime.strptime(datetimestr,'%Y%m%d_%H%M%S_%f').strftime('%Y%m%d %H:%M:%S')
        self.plot_lines['reference'].setData(wavelengths,spectrum)
        self.cornertexts['reference'].setText(datetimestr,color='00FF00')
        
    def set_spectrum(self,wavelengths=None,spectrum=None,datetimestr=None,**kwargs):
        if wavelengths is None:
            self.plot_lines['current'].clear()
            self.cornertexts['current'].setText('...')
            self.reference=dict(wavelengths=None,spectrum=None,datetime=None)
            return
        datetimestr = datetime.strptime(datetimestr,'%Y%m%d_%H%M%S_%f').strftime('%Y%m%d %H:%M:%S')
        self.plot_lines['current'].setData(wavelengths,spectrum)
        self.cornertexts['current'].setText(datetimestr,color='000000')
        
    def get_config(self):
        rect = self.plot_items['spectrum'].viewRect()
        return dict(ax_lims=dict(xmin=rect.left(),xmax=rect.right(),ymin=rect.top(),ymax=rect.bottom()))
    def set_config(self,config):
        if 'ax_lims' in config:
            self.plot_items['spectrum'].setRange(
                xRange=(config['ax_lims']['xmin'],config['ax_lims']['xmax']),
                yRange=(config['ax_lims']['ymin'],config['ax_lims']['ymax']))
                
class SpectrumParameterDisplay(QtWidgets.QWidget):
    
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        hbox = QtWidgets.QHBoxLayout()
        self.text_fwhm = QtWidgets.QLabel()
        self.text_centre_peak = QtWidgets.QLabel()
        self.text_centre_moment = QtWidgets.QLabel()
        self.text_sum = QtWidgets.QLabel()
        self.check_smooth_fwhm = QtWidgets.QCheckBox('Smooth')
        self.spin_smooth_amount = QtWidgets.QSpinBox()
        self.spin_smooth_amount.setRange(1,200)
        self.spin_smooth_amount.setValue(10)
        f = QtWidgets.QFont()
        f.setPixelSize(14)
        for txt in [self.text_fwhm,self.text_sum,self.text_centre_peak,self.text_centre_moment]:
            txt.setFont(f)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.text_fwhm)
        hbox_smooth = QtWidgets.QHBoxLayout()
        hbox_smooth.addWidget(self.check_smooth_fwhm)
        hbox_smooth.addWidget(self.spin_smooth_amount)
        vbox.addLayout(hbox_smooth)
        hbox.addWidget(wrap_in_panel(vbox,'FWHM'))
        hbox.addWidget(wrap_in_panel(self.text_centre_peak,'Peak'))
        hbox.addWidget(wrap_in_panel(self.text_centre_moment,'Mean'))
        hbox.addWidget(wrap_in_panel(self.text_sum,'Sum'))
        self.setLayout(hbox)
        self.wavelengths = None
        self.spectrum = None
        self.update()
        
    def update(self):
        def smooth(signal,box_width):
            box = np.ones(box_width)/box_width
            return np.convolve(signal,box,mode='same')
        if self.wavelengths is None or self.spectrum is None:
            for txt in [self.text_fwhm,self.text_sum,self.text_centre_peak,self.text_centre_moment]:
                txt.setText('')
            return
        if self.check_smooth_fwhm.isChecked():
            self.text_fwhm.setText('{0:.2f} nm'.format(fwhm(self.wavelengths,smooth(self.spectrum,self.spin_smooth_amount.value()))))
        else:
            self.text_fwhm.setText('{0:.2f} nm'.format(fwhm(self.wavelengths,self.spectrum)))
        self.text_centre_peak.setText('{0:.2f} nm'.format(self.wavelengths[self.spectrum.argmax()]))
        sum=np.sum(self.spectrum)
        if np.sum(self.spectrum) ==0:
            self.text_centre_moment.setText('{0:.2f} nm'.format(0))
        else:
            self.text_centre_moment.setText('{0:.2f} nm'.format(np.average(self.wavelengths,weights=self.spectrum)))
        self.text_sum.setText('{0:.1f}'.format(sum))
    
    def set_input(self,wavelengths,spectrum,**kwargs):
        self.wavelengths = wavelengths
        self.spectrum = spectrum
        self.update()
        
    def get_config(self):
        return dict(smooth=self.check_smooth_fwhm.isChecked(),smooth_amount=self.spin_smooth_amount.value())
        
    def set_config(self,config):
        self.spin_smooth_amount.setValue(config.pop('smooth_amount',10))
        self.check_smooth_fwhm.setChecked(config.pop('smooth',False))
        if len(config)>0:
            raise Exception('Found unused config keys')
        
class XFROGViewer(QtWidgets.QWidget):
    """
    Widget to compactly view an XFROG trace, its reconstruction and the resulting pulse
    in the time and frequency domains for both the gate and the test pulse
    """
    def __init__(self, parent=None):
        PhaseAmp = namedtuple('PhaseAmpPlot', ['amp', 'phase'])

        def add_amp_phase_plot(gl, row, col, second_colour):
            amp = gl.addAlignedPlot(row, col)
            amp.showAxis('right')
            amp.getAxis('right').setPen(pg.mkPen(color=second_colour))
            phase = pg.ViewBox()
            phase.setXLink(amp)
            amp.getAxis('right').linkToView(phase)
            amp.scene().addItem(phase)

            def update_views():
                phase.setGeometry(amp.getViewBox().sceneBoundingRect())
                phase.linkedViewChanged(amp.getViewBox(), phase.XAxis)
            amp.getViewBox().sigResized.connect(update_views)
            return PhaseAmp(amp=amp, phase=phase)
        super().__init__(parent=parent)
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plot_widget.show()
        gl = self.plot_widget.ci
        
        hspace = 30
        vspace = 40
        measured = gl.addAlignedPlot(0, 0)
        gl.addHorizontalSpacer(hspace, 0, 3)
        reconstructed = gl.addAlignedPlot(0, 4)
        self.cbar = pg.ColorBarItem()
        gl.addItem(self.cbar, 2, 7)
        gl.addVerticalSpacer(vspace, 3, 0)
        gate_time = add_amp_phase_plot(gl, 4, 0, '#2000AA')
        gl.addHorizontalSpacer(4, 3)
        test_time = add_amp_phase_plot(gl, 4, 4, '#2000AA')
        gl.addVerticalSpacer(vspace, 7, 0)
        gate_freq = add_amp_phase_plot(gl, 8, 0, '#2000AA')
        gl.addHorizontalSpacer(8, 3)
        test_freq = add_amp_phase_plot(gl, 8, 4, '#2000AA')
        
        measured.setXLink(reconstructed)
        measured.setYLink(reconstructed)
        
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.plot_widget)
        self.setLayout(vbox)
        
        self.image_items = dict(measured=measured, reconstructed=reconstructed)
        self.plot_amp_phase_items = dict(
                        gate=dict(time=gate_time,
                                  freq=gate_freq),
                        test=dict(time=test_time,
                                  freq=test_freq)
                        )
        
        measured.setTitle('Measured')
        reconstructed.setTitle('Reconstructed')
        self.plot_amp_phase_items['gate']['time'].amp.setTitle('Gate')
        self.plot_amp_phase_items['test']['time'].amp.setTitle('Test pulse')
        # reconstructed.getAxis('left').setStyle(showValues=False)
        for time in [test_time.amp, gate_time.amp]:
            time.setLabel('bottom', 'Time [fs]')
        for freq in [test_freq.amp, gate_freq.amp]:
            freq.setLabel('bottom', 'Wavelength [nm]')
        for plt in [test_time.amp, gate_time.amp, test_freq.amp, gate_freq.amp,
                    measured, reconstructed]:
            plt.showAxis('top')
            plt.getAxis('top').setStyle(showValues=False)
        for plt in [measured, reconstructed]:
            plt.showAxis('right')
            plt.getAxis('right').setStyle(showValues=False)
            plt.setLabel('bottom', 'Delay [fs]')
            plt.setLabel('left', 'Frequency [rad/fs]')
        self.images = dict(measured=measured.image(),
                           reconstructed=reconstructed.image())
        self.cbar.setImages([self.images['measured']])
        self.images['measured'].sigLevelsChanged.connect(
            lambda: self.images['reconstructed'].setLevels(
                self.images['measured'].getLevels()))
        for img in self.images.values():
            img.setLevels((0, 1))
        self.lines = dict(
            gate=dict(
                time=dict(
                    amp=gate_time.amp.plot([0,1],[0,0],pen=pg.mkPen('k')),
                    phase=gate_time.phase.plot([0,1],[1,1],pen=pg.mkPen(color='#2000AA')),
                    amp_ref=gate_time.amp.plot([0,1],[0,1],pen=pg.mkPen(color='r',style=QtCore.Qt.DashLine))),
                freq=dict(
                    amp=gate_freq.amp.plot([0,1],[0,0],pen=pg.mkPen('k')),
                    amp_ref=gate_freq.amp.plot([0,1],[1,0],pen=pg.mkPen('r')),
                    phase=gate_freq.phase.plot([0,1],[1,1],pen=pg.mkPen(color='#2000AA')),
                    phase_fit=gate_freq.phase.plot([0,1],[0,1],pen=pg.mkPen(color='#2000AA',style=QtCore.Qt.DashLine)),
                    phase_ref=gate_freq.phase.plot([0,1],[0,1],pen=pg.mkPen(color='r',style=QtCore.Qt.DashLine)) )
                    ),
            test=dict(
                time=dict(
                    amp=test_time.amp.plot([0,1],[0,0],pen=pg.mkPen('k')),
                    phase=test_time.phase.plot([0,1],[1,1],pen=pg.mkPen(color='#2000AA')),
                    amp_ref=test_time.amp.plot([0,1],[0,1],pen=pg.mkPen(color='r',style=QtCore.Qt.DashLine))),
                freq=dict(
                    amp=test_freq.amp.plot([0,1],[0,0],pen=pg.mkPen('k')),
                    amp_ref=test_freq.amp.plot([0,1],[1,0],pen=pg.mkPen('r')),
                    phase=test_freq.phase.plot([0,1],[1,1],pen=pg.mkPen(color='#2000AA')),
                    phase_fit=test_freq.phase.plot([0,1],[0,1],pen=pg.mkPen(color='#2000AA',style=QtCore.Qt.DashLine)),
                    phase_ref=test_freq.phase.plot([0,1],[0,1],pen=pg.mkPen(color='r',style=QtCore.Qt.DashLine)) )
                    )
                )
        
        self.lines['test']['freq']['amp_ref'].hide()
        
    def set_measured(self,tau,omega,trace):
        self.images['measured'].setImage(trace,autoLevels=False)
        self.images['measured'].setRect(pg.axes_to_rect(tau,omega))
        
    def set_reconstructed(self,tau,omega,trace):
        self.images['reconstructed'].setImage(trace,autoLevels=False)
        self.images['reconstructed'].setRect(pg.axes_to_rect(tau,omega))

    def auto_range(self):
        for pulse in ('gate', 'test'):
            for space in ('time', 'freq'):
                amp_line = self.lines[pulse][space]['amp']
                phase_line = self.lines[pulse][space]['phase']
                x0 = moment(amp_line.xData, amp_line.yData, 1)
                x_fwhm = fwhm(amp_line.xData, amp_line.yData)
                x_lims = x0 + x_fwhm*2*np.array([-1, 1])
                x_lims_phi = x0 + x_fwhm*np.array([-1, 1])
                x_lims_inds = np.sort([
                    np.abs(phase_line.xData-lim).argmin() for lim in x_lims_phi])
                phi_in_lims = phase_line.yData[x_lims_inds[0]:x_lims_inds[1]]
                phi_lims = (phi_in_lims.min()-0.5,
                            phi_in_lims.max()+0.5)
                self.plot_amp_phase_items[pulse][space].phase.setRange(
                    yRange=phi_lims)
                self.plot_amp_phase_items[pulse][space].amp.setRange(
                    xRange=x_lims)

            
class ReferenceControls(QtWidgets.QWidget):
    """
    Set of buttons to control reference taking, saving and loading. if "show" is True, 
    also shows a checkbox to show the reference somewhere (it's up to the parent app to implement this)
    Buttons can be shown vertically or horizontally ordered (default horizontal)
    This only builds the GUI for convenience, no actual reference handling is done!
    """
    def __init__(self,parent=None,show=True,dir='horz'):
        super().__init__(parent=parent)
        if dir is 'horz':
            box = QtWidgets.QHBoxLayout()
        elif dir is 'vert':
            box = QtWidgets.QVBoxLayout()
        else:
            raise Exception('Invalid direction given')
        self.setButton = QtWidgets.QPushButton('Set')
        box.addWidget(self.setButton)
        self.clearButton = QtWidgets.QPushButton('Clear')
        box.addWidget(self.clearButton)
        self.loadButton = QtWidgets.QPushButton('Load')
        box.addWidget(self.loadButton)
        self.saveButton = QtWidgets.QPushButton('Save')
        box.addWidget(self.saveButton)
        self.showCheck = QtWidgets.QCheckBox('Show')
        if show:
            box.addWidget(self.showCheck)
        box.setSpacing(1)
        self.setButton.setMaximumWidth(50)
        self.clearButton.setMaximumWidth(50)
        self.loadButton.setMaximumWidth(50)
        self.saveButton.setMaximumWidth(50)
        self.setLayout(box)
        
class ContinuousButton(QtWidgets.QWidget):
    """Set of button and check box to execute a callback either once (button) or continuously (checkbox)
    Also creates a label showing the framerate in frames per second
    Args:
        callback:   Function to be executed either once or in a loop. Needs to be callable (obvs)
        condition:  Function to evaluate a running condition. Must be callable, not boolean. 
                    This can be used to interrupt the continuous execution from the outside, e.g. if a device is disconnected
                    Defaults to function that always evaluates to True
        fps_buffer_length: length of buffer to be kept for fps measurement. fps displayed is the average of this buffer
                            Defaults to 20
    """
    def __init__(self,callback,condition=None,fps_buffer_length=20,
                 play_pause=False,parent=None):
        super().__init__(parent=parent)
        hbox = QtWidgets.QHBoxLayout()
        self.single = QtWidgets.QPushButton('Single')
        hbox.addWidget(self.single)
        self.continuous = (QtWidgets.QPushButton('Play')
                           if play_pause else QtWidgets.QCheckBox('Continuous'))
        self.continuous.setCheckable(True)
        hbox.addWidget(self.continuous)
        self.fps = QtWidgets.QLabel(' ')
        hbox.addWidget(self.fps)
        self.setLayout(hbox)
        
        self.fps_buffer_length = fps_buffer_length
        self.fps_buffer = deque(maxlen=fps_buffer_length)
        
        self.callback = callback
        if condition is None:
            self.condition = lambda: True
        else:
            self.condition = condition
            
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._timer_func)
        self.timer_stopping = False
        
        self.single.clicked.connect(self._single_clicked)
        # self.continuous.toggled.connect(self._continuous_toggled)
        self.continuous.toggled.connect(self._set_run)
        if play_pause:
            self.continuous.toggled.connect(
                lambda live: self.continuous.setText(
                    'Pause' if live else 'Play'))
        
    def _single_clicked(self):
        if self.condition():
            self.callback()

    def stop(self):
        self.continuous.setChecked(False)
            
    def _set_run(self,val):
        if val is True:
            self.timer_stopping = False
            self.timer.start()
        else:
            self.timer.stop()
            self.timer_stopping = True
            
    def _timer_func(self):
        if self.condition() is True:
            try:
                self.callback()
            except Exception as e:
                self.continuous.setChecked(False)
                raise e
            self._update_fps()
            self.continuous.setStyleSheet("background-color : red;")
            QtWidgets.QApplication.processEvents()
        else:
            self.continuous.setChecked(False)
        if self.timer_stopping is True:
            self.continuous.setStyleSheet("background-color : green;")
            self.fps_buffer.clear()
    
    def _continuous_toggled(self):
        #Not in use as of 2017/02/17 to avoid blocking
        while self.continuous.isChecked():
            if self.condition() is True:
                self.callback()
                self.continuous.setStyleSheet("background-color : red;")
                self._update_fps()
                QtWidgets.QApplication.processEvents()
            else:
                self.continuous.setChecked(False)
        self.continuous.setStyleSheet("background-color : green;")
        self.fps_buffer.clear()
            
    def _update_fps(self):
        self.fps_buffer.append(datetime.now())
        if len(self.fps_buffer)>1:
            fps = 1/np.mean(np.diff(self.fps_buffer)).total_seconds()
            self.fps.setText('{:.2f} fps'.format(fps))
        
        
class SaveControls(QtWidgets.QWidget):
    """Generic widget to control saving to files. This only creates the GUI based on the user-specified options. 
    The actual saving will have to be handled by the parent app.
    Constructor input:
            options:    List of strings which serve as labels for different options. 
                        e.g. ('.mat','.p','screenshot') 
    """
    def __init__(self,options,parent=None):
        super().__init__(parent=parent)
        label_width = 38
        vbox = QtWidgets.QVBoxLayout()
        #Directory
        hbox = QtWidgets.QHBoxLayout()
        vbox.addLayout(hbox)
        label = QtWidgets.QLabel('Folder:')
        label.setMinimumWidth(label_width)
        label.setMaximumWidth(label_width)
        hbox.addWidget(label)
        self.folder_text = QtWidgets.QLineEdit(os.path.join(os.path.expanduser('~'),'Documents'))
        self.folder_text.setMinimumWidth(150)
        self.folder_text.setPlaceholderText('Destination folder')
        hbox.addWidget(self.folder_text)
        self.folder_pick = QtWidgets.QPushButton('Browse...')
        self.folder_pick.setToolTip('Choose the folder used for saved images')
        hbox.addWidget(self.folder_pick)
        #File name
        hbox = QtWidgets.QHBoxLayout()
        vbox.addLayout(hbox)
        label = QtWidgets.QLabel('Name:')
        label.setMinimumWidth(label_width)
        label.setMaximumWidth(label_width)
        hbox.addWidget(label)
        self.name_text = QtWidgets.QLineEdit('camera')
        self.name_text.setPlaceholderText('File name')
        hbox.addWidget(self.name_text)
        #Saving options
        hbox = QtWidgets.QHBoxLayout()
        vbox.addLayout(hbox)
        label = QtWidgets.QLabel('Format:')
        label.setMinimumWidth(label_width)
        label.setMaximumWidth(label_width)
        hbox.addWidget(label)
        self.check_option = []
        for option in options:
            self.check_option.append(QtWidgets.QCheckBox(option))
            hbox.addWidget(self.check_option[-1])
        if self.check_option:
            self.check_option[0].setChecked(True)
        #Saving buttons
        hbox = QtWidgets.QHBoxLayout()
        vbox.addLayout(hbox)
        label = QtWidgets.QLabel('Save:')
        label.setMinimumWidth(label_width)
        label.setMaximumWidth(label_width)
        hbox.addWidget(label)
        self.push_single = QtWidgets.QPushButton('Save current')
        hbox.addWidget(self.push_single)
        hbox = QtWidgets.QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(QtWidgets.QLabel('Frames:'))
        self.spin_sequence = QtWidgets.QSpinBox()
        self.spin_sequence.setValue(10)
        self.spin_sequence.setMinimum(2)
        self.spin_sequence.setMaximum(1000000)
        hbox.addWidget(self.spin_sequence)
        self.push_sequence = QtWidgets.QPushButton('Save sequence')
        hbox.addWidget(self.push_sequence)
        self.sequence_counter = QtWidgets.QLabel(' ')
        self.sequence_counter.setMinimumWidth(50)
        hbox.addWidget(self.sequence_counter)
        self.status = QtWidgets.QLabel('Ready')
        self.status.setWordWrap(True)
        vbox.addWidget(self.status)
            
        self.setLayout(vbox)
        vbox.setAlignment(QtCore.Qt.AlignTop)
        self.folder_pick.clicked.connect(self._browse_folder)
        
    def _browse_folder(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Choose save folder', self.folder_text.text())
        if path:
            self.folder_text.setText(path)

    def set_status(self, message, success):
        colour = '#8ce0ac' if success else '#ffaaa3'
        self.status.setText(message)
        self.status.setStyleSheet('color: {};'.format(colour))

def wrap_in_panel(obj,title=None):
    panel = QtWidgets.QGroupBox(title)
    if isinstance(obj,QtWidgets.QLayout):
        panel.setLayout(obj)
    elif isinstance(obj,QtWidgets.QWidget):
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(obj)
        hbox.setSpacing(0)
        panel.setLayout(hbox)
    else:
        raise ValueError('Can only wrap QLayouts or QWidgets. Got type {0}'.format(type(obj)))
    return panel
    
def auto_button_width(button):
    metrics = button.fontMetrics()
    width = metrics.width(button.text())
    # button.setMaximumWidth(width+10)
    button.setMinimumWidth(width+10)

if __name__=="__main__":
    # Standard 'boilerplate' code, common to all applications
    app = QtWidgets.QApplication(sys.argv)
    # Create widget
    widget=XFROGViewer()
    widget.show()
    gl = widget.plot_widget.ci
    widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    # More boilerplate
    sys.exit(app.exec_())
