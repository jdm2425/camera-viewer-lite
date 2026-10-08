import sys, os, logging
from time import sleep
from datetime import datetime
from hardware.PI.gcs2 import *
from hardware import AbsoluteStage
logger = logging.getLogger(__name__)
# A class for PI stages which can be controlled using PI's general command set 2
# (GCS2)
class PI_Stage(AbsoluteStage):
    
    def __init__(self):
        self.gcs = GeneralCommandSet2()
        self._jog_step_size = None
    
    # port is an integer: 1 for 'COM 1' etc    
    def open(self, port = None):
        if port is not None and type(port) is not int:
            raise TypeError('port should be an integer')
        if port is not None and type(port) is int:            
            self.gcs.connectRS232(port)
    
    # Axis is an int         
    def trigger(self, pos, axis=None):
        if not self.online:
            return
        if pos < self.min_travel or pos > self.max_travel:
            logger.debug('Target position out of range')
            return
        if axis == None:
            return
        else:
            self.gcs.setTargetPosition(str(axis), pos)
        
    def wait(self, axis = None, timeout = 30000):
        if not self.online:
            return False
        # If no axis specified check all axes
        if axis == None:
            axis = ""
        if not self.is_moving(str(axis)):
            sleep(0.1)
        timed_out = False
        start = datetime.now()
        while self.is_moving(str(axis))==True and timed_out == False:
            timed_out = (datetime.now()-start).total_seconds() > timeout/1000
            sleep(0.01)
        return not timed_out
        
    def is_moving(self, axis = None):
        if not self.online:
            return 
        if axis == None:
            return self.gcs.isMoving("")
        else:
            return self.gcs.isMoving(str(axis))
            
    def move(self, pos, axis = None, timeout=30000):
        self.trigger(pos, axis)
        return self.wait(axis, timeout = 3000)
        
    # Performs a referencing move (similar to home) where the stage moves to its 
    # negative limit switch.
    def reference(self, axis, timeout = 6000):
        if self.online == False:
            return 
        # check whether this axis is referenced 
        if self.gcs.isReferenced(str(axis)):
            logger.debug('Axis ' + str(axis) + ' is already referenced')
        else:
            self.gcs.findNegativeLimit(axis)
            return wait(axis)
            
    def close(self):
        if not self.online:
            return 
        self.gcs.closeConnection()
    ## TO DO: currently properties are only for 1 axis
    @property 
    def position(self):
        if not self.online:
            return None
        return self.gcs.getPosition('1') # "" queries all axes - returns list
        
    @property 
    def online(self):
        if not self.gcs:
            return False
        return self.gcs._isConnected() 
        
    @property 
    def unit(self):
        if not self.online:
            return None
        return self.gcs.getUnit("1")
        
    @property 
    def is_referenced(self):
        if not self.online:
            return None
        return self.gcs.isReferenced("1")
        
    @property 
    def is_homed(self):
        if not self.online:
            return None
        return self.gcs.getHome("1") == self.gcs.getPosition("1")
        
    @property
    def jog_step_size(self):
        if not self.online:
            return None
        return self._jog_step_size
        
    @jog_step_size.setter
    def jog_step_size(self, value):
        self._jog_step_size = value
        
    @property
    def max_travel(self):
        if not self.online:
            return None
        return self.gcs.getMaxTravel("1")
        
    @property
    def min_travel(self):
        if not self.online:
            return None
        return self.gcs.getMinTravel("1") 
        
    
    
