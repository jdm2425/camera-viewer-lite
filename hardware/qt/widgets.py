from PyQt5 import QtGui, QtWidgets,QtCore, QtWidgets
from .widget_interfaces import MotorisedMirrorWidget

class CameraROIChooser(QtGui.QGroupBox):
    """Generic rectangular region-of-interest chooser QWidget for a camera."""
    changed=QtCore.pyqtSignal(tuple)
    
    def __init__(self,title='ROI',parent=None):
        QtGui.QGroupBox.__init__(self,title,parent)
        self.setContentsMargins(0,0,0,0)
        hbox=QtGui.QHBoxLayout(self)
        def make_spin_box(label,func):
            hbox.addWidget(QtGui.QLabel(label))
            sb=QtGui.QSpinBox()
            sb.setRange(0,1e6)
            sb.valueChanged.connect(func)
            hbox.addWidget(sb)
            return sb
        self.x=make_spin_box('x:',self._respond_x)
        self.y=make_spin_box('y:',self._respond_y)
        self.width=make_spin_box('w:',self._respond_width)
        self.height=make_spin_box('h:',self._respond_height)
        butt=QtGui.QPushButton('full')
        butt.clicked.connect(lambda _:self.set_full())
        hbox.addWidget(butt)
        
        self.set_max_width(100)
        self.set_max_height(100)
            
        self.suppress=False
        
    def set_max_width(self,v):
        self.max_width=v
        self.x.setRange(0,v)
        self.width.setRange(0,v-self.x.value())
         
    def set_max_height(self,v):
        self.max_height=v
        self.y.setRange(0,v)
        self.height.setRange(0,v-self.y.value())
        
    def set_full(self,emit=True):
        self.set_roi((0,0,self.max_width,self.max_height),emit)
            
    @property
    def roi(self):
        """Current ROI based on spin boxes: (x,y,width,height)"""
        return self.x.value(),self.y.value(),self.width.value(),self.height.value()
        
    def set_horizontal_increment(self,v):
        self.x.setSingleStep(v)
        self.width.setSingleStep(v)
        
    def set_vertical_increment(self,v):
        self.y.setSingleStep(v)
        self.height.setSingleStep(v)
        
    def set_roi(self,roi,emit=True):
        if roi==self.roi:
            return
        try:
            self.suppress=True
            self.x.setValue(roi[0])
            self.y.setValue(roi[1])
            self.width.setValue(roi[2])
            self.height.setValue(roi[3])
        finally:
            self.suppress=False
        if emit:
            self._emit()
        
    def _respond_x(self,v):
        self.width.setRange(0,self.max_width-v)
        self._emit()
        
    def _respond_y(self,v):
        self.height.setRange(0,self.max_height-v)
        self._emit()
    
    def _respond_width(self,v):
        self.x.setRange(0,self.max_width-v)
        self._emit()
        
    def _respond_height(self,v):
        self.y.setRange(0,self.max_height-v)
        self._emit()
    
    def _emit(self):
        if not self.suppress:
            self.changed.emit(self.roi)
            
class MotorisedMirrorButtonsWidget(MotorisedMirrorWidget):
    def __init__(self,mirror,parent=None):
        super().__init__(parent=parent)
        self.mirror = mirror
        vbox = QtGui.QVBoxLayout()
        grid = QtGui.QGridLayout()
        vbox.addLayout(grid)
        grid.setSpacing(1)
        spacerH = 40
        spacerV = 40
        row = 0
        col = 0
        grid.addItem(QtWidgets.QSpacerItem(spacerH,spacerV),row,col)
        col +=1
        self.push_up = QtGui.QPushButton('U')
        grid.addWidget(self.push_up,row,col)
        col+=1
        grid.addItem(QtWidgets.QSpacerItem(spacerH,spacerV),row,col)
        col = 0
        row +=1
        self.push_left = QtGui.QPushButton('L')
        grid.addWidget(self.push_left,row,col)
        col+=1
        self.spin_stepsize = QtGui.QSpinBox()
        grid.addWidget(self.spin_stepsize,row,col)
        col+=1
        self.push_right = QtGui.QPushButton('R')
        grid.addWidget(self.push_right,row,col)
        col = 0
        row +=1
        grid.addItem(QtWidgets.QSpacerItem(spacerH,spacerV),row,col)
        col+=1
        self.push_down = QtGui.QPushButton('D')
        grid.addWidget(self.push_down,row,col)
        col+=1
        grid.addItem(QtWidgets.QSpacerItem(spacerH,spacerV),row,col)
        [button.setMaximumSize(spacerH,spacerV) for button in [self.push_down,self.push_left,self.push_right,self.push_up,self.spin_stepsize] ]
        [button.setMinimumSize(spacerH,spacerV) for button in [self.push_down,self.push_left,self.push_right,self.push_up,self.spin_stepsize] ]
        self.setLayout(vbox)
        
        self.spin_stepsize.setMinimum(0)
        self.spin_stepsize.setMaximum(10000)
        self.spin_stepsize.setValue(5)
        
        self.push_down.clicked.connect(lambda checked:self._move('down'))
        self.push_up.clicked.connect(lambda checked:self._move('up'))
        self.push_left.clicked.connect(lambda checked:self._move('left'))
        self.push_right.clicked.connect(lambda checked:self._move('right'))
        
        self.setMaximumSize(180,180)
        
    def _move(self,dir):
        steps = self.spin_stepsize.value()
        if dir == 'down':
            self.move('v',-1*steps)
        if dir == 'up':
            self.move('v',steps)
        if dir == 'left':
            self.move('h',-1*steps)
        if dir == 'right':
            self.move('h',steps)
        
    def set_keyboard_shortcuts(self,style='numpad'):
        if style == 'WASD':
            self.push_up.setShortcut(QtGui.QKeySequence('W'))
            self.push_down.setShortcut(QtGui.QKeySequence('S'))
            self.push_right.setShortcut(QtGui.QKeySequence('D'))
            self.push_left.setShortcut(QtGui.QKeySequence('A'))
        elif style == 'numpad':
            self.push_up.setShortcut(QtGui.QKeySequence('8'))
            self.push_down.setShortcut(QtGui.QKeySequence('5'))
            self.push_right.setShortcut(QtGui.QKeySequence('6'))
            self.push_left.setShortcut(QtGui.QKeySequence('4'))
            
    ##wrap methods from mirror object
    def move(self,dir,dist):
        ret = self.mirror.move(dir,dist)
        self.moved.emit(dir,dist,ret)
        return ret
        
    def trigger(self,dir,dist):
        self.mirror.trigger(dir,dist)
        
    def wait_both(self):
        return self.mirror.wait_both()
        
    @property
    def online(self):
        return self.mirror.online
        
    @property
    def position(self):
        return {dir: self.mirror.controller.position[self.axes[dir]] for dir in ['h','v']}
    
    @property
    def axes(self):
        return self.mirror.axes
        
