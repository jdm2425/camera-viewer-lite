"""Abstract interfaces to Qt widgets that control hardware."""
from PyQt5 import QtGui, QtWidgets, QtCore
from .. import Camera, RelativeStage, Spectrometer, MotorisedMirror, AbsoluteStage


class CameraWidget(Camera, QtGui.QWidget):
    """Interface for a Qt widget that allows the user to control a camera."""
    # When self.online changes state. Implies a format_changed as well.
    online_changed = QtCore.pyqtSignal(bool)
    format_changed = QtCore.pyqtSignal()
    # image_acquired has to be emitted whenever the camera controlled by the widget acquires an image
    image_acquired = QtCore.pyqtSignal()

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)

    def get_settings(self):
        """Should return a dictionary of the camera settings."""
        pass


class SpectrometerWidget(Spectrometer, QtGui.QWidget):
    """Interface for Qt widget that allows control of a spectrometer"""
    # When self.online changes state. Implies wavelengths_changed event
    online_changed = QtCore.pyqtSignal(bool)
    # Emitted when wavelengths has changed so applications can allocate arrays
    # and set things up
    wavelengths_changed = QtCore.pyqtSignal()
    # spectrum_acquired has to be emitted whenever the spectrometer controlled by the widget acquires a new spectrum
    spectrum_acquired = QtCore.pyqtSignal()

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)


class RelativeStageWidget(RelativeStage, QtGui.QWidget):
    # Should be emitted whenever the stage has moved. Argument informs whether move was successful or timed out
    moved = QtCore.pyqtSignal(bool)
    # When self.online changes state.
    online_changed = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)

    def get_settings(self):
        """Should return a dictionary of the settings."""
        pass


class AbsoluteStageWidget(AbsoluteStage, QtGui.QWidget):
    # Should be emitted whenever the stage has moved (i.e. finished moving). Argument informs whether move was successful or timed out
    moved = QtCore.pyqtSignal(bool)
    # When self.online changes state.
    online_changed = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)

    def get_settings(self):
        """Should return a dictionary of the settings."""
        pass


class MotorisedMirrorWidget(MotorisedMirror, QtGui.QWidget):
    moved = QtCore.pyqtSignal(str, int, bool)

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)
