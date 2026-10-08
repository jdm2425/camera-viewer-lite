import sys, os, logging
import yaml
from datetime import datetime
from time import sleep
import clr
from System import Decimal #.NET Decimal class
from hardware import AbsoluteStage
from hardware import MotorisedMirror

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

class KCubePiezo(AbsoluteStage):
    """Controller class for a Thorlabs KPZ101 piezo controller KCube
            In addition, .NET libraries are much easier to use in python, since the namespace can be imported and 
            all functions and their signatures are known e.g. for auto-completion
        In order to use this, simply install Kinesis from the Thorlabs website. 
        ***DO NOT CHANGE THE INSTALLATION PATH. THIS CLASS ASSUMES THAT KINESIS IS INSTALLED IN 'C:/Program Files/Thorlabs/Kinesis'***
        """
    ##Load Thorlabs Kinesis library
    kinesis_path = os.path.join("C:/","Program Files","Thorlabs","Kinesis")# standard installation location for 64-bit kinesis
    if not os.path.isdir(kinesis_path):
        raise IOError('Thorlabs Kinesis folder not found in {0}. Have you installed Kinesis?'.format(kinesis_path))
    sys.path.append(kinesis_path)
    pcli = clr.FindAssembly('Thorlabs.MotionControl.KCube.PiezoCLI')
    clr.AddReference(pcli)
    clr.AddReference('Thorlabs.MotionControl.GenericPiezoCLI')
    clr.AddReference('Thorlabs.MotionControl.DeviceManagerCLI')
    ##Import relevant namespaces - DeviceManagerCLI reference is added automatically as a dependence of DCServoCLI
    from Thorlabs.MotionControl.KCube.PiezoCLI import KCubePiezo
    from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI as device_mgr
    from Thorlabs.MotionControl.DeviceManagerCLI import MoveTimeoutException
    from Thorlabs.MotionControl.GenericPiezoCLI import Settings as piezo_settings
    def __init__(self):
        self.found_serials = None
        self.device = None
        
    def rescan(self):
        logger.debug("Scanning for devices")
        self.device_mgr.BuildDeviceList()
        num_devs = self.device_mgr.GetDeviceListSize()
        dev_list = self.device_mgr.GetDeviceList()
        self.found_serials = [dev for dev in dev_list]
        print(self.found_serials)
        logger.debug("Found {0} device(s)".format(num_devs))
        
    def open(self,serial=None,indx=0):
        if serial is not None and type(serial) is not str:
            raise ValueError('serial needs to be a string, got {0} instead.'.format(type(serial).__name__))
        if not self.found_serials:
            logger.warning("Tried to open but no devices found. Have you rescan()ed before opening?")
            return
        if serial is None:
            serial = self.found_serials[indx]
            logger.debug('No serial no. supplied, using index {0} from found serials'.format(indx))
        logger.debug('Opening device with serial {0}'.format(serial))
        if serial not in self.found_serials:
            logger.warning('Tried to open serial no. {0}, but no device with this serial was found'.format(serial))
            return
        self.device = self.KCubePiezo.CreateKCubePiezo(serial)
        self.device.Connect(serial)
        if not self.device.IsConnected:
            logger.warning('Connecting failed')
            return
        if not self.device.IsSettingsInitialized():
            self.device.WaitForSettingsInitialized(5000)
        self.motor_config = self.device.GetPiezoConfiguration(self.serial) #have to call this once to initialize motor settings
        self.device.StartPolling(100) #starts position and status update at 100 ms intervals
        #if not self.device.IsEnabled:
        self.device.EnableDevice()
        #self.device.SetLimitsSoftwareApproachPolicy(self.motor_settings.LimitSettings.LimitsSoftwareApproachPolicies.AllowPartialMoves)
        self.device.SetMaxOutputVoltage(Decimal(150))

    def close(self):
        self.device.DisableDevice()
        self.device.Disconnect()
        self.device = None

    def identify(self):
        if not self.online:
            logger.debug("Tried to identify but not online")
            return
        self.device.IdentifyDevice()
    
    def is_moving(self):
        if not self.online:
            return False
        return not (self.device.IsSetOutputVoltageActive or self.device.IsSetPositionActive or self.device.Status.IsZeroed)
        #flipped bool because these return true once they have been completed
    def trigger_home(self):
        if not self.online:
            return
        self.device.SetOutputVoltage(Decimal(75))
    
    def home(self,timeout=60000):
        self.trigger_home()
        sleep(0.1)
        return self.wait(timeout=timeout)
        
    def trigger(self,pos):
        if not self.online:
            return
        if self.is_moving(): 
            return
        cur_pos = self.device.GetOutputVoltage()
        nu_pos = Decimal.Add(cur_pos,Decimal(pos))
        self.device.SetOutputVoltage(nu_pos)
        
        
    def wait(self,timeout=30000):
        """Wait for stage to finish moving or homing"""
        if not self.online:
            return False
        if not self.is_moving():
            sleep(0.1) #wait for a tiny bit for the motor to start moving so wait() does not immediately return
        timed_out = False
        start = datetime.now()
        while self.is_moving() and not timed_out:
            timed_out = (datetime.now()-start).total_seconds() > timeout/1000
            sleep(0.01)
        return not timed_out
        
    def move(self,pos,timeout=30000):
        self.trigger(pos)
        return self.wait(timeout=timeout)
            
    def set_jog_stepsize(self,step):
        if not self.online:
            return
        self.device.SetJogSteps(self.piezo_settings.ControlSettings.JogStepStruct(step,step,step)) #needs all 3 arguments to be step for some reason
        
    def jog(self,dir):
        if not self.online:
            return
        if self.is_moving():
            return
        if dir<0:
            self.device.Jog(self.piezo_settings.ControlSettings.PiezoJogDirection.Decrease)
        else:
            self.device.Jog(self.piezo_settings.ControlSettings.PiezoJogDirection.Increase)
            
    def stop(self):
        if not self.online:
            return
        if self.is_moving():
            self.device.Stop(0)
        
    @property
    def position(self):
        if not self.online:
            return None
        return Decimal.ToDouble(self.device.Status.Position) #under the assmption that voltage is the same as position
        
    @property
    def online(self):
        if self.device is None:
            return False
        return self.device.IsConnected and self.device.IsSettingsInitialized()
        
    @property
    def serial(self):
        if not self.online:
            return None
        return self.device.SerialNo
        
    @property
    def unit(self):
        if not self.online:
            return None
        return 'V'
    
    @property
    def voltage(self):
        if not self.online:
            return None
        return Decimal.ToDouble(self.device.GetOutputVoltage())    
    @property
    def jog_stepsize(self):
        if not self.online:
            return None
        return Decimal.ToDouble(self.device.GetJogSteps().VoltageStepSize)
        
    @property
    def position_limits(self):
        if not self.online:
            return (None,None)
        return ( Decimal.ToDouble(self.device.AdvancedMotorLimits.LengthMinimum),
            Decimal.ToDouble(self.device.AdvancedMotorLimits.LengthMaximum))

class KCubeMirror(MotorisedMirror):
    """Motorised mirror using two piezomotors controlled by a two thorlabs kcubes"""
    def __init__(self,controller_h=None,controller_v=None,axes=dict(h=0,v=1,invert_h=False,invert_v=False)):
        self.controller_h = (KCubePiezo() if controller_h is None else controller_h)
        self.controller_v = (KCubePiezo() if controller_v is None else controller_v)
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
        if dir == 'h':
            return self.controller_h.move(dist,self.axes[dir])
        elif dir == 'v':
            return self.controller_v.move(dist,self.axes[dir])
        
    def wait_both(self,timeout=5000):
        return self.controller.wait_multi(list(self.axes.values()),timeout=timeout)
    
    @property
    def online(self):
        return self.controller.online
        
    @property
    def position(self):
        return {dir: self.controller.position[self.axes[dir]] for dir in ['h','v']}
        
if __name__ == "__main__":
    o = KCubePiezo()
    o.rescan()
    o.open()
