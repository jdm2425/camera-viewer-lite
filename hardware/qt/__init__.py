# Mapping of short class name (e.g. pymbax) to (module, widget class name)
widget_classes={'pymbax':('hardware.pymbax.qt','PymbaCameraWidget'),
    'basler':('hardware.basler_pypylon','BaslerWidget')}

from .widget_interfaces import *
from .widgets import *
