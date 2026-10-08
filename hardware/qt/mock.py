import numpy as np
from time import sleep
import logging
from scipy.interpolate import interp1d
from datetime import datetime
from PyQt5 import QtGui, QtWidgets, QtCore
import mathx
import fourier
from hardware.qt.widget_interfaces import (
    SpectrometerWidget, AbsoluteStageWidget, CameraWidget)

logger = logging.getLogger(__name__)


class Spectrometer(SpectrometerWidget):
    def __init__(self, config={}, parent=None, **kwargs):
        SpectrometerWidget.__init__(self, parent, **kwargs)
        vbox = QtGui.QVBoxLayout()
        self.setLayout(vbox)
        # Spectral range and resolution
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        # Min wavelength
        hbox.addWidget(QtGui.QLabel('Wavelength (nm): min:'))
        sb = QtGui.QDoubleSpinBox()
        self.lamb_min = sb
        hbox.addWidget(sb)
        sb.setRange(0, 1e10)
        sb.setValue(config.pop('lamb_min', 100))
        sb.valueChanged.connect(self.update)
        # Max wavelength
        hbox.addWidget(QtGui.QLabel('max:'))
        sb = QtGui.QDoubleSpinBox()
        self.lamb_max = sb
        hbox.addWidget(sb)
        sb.setRange(0, 1e10)
        sb.setValue(config.pop('lamb_max', 1200))
        sb.valueChanged.connect(self.update)
        # Num points
        hbox.addWidget(QtGui.QLabel('num:'))
        sb = QtGui.QSpinBox()
        self.lamb_num = sb
        hbox.addWidget(sb)
        sb.setRange(0, 1e4)
        sb.setValue(config.pop('lamb_num', 10000))
        sb.valueChanged.connect(self.update)
        # Signal
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        # Noise
        hbox.addWidget(QtGui.QLabel('Noise (counts):'))
        sb = QtGui.QDoubleSpinBox()
        self.noise = sb
        sb.setValue(config.pop('noise', 1))
        sb.setRange(0, 1e3)
        hbox.addWidget(sb)
        # Bit depth
        hbox.addWidget(QtGui.QLabel('Bit depth:'))
        sb = QtGui.QSpinBox()
        self.bit_depth = sb
        sb.setValue(config.pop('bit_depth', 8))
        sb.setRange(1, 16)
        hbox.addWidget(sb)
        # Intensity
        hbox.addWidget(QtGui.QLabel('Peak intensity:'))
        sb = QtGui.QDoubleSpinBox()
        self.peak_intensity = sb
        sb.setRange(0, 2**17)
        sb.setValue(config.pop('peak_intensity', 128))
        sb.valueChanged.connect(self.update)
        hbox.addWidget(sb)
        # GUI finished
        self.online = True
        self.set_input([0, 1], [0, 1])
        if len(config) > 0:
            logger.warning('Unused config keys %s' % str(config.keys()))
        self.update()

    def trigger(self):
        # Apply noise to ideal beam image
        data = self.intensity + \
            np.random.normal(0, self.noise.value(), self.intensity.shape)
        # Quantize and clip to maximum permitted by bit depth
        self.spectrum = np.clip(np.round(data).astype(
            int), 0, 2**self.bit_depth.value() - 1)
        self.datetime = datetime.now()

    def wait(self, timeout=5000):
        sleep(0.01)
        self.spectrum_acquired.emit()
        return True

    def set_input(self, lamb, intensity):
        self.input_lamb = lamb
        self.input_intensity = intensity
        self.update()

    def update(self):
        self.wavelengths = np.linspace(
            self.lamb_min.value(),
            self.lamb_max.value(),
            self.lamb_num.value())
        self.intensity = interp1d(
            self.input_lamb,
            mathx.norm_max(self.input_intensity) * self.peak_intensity.value(),
            bounds_error=False,
            fill_value=0)(self.wavelengths)
        self.wavelengths_changed.emit()

    def get_config(self):
        return dict(
            lamb_min=self.lamb_min.value(),
            lamb_max=self.lamb_max.value(),
            lamb_num=self.lamb_num.value(),
            noise=self.noise.value(),
            bit_depth=self.bit_depth.value(),
            peak_intensity=self.peak_intensity.value())

    def set_config(self, config):
        self.lamb_min.setValue(config.pop('lamb_min', 600))
        self.lamb_max.setValue(config.pop('lamb_max', 1000))
        self.lamb_num.setValue(config.pop('lamb_num', 512))
        self.noise.setValue(config.pop('noise', 0))
        self.bit_depth.setValue(config.pop('bit_depth', 8))
        self.peak_intensity.setValue(config.pop('peak_intensity', 128))
        if len(config) > 0:
            logger.warning(
                'Found unused config keys {0}'.format(config.keys()))

    def set_peak_intensity(self, peak):
        self.peak_intensity.setValue(peak)


