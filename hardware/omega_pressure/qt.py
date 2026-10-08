import sys
from PyQt5 import QtGui, QtWidgets, QtCore
from lab_apps.gui_elements import wrap_in_panel, ContinuousButton
from hardware.omega_pressure import OmegaPressureGauge


class OmegaPressureWidget(QtGui.QWidget):
    def __init__(self, controller=None, parent=None):
        super().__init__(parent=parent)
        if controller is None:
            self.controller = OmegaPressureGauge()
        else:
            self.controller = controller

        self.dropdown_ports = QtGui.QComboBox()
        self.push_rescan = QtGui.QPushButton('Rescan')
        self.push_openclose = QtGui.QPushButton('Open')
        self.continuous = ContinuousButton(self.update, lambda: self.online)
        self.pressure_text = QtGui.QLabel('...')

        self.push_rescan.clicked.connect(self.rescan)
        self.push_openclose.clicked.connect(
            lambda: self.set_online(not self.online))

        ft = QtGui.QFont()
        ft.setFamily('Courier New')
        ft.setPointSize(14)
        self.pressure_text.setFont(ft)

        vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.dropdown_ports)
        hbox.addWidget(self.push_rescan)
        hbox.addWidget(self.push_openclose)
        hbox.addWidget(self.continuous)
        vbox.addWidget(wrap_in_panel(hbox))
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.pressure_text)
        hbox.setAlignment(QtCore.Qt.AlignCenter)
        vbox.addWidget(wrap_in_panel(hbox))

        self.setLayout(vbox)

    def rescan(self):
        self.controller.rescan()
        self.dropdown_ports.clear()
        self.dropdown_ports.addItems(self.controller.ports_available)

    def set_online(self, val):
        if val == self.online:
            self._update_openclose_text()
            return
        if val:
            try:
                self.controller.open(port=self.dropdown_ports.currentText())
            except Exception as e:
                self._update_openclose_text()
                raise e
        else:
            self.controller.close()
        self._update_openclose_text()

    def _update_openclose_text(self):
        self.push_openclose.setText(
            'Close' if self.online else 'Open')

    def update(self):
        P = self.controller.acquire_pressure()
        self.pressure_text.setText(
            '{0:5.3f} bar'.format(P))

    @property
    def online(self):
        return self.controller.online


def main():
    app = QtGui.QApplication(sys.argv)
    o = OmegaPressureWidget()
    o.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    if QtGui.QApplication.instance() is None:
        main()
    else:
        o = OmegaPressureWidget()
        o.show()
