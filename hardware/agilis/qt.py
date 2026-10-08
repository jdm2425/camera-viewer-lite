import sys, logging
from PyQt5 import QtGui, QtWidgets,QtCore
from datetime import datetime
from hardware.qt import RelativeStageWidget,MotorisedMirrorButtonsWidget
from hardware.agilis import NewportAGUC8,NewportAGUC8Mirror

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

class NewportAGUC8Widget(RelativeStageWidget):
    """Widget to control a AGUC8 Agilis motor controller"""
    def __init__(self,controller=None,parent=None):
        super().__init__(parent=parent)
        self.controller = ( NewportAGUC8() if controller is None else controller)
        vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        self.dropdown_device = QtGui.QComboBox()
        self.dropdown_device.setMinimumWidth(85)
        hbox.addWidget(QtGui.QLabel('Serial no.:'))
        hbox.addWidget(self.dropdown_device)
        self.push_rescan = QtGui.QPushButton('Rescan')
        hbox.addWidget(self.push_rescan)
        self.push_open = QtGui.QPushButton('Open')
        self.push_open.setEnabled(False)
        hbox.addWidget(self.push_open)
        self.axis_controls = []
        grid = QtGui.QGridLayout()
        vbox.addLayout(grid)
        ##Labels at top of each column
        col = 0
        lab = QtGui.QLabel('Axis')
        lab.setAlignment(QtCore.Qt.AlignCenter)
        grid.addWidget(lab,0,col)
        col +=1
        lab = QtGui.QLabel('Steps')
        lab.setAlignment(QtCore.Qt.AlignCenter)
        grid.addWidget(lab,0,col)
        col +=1
        lab = QtGui.QLabel('+ amp')
        lab.setAlignment(QtCore.Qt.AlignCenter)
        grid.addWidget(lab,0,col)
        col +=1
        lab = QtGui.QLabel('- amp')
        lab.setAlignment(QtCore.Qt.AlignCenter)
        grid.addWidget(lab,0,col)
        col +=1
        ##Controls for each axis
        for i in range(8):
            col = 0
            lab = QtGui.QLabel('{0}'.format(i))
            lab.setMinimumWidth(30)
            lab.setAlignment(QtCore.Qt.AlignCenter)
            grid.addWidget(lab,i+1,col)
            col +=1
            steps = QtGui.QSpinBox()
            steps.setValue(10)
            steps.setRange(1,10000)
            steps.setMinimumWidth(50)
            grid.addWidget(steps,i+1,col)
            col +=1
            pos_amp = QtGui.QSpinBox()
            pos_amp.setRange(1,50)
            pos_amp.valueChanged.connect(lambda val,i=i:self._step_amp_changed(axis=i,dir=1))
            pos_amp.setMinimumWidth(50)
            grid.addWidget(pos_amp,i+1,col)
            col +=1
            neg_amp = QtGui.QSpinBox()
            neg_amp.setRange(1,50)
            neg_amp.valueChanged.connect(lambda val,i=i:self._step_amp_changed(axis=i,dir=-1))
            neg_amp.setMinimumWidth(50)
            grid.addWidget(neg_amp,i+1,col)
            col +=1
            push_plus = QtGui.QPushButton('+')
            grid.addWidget(push_plus,i+1,col)
            col +=1
            push_plus.clicked.connect(lambda checked,i=i:self._move_gui(axis=i,sign=1))
            push_minus = QtGui.QPushButton('-')
            grid.addWidget(push_minus,i+1,col)
            col +=1
            push_minus.clicked.connect(lambda checked,i=i:self._move_gui(axis=i,sign=-1))
            self.axis_controls.append(dict(steps=steps,plus=push_plus,minus=push_minus,pos_amp=pos_amp,neg_amp=neg_amp))
        vbox.setSpacing(1)
        self.setLayout(vbox)
        
        self.push_open.clicked.connect(lambda: self.set_open(not self.online))
        self.push_rescan.clicked.connect(self.rescan)
        self.rescan()
        
    def set_open(self,val):
        logger.debug('Opening controller' if val else 'Closing controller')
        if val is True:
            if not self.online:
                self._open()     
        else:
            if self.online:
                self._close()
                
    def _open(self):
        com_port = self.dropdown_device.currentText()
        if not com_port:
            return
        self.controller.open(com_port=com_port)
        if self.controller.online:
            self.push_open.setText("Close")
            self.online_changed.emit(True)
            self._update_gui()
    
    def _close(self):
        self.controller.close()
        self.push_open.setText("Open")
        self.online_changed.emit(False)
        
    def rescan(self):
        self.dropdown_device.clear()
        self.push_rescan.setText('...')
        QtGui.QApplication.processEvents()
        self.controller.rescan()
        self.push_rescan.setText('Rescan')
        
        if self.controller.found_devices:
            self.dropdown_device.addItems(self.controller.found_devices)
            self.push_open.setEnabled(True)
        else:
            self.push_open.setEnabled(False)
        
    def _move_gui(self,axis,sign):
        if not self.controller.online:
            return
        dist = self.axis_controls[axis]['steps'].value()
        logger.debug('GUI request: Move axis {0} by {1} steps'.format(axis,sign*dist))
        self.move(sign*dist,axis)
        
    def _step_amp_changed(self,axis,dir):
        if dir>0:
            val = self.axis_controls[axis]['pos_amp'].value()
        else:
            val = self.axis_controls[axis]['neg_amp'].value()
        self.controller.set_step_amplitude(axis,dir,val)
        
    def _update_gui(self):
        if self.controller.online:
            for axis in range(8):
                self.axis_controls[axis]['neg_amp'].setValue(self.controller.get_step_amplitude(axis,-1))
                self.axis_controls[axis]['pos_amp'].setValue(self.controller.get_step_amplitude(axis,1))
            self.push_open.setText("Close")
            self.online_changed.emit(True)
        else:
            self.push_open.setText("Open")
            self.online_changed.emit(False)
        
    def move(self,dist,axis):
        logger.debug('Moving axis {0} by {1} steps'.format(axis,dist))
        ret = self.controller.move(dist,axis)
        self.moved.emit(ret)
        
    def trigger(self,dist,axis):
        self.controller.trigger(dist,axis)
        
    def wait(self,axis,timeout=5000):
        return self.controller.wait(axis,timeout)
        
    def get_config(self):
        axis_settings = [{key: self.axis_controls[i][key].value() for key in ['steps','pos_amp','neg_amp']} for i in range(8)]
        return dict(online=self.online,com_port=self.dropdown_device.currentText(),axis_settings=axis_settings)
        
    def set_config(self,config):
        com_port = config.pop('com_port','COM2')
        indx = self.dropdown_device.findText(com_port)
        if indx != -1: 
            self.dropdown_device.setCurrentIndex(indx)
        else:#if findText() returns -1, the text was not found, so we don't want to set the online status to True
            if 'online' in config: config['online']=False
        self.set_open(config.pop('online',False))
        axis_settings = config.pop('axis_settings',None)
        if axis_settings is not None:
            for i in range(8):
                for key in ['steps','pos_amp','neg_amp']:
                    self.axis_controls[i][key].setValue(axis_settings[i][key])
        if len(config)>0:
            logger.warning('Found unexpected keys in config: {0}'.format(list(config.keys())))
            
    @property
    def position(self):
        return self.controller.position
    
    @property
    def online(self):
        return self.controller.online
        
