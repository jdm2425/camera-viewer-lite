import sys
import numpy as np
from PyQt5 import QtGui, QtWidgets, QtCore
from collections import deque
from mathx import moment
import pyqtgraph_extended as pg


class BeamProfilerWidget(QtGui.QGroupBox):
    def __init__(self, plot=None, parent=None):
        super().__init__(parent=parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.setTitle('Beam Profiling')
        self.plot = plot

        self.formstr = '{0:6.2f}'
        self.reference_settings = QtCore.QSettings(
            'CameraViewerLite', 'CameraReferences')
        self.reference_key = None
        self.reference_position = None
        self.reference_colour = '#00d060'
        self.reference_angle = 0
        self.current_centroid = None

        self.check_centroid = QtGui.QCheckBox('Find centroid')
        self.check_centroid.setChecked(True)
        self.text_centroid_x = QtGui.QLabel(self.formstr.format(0))
        self.text_centroid_y = QtGui.QLabel(self.formstr.format(0))
        self.text_mean_x = QtGui.QLabel(self.formstr.format(0))
        self.text_mean_y = QtGui.QLabel(self.formstr.format(0))
        self.text_rms_x = QtGui.QLabel(self.formstr.format(0))
        self.text_rms_y = QtGui.QLabel(self.formstr.format(0))
        self.spin_stats_length = QtGui.QSpinBox()
        self.spin_stats_length.setRange(1, 1000)
        self.spin_stats_length.setSingleStep(1)
        self.spin_stats_length.setValue(20)

        self.spin_stats_length.valueChanged.connect(self.renew_buffer)

        self.data_grid = QtGui.QGridLayout()
        self.data_grid.addWidget(QtGui.QLabel('Current'), 0, 1)
        self.data_grid.addWidget(QtGui.QLabel('Mean'), 0, 2)
        self.data_grid.addWidget(QtGui.QLabel('RMS'), 0, 3)
        self.data_grid.addWidget(QtGui.QLabel('X'), 1, 0)
        self.data_grid.addWidget(self.text_centroid_x, 1, 1)
        self.data_grid.addWidget(self.text_mean_x, 1, 2)
        self.data_grid.addWidget(self.text_rms_x, 1, 3)
        self.data_grid.addWidget(QtGui.QLabel('Y'), 2, 0)
        self.data_grid.addWidget(self.text_centroid_y, 2, 1)
        self.data_grid.addWidget(self.text_mean_y, 2, 2)
        self.data_grid.addWidget(self.text_rms_y, 2, 3)

        vbox = QtGui.QVBoxLayout()
        vbox.setAlignment(QtCore.Qt.AlignLeft)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.check_centroid)
        hbox.addLayout(self.data_grid)
        hbox.addWidget(QtGui.QLabel(
            'Buffer length:'))
        hbox.addWidget(self.spin_stats_length)
        vbox.addLayout(hbox)
        reference_box = QtGui.QHBoxLayout()
        self.show_reference = QtGui.QCheckBox('Show reference')
        self.show_reference.setEnabled(False)
        self.save_reference = QtGui.QPushButton('Save centroid as reference')
        self.save_reference.setEnabled(False)
        self.reference_colour_button = QtGui.QPushButton('Reference colour')
        self.reference_angle_chooser = QtGui.QComboBox()
        self.reference_angle_chooser.addItem('Cross (+)', 0)
        self.reference_angle_chooser.addItem('Diagonal (×)', 45)
        self.reference_angle_chooser.setToolTip(
            'Rotate the saved reference by 45 degrees to distinguish it from the centroid.')
        self.reference_colour_swatch = QtGui.QLabel()
        self.reference_colour_swatch.setFixedSize(22, 22)
        self.reference_status = QtGui.QLabel('No reference saved')
        reference_box.addWidget(self.show_reference)
        reference_box.addWidget(self.save_reference)
        reference_box.addWidget(self.reference_colour_button)
        reference_box.addWidget(self.reference_colour_swatch)
        reference_box.addWidget(self.reference_angle_chooser)
        reference_box.addWidget(self.reference_status, 1)
        vbox.addLayout(reference_box)
        self.setLayout(vbox)

        self.renew_buffer()

        self.clicked.connect(self.show_hide_crosshair)
        self.check_centroid.clicked.connect(self.show_hide_crosshair)
        self.show_reference.toggled.connect(self.show_hide_reference)
        self.save_reference.clicked.connect(self.save_current_reference)
        self.reference_colour_button.clicked.connect(self.choose_reference_colour)
        self.reference_angle_chooser.currentIndexChanged.connect(
            self.set_reference_angle)

        self.input = dict(x=None, y=None, img=None)

        self.crosshair = dict(
            h=pg.InfiniteLine(angle=0, pen=pg.mkPen('r')),
            v=pg.InfiniteLine(pen=pg.mkPen('r')))
        self.reference_crosshair = dict(
            h=pg.InfiniteLine(angle=0, pen=pg.mkPen(self.reference_colour, width=2)),
            v=pg.InfiniteLine(pen=pg.mkPen(self.reference_colour, width=2)))

        if self.plot is not None:
            for line in self.crosshair.values():
                self.plot.addItem(line)
                line.hide()
            for line in self.reference_crosshair.values():
                self.plot.addItem(line)
                line.hide()
        self._update_colour_swatch()

    def set_reference_key(self, key):
        if key == self.reference_key:
            return
        self.reference_key = key
        self.reference_position = None
        if key:
            x = self.reference_settings.value(key + '/x')
            y = self.reference_settings.value(key + '/y')
            colour = self.reference_settings.value(
                key + '/colour', '#00d060', type=str)
            self.reference_angle = self.reference_settings.value(
                key + '/angle', 0, type=int)
            if x is not None and y is not None:
                try:
                    self.reference_position = (float(x), float(y))
                except (TypeError, ValueError):
                    self.reference_position = None
            self.reference_colour = (
                colour if QtGui.QColor(colour).isValid() else '#00d060')
        blocker = QtCore.QSignalBlocker(self.reference_angle_chooser)
        index = self.reference_angle_chooser.findData(self.reference_angle)
        self.reference_angle_chooser.setCurrentIndex(max(0, index))
        del blocker
        self.show_reference.setEnabled(self.reference_position is not None)
        self.save_reference.setEnabled(
            self.reference_key is not None and self.current_centroid is not None)
        self.save_reference.setEnabled(
            self.reference_key is not None and self.current_centroid is not None)
        self.reference_status.setText(
            'Reference: X {}, Y {}'.format(
                self.formstr.format(self.reference_position[0]).strip(),
                self.formstr.format(self.reference_position[1]).strip())
            if self.reference_position is not None else 'No reference saved')
        self._update_reference_lines()
        self._update_colour_swatch()
        self.show_hide_reference()

    def save_current_reference(self):
        if self.reference_key is None or self.current_centroid is None:
            return
        if self.reference_position is not None:
            answer = QtWidgets.QMessageBox.warning(
                self, 'Overwrite reference?',
                'A reference is already saved for this camera. Replace it with the current centroid?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes:
                return
        self.reference_position = self.current_centroid
        self.reference_settings.setValue(
            self.reference_key + '/x', self.reference_position[0])
        self.reference_settings.setValue(
            self.reference_key + '/y', self.reference_position[1])
        self.reference_settings.setValue(
            self.reference_key + '/colour', self.reference_colour)
        self.reference_settings.setValue(
            self.reference_key + '/angle', self.reference_angle)
        self.reference_settings.sync()
        if self.reference_settings.status() != QtCore.QSettings.NoError:
            QtWidgets.QMessageBox.warning(
                self, 'Reference not saved',
                'The reference could not be stored on this PC.')
            return
        self.reference_status.setText(
            'Reference: X {}, Y {}'.format(
                self.formstr.format(self.reference_position[0]).strip(),
                self.formstr.format(self.reference_position[1]).strip()))
        self.show_reference.setEnabled(True)
        self.show_reference.setChecked(True)
        self._update_reference_lines()

    def choose_reference_colour(self):
        colour = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(self.reference_colour), self, 'Reference colour')
        if not colour.isValid():
            return
        self.reference_colour = colour.name()
        if self.reference_key:
            self.reference_settings.setValue(
                self.reference_key + '/colour', self.reference_colour)
            self.reference_settings.sync()
        self._update_reference_lines()
        self._update_colour_swatch()

    def _update_colour_swatch(self):
        self.reference_colour_swatch.setStyleSheet(
            'background: {}; border: 1px solid #ffffff; border-radius: 3px;'.format(
                self.reference_colour))

    def set_reference_angle(self):
        self.reference_angle = int(
            self.reference_angle_chooser.currentData() or 0)
        if self.reference_key:
            self.reference_settings.setValue(
                self.reference_key + '/angle', self.reference_angle)
            self.reference_settings.sync()
        self._update_reference_lines()

    def _update_reference_lines(self):
        pen = pg.mkPen(self.reference_colour, width=2)
        angles = ((45, 135) if self.reference_angle == 45 else (0, 90))
        for line, angle in zip(self.reference_crosshair.values(), angles):
            line.setPen(pen)
            line.setAngle(angle)
        if self.reference_position is not None:
            for line in self.reference_crosshair.values():
                line.setPos(QtCore.QPointF(*self.reference_position))

    def show_hide_reference(self):
        visible = (
            self.show_reference.isChecked()
            and self.reference_position is not None
            and self.plot is not None)
        for line in self.reference_crosshair.values():
            line.setVisible(visible)

    def set_input(self, x, y, img):
        if img.shape != (len(x.squeeze()), len(y.squeeze())):
            raise Exception('Inconsistent shapes: Image has shape {0},\
                x has shape {1} and y has shape {2}'.format(
                img.shape, x.shape, y.shape))
        self.input['x'] = x.squeeze()
        self.input['y'] = y.squeeze()
        self.input['img'] = img
        self.update()

    def show_hide_crosshair(self):
        if (self.isChecked()
            and self.check_centroid.isChecked()
                and self.plot is not None):
            for line in self.crosshair.values():
                line.show()
        else:
            for line in self.crosshair.values():
                line.hide()

    def update(self):
        if self.isChecked() and self.check_centroid.isChecked():
            self.update_centroid()

    def update_centroid(self):
        x = self.input['x']
        y = self.input['y']
        img = self.input['img']
        x_marg = img.sum(1)
        y_marg = img.sum(0)
        centroid_x = moment(x, x_marg, 1)
        centroid_y = moment(y, y_marg, 1)
        if not np.isfinite(centroid_x) or not np.isfinite(centroid_y):
            self.current_centroid = None
            self.save_reference.setEnabled(False)
            return
        self.current_centroid = (float(centroid_x), float(centroid_y))
        self.save_reference.setEnabled(self.reference_key is not None)
        self.stats_buffers['centroid_x'].append(centroid_x)
        self.stats_buffers['centroid_y'].append(centroid_y)
        mean_x = np.mean(self.stats_buffers['centroid_x'])
        mean_y = np.mean(self.stats_buffers['centroid_y'])
        sq = (np.array(self.stats_buffers['centroid_x'])-mean_x)**2
        rms_x = sq.mean()**0.5
        sq = (np.array(self.stats_buffers['centroid_y'])-mean_y)**2
        rms_y = sq.mean()**0.5

        self.text_centroid_x.setText(self.formstr.format(centroid_x))
        self.text_centroid_y.setText(self.formstr.format(centroid_y))
        self.text_mean_x.setText(self.formstr.format(mean_x))
        self.text_mean_y.setText(self.formstr.format(mean_y))
        self.text_rms_x.setText(self.formstr.format(rms_x))
        self.text_rms_y.setText(self.formstr.format(rms_y))

        if self.plot is not None:
            self.crosshair['h'].setValue(centroid_y)
            self.crosshair['v'].setValue(centroid_x)

    def renew_buffer(self):
        self.stats_buffers = dict(
            centroid_x=deque(
                maxlen=self.spin_stats_length.value()),
            centroid_y=deque(
                maxlen=self.spin_stats_length.value()))


def main():
    app = QtGui.QApplication(sys.argv)
    o = BeamProfilerWidget()
    o.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    if QtGui.QApplication.instance() is None:
        main()
    else:
        o = BeamProfilerWidget()
        o.show()
