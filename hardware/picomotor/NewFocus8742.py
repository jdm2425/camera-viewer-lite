import os, logging
from datetime import datetime
from time import sleep
import clr
import System #System namespace from .NET (for data types)
from hardware import RelativeStage
from hardware import MotorisedMirror
import System
from System.Reflection import Assembly


THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure native dependencies can be found
os.environ["PATH"] = THIS_DIR + os.pathsep + os.environ.get("PATH", "")

dll_path = os.path.join(THIS_DIR, "CmdLib.dll")


clr.AddReference(dll_path)


class NewFocus8742(RelativeStage):
    """ Controller class for a New Focus 8742 4-channel USB picomotor controller
    NOTE: The 8742 controller counts its axes 1-based, but this class translates that to 0-based to be consistent with python convention"""
    logging.debug("Loading Library")
    
    
    from NewFocus import Picomotor
    logging.debug("Library loaded")
    def __init__(self):
        super().__init__()
        self.device_keys = None
        self.lib = None
        self.online = False
    
    def rescan(self):
        """Scan for connected 8742 controllers"""
        if self.lib is not None:
            self.lib.Shutdown()
        self.lib = self.Picomotor.CmdLib8742()
        self.device_keys = self.lib.GetDeviceKeys()
        
    def open(self,serial_no=None,indx=0):
        """Open controller. Input can be serial number or indexing the list of found devices
        If neither is given, opens the first one it found"""
        if self.device_keys is None:
            self.online = False
            self.serial_no = None
            return
        if serial_no is None:
            serial_no = self.device_keys[indx]
        self.serial_no = serial_no
        logging.debug('Opening controller serial no. '+serial_no)
        ret = self.lib.Open(serial_no)
        if ret:
            self.online = True
            logging.debug('Opening successful')
        else:
            self.online = False
            logging.debug('Opening failed')
    
    def close(self):
        self.lib.Close(self.serial_no)
        self.online = False
            
    def trigger(self,dist,axis):
        """Start movement along axis axis by distance dist"""
        if not self.online:
            return
        #TODO: Find a way around the wait time in the next line
        self.wait_multi() #Need to wait for all axes to stop moving, or the hardware will simply ignore the command to move 
        logging.debug('Triggered motion by distance {0} on axis {1}'.format(dist,axis))
        if dist == 0:
            logging.debug('Distance is 0, no action')
            return
        self.lib.RelativeMove(self.serial_no,axis+1,dist)
        
    def wait(self,axis,timeout=5000):
        """Wait for axis to finish moving"""
        if not self.online:
            return False
        timed_out = False
        logging.debug('Waiting for axis {0} to finish moving'.format(axis))
        start = datetime.now()
        while self.is_moving(axis) and not timed_out:
            timed_out = (datetime.now()-start).total_seconds() > timeout/1000
            sleep(0.01)
        logging.debug('Movement '+('timed out.' if timed_out else 'finished.'))
        return not timed_out
        
    def wait_multi(self,axes=[0,1,2,3],timeout=5000):
        """Wait for several axes to stop moving"""
        if not self.online:
            return False
        timed_out = False
        logging.debug('Waiting for axes {0} to finish moving'.format(axes))
        start = datetime.now()
        moving = any([self.is_moving(axis) for axis in axes])
        while moving and not timed_out:
            timed_out = (datetime.now()-start).total_seconds() > timeout/1000
            moving =  any([self.is_moving(axis) for axis in axes])
            sleep(0.01)
        logging.debug('Movement '+('timed out.' if timed_out else 'finished.'))
        return not timed_out
        
    def is_moving(self,axis):
        """Check if motor on axis is currently moving"""
        if not self.online:
            return False

        done = System.Boolean(False)
        ret = self.lib.GetMotionDone(System.String(self.serial_no), System.Int32(axis + 1), done)
        return not bool(done)
        #return not self.lib.GetMotionDone(self.serial_no,axis+1,[])[1] #GetMotionDone returns tuple of booleans: (Was command successful?, Is motion done?)
        
    def set_zero(self,axis):
        """Set position on axis to zero"""
        self.lib.SetZeroPosition(o.serial_no,axis+1)
        
    def set_velocity(self,axis,vel):
        """Set velocity for axis in steps per second"""
        self.lib.SetVelocity(self.serial_no,axis+1,vel)
        
    def get_velocity(self,axis):
        """get velocity in axis in steps per second"""
        if not self.online:
            return None
        #need to explicitly use System data types to select the correct overloaded method
        (ret,vel) = self.lib.GetVelocity(System.String(self.serial_no),System.Int32(axis+1),System.Int32(1))
        return (vel if ret else None)
        
    @property
    def position(self):
        out = [None,None,None,None]
        for axis in range(4):
            #need to explicitly use System data types to select the correct overloaded method
            (ret,pos)= self.lib.GetPosition(System.String(self.serial_no),System.Int32(axis+1),System.Int32(1))
            if ret:
                out[axis] = pos
        return out
        
class NewFocus8742Mirror(MotorisedMirror):
    """Motorised mirror using two picomotors controlled by a 4-channel 8742 controller"""
    def __init__(self,controller=None,axes=dict(h=0,v=1,invert_h=False,invert_v=False)):
        self.controller = (NewFocus8742() if controller is None else controller)
        self.axes = axes
        
    def set_axes(self,axis_h,axis_v,invert_h=False,invert_v=False):
        self.axes = dict(h=axis_h,v=axis_v,invert_h=invert_h,invert_v=invert_v)
        
    def trigger(self,dir,dist):
        if (dir == 'h' and self.axes['invert_h']) or (dir == 'v' and self.axes['invert_v']):
            dist = -1*dist
        self.controller.trigger(dist,self.axes[dir])
        
    def move(self,dir,dist):
        if (dir == 'h' and self.axes['invert_h']) or (dir == 'v' and self.axes['invert_v']):
            dist = -1*dist
        #for axis in self.axes[dir]:
        #    self.controller.move(dist, axis)
        return self.controller.move(dist,self.axes[dir])
        
    def wait_both(self,timeout=5000):
        return self.controller.wait_multi(list(self.axes.values()),timeout=timeout)
    
    @property
    def online(self):
        return self.controller.online
        
    @property
    def position(self):
        return {dir: self.controller.position[self.axes[dir]] for dir in ['h','v']}
        
if __name__ == "__main__":
    o = NewFocus8742()
    o.rescan()
    o.open()
