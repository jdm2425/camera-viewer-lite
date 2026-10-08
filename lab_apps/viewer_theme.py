'''Dark appearance for the standalone camera viewer.'''
from PyQt5 import QtCore, QtGui, QtWidgets


class _NoWheelChanges(QtCore.QObject):
    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Wheel:
            event.ignore()
            return True
        return super().eventFilter(watched, event)


def apply_theme(viewer):
    palette = QtGui.QPalette()
    for role, colour in (
        (QtGui.QPalette.Window, '#191e27'),
        (QtGui.QPalette.WindowText, '#ffffff'),
        (QtGui.QPalette.Base, '#111720'),
        (QtGui.QPalette.AlternateBase, '#242c38'),
        (QtGui.QPalette.Text, '#ffffff'),
        (QtGui.QPalette.Button, '#2b3544'),
        (QtGui.QPalette.ButtonText, '#ffffff'),
        (QtGui.QPalette.Highlight, '#397dcc'),
        (QtGui.QPalette.HighlightedText, '#ffffff'),
        (QtGui.QPalette.ToolTipBase, '#242c38'),
        (QtGui.QPalette.ToolTipText, '#e1e7ef'),
    ):
        palette.setColor(role, QtGui.QColor(colour))
    for role in (QtGui.QPalette.Text, QtGui.QPalette.WindowText,
                 QtGui.QPalette.ButtonText):
        palette.setColor(QtGui.QPalette.Disabled, role, QtGui.QColor('#788494'))
    viewer.setPalette(palette)
    viewer.setAutoFillBackground(True)
    # Scroll viewports and their contents may retain their own light palette.
    for panel in (viewer.controls_scroll, viewer.controls_scroll.viewport(),
                  viewer.controls_scroll.widget()):
        panel.setPalette(palette)
        panel.setAutoFillBackground(True)
    viewer.setFont(QtGui.QFont('Segoe UI', 9))
    viewer.setStyleSheet('''
        QWidget { background-color: #191e27; color: #ffffff; }
        QWidget:disabled { color: #788494; }
        QLabel, QCheckBox, QRadioButton { background-color: transparent; }
        QGroupBox {
            border: 1px solid #354152; border-radius: 6px;
            margin-top: 12px; padding: 10px 4px 4px 4px;
            font-weight: 600;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 12px; }
        QPushButton {
            background: #2b3544; color: #ffffff;
            border: 1px solid #46546a; border-radius: 4px;
            padding: 4px 8px;
        }
        QPushButton:hover { background: #37465b; border-color: #6a96cc; }
        QPushButton:pressed { background: #214d7f; }
        QPushButton:disabled { color: #788494; border-color: #303947; }
        QPushButton:focus, QLineEdit:focus, QComboBox:focus {
            border: 1px solid #7db5ff;
        }
        QLineEdit, QTextEdit, QAbstractSpinBox, QComboBox {
            background: #111720; color: #ffffff;
            border: 1px solid #46546a; border-radius: 3px;
            padding: 3px;
        }
        QComboBox QAbstractItemView {
            background: #242c38; color: #ffffff;
            selection-background-color: #397dcc;
        }
        QToolTip { background: #242c38; color: #ffffff; }
        QScrollArea { border: none; }
    ''')
    # Mouse-wheel changes are too easy to make accidentally while scrolling
    # the controls panel. Keyboard entry and arrow buttons remain available.
    viewer._numeric_wheel_guard = _NoWheelChanges(viewer)
    for field in viewer.findChildren(QtWidgets.QAbstractSpinBox):
        field.installEventFilter(viewer._numeric_wheel_guard)

    # Respect translated/long labels and display scaling: no button may be
    # laid out smaller than the content requested by its style and font.
    for button in viewer.findChildren(QtWidgets.QPushButton):
        hint = button.sizeHint()
        button.setMinimumSize(hint.width(), hint.height())
    plot = viewer.viewer.mainplot
    plot.widget.setBackground('#111720')
    for item in plot.plots.values():
        for side in ('left', 'right', 'top', 'bottom'):
            axis = item.getAxis(side)
            if axis is not None:
                axis.setPen('#8391a4')
                axis.setTextPen('#ffffff')
    viewer.viewer.projection_colour = '#8fc4ff'
