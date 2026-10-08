import sys
from PyQt5 import QtGui, QtCore

# Import the existing camera viewer app
from lab_apps.CameraViewer import CameraViewer

# Choose your camera type
# Webcam:
from hardware.webcam import WebcamWidget

# If you instead use a Basler camera, replace the line above with:
# from hardware.basler_pypylon import BaslerPylonCameraWidget as WebcamWidget
# or for GigE:
# from hardware.basler_pypylon_gige import BaslerPylonGigECameraWidget as WebcamWidget


def main():
    # Reuse existing QApplication if one exists
    if QtGui.QApplication.instance() is None:
        app = QtGui.QApplication(sys.argv)
    else:
        app = QtGui.QApplication.instance()

    # Optional font settings (matches the stabiliser apps)
    font = QtGui.QFont("Tahoma", 8)
    app.setFont(font)

    # Create camera viewer only
    if '--smoke-test' in sys.argv:
        from hardware.qt import CameraWidget
        camera_widget = CameraWidget()
        camera_widget.online = False
        camera_widget.opened = False
    else:
        camera_widget = WebcamWidget()
    viewer = CameraViewer(camera_widget)

    viewer.setWindowTitle("Camera Viewer")
    viewer.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    viewer.show()
    if '--smoke-test' in sys.argv:
        QtCore.QTimer.singleShot(500, app.quit)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