class AbsoluteStage(AbsoluteStageWidget):
    def __init__(self, config={}, parent=None):
        super().__init__(parent=parent)
        self.unit = 'mm'
        self.max_pos = 25
        self.min_pos = 0
        self.online = True
        self.is_homed = True
        self.position = 0
        self.spin_pos = QtGui.QDoubleSpinBox()
        self.spin_pos.setRange(self.min_pos, self.max_pos)
        self.spin_pos.setSingleStep(0.005)
        self.spin_pos.setDecimals(4)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel('Position [mm]: '))
        hbox.addWidget(self.spin_pos)
        hbox.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(hbox)
        self.spin_pos.valueChanged.connect(self.move)
        self.set_config(config)

    def trigger(self, pos):
        if pos == self.position:
            return
        if pos > self.max_pos:
            self.position = self.max_pos
        elif pos < self.min_pos:
            self.position = self.min_pos
        else:
            self.position = pos
        self.spin_pos.setValue(self.position)

    def wait(self, timeout=0):
        self.moved.emit(True)
        return True

    def move(self, pos, timeout=0):
        self.trigger(pos)
        return self.wait(timeout=timeout)

    def home(self, timeout=0):
        return True

    def get_config(self):
        return dict()

    def set_config(self, config):
        return


class Camera(CameraWidget):
    """Mock camera with a beam on it.

    Attributes:
        u (array of shape (nx,)): x axis in SI units
        v (array of shape (ny,1)): y axis in SI units
        beam (self.Beam): current beam

        num_pix_x (QSpinBox): num. pixels in x, likewise for y
        pix_size (QDoubleSpinBox): in microns
        noise (QDoubleSpinBox): noise mean in counts
        bit_depth (QSpinBox): bit depth (log_2 of 1+max. signal)
        intensity (QSpinBox): peak intensity of beam in counts
    """
    pix_size = 5e-6

    def __init__(self):  # parent=None,**kwargs):
        super().__init__()  # ,parent,**kwargs)
        vbox = QtGui.QVBoxLayout()
        self.setLayout(vbox)
        # Resolution and pixel size
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(QtGui.QLabel('Num pix:'))

        def make_pix_spin_box(axis):
            hbox.addWidget(QtGui.QLabel(axis + ':'))
            sb = QtGui.QSpinBox()
            hbox.addWidget(sb)
            sb.setRange(2, 1e4)
            sb.setValue({'x': 320, 'y': 240}[axis])
            sb.valueChanged.connect(self.update)
            return sb
        self.num_pix_x, self.num_pix_y = [
            make_pix_spin_box(axis) for axis in ('x', 'y')]
        hbox.addWidget(QtGui.QLabel('Pix size (micron):'))
        sb = QtGui.QDoubleSpinBox()
        sb.setValue(5)
        sb.setRange(1, 20)
        sb.valueChanged.connect(self.update)
        self.pix_size = sb
        hbox.addWidget(sb)
        # Noise, bit depth, intensity
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        # Noise
        hbox.addWidget(QtGui.QLabel('Noise (counts):'))
        sb = QtGui.QDoubleSpinBox()
        self.noise = sb
        sb.setValue(0)
        sb.setRange(0, 1e3)
        hbox.addWidget(sb)
        # Bit depth
        hbox.addWidget(QtGui.QLabel('Bit depth:'))
        sb = QtGui.QSpinBox()
        self.bit_depth = sb
        sb.setValue(8)
        sb.setRange(1, 16)
        hbox.addWidget(sb)
        # Intensity
        hbox.addWidget(QtGui.QLabel('Intensity:'))
        sb = QtGui.QSpinBox()
        self.intensity = sb
        sb.setRange(0, 2**17)
        sb.setValue(128)
        sb.valueChanged.connect(self.update)
        hbox.addWidget(sb)

        self.online = True
        self.set_beam(None)

    def trigger(self):
        # Apply noise to ideal beam image
        data = self.data + \
            np.random.poisson(self.noise.value(), self.data.shape)
        # Quantize and clip to maximum permitted by bit depth
        self.image = np.clip(np.round(data).astype(
            int), 0, 2**self.bit_depth.value() - 1)
        # TODO hack - I think the stabilizer code requires a transposed array
        # (with respect to definition in Camera interface class)
        self.image = self.image.T
        self.datetime = datetime.now()
        self.image_acquired.emit()

    def wait(self, timeout=5000):
        return True

    def set_beam(self, beam):
        self.beam = beam
        self.update()

    def update(self):
        """Compute axes and ideal beam image"""
        num_pix_x = self.num_pix_x.value()
        num_pix_y = self.num_pix_y.value()
        self.x = np.arange(num_pix_x, dtype=int)
        self.y = np.arange(num_pix_y, dtype=int)[:, None]
        pix_size = self.pix_size.value() * 1e-6
        self.u = (self.x - (num_pix_x - 1) / 2) * pix_size
        self.v = (self.y - (num_pix_y - 1) / 2) * pix_size
        if self.beam is not None:
            self.data = (np.exp(
                -((self.beam.x - self.u)**2 + (self.beam.y - self.v)**2) /
                self.beam.w**2) *
                self.intensity.value())
        else:
            self.data = np.zeros(np.broadcast(self.x, self.y).shape)

    def get_config(self):
        return dict(
            num_pix_x=self.num_pix_x.value(),
            num_pix_y=self.num_pix_y.value(),
            pix_size=self.pix_size.value(),
            noise=self.noise.value(),
            intensity=self.intensity.value())

    def set_config(self, config):
        self.num_pix_x.setValue(config['num_pix_x'])
        self.num_pix_y.setValue(config['num_pix_y'])
        self.pix_size.setValue(config['pix_size'])
        self.noise.setValue(config['noise'])
        self.intensity.setValue(config['intensity'])


