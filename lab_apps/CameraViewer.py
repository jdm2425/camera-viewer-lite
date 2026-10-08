import sys
import logging
import os
from PyQt5 import QtGui, QtWidgets,QtCore
import scipy.io
import pickle
import numpy as np
import pyqtgraph_extended as pg
from lab_apps.gui_elements import (CameraImageViewer, SaveControls, 
    ContinuousButton, wrap_in_panel)
from lab_apps.image_processing import ImageProcessorStd
from lab_apps.beam_profiling import BeamProfilerWidget
from lab_apps.viewer_theme import apply_theme

logger = logging.getLogger(__name__)

class CameraViewer(QtGui.QWidget):
    def __init__(self,camera_widget,parent=None):
        super().__init__(parent = parent)
        self.save_options = ['.mat', '.mat (raw)', '.p', '.p (raw)', 'screenshot']
        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(12, 12, 12, 12)
        hbox.setSpacing(12)
        vbox_left = QtGui.QVBoxLayout()
        self.viewer = CameraImageViewer()
        vbox_left.addWidget(wrap_in_panel(self.viewer))
        hbox.addLayout(vbox_left, 1)
        vbox_right = QtGui.QVBoxLayout()
        self.camera_widget = camera_widget
        vbox_right.addWidget(wrap_in_panel(self.camera_widget,'Camera'))
        self.image_processor = ImageProcessorStd(self.camera_widget)
        vbox_right.addWidget(wrap_in_panel(self.image_processor,'Image Processing'))
        self.save_controls = SaveControls(self.save_options)
        vbox_right.addWidget(wrap_in_panel(self.save_controls,'Saving'))
        self.beam_profiler = BeamProfilerWidget(
            self.viewer.mainplot.plots['image'])
        vbox_right.addWidget(self.beam_profiler)
        self.continuous_button = ContinuousButton(
            self.camera_widget.acquire_image, condition=self._run_condition,
            play_pause=True)
        self.continuous_button.single.hide()
        self.continuous_button.continuous.setToolTip(
            'Play or pause live image updates without disconnecting the camera.')
        self.camera_widget.online_changed.connect(
            self._camera_online_changed)
        vbox_right.setAlignment(QtCore.Qt.AlignTop)
        vbox_right.setSpacing(10)
        widget_right = QtGui.QWidget()
        widget_right.setLayout(vbox_right)
        self.controls_scroll = QtWidgets.QScrollArea()
        self.controls_scroll.setWidgetResizable(True)
        self.controls_scroll.setWidget(widget_right)
        self.controls_scroll.setMinimumWidth(480)
        hbox.addWidget(self.controls_scroll)
        
        self.save_controls.push_single.clicked.connect(lambda: self._run_save(False))
        self.save_controls.push_sequence.clicked.connect(lambda: self._run_save(True))

        layout = QtWidgets.QVBoxLayout()
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.addWidget(self.continuous_button)
        self.connection_status = QtWidgets.QLabel()
        self.connection_status.setTextFormat(QtCore.Qt.PlainText)
        toolbar.addWidget(self.connection_status, 1)
        self.fullscreen_button = QtWidgets.QPushButton('Image only (F11)')
        self.fullscreen_button.setToolTip('Hide controls without changing the window. Restore with this button or Escape.')
        self.fullscreen_button.setCheckable(True)
        self.fullscreen_button.toggled.connect(self.set_fullscreen)
        toolbar.addWidget(self.fullscreen_button)
        layout.addLayout(toolbar)
        layout.addLayout(hbox, 1)
        self.setLayout(layout)
        self._saving = False
        self._has_frame = False
        self.fullscreen_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence('F11'), self)
        self.fullscreen_shortcut.activated.connect(self.fullscreen_button.toggle)
        self.escape_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence('Escape'), self)
        self.escape_shortcut.activated.connect(lambda: self.fullscreen_button.setChecked(False))
        self.setMinimumSize(900, 600)
        self.resize(1280, 820)
        apply_theme(self)
        self.image_processor.image_acquired.connect(self.update)
        self.image_processor.Cropper.current.clicked.connect(self.clicked_crop_current)
        self.image_processor.Cropper.current.setEnabled(True)
        self.image_processor.setMaximumHeight(16777215)
        self.state_timer = QtCore.QTimer(self)
        self.state_timer.timeout.connect(self.refresh_controls)
        self.state_timer.start(250)
        self.refresh_controls()

    def _camera_online_changed(self, online):
        if online:
            self.continuous_button.continuous.setChecked(True)
        else:
            self.continuous_button.stop()

    def set_fullscreen(self, enabled):
        # Keep the OS window state/geometry intact so camera windows can be tiled.
        self.controls_scroll.setVisible(not enabled)
        self.viewer.ax_cont.setVisible(not enabled)
        self.viewer.buffer_cont.setVisible(not enabled)
        self.continuous_button.setVisible(not enabled)
        self.setMinimumSize(360, 260) if enabled else self.setMinimumSize(900, 600)
        self.fullscreen_button.setText('Show controls (Esc)' if enabled else 'Image only (F11)')

    def refresh_controls(self):
        online = bool(self.camera_widget.online)
        opened = bool(getattr(self.camera_widget, 'opened', online))
        name = getattr(self.camera_widget, 'display_name', 'Camera')
        self.beam_profiler.set_reference_key(
            getattr(self.camera_widget, 'reference_key', None))
        state = ('Live' if online and self.continuous_button.continuous.isChecked()
                 else 'Paused' if online else 'Connected - stream unavailable'
                 if opened else 'Disconnected')
        self.connection_status.setText('{} | {}'.format(name, state))
        if not online:
            self.continuous_button.stop()
        self.continuous_button.setEnabled(online and not self._saving)
        options = self._selected_save_options()
        destination = bool(self.save_controls.folder_text.text().strip()
                           and self.save_controls.name_text.text().strip())
        self.save_controls.push_single.setEnabled(
            not self._saving and destination and bool(options)
            and (self._has_frame or options == ['screenshot']))
        self.save_controls.push_sequence.setEnabled(
            not self._saving and destination and bool(options) and online)
        self.image_processor.Cropper.current.setEnabled(self._has_frame and not self._saving)
        self.viewer.ax_cont.auto_c_limits.setEnabled(self._has_frame)
        self.viewer.buffer_cont.setEnabled(self._has_frame and not self._saving)
        self.image_processor.FixedBGRmvr.readBG.setEnabled(self._has_frame and not self._saving)

    def _run_save(self, sequence):
        if self._saving:
            return
        self._saving = True
        was_live = self.continuous_button.continuous.isChecked()
        self.continuous_button.stop()
        self.controls_scroll.setEnabled(False)
        self.refresh_controls()
        self.save_controls.set_status('Saving...', True)
        try:
            if sequence:
                self.save_sequence()
            else:
                self.save_single()
        except Exception as error:
            logger.exception('Saving failed')
            self._show_save_error('Save failed: {}'.format(error))
        finally:
            self._saving = False
            self.controls_scroll.setEnabled(True)
            if was_live and self.camera_widget.online:
                self.continuous_button.continuous.setChecked(True)
            self.refresh_controls()

    def closeEvent(self, event):
        if self._saving:
            event.ignore()
            return
        self.continuous_button.stop()
        self.state_timer.stop()
        super().closeEvent(event)
        
    def save_single(self):
        def none_to_empty(d):
            #convert "None"s in a dict (and sub-dicts) to empty arrays to be compatible with savemat
            for key1 in d.keys():
                if d[key1] is None:
                    d[key1] = []
                elif isinstance(d[key1],dict):
                    d[key1] = none_to_empty(d[key1])
            return d       
        opts = self._selected_save_options()
        if not opts:
            self._show_save_error('Select at least one file format.')
            return
        save_path, name = self._save_destination()
        if save_path is None:
            return
        os.makedirs(save_path, exist_ok=True)
        # save processed image
        if '.mat' in opts:
            configs = dict(image_processing = self.image_processor.get_config(), camera = self.camera_widget.get_config())
            d = dict(x=self.image_processor.x,
                    y=self.image_processor.y,
                    image=self.image_processor.image,
                    datetime = self.image_processor.datetime.strftime('%Y%m%d_%H%M%S_%f'),
                    configs = configs)  
            pth = os.path.join(save_path,name+'_proc')
            scipy.io.savemat(pth,none_to_empty(d),do_compression=True) 
        if '.p' in opts:
            configs = dict(image_processing = self.image_processor.get_config(), camera = self.camera_widget.get_config())
            d = dict(x=self.image_processor.x,
                    y=self.image_processor.y,
                    image=self.image_processor.image,
                    datetime = self.image_processor.datetime,
                    configs = configs)  
            pth = os.path.join(save_path,name+'_proc.p')
            with open(pth,'wb') as file:
                pickle.dump(d,file)
        # save raw image
        if '.mat (raw)' in opts:
            configs = dict(camera = self.camera_widget.get_config())
            d = dict(x=self.camera_widget.x,
                    y=self.camera_widget.y,
                    image=self.camera_widget.image,
                    datetime = self.camera_widget.datetime.strftime('%Y%m%d_%H%M%S_%f'),
                    configs = configs)
            pth = os.path.join(save_path,name+'_raw')
            scipy.io.savemat(pth,none_to_empty(d),do_compression=True)
        if '.p (raw)' in opts:
            configs = dict(camera = self.camera_widget.get_config())
            d = dict(x=self.camera_widget.x,
                    y=self.camera_widget.y,
                    image=self.camera_widget.image,
                    datetime = self.camera_widget.datetime,
                    configs = configs)
            pth = os.path.join(save_path,name+'_raw.p')
            with open(pth,'wb') as file:
                pickle.dump(d,file)
        if 'screenshot' in opts:
            self.grab().save(os.path.join(save_path, name + '.png'), 'png')
        self.save_controls.set_status('Saved', success=True)
            
    def save_sequence(self):
        def none_to_empty(d):
            #convert "None"s in a dict (and sub-dicts) to empty arrays to be compatible with savemat
            for key1 in d.keys():
                if d[key1] is None:
                    d[key1] = []
                elif isinstance(d[key1],dict):
                    d[key1] = none_to_empty(d[key1])
            return d       
        opts = self._selected_save_options()
        if not opts:
            self._show_save_error('Select at least one file format.')
            return
        save_path, name = self._save_destination()
        if save_path is None:
            return
        os.makedirs(save_path, exist_ok=True)
        num = self.save_controls.spin_sequence.value()
        if not self.camera_widget.acquire_image():
            self._show_save_error('Could not acquire the first frame.')
            return
        self.save_controls.sequence_counter.setText("<font color='Red'>"+('{0}/{1}'.format(1,num))+ "</font>")
        if 'screenshot' in opts:
            self.grab().save(os.path.join(save_path, name + 'frame1.png'), 'png')
        tmp_raw = self.camera_widget.image
        tmp_proc = self.image_processor.image
        if '.mat (raw)' in opts or '.p (raw)' in opts:
            raw = np.zeros(np.append(list(tmp_raw.shape),num))
            raw[..., 0] = tmp_raw
        if '.mat' in opts or '.p' in opts:
            proc = np.zeros(np.append(list(tmp_proc.shape),num))
            proc[..., 0] = tmp_proc
        dt = [self.camera_widget.datetime]
        for i in range(num-1):
            if not self.camera_widget.acquire_image():
                self._show_save_error('Acquisition stopped at frame {}.'.format(i + 2))
                return
            self.save_controls.sequence_counter.setText("<font color='Red'>"+('{0}/{1}'.format(i+2,num))+ "</font>")
            if '.mat (raw)' in opts or '.p (raw)' in opts:
                raw[..., i + 1] = self.camera_widget.image
            if '.mat' in opts or '.p' in opts:
                proc[..., i + 1] = self.image_processor.image
            dt.append(self.camera_widget.datetime)
            if 'screenshot' in opts:
                self.grab().save(os.path.join(save_path, name + 'frame' + str(i + 2) + '.png'), 'png')
            QtWidgets.QApplication.processEvents()
        self.save_controls.sequence_counter.setText("<font color='Green'>Done</font>")
        # save processed image
        if '.mat' in opts:
            configs = dict(image_processing = self.image_processor.get_config(), camera = self.camera_widget.get_config())
            d = dict(x=self.image_processor.x,
                    y=self.image_processor.y,
                    image=proc,
                    datetime = [d.strftime('%Y%m%d_%H%M%S_%f') for d in dt],
                    configs = configs)  
            pth = os.path.join(save_path,name+'_proc_'+str(num)+'frames')
            scipy.io.savemat(pth,none_to_empty(d),do_compression=True) 
        if '.p' in opts:
            configs = dict(image_processing = self.image_processor.get_config(), camera = self.camera_widget.get_config())
            d = dict(x=self.image_processor.x,
                    y=self.image_processor.y,
                    image=proc,
                    datetime = dt,
                    configs = configs)  
            pth = os.path.join(save_path,name+'_proc_'+str(num)+'frames.p')
            with open(pth,'wb') as file:
                pickle.dump(d,file)
        # save raw image
        if '.mat (raw)' in opts:
            configs = dict(camera = self.camera_widget.get_config())
            d = dict(x=self.camera_widget.x,
                    y=self.camera_widget.y,
                    image=raw,
                    datetime = [d.strftime('%Y%m%d_%H%M%S_%f') for d in dt],
                    configs = configs)
            pth = os.path.join(save_path,name+'_raw_'+str(num)+'frames')
            scipy.io.savemat(pth,none_to_empty(d),do_compression=True)
        if '.p (raw)' in opts:
            configs = dict(camera = self.camera_widget.get_config())
            d = dict(x=self.camera_widget.x,
                    y=self.camera_widget.y,
                    image=raw,
                    datetime = dt,
                    configs = configs)
            pth = os.path.join(save_path,name+'_raw_'+str(num)+'frames.p')
            with open(pth,'wb') as file:
                pickle.dump(d,file)
        self.save_controls.set_status('Saved {} frames'.format(num), success=True)

    def _selected_save_options(self):
        return [
            option for option, checkbox in
            zip(self.save_options, self.save_controls.check_option)
            if checkbox.isChecked()
        ]

    def _save_destination(self):
        save_path = self.save_controls.folder_text.text().strip()
        name = self.save_controls.name_text.text().strip()
        if not save_path:
            self._show_save_error('Choose a destination folder.')
            return None, None
        if not name:
            self._show_save_error('Enter a file name.')
            return None, None
        return save_path, name

    def _show_save_error(self, message):
        self.save_controls.set_status(message, success=False)
        
    def clicked_crop_current(self):
        rect = self.viewer.mainplot.plots['image'].viewRect()
        self.image_processor.Cropper.set_lims(xmin=rect.left(),xmax=rect.right(),ymin=rect.top(),ymax=rect.bottom())
        
    def update(self):
        try:
            img = self.image_processor.image
            x = self.image_processor.x
            y = self.image_processor.y
            self.viewer.setImage(x, y, img)
            self.beam_profiler.set_input(x, y, img)
            self._has_frame = True
        except Exception as e:
            self.continuous_button.stop()
            raise e
        
    def _run_condition(self):
        return self.camera_widget.online
    
        
if __name__=="__main__":
    from hardware.webcam import WebcamWidget
    # from hardware.EHD_407UV import EHDCamWidget
    app = QtGui.QApplication(sys.argv)
    widget=CameraViewer(WebcamWidget())
    widget.setWindowTitle('CameraViewer')
    widget.show()
    widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    sys.exit(app.exec_())
