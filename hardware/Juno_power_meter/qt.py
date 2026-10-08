import sys,os
from PyQt5 import QtGui, QtWidgets,QtCore
from datetime import datetime
import numpy as np
from scipy import interpolate
from collections import deque,namedtuple
from time import sleep
from hardware.Juno_power_meter.Powermeterreader import powermeterreader
import pyqtgraph_extended as pg
import pyqtgraph_recipes
import fourier
from mathx.mathx import fwhm, moment
import win32com.client
from lab_apps.gui_elements import ContinuousButton

class PowerMeterReader(QtGui.QWidget):
    """Widget to read and display the readout of a Juno Ophir power meter, and change parameters as 
    necessary"""
    def __init__(self):
        super().__init__() 
        self.power = powermeterreader()
        self.display = QtGui.QLCDNumber()
        self.dropdown_serials = QtGui.QComboBox()
        self.push_rescan = QtGui.QPushButton('Rescan')
        self.open = QtGui.QCheckBox()
        self.open.setText("Open")
        self.push_rescan.clicked.connect(self.scanner)
        self.open.toggled.connect(self.opener)
        self.stream = QtGui.QCheckBox()
        self.stream.toggled.connect(self.connecter)
        self.stream.setText("Connect")
        self.run = ContinuousButton(self.readpower)
        self.displayed = 0
        vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(self.push_rescan)
        hbox.addWidget(self.dropdown_serials)
        hbox.addWidget(self.open)
        hbox.addWidget(self.stream)#
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(self.run)
        hbox.addWidget(self.display)
        self.setLayout(vbox)
        

    def opener(self, serial=None):
        # if serial == None:
            # meter = win32com.client.Dispatch("OphirLMMeasurement.CoLMMeasurement")
            # serials = meter.ScanUSB()
            # found_devices = []
            # for serial in serials: found_devices.append(serial)
            # serial=found_devices[0]
            # self.power.newloader(serial)
            # return
        # else:
        serial = self.dropdown_serials.currentText()
        if self.open.isChecked():
            self.power.newloader(serial)
        elif self.power.handle:
            self.power.closer() #not specific to work around bug
        else:
            print('Could not connect to the Ophir power meter')
            self.display.updatetext()
            return

    def connecter(self):
        if self.stream.isChecked():
            self.power.starter()
        else:
            self.power.stopper()

    def readpower(self):
        result = self.power.AveragePower()
        print(result)
        if result == 'no data available':
            if self.displayed == 0:
                self.display.display(0.0)
                self.displayed = 1
            elif self.displayed == 1:
                pass
        else:
            resulttr = str(result)[0:6] if len(str(result)) > 5 else str(result)
            self.display.display(resulttr)
        

    def scanner(self):
        self.dropdown_serials.clear()
        self.power.reader()
        if not self.power.found_devices:
            return
        serials = self.power.found_devices
        self.dropdown_serials.addItems(serials)

    def closeEvent(self, event):
        print("Closing connection to Ophir power meter")
        self.power.closecom()
        return

class powermetercontrols(QtGui.QWidget):
    """popup window with controls for the power meter reading"""
    def __init__(self, parent=None):
        super.__init__(parent)
        



if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    widget = PowerMeterReader()
    widget.show()
    widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    sys.exit(app.exec_())