class NewportAGUC8MirrorWidget(MotorisedMirrorButtonsWidget):
    """Widget to control an agilis mirror mount connected to two axes of an AGUC8 controller
    
    Args:
        mirror: An instance of NewportAGUC8Mirror. If none is supplied it is created
    """
    def __init__(self,mirror=NewportAGUC8Mirror(),parent=None):
        super().__init__(mirror=mirror,parent=parent)
        vbox = self.layout()
        hbox = QtGui.QHBoxLayout()
        self.push_controller = QtGui.QPushButton('Controller')
        self.push_settings = QtGui.QPushButton('Settings')
        hbox.addWidget(self.push_controller)
        hbox.addWidget(self.push_settings)
        vbox.addLayout(hbox)
        self.controller_widget = NewportAGUC8Widget(controller=self.mirror.controller)
        self.settings_widget = NewportAGUC8MirrorSettingsWidget(self.mirror)
        self.push_controller.clicked.connect(self.show_controller)
        self.push_settings.clicked.connect(self.settings_widget.show)
        
    def show_controller(self):
        self.controller_widget.show()
        self.controller_widget._update_gui()
        
    def get_config(self):
        return dict(controller_settings=self.controller_widget.get_config(),settings=self.settings_widget.get_config(),steps=self.spin_stepsize.value())
    
    def set_config(self,config):
        if 'settings' in config:
            self.settings_widget.set_config(config['settings'])
        if 'controller_settings' in config:
            self.controller_widget.set_config(config['controller_settings'])
        if 'steps' in config:
            self.spin_stepsize.setValue(config['steps'])
        
