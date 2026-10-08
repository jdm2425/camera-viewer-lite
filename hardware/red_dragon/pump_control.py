import logging
import sys
import os
import yaml
from datetime import datetime
from shutil import copyfile
from PyQt5 import QtGui, QtWidgets, QtCore
import serial
from serial.tools.list_ports import comports
from time import time, sleep
from lab_apps.gui_elements import wrap_in_panel

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RedDragonPumpController(QtGui.QWidget):

    """Widget to control the pump lasers on the Red Dragon
    Consists of three PIDMLaserControllerWidgets and an update timer

    Attributes:
        check_update_timer (QCheckBox): Checkbox indicating whether to update
        path (string): path to folder for config file and (future) logs
        pump_controllers (list): list of PIDMLaserControllerWidget
        push_save_config (QPushButton): click to save config file
        spin_update_period (QSpinBox): Spinner to set update period
        status_text (QLabel): Text across the top which displays
                              Current status and any errors
        timer (QTimer): Timer updating currents
    """

    def __init__(self, path=None, parent=None):
        super().__init__(parent=parent)
        if path is None:
            self.path = os.path.join(
                os.path.expanduser('~'),
                'Documents',
                'Red_Dragon_Controller')
        else:
            self.path = path

        ft = QtGui.QFont()
        ft.setFamily('Courier New')
        ft.setPointSize(10)

        self.pump_controllers = [PIDMLaserControllerWidget() for i in range(3)]
        self.check_update_timer = QtGui.QCheckBox('Update every:')
        self.check_update_timer.clicked.connect(self.start_stop_timer)
        self.spin_update_period = QtGui.QSpinBox()
        self.spin_update_period.setRange(1, 10)
        self.spin_update_period.valueChanged.connect(self._update_period)
        self.push_save_config = QtGui.QPushButton('Save config')
        self.push_save_config.clicked.connect(self.save_config_file)
        self.status_text = QtGui.QLabel('...')
        self.status_text.setFont(ft)
        self.status_text.setAlignment(QtCore.Qt.AlignCenter)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._timer_func)
        self.timer.setInterval(1000)

        vbox = QtGui.QVBoxLayout()
        vbox.setSpacing(0)
        hbox = QtGui.QHBoxLayout()
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(self.check_update_timer)
        hbox2.addWidget(self.spin_update_period)
        hbox2.addWidget(QtGui.QLabel('seconds'))
        hbox2.setAlignment(QtCore.Qt.AlignLeft)
        hbox.addLayout(hbox2)
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(self.status_text)
        hbox2.setAlignment(QtCore.Qt.AlignCenter)
        hbox.addLayout(hbox2)
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(self.push_save_config)
        hbox2.setAlignment(QtCore.Qt.AlignRight)
        hbox.addLayout(hbox2)
        vbox.addWidget(wrap_in_panel(hbox))
        for ix, controller in enumerate(self.pump_controllers):
            hbox = QtGui.QHBoxLayout()
            hbox.addWidget(QtGui.QLabel('Pump {0}'.format(ix + 1)))
            hbox.addWidget(controller)
            vbox.addLayout(hbox)
        vbox.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(vbox)

        self.load_config_file()

    def start_stop_timer(self):
        val = self.check_update_timer.isChecked()
        if val:
            self.timer.start()
        else:
            self.timer.stop()

    def _update_period(self):
        self.timer.setInterval(1000*self.spin_update_period.value())

    def _timer_func(self):
        error = []
        for idx, controller in enumerate(self.pump_controllers):
            self.status_text.setText(
                'Reading current from pump {0}'.format(idx+1))
            self.status_text.setStyleSheet(
                "color : black")
            QtGui.QApplication.processEvents()
            try:
                controller.update()
            except IOError:

                QtGui.QApplication.processEvents()
                error.append(idx+1)
        if not error:
            self.status_text.setText(
                'Updated {0:%Y-%m-%d %H:%M:%S}'.format(datetime.now()))
            self.status_text.setStyleSheet(
                "color : green")
        else:
            self.status_text.setText(
                'Reading from pump {0} failed.'.format(error))
            self.status_text.setStyleSheet(
                "color : red")
        QtGui.QApplication.processEvents()

    def get_config(self):
        return dict(
            pump1=self.pump_controllers[0].get_config(),
            pump2=self.pump_controllers[1].get_config(),
            pump3=self.pump_controllers[2].get_config(),
            update_period=self.spin_update_period.value())

    def set_config(self, config):
        self.pump_controllers[0].set_config(
            config.pop('pump1', dict()))
        self.pump_controllers[1].set_config(
            config.pop('pump2', dict()))
        self.pump_controllers[2].set_config(
            config.pop('pump3', dict()))
        self.spin_update_period.setValue(
            config.pop('update_period', 1))
        if len(config) > 0:
            raise Exception('Found unused keys in config.')

    def save_config_file(self):
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        contents = os.listdir(self.path)
        files = [c for c in contents if c.endswith('config.yml')]
        if files:
            copyfile(
                os.path.join(self.path, files[0]),
                os.path.join(self.path, 'config.yml.backup'))
        with open(
                os.path.join(self.path, 'config.yml'), 'w') as file:
            yaml.dump(self.get_config(), file, default_flow_style=False)

    def load_config_file(self):
        if not os.path.isdir(self.path):
            return
        contents = os.listdir(self.path)
        files = [c for c in contents if c.endswith('config.yml')]
        if files:
            with open(
                    os.path.join(self.path, 'config.yml'), 'r') as file:
                config = yaml.load(file)
                if config is not None:
                    self.set_config(config)

    def closeEvent(self, event):
        self.save_config_file()
        event.accept()


