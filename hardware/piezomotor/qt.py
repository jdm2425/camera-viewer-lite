import sys, logging
from PyQt5 import QtGui, QtWidgets, QtCore
from datetime import datetime
from time import sleep
from hardware.piezomotor import KCubePiezo, KCubeMirror
from hardware.qt import AbsoluteStageWidget, MotorisedMirrorButtonsWidget 
from lab_apps.gui_elements import wrap_in_panel

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


class KCubeWidget(AbsoluteStageWidget):
    """Widget to control a Kcube using the Kinesis .NET interface.

    A KCubeWidget has a KCubePiezo, self.controller.
    """

    def __init__(self, controller=None, parent=None):
        """
        Args:
            controller (:class:`.KCubePiezo`): if None, one is created.
        """
        super().__init__(parent=parent)
        # Create GUI elements
        self.controller = (controller
                           if controller is not None
                           else KCubePiezo())
        self.dropdown_device = QtGui.QComboBox()
        self.push_rescan = QtGui.QPushButton('Rescan')
        self.push_openclose = QtGui.QPushButton('Open')
        self.text_voltage = QtGui.QLabel('{0:2.5f} {1}'.format(0, '--'))
        self.text_status = QtGui.QLabel('None')
        self.spin_go_position = QtGui.QDoubleSpinBox()
        self.push_go = QtGui.QPushButton('Go')
        self.push_fwd = QtGui.QToolButton()
        self.push_bwd = QtGui.QToolButton()
        self.push_identify = QtGui.QPushButton('ID')
        self.push_home = QtGui.QPushButton('Home')
        self.push_stop = QtGui.QPushButton('STOP')
        self.spin_jog_step = QtGui.QDoubleSpinBox()

        # Set GUI settings
        ft = QtGui.QFont()
        ft.setFamily('Courier New')
        ft.setPointSize(14)

        self.push_rescan.clicked.connect(self.rescan)
        self.push_openclose.clicked.connect(
            lambda: self.set_open(not self.online))
        self.push_fwd.clicked.connect(lambda: self.jog(1))
        self.push_bwd.clicked.connect(lambda: self.jog(-1))
        self.spin_jog_step.setRange(0, 150)
        self.spin_jog_step.setSingleStep(0.1)
        self.spin_jog_step.setDecimals(1)
        self.dropdown_device.setMinimumWidth(80)
        self.text_voltage.setFont(ft)
        self.text_status.setFont(ft)
        self.push_fwd.setArrowType(QtCore.Qt.UpArrow)
        self.push_fwd.setMinimumWidth(70)
        self.push_bwd.setArrowType(QtCore.Qt.DownArrow)
        self.push_bwd.setMinimumWidth(70)
        self.spin_go_position.setDecimals(1)
        self.spin_go_position.setValue(0)
        self.spin_go_position.setSingleStep(1)
        self.push_home.clicked.connect(self.home) 
        self.push_identify.clicked.connect(self.controller.identify)
        self.push_go.clicked.connect(self._move)
        self.push_stop.clicked.connect(self.controller.stop)
        self.push_stop.setStyleSheet('background-color: red')

        # Build GUI layout
        vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.dropdown_device)
        hbox.addWidget(self.push_rescan)
        hbox.addWidget(self.push_openclose)
        vbox.addWidget(wrap_in_panel(hbox))
        hbox = QtGui.QHBoxLayout()
        vbox2 = QtGui.QVBoxLayout()
        vbox2.addWidget(wrap_in_panel(self.text_voltage, 'Voltage'))
        vbox2.addWidget(wrap_in_panel(self.text_status, 'Status'))
        hbox.addLayout(vbox2)
        vbox2 = QtGui.QVBoxLayout()
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(self.spin_go_position)
        hbox2.addWidget(self.push_go)
        vbox2.addWidget(wrap_in_panel(hbox2, 'Set voltage'))
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(self.push_identify)
        hbox2.addWidget(self.push_home)
        hbox2.addWidget(self.push_stop)
        vbox2.addWidget(wrap_in_panel(hbox2))
        hbox.addLayout(vbox2)
        grid = QtGui.QGridLayout()
        grid.addWidget(self.push_fwd, 0, 0)
        grid.addWidget(self.spin_jog_step, 1, 0)
        grid.addWidget(self.push_bwd, 2, 0)
        hbox.addWidget(wrap_in_panel(grid, 'Jog'))
        vbox.addLayout(hbox)

        self.setLayout(vbox)
        # Timer and app signals
        self.update_timer = QtCore.QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self._update_status)

        self.online_changed.connect(self._update_gui)
        self.moved.connect(self._update_gui)
        self.rescan()
        self._update_gui()

    def rescan(self):
        self.controller.rescan()
        self.dropdown_device.clear()
        self.dropdown_device.addItems(self.controller.found_serials)

    def set_open(self, val):
        logger.debug('Opening controller' if val else 'Closing controller')
        if val is True:
            if not self.online:
                self._open()
        else:
            if self.online:
                self._close()

    def _open(self):
        serial = self.dropdown_device.currentText()
        if not serial:
            return
        self.controller.open(serial=serial)
        if self.controller.online:
            self.online_changed.emit(True)
        self.update_timer.start()

    def _close(self):
        self.controller.close()
        self.online_changed.emit(False)
        self.update_timer.stop()

    def _update_gui(self):
        for w in [self.dropdown_device, self.push_rescan]:
            w.setEnabled(not self.online)
        for w in [self.push_fwd, self.push_bwd,
                  self.spin_go_position, self.spin_jog_step,
                  self.push_go, self.push_home,
                  self.push_identify, self.push_stop]:
            w.setEnabled(bool(self.online))
        if self.online:
            self.push_openclose.setText('Close')
            self._update_status()
            self.spin_jog_step.setValue(self.controller.jog_stepsize)
            self.spin_go_position.setSuffix('  ' + self.unit)
            self.spin_jog_step.setSuffix('  ' + self.unit)
        else:
            self.push_openclose.setText('Open')
        self._update_status()

    def _update_status(self):
        if not self.online:
            self.text_voltage.setText('{0:+2.5f} {1}'.format(0, '..'))
            return
        #print(self.controller.position)#, self.unit)
        self.text_voltage.setText(
            '{0:+2.5f} {1}'.format(self.voltage, self.unit))
        if self.is_moving():
            self.text_status.setText('Moving')
        else:
           self.text_status.setText('Stopped')

    def _move(self):
        self.move(self.spin_go_position.value())

    def trigger(self, pos):
        self.controller.trigger(pos)

    def wait(self, timeout=30000):
        """Wait for stage to finish moving or homing
        Need to re-implement the same routine as in
        controller here to include processEvents()"""
        if not self.online:
            return False
        if not self.is_moving():
            # wait for a tiny bit for the motor to start moving
            # so wait() does not immediately return
            sleep(0.1)
        timed_out = False
        start = datetime.now()
        while self.is_moving() and not timed_out:
            timed_out = (datetime.now() -
                         start).total_seconds() > timeout / 1000
            sleep(0.1)
            QtGui.QApplication.processEvents()  # update GUI
        self.moved.emit(not timed_out)
        return not timed_out

    def move(self, pos, timeout=30000):
        self.trigger(pos)
        return self.wait(timeout=timeout)

    def is_moving(self):
        return self.controller.is_moving()

    def jog(self, dir):
        if self.spin_jog_step.value() != self.controller.jog_stepsize:
            self.controller.set_jog_stepsize(self.spin_jog_step.value())
        self.controller.jog(dir)
        self.moved.emit(True)
        self._update_gui()

    def home(self):
        for w in [self.push_fwd, self.push_bwd,
                  self.spin_go_position, self.spin_jog_step,
                  self.push_go, self.push_home, self.push_identify]:
            w.setEnabled(False)
        self.text_status.setText('Homing...')
        self.controller.trigger_home()
        return self.wait(timeout=60000)
        self._update_gui()

    def get_config(self):
        return dict(
            serial=self.serial,
            online=self.online,
            jog_stepsize=self.spin_jog_step.value(),
            go_pos=self.spin_go_position.value())

    def set_config(self, config):
        self.rescan()
        if 'serial' in config:
            indx = self.dropdown_device.findText(config['serial'])
            if indx != -1:
                self.dropdown_device.setCurrentIndex(indx)
            # if findText() returns -1, the text was not found,
            # so we don't want to connect to the wrong thing
            else:
                if 'online' in config:
                    config['online'] = False
        if 'online' in config:
            self.set_open(config['online'])
        if 'go_pos' in config:
            self.spin_go_position.setValue(config['go_pos'])
        if 'jog_stepsize' in config:
            self.spin_jog_step.setValue(config['jog_stepsize'])

    @property
    def online(self):
        return self.controller.online

    @property
    def voltage(self):
        return self.controller.voltage

    @property
    def unit(self):
        return self.controller.unit

    @property
    def serial(self):
        return self.controller.serial
        