class NewportAGUC8MirrorSettingsWidget(QtGui.QWidget):
    """Small settings widget for Agilis mirror on an AGUC8 controller. Sets up axes and inversion"""
    def __init__(self,agilis_mirror,parent=None):
        super().__init__(parent=parent)
        self.mirror = agilis_mirror
        vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        label = QtGui.QLabel('Horizontal')
        label.setMinimumWidth(55)
        hbox.addWidget(label)
        hbox.addWidget(QtGui.QLabel('Motor:'))
        self.axis_h = QtGui.QComboBox()
        hbox.addWidget(self.axis_h)
        self.invert_h = QtGui.QCheckBox('Invert')
        hbox.addWidget(self.invert_h)
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        label = QtGui.QLabel('Vertical')
        label.setMinimumWidth(55)
        hbox.addWidget(label)
        hbox.addWidget(QtGui.QLabel('Motor:'))
        self.axis_v = QtGui.QComboBox()
        hbox.addWidget(self.axis_v)
        self.invert_v = QtGui.QCheckBox('Invert')
        hbox.addWidget(self.invert_v)
        self.setLayout(vbox)
        self.set_config(self.mirror.axes.copy())
        
        for check in [self.invert_h,self.invert_v]: check.toggled.connect(self._update)
        for combo in [self.axis_h,self.axis_v]: combo.addItems([str(i) for i in range(8)])
        for combo in [self.axis_v,self.axis_h]: combo.currentIndexChanged.connect(self._update)
        
        self.axis_h.setCurrentIndex(self.mirror.axes['h'])
        self.axis_v.setCurrentIndex(self.mirror.axes['v'])
        self.invert_h.setChecked(self.mirror.axes['invert_h'])
        self.invert_v.setChecked(self.mirror.axes['invert_v'])
        
    def _update(self):
        invert_h  = self.invert_h.isChecked()
        invert_v = self.invert_v.isChecked()
        axis_h = self.axis_h.currentIndex()
        axis_v = self.axis_v.currentIndex()
        self.mirror.set_axes(axis_h,axis_v,invert_h,invert_v)
        
    def get_config(self):
        return self.mirror.axes
        
    def set_config(self,config):
        self.invert_h.setChecked(config.pop('invert_h',False))
        self.invert_h.setChecked(config.pop('invert_v',False))
        self.axis_h.setCurrentIndex(config.pop('h',0))
        self.axis_v.setCurrentIndex(config.pop('v',0))
        if len(config)>0:
            logger.warning('Unused keys in config: {0}'.format(list(config.keys())))
        
if __name__ == "__main__":
    widget = NewportAGUC8MirrorWidget()
    widget.show()
