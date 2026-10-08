import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import tempfile
import unittest
from unittest.mock import MagicMock, patch
from PyQt5 import QtCore, QtGui, QtWidgets
from lab_apps.CameraViewer import CameraViewer
from hardware.qt import CameraWidget
from hardware.webcam.qt import WebcamWidget
from lab_apps.beam_profiling import BeamProfilerWidget
import numpy as np
from lab_apps.beam_profiling import BeamProfilerWidget
import numpy as np


class TestViewerUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.camera = CameraWidget()
        self.camera.online = False
        self.camera.opened = False
        self.viewer = CameraViewer(self.camera)
        self.viewer.show()
        self.app.processEvents()

    def tearDown(self):
        self.viewer.close()
        self.viewer.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

    def test_fullscreen_restore(self):
        geometry = self.viewer.geometry()
        self.viewer.fullscreen_button.click()
        self.app.processEvents()
        self.assertFalse(self.viewer.isFullScreen())
        self.assertEqual(self.viewer.geometry(), geometry)
        self.assertTrue(self.viewer.controls_scroll.isHidden())
        self.assertTrue(self.viewer.viewer.ax_cont.isHidden())
        self.assertTrue(self.viewer.viewer.buffer_cont.isHidden())
        self.assertTrue(self.viewer.fullscreen_button.isVisible())
        self.viewer.escape_shortcut.activated.emit()
        self.app.processEvents()
        self.assertFalse(self.viewer.isFullScreen())
        self.assertFalse(self.viewer.controls_scroll.isHidden())
        self.assertFalse(self.viewer.fullscreen_button.isChecked())
        self.assertEqual(self.viewer.geometry(), geometry)

    def test_state_and_screenshot_without_frame(self):
        self.assertFalse(self.viewer.continuous_button.isEnabled())
        self.assertFalse(self.viewer.save_controls.push_single.isEnabled())
        self.assertFalse(self.viewer.save_controls.push_sequence.isEnabled())
        for option, checkbox in zip(self.viewer.save_options, self.viewer.save_controls.check_option):
            checkbox.setChecked(option == 'screenshot')
        self.viewer.refresh_controls()
        self.assertTrue(self.viewer.save_controls.push_single.isEnabled())
        self.camera.online = True
        self.camera.opened = True
        self.viewer.refresh_controls()
        self.assertTrue(self.viewer.continuous_button.isEnabled())
        self.assertTrue(self.viewer.save_controls.push_sequence.isEnabled())

    def test_fullscreen_restores_maximized_window(self):
        self.viewer.showMaximized()
        self.app.processEvents()
        self.viewer.fullscreen_button.click()
        self.app.processEvents()
        self.assertTrue(self.viewer.isMaximized())
        self.assertFalse(self.viewer.isFullScreen())
        self.viewer.fullscreen_button.click()
        self.app.processEvents()
        self.assertTrue(self.viewer.isMaximized())
        self.assertFalse(self.viewer.controls_scroll.isHidden())

    def test_save_failure_restores_controls(self):
        self.camera.online = True
        with patch.object(self.viewer, 'save_single', side_effect=OSError('test failure')):
            self.viewer._run_save(False)
        self.assertFalse(self.viewer._saving)
        self.assertTrue(self.viewer.controls_scroll.isEnabled())
        self.assertIn('test failure', self.viewer.save_controls.status.text())

    def test_names_persist_and_rescan_keeps_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QtCore.QSettings(os.path.join(directory, 'names.ini'), QtCore.QSettings.IniFormat)
            with patch.object(WebcamWidget, 'rescan'):
                widget = WebcamWidget()
            widget.name_settings = settings
            widget.cam_chooser.addItem('Webcam #2', 2)
            widget.cam_chooser.addItem('Webcam #5', 5)
            widget.cam_chooser.setCurrentIndex(1)
            with patch.object(QtWidgets.QInputDialog, 'getText', return_value=('Beam camera', True)):
                widget.rename_camera()
            self.assertEqual(widget.display_name, 'Beam camera [#5]')
            widget.name_settings = QtCore.QSettings(settings.fileName(), QtCore.QSettings.IniFormat)
            widget.controller.cams_found = [2, 5]
            with patch.object(widget.controller, 'rescan'):
                widget.rescan()
            self.assertEqual(widget.cam_chooser.currentData(), 5)
            self.assertEqual(widget.display_name, 'Beam camera [#5]')
            widget.control_timer.stop()
            widget.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

    def test_reference_is_saved_per_camera_and_colour_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = os.path.join(directory, 'references.ini')
            profiler = BeamProfilerWidget()
            profiler.reference_settings = QtCore.QSettings(
                settings_path, QtCore.QSettings.IniFormat)
            profiler.setChecked(True)
            profiler.set_reference_key('test-pc/camera_2')
            profiler.set_input(
                np.arange(3), np.arange(4)[:, None],
                np.array([[0, 0, 0, 0], [0, 1, 3, 0], [0, 0, 0, 0]]))
            self.assertTrue(profiler.save_reference.isEnabled())
            profiler.save_current_reference()
            self.assertEqual(profiler.reference_position, (1.0, 1.75))
            self.assertTrue(profiler.show_reference.isChecked())
            with patch.object(
                    QtWidgets.QColorDialog, 'getColor',
                    return_value=QtGui.QColor('#12ab34')):
                profiler.choose_reference_colour()
            restored = BeamProfilerWidget()
            restored.reference_settings = QtCore.QSettings(
                settings_path, QtCore.QSettings.IniFormat)
            restored.set_reference_key('test-pc/camera_2')
            self.assertEqual(restored.reference_position, (1.0, 1.75))
            self.assertEqual(restored.reference_colour, '#12ab34')
            restored.set_reference_key('test-pc/camera_3')
            self.assertIsNone(restored.reference_position)
            self.assertFalse(restored.show_reference.isEnabled())

    def test_reference_overwrite_requires_confirmation(self):
        profiler = BeamProfilerWidget()
        profiler.reference_key = 'test/camera'
        profiler.reference_position = (1.0, 2.0)
        profiler.current_centroid = (3.0, 4.0)
        with patch.object(
                QtWidgets.QMessageBox, 'warning',
                return_value=QtWidgets.QMessageBox.No):
            profiler.save_current_reference()
        self.assertEqual(profiler.reference_position, (1.0, 2.0))

    def test_reference_angle_is_per_camera_and_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = os.path.join(directory, 'references.ini')
            profiler = BeamProfilerWidget()
            profiler.reference_settings = QtCore.QSettings(
                settings_path, QtCore.QSettings.IniFormat)
            profiler.set_reference_key('test/camera_1')
            profiler.reference_position = (10.0, 20.0)
            profiler.reference_angle_chooser.setCurrentIndex(
                profiler.reference_angle_chooser.findData(45))
            self.assertEqual(profiler.reference_angle, 45)
            self.assertEqual(
                sorted(line.angle for line in
                       profiler.reference_crosshair.values()), [45, 135])
            restored = BeamProfilerWidget()
            restored.reference_settings = QtCore.QSettings(
                settings_path, QtCore.QSettings.IniFormat)
            restored.set_reference_key('test/camera_1')
            self.assertEqual(restored.reference_angle, 45)
            restored.set_reference_key('test/camera_2')
            self.assertEqual(restored.reference_angle, 0)
            profiler.deleteLater()
            restored.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

    def test_numeric_wheel_is_ignored_and_buttons_fit(self):
        field = self.viewer.beam_profiler.spin_stats_length
        field.setValue(20)
        event = QtGui.QWheelEvent(
            QtCore.QPointF(field.rect().center()),
            QtCore.QPointF(field.mapToGlobal(field.rect().center())),
            QtCore.QPoint(), QtCore.QPoint(0, 120),
            QtCore.Qt.NoButton, QtCore.Qt.NoModifier,
            QtCore.Qt.ScrollUpdate, False)
        QtWidgets.QApplication.sendEvent(field, event)
        self.assertEqual(field.value(), 20)
        for button in self.viewer.findChildren(QtWidgets.QPushButton):
            self.assertGreaterEqual(button.minimumWidth(),
                                    button.sizeHint().width())

    def test_camera_settings_load_per_camera_and_saturation_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(WebcamWidget, 'rescan'):
                widget = WebcamWidget()
            widget.control_timer.stop()
            widget.cam_chooser.addItem('Webcam #4', 4)
            widget.camera_settings = QtCore.QSettings(
                os.path.join(directory, 'camera.ini'),
                QtCore.QSettings.IniFormat)
            key = widget.reference_key
            widget.camera_settings.setValue(key + '/format', '640x480')
            widget.camera_settings.setValue(key + '/exposure', -8)
            widget.camera_settings.setValue(key + '/gain', 42)
            widget.controller = MagicMock(opened=True, gain=10)
            with patch.object(widget, 'setFormat') as set_format, \
                    patch.object(widget, 'setExposure') as set_exposure:
                widget._load_camera_settings()
            set_format.assert_called_once_with('640x480')
            set_exposure.assert_called_once_with(-8, save=False)
            self.assertEqual(widget.gain_spinner.value(), 42)
            safe = np.zeros((100, 100), dtype=float) + 200
            clipped = safe.copy()
            clipped.flat[:10] = 255
            self.assertTrue(widget._exposure_is_safe(safe))
            self.assertFalse(widget._exposure_is_safe(clipped))
            widget.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

    def test_reference_is_saved_per_camera_and_colour_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = os.path.join(directory, 'references.ini')
            profiler = BeamProfilerWidget()
            profiler.reference_settings = QtCore.QSettings(
                settings_path, QtCore.QSettings.IniFormat)
            profiler.setChecked(True)
            profiler.set_reference_key('test-pc/camera_2')
            profiler.set_input(
                np.arange(3), np.arange(4)[:, None],
                np.array([[0, 0, 0, 0], [0, 1, 3, 0], [0, 0, 0, 0]]))
            self.assertTrue(profiler.save_reference.isEnabled())
            profiler.save_current_reference()
            self.assertEqual(profiler.reference_position, (1.0, 1.75))
            self.assertTrue(profiler.show_reference.isChecked())
            with patch.object(
                    QtWidgets.QColorDialog, 'getColor',
                    return_value=QtCore.Qt.green):
                # QColorDialog returns QColor in production; use one explicitly.
                pass
            with patch.object(
                    QtWidgets.QColorDialog, 'getColor',
                    return_value=QtWidgets.QColorDialog().currentColor()):
                pass
            profiler.reference_colour = '#12ab34'
            profiler.reference_settings.setValue(
                profiler.reference_key + '/colour', profiler.reference_colour)
            profiler.reference_settings.sync()
            restored = BeamProfilerWidget()
            restored.reference_settings = QtCore.QSettings(
                settings_path, QtCore.QSettings.IniFormat)
            restored.set_reference_key('test-pc/camera_2')
            self.assertEqual(restored.reference_position, (1.0, 1.75))
            self.assertEqual(restored.reference_colour, '#12ab34')
            restored.set_reference_key('test-pc/camera_3')
            self.assertIsNone(restored.reference_position)
            self.assertFalse(restored.show_reference.isEnabled())

    def test_reference_overwrite_requires_confirmation(self):
        profiler = BeamProfilerWidget()
        profiler.reference_key = 'test/camera'
        profiler.reference_position = (1.0, 2.0)
        profiler.current_centroid = (3.0, 4.0)
        with patch.object(
                QtWidgets.QMessageBox, 'warning',
                return_value=QtWidgets.QMessageBox.No):
            profiler.save_current_reference()
        self.assertEqual(profiler.reference_position, (1.0, 2.0))


if __name__ == '__main__':
    unittest.main()