class KCubeMirrorWidget(MotorisedMirrorButtonsWidget):
    def __init__(self,mirror=KCubeMirror(),parent=None):
        super().__init__(mirror=mirror,parent=parent)
        vbox = self.layout()
        hbox = QtGui.QHBoxLayout()
        self.push_controller = QtGui.QPushButton('Controller')
        hbox.addWidget(self.push_controller)
        vbox.addLayout(hbox)
        self.controller_widget = KCubeAssignmentWidget(controller_h=self.mirror.controller_h,
                                                        controller_v=self.mirror.controller_v,
                                                        mirror = self.mirror)
        self.settings_widget = KCubeMirrorSettingsWidget(self.mirror)
        self.push_controller.clicked.connect(self.show_controller)
        
    def show_controller(self):
        self.controller_widget.show()
        #self.controller_widget._update_gui()
        
    def get_config(self):
        return dict(controller_settings=self.controller_widget.get_config(),settings=self.settings_widget.get_config(),steps=self.spin_stepsize.value())
    
    def set_config(self,config):
        if 'settings' in config:
            self.settings_widget.set_config(config['settings'])
        if 'controller_settings' in config:
            self.controller_widget.set_config(config['controller_settings'])
        if 'steps' in config:
            self.spin_stepsize.setValue(config['steps'])

    def closeEvent(self,event):
        self.controller_widget.controller_widget_h.set_open(False)
        self.controller_widget.controller_widget_v.set_open(False)
        event.accept()


