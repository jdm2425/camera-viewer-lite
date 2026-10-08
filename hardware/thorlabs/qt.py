import logging
from PyQt5 import QtGui, QtWidgets, QtCore
from datetime import datetime
from time import sleep
from hardware.thorlabs import TCubeServo
from hardware.qt import AbsoluteStageWidget
from lab_apps.gui_elements import wrap_in_panel

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


class TCubeWidget(AbsoluteStageWidget):
    """Widget to control a TCube using the Kinesis .NET interface.

    A TCubeWidget has a TCubeServo, self.controller.
    """

    def __init__(self, controller=None, parent=None):
        """
        Args:
            controller (:class:`.TCubeServo`): if None, one is created.
        """
        super().__init__(parent=parent)
        # Create GUI elements
        self.controller = (controller
                           if controller is not None
                           else TCubeServo())
        self.dropdown_device = QtGui.QComboBox()
        self.push_rescan = QtGui.QPushButton('Rescan')
        self.push_openclose = QtGui.QPushButton('Open')
        self.text_position = QtGui.QLabel('{0:2.5f} {1}'.format(0, '--'))
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
        self.spin_jog_step.setRange(0, 5)
        self.spin_jog_step.setSingleStep(0.005)
        self.spin_jog_step.setDecimals(3)
        self.dropdown_device.setMinimumWidth(80)
        self.text_position.setFont(ft)
        self.text_status.setFont(ft)
        self.push_fwd.setArrowType(QtCore.Qt.UpArrow)
        self.push_fwd.setMinimumWidth(70)
        self.push_bwd.setArrowType(QtCore.Qt.DownArrow)
        self.push_bwd.setMinimumWidth(70)
        self.spin_go_position.setDecimals(4)
        self.spin_go_position.setValue(0)
        self.spin_go_position.setSingleStep(0.1)
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
        vbox2.addWidget(wrap_in_panel(self.text_position, 'Position'))
        vbox2.addWidget(wrap_in_panel(self.text_status, 'Status'))
        hbox.addLayout(vbox2)
        vbox2 = QtGui.QVBoxLayout()
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(self.spin_go_position)
        hbox2.addWidget(self.push_go)
        vbox2.addWidget(wrap_in_panel(hbox2, 'Move to position'))
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
            self.text_position.setText('{0:+2.5f} {1}'.format(0, '..'))
            return
        self.text_position.setText(
            '{0:+2.5f} {1}'.format(self.position, self.unit))
        self.push_home.setStyleSheet(
            'background-color: {0}'.format(
                'green' if self.controller.is_homed else 'red'))
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
            indx = self.self.dropdown_device.findText(config['serial'])
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
    def position(self):
        return self.controller.position

    @property
    def unit(self):
        return self.controller.unit

    @property
    def serial(self):
        return self.controller.serial


if __name__ == "__main__":
    widget = TCubeWidget()
    widget.setWindowTitle('TCube')
    widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    widget.show()