class PIDMLaserControllerWidget(QtGui.QWidget):

    """Controller widget for a single PI DM30/40 laser

    Attributes:
        currents (dict): Contains set and actual currents
        dropdown_ports (QComboBox): Serial port selector
        online (bool): True if serial is connected and open
        ports_available (list): List of availabe serial ports
        push_open (QPushButton): Open/serial port
        push_set (QPushButton): Set current to value in spin_current
        push_zero (QPushButton): Set current to 0 A
        serial (serial): pySerial serial object
        spin_current (QDoubleSpinBox): Spinner to set current
        status (dict): Status of laser (shutter, LDD etc)
        text_actual_current (QLabel): Displays actual current
        text_set_current (QLabel): Displays set current
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ports_available = [port[0] for port in comports()]

        ft = QtGui.QFont()
        ft.setFamily('Courier New')
        ft.setPointSize(14)

        self.dropdown_ports = QtGui.QComboBox()
        self.dropdown_ports.addItems(self.ports_available)
        self.push_open = QtGui.QPushButton('Open')
        self.text_set_current = QtGui.QLabel('{0:5.2f} A'.format(0))
        self.text_set_current.setFont(ft)
        self.text_actual_current = QtGui.QLabel('{0:5.2f} A'.format(0))
        self.text_actual_current.setFont(ft)
        self.push_zero = QtGui.QPushButton('0 A')
        self.push_set = QtGui.QPushButton('Set: ')
        self.spin_current = QtGui.QDoubleSpinBox()
        self.spin_current.setRange(0, 45)
        self.spin_current.setSingleStep(0.25)
        self.spin_current.setValue(35)

        self.push_open.clicked.connect(self.open_pushed)
        self.push_zero.clicked.connect(lambda: self.set_current(0))
        self.push_set.clicked.connect(
            lambda: self.set_current(self.spin_current.value()))

        hbox = QtGui.QHBoxLayout()
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(self.dropdown_ports)
        hbox2.addWidget(self.push_open)
        self.port_panel = wrap_in_panel(hbox2, 'Unlock')
        self.port_panel.setCheckable(True)
        hbox.addWidget(self.port_panel)
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(self.push_zero)
        hbox2.addWidget(self.push_set)
        hbox2.addWidget(self.spin_current)
        hbox.addWidget(
            wrap_in_panel(hbox2, 'Set'))
        hbox.addWidget(
            wrap_in_panel(self.text_set_current, 'Set Current'))
        hbox.addWidget(
            wrap_in_panel(self.text_actual_current, 'Actual Current'))

        self.online = False
        self.serial = None
        self.status = None
        self.currents = dict(set=0, actual=0, max=0)

        self.setLayout(hbox)

    def open_pushed(self):
        logger.debug('Open pushed')
        self.set_online(not self.online)

    def set_online(self, val):
        """Set online to True or False

        Args:
            val (bool): value to set online to

        Returns:
            None
        """
        logger.debug('Setting online to {0}'.format(val))
        if val == self.online:
            self.update_openclose_text()
            return
        if val:
            self.serial = serial.Serial()
            self.serial.baudrate = 19200
            self.serial.port = self.dropdown_ports.currentText()
            self.serial.open()
            self.online = True
            self.update_openclose_text()
            try:
                self.update(all=True)
                self.read_max_current()
            except IOError:
                logger.warning('Reading serial port failed')
        else:
            if self.serial is not None:
                self.serial.close()
                self.online = False
                self.update_openclose_text()

    def update_openclose_text(self):
        """Update text on open/close button depending on online state
        """
        text = ('Close' if self.online else 'Open')
        self.push_open.setText(text)

    def read_set_current(self):
        """Read the set (desired) current. Also updates GUI.

        Returns:
            float: Set current in Amps
        """
        if not self. online:
            return 0
        cmd = '000A'
        self.send_cmd(cmd)
        tmp = self.read_serial(7)
        # split into two-character chunks (i.e. 1 byte in hex):
        chunks = [tmp[i:i + 2] for i in range(0, len(tmp), 2)]
        # convert chunks to numbers (except newline at the end):
        byte_values = [int(chunk, 16) for chunk in chunks[0:-1]]
        # 2nd and 3rd bytes contain the value with 2nd byte most significant:
        current = byte_values[2] * 256 + byte_values[3]
        self.currents['set'] = current / 100
        self.text_set_current.setText(
            '{0:5.2f} A'.format(self.currents['set']))
        return current / 100

    def read_actual_current(self):
        """Read the actual current. Also updates GUI.

        Returns:
            float: Actual current in Amps
        """
        if not self.online:
            return 0
        cmd = '000B'
        self.send_cmd(cmd)
        tmp = self.read_serial(7)
        chunks = [tmp[i:i + 2] for i in range(0, len(tmp), 2)]
        byte_values = [int(chunk, 16) for chunk in chunks[0:-1]]
        current = byte_values[2] * 256 + byte_values[3]
        # value is in 0.01 A - convert to A:
        self.currents['actual'] = current / 100
        self.text_actual_current.setText(
            '{0:5.2f} A'.format(self.currents['actual']))
        return current / 100

    def read_max_current(self):
        """Read the maximum current.

        Returns:
            float: max current in Amps.
        """
        if not self.online:
            return 0
        cmd = '000D'
        self.send_cmd(cmd)
        tmp = self.read_serial(7)
        chunks = [tmp[i:i + 2] for i in range(0, len(tmp), 2)]
        byte_values = [int(chunk, 16) for chunk in chunks[0:-1]]
        current = byte_values[2] * 256 + byte_values[3]
        self.currents['max'] = current / 100
        return current / 100

    def set_current(self, current):
        """Set current to some value

        Args:
            current (float): Desired current in Amps

        Returns:
            None
        """
        if not self.online:
            return
        cmd = '0109'
        value = format(int(current * 100), '04x')
        self.send_cmd(cmd + value)
        self.read_serial(7)
        self.update(all=True)

    def set_shutter_onoff(self, val):
        """Open or close shutter (not currently used)

        Args:
            val (bool): True for open, False for close

        Returns:
            None
        """
        if not self.online:
            return
        cmd = ('01010100' if val else '01010000')
        self.send_cmd(cmd)
        self.update()

    def read_status(self):
        """Read laser status

        Returns:
            dict: contains fields (all bool) that give information
            on laser status, see below for fields
        """
        if not self.online:
            return dict()
        cmd = '0008'
        self.send_cmd(cmd)
        tmp = self.read_serial(7)
        chunks = [tmp[i:i + 2] for i in range(0, len(tmp), 2)]
        status_byte = int(chunks[2], 16)
        ret = dict(
            ldd_on=bool(status_byte & 1),
            shutter_on=bool(status_byte & 2),
            qsw_on=bool(status_byte & 4),
            keypad_enabled=bool(status_byte & 8),
            interlock=bool(status_byte & 32),
            key_on=bool(status_byte & 64),
            power_on=bool(status_byte & 128))
        self.status = ret
        return ret

    def set_LDD_onoff(self, val):
        """Turn LDD on or orr

        Args:
            val (bool): True for on, False for off

        Returns:
            TYPE: Description
        """
        if not self.online:
            return
        cmd = ('01000100' if val else '01000000')
        self.send_cmd(cmd)
        self.update()

    def send_cmd(self, cmd):
        """Utility function to send serial command with checksum

        Args:
            cmd (string): Hex string of command

        Raises:
            Exception: If serial port is not connected
        """
        def checksum(cmd):
            chunks = [cmd[i:i + 2] for i in range(0, len(cmd), 2)]
            byte_values = [int(chunk, 16) for chunk in chunks]
            return format(sum(byte_values), '04x')
        if not self.online:
            raise Exception('Cannot send command - not online')
        self.serial.flushInput()
        self.serial.write((cmd + checksum(cmd) + '\r').encode('ascii'))

    def read_serial(self, length, timeout=2):
        """Utility function to read from serial port with timeout

        Args:
            length (int): Number of bytes to read
            timeout (float, optional): How long to wait
            for length bytes to be available, in seconds

        Returns:
            list: Bytes read from serial ports

        Raises:
            Exception: If reading failed (did not get length bytes
            before timeout)
        """
        now = time()
        while self.serial.inWaiting() < length:
            sleep(0.2)
            if time() - now > timeout:
                raise IOError('Reading serial port timed out')
        return self.serial.read(self.serial.inWaiting())

    def update(self, all=False):
        """Update currents and GUI

        Args:
            all (bool, optional): If True, updates set currents and status
            as well as actual current. Defaults to False.
        """
        self.read_actual_current()
        if all:
            self.read_set_current()
            self.read_status()

    def get_config(self):
        return dict(
            port=(None if self.serial is None else self.serial.port),
            online=self.online,
            port_unlocked=self.port_panel.isChecked())

    def set_config(self, config):
        port = config.pop('port', None)
        if port is not None:
            self.dropdown_ports.setCurrentIndex(
                self.dropdown_ports.findText(port))
        self.set_online(config.pop('online', False))
        self.port_panel.setChecked(
            config.pop('port_unlocked', True))
        if len(config) > 0:
            raise Exception('Found unused keys in config.')


def main():
    app = QtGui.QApplication(sys.argv)
    o = RedDragonPumpController()
    o.show()
    app.exec()


if __name__ == '__main__':
    if QtGui.QApplication.instance() is None:
        main()
    else:
        o = RedDragonPumpController()
        o.show()