class KCubeAssignmentWidget(QtGui.QWidget):
    """ Widget to make controlling two kcubes at one time easier. Contains assignment to different serial numbers, 
        inversion, the ability to rescan and the ability to open the full control panel.
        Currently if you change the serial and open from within the controller rather than this widget 
        this widget doesn't know that, so the display will be wrong, but the behaviour should still be correct."""
    def __init__(self, controller_h = None, controller_v = None, parent = None, mirror = None):
        super().__init__(parent = parent)
        self.controller_h = (KCubePiezo() if controller_h is None else controller_h)
        self.controller_v = (KCubePiezo() if controller_v is None else controller_v)
        self.mirror = (KCubeMirror() if mirror is None else mirror)
        self.push_horizontal = QtGui.QPushButton('Horizontal')
        self.push_vertical = QtGui.QPushButton('Vertical')
        self.invert_h = QtGui.QCheckBox('Invert')
        self.invert_v = QtGui.QCheckBox('Invert')
        self.dropdown_device_h = QtGui.QComboBox()
        self.dropdown_device_v = QtGui.QComboBox()
        self.push_rescan = QtGui.QPushButton('Rescan')
        self.push_openclose_h = QtGui.QPushButton('Open')
        self.push_openclose_v = QtGui.QPushButton('Open')

        self.controller_widget_h = KCubeWidget(controller=self.controller_h)
        self.controller_widget_v = KCubeWidget(controller=self.controller_v)
        self.push_horizontal.clicked.connect(self.show_controller_h)
        self.push_vertical.clicked.connect(self.show_controller_v)
        for check in [self.invert_h,self.invert_v]: check.toggled.connect(self._update)
        self.push_rescan.clicked.connect(self.rescan)
        self.push_openclose_h.clicked.connect(self.openclose_h)#lambda: self.controller_widget_h.set_open(not self.controller_widget_h.online))
        self.push_openclose_v.clicked.connect(self.openclose_v)#lambda: self.controller_widget_v.set_open(not self.controller_widget_v.online))
        
        vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(self.push_rescan)
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(self.push_horizontal)
        hbox.addWidget(self.dropdown_device_h)
        hbox.addWidget(self.push_openclose_h)
        hbox.addWidget(self.invert_h)
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(self.push_vertical)
        hbox.addWidget(self.dropdown_device_v)
        hbox.addWidget(self.push_openclose_v)
        hbox.addWidget(self.invert_v)
        self.setLayout(vbox)
        self.rescan()

    def show_controller_h(self):
        self.controller_widget_h.show()
        self.controller_widget_h._update_gui()

    def show_controller_v(self):
        self.controller_widget_v.show()
        self.controller_widget_v._update_gui()

    def _update(self):
        invert_h  = self.invert_h.isChecked()
        invert_v = self.invert_v.isChecked()
        self.mirror.set_axes('h','v',invert_h,invert_v) #h and v b/c this is a bodge and it needs values for axes, 
                            #which aren't used here as horizontal and vertical are separate instances of kcube piezo

    def get_config(self):
        return self.mirror.axes
        
    def set_config(self,config):
        config = config.copy()
        self.invert_h.setChecked(config.pop('invert_h',False))
        self.invert_h.setChecked(config.pop('invert_v',False))
        if len(config)>0:
            logger.warning('Found unexpected keys in config: {0}'.format(list(config.keys())))

    def rescan(self):
        self.controller_h.rescan()
        self.controller_widget_h.rescan()
        self.dropdown_device_h.clear()
        self.dropdown_device_h.addItems(self.controller_h.found_serials)
        self.controller_v.rescan()
        self.controller_widget_v.rescan()
        self.dropdown_device_v.clear()
        self.dropdown_device_v.addItems(self.controller_v.found_serials)

    def openclose_h(self):
        self.controller_widget_h.dropdown_device.setCurrentIndex(self.dropdown_device_h.currentIndex())# sets the controller serial to the one in the assignment widget
        self.controller_widget_h.set_open(not self.controller_widget_h.online)
        if self.controller_widget_h.online:
            self.push_openclose_h.setText('Close')
        else:
            self.push_openclose_h.setText('Open')

    def openclose_v(self):
        self.controller_widget_v.dropdown_device.setCurrentIndex(self.dropdown_device_v.currentIndex())
        self.controller_widget_v.set_open(not self.controller_widget_v.online)
        if self.controller_widget_v.online:
            self.push_openclose_v.setText('Close')
        else:
            self.push_openclose_v.setText('Open')
        
class KCubeMirrorSettingsWidget(QtGui.QWidget):
    def __init__(self,piezomotor_mirror,parent=None):
        super().__init__(parent=parent)
        self.mirror = piezomotor_mirror
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
        self.set_config(self.mirror.axes)
        
        for check in [self.invert_h,self.invert_v]: check.toggled.connect(self._update)
        for combo in [self.axis_h,self.axis_v]: combo.addItems(['1','2','3','4'])
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
        config = config.copy()
        self.invert_h.setChecked(config.pop('invert_h',False))
        self.invert_h.setChecked(config.pop('invert_v',False))
        if len(config)>0:
            logger.warning('Found unexpected keys in config: {0}'.format(list(config.keys())))
        
        
        
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    widget=KCubeWidget()
    widget.setWindowTitle('Piezomotor KCube controller')
    widget.show()
    widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    sys.exit(app.exec_())
            
        