class XFROG:
    def __init__(self):
        self.spectrometer = Spectrometer()
        self.stage = AbsoluteStage()
        self.spectrometer.set_config(dict(
            bit_depth=14,
            lamb_max=1000,
            lamb_min=190,
            lamb_num=2048,
            noise=1,
            peak_intensity=1e4))
        self.spectrometer.update()

        self.t = np.linspace(-2000, 2000, 2**15)
        self.omega = fourier.conj_axis(self.t, offset=1.9, offset_type='start')
        self.wl = 2 * np.pi * 300 / self.omega
        self.ftd = fourier.FTD(sign=1, x=self.t, k=self.omega)

        def ft(Et):
            return self.ftd.trans(Et)

        def ift(Ew):
            return self.ftd.inv_trans(Ew)

        phi2 = 0.5
        phi3 = 0
        spm = 0

        spm_gate = 0
        phi2_gate = 500
        phi3_gate = 2000

        tau_test = 3
        tau_gate = 70
        omega0_test = 2*np.pi*299.8 / 1800
        omega0_gate = 2*np.pi*299.8 / 790
        self.test = (np.exp(-((2 * np.log(2) * self.t / tau_test)**2))
                     * np.exp(-1j * omega0_test * self.t))
        self.test *= np.exp(1j * spm * np.abs(self.test)**2)
        self.test = ift(ft(self.test)
                        * np.exp(1j
                                 * (phi2/2 * (self.omega - omega0_test)**2
                                    + phi3/6 * (self.omega - omega0_test)**3)
                                 )
                        )
        self.gate = (np.exp(-((2*np.log(2) * self.t/tau_gate)**2))
                     * np.exp(-1j * omega0_gate * self.t))
        self.gate *= np.exp(1j * spm_gate * np.abs(self.gate)**2)
        self.gate = ift(ft(self.gate)
                        * np.exp(1j
                                 * (phi2_gate/2*(self.omega - omega0_gate)**2
                                    + phi3_gate/6*(self.omega - omega0_gate)**3)
                                 )
                        )
        self.gate_spectrum = np.abs(ft(self.gate))**2
        self.gate_phase = np.unwrap(np.angle(ft(self.gate)))
        self.gate_phase -= self.gate_phase[np.abs(self.omega-omega0_gate).argmin()]
        self.gate_spectrum *= (self.gate_spectrum >
                               1e-6 * self.gate_spectrum.max())
        # self.gate_spectrum += np.abs(
        # np.random.normal(0, 1e-4, self.gate_spectrum.shape))
        self.test_spectrum = np.abs(ft(self.test))**2
        self.test_phase = np.unwrap(np.angle(ft(self.test)))
        self.test_phase -= self.test_phase[np.abs(self.omega-omega0_test).argmin()]

        self.t0 = 1  # t0 in mm gives stage position of central overlap

        self.stage.moved.connect(self.update)

    def update(self):
        def ft(Et):
            return self.ftd.trans(Et)

        def ift(Ew):
            return self.ftd.inv_trans(Ew)

        def taushift(Et, tau):
            return ift(ft(Et) * np.exp(1j * self.omega * tau))
        tau = 2 * (self.stage.position - self.t0) / 2.998e-4
        gate_shift = taushift(self.gate, tau)
        trace = np.abs(ft(gate_shift * self.test))**2 #for DFG add a np.conj in front of gate_shift
        self.spectrometer.set_peak_intensity(2e3 * trace.max())
        self.spectrometer.set_input(self.wl, trace)
