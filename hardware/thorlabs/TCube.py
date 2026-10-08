import sys, os, logging
import yaml
from datetime import datetime
from time import sleep
import clr
from System import Decimal #.NET Decimal class
from hardware import AbsoluteStage

logger = logging.getLogger(__name__)
#logging.basicConfig(level=logging.DEBUG)
class TCubeServo(AbsoluteStage):
    """Controller class for a Thorlabs TDC001 DC servo controller TCube
        This interface uses the new Thorlabs Kinesis software, for two reasons:
            1.  Associations between stage and TCube (which serial no. has what type of actuator)
                do not need to be done by hand in most cases, but are automatically detected.
                Therefore, encoder units do not need to be manually converted to real world units
            2.  The Kinesis C# (.NET) library has a dedicated IsMoving and IsHoming funcionality that is much more
                reliable than waiting for the stage to finish using the old APT IsInMotion function.
                This is because for absolute moves, the stage may stop moving and then correct for
                backlash afterwards, so a wait function based on whether the stage is moving may incorrectly
                conclude that the move has finished.
            In addition, .NET libraries are much easier to use in python, since the namespace can be imported and 
            all functions and their signatures are known e.g. for auto-completion
        In order to use this, simply install Kinesis from the Thorlabs website. 
        ***DO NOT CHANGE THE INSTALLATION PATH. THIS CLASS ASSUMES THAT KINESIS IS INSTALLED IN 'C:/Program Files/Thorlabs/Kinesis'***
        """
    ##Load Thorlabs Kinesis library
    kinesis_path = 'C:/Program Files/Thorlabs/Kinesis'
    if not os.path.isdir(kinesis_path):
        raise IOError('Thorlabs Kinesis folder not found in {0}. Have you installed Kinesis?'.format(kinesis_path))
    sys.path.append(kinesis_path)
    clr.AddReference('Thorlabs.MotionControl.TCube.DCServoCLI')
    ##Import relevant namespaces - DeviceManagerCLI reference is added automatically as a dependence of DCServoCLI
    from Thorlabs.MotionControl.TCube.DCServoCLI import TCubeDCServo
    from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI as device_mgr
    from Thorlabs.MotionControl.DeviceManagerCLI import MoveTimeoutException
    from Thorlabs.MotionControl.GenericMotorCLI import Settings as motor_settings
    def __init__(self):
        self.found_serials = None
        self.device = None
        
    def rescan(self):
        logger.debug("Scanning for devices")
        self.device_mgr.BuildDeviceList()
        num_devs = self.device_mgr.GetDeviceListSize()
        dev_list = self.device_mgr.GetDeviceList()
        self.found_serials = [dev for dev in dev_list]
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
        self.device = self.TCubeDCServo.CreateTCubeDCServo(serial)
        self.device.Connect(serial)
        if not self.device.IsConnected:
            logger.warning('Connecting failed')
            return
        if not self.device.IsSettingsInitialized():
            self.device.WaitForSettingsInitialized(5000)
        self.motor_config = self.device.LoadMotorConfiguration(self.serial) #have to call this once to initialize motor settings
        self.device.StartPolling(100) #starts position and status update at 100 ms intervals
        if not self.device.IsEnabled:
            self.device.EnableDevice()
        self.device.SetLimitsSoftwareApproachPolicy(self.motor_settings.LimitSettings.LimitsSoftwareApproachPolicies.AllowPartialMoves)
            
    def close(self):
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
        return (self.device.Status.IsMoving or self.device.Status.IsHoming or self.device.Status.IsInMotion)
        
    def trigger_home(self):
        if not self.online:
            return
        self.device.Home(0)
    
    def home(self,timeout=60000):
        self.trigger_home()
        sleep(0.1)
        return self.wait(timeout=timeout)
        
    def trigger(self,pos):
        if not self.online:
            return
        if self.is_moving():
            return
        self.device.MoveTo(Decimal(float(pos)),0)
        
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
        self.device.SetJogStepSize(Decimal(step))
        
    def jog(self,dir):
        if not self.online:
            return
        if self.is_moving():
            return
        self.wait_handler = self.device.InitializeWaitHandler()
        if dir<0:
            self.device.MoveJog(2,self.wait_handler)
        else:
            self.device.MoveJog(1,self.wait_handler)
            
    def stop(self):
        if not self.online:
            return
        if self.is_moving():
            self.device.Stop(0)
        
    @property
    def position(self):
        if not self.online:
            return None
        return Decimal.ToDouble(self.device.Position)
        
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
        return self.device.MotorDeviceSettings.Physical.RealUnits
    
    @property
    def is_homed(self):
        if not self.online:
            return False
        return self.device.Status.IsHomed
        
    @property
    def jog_stepsize(self):
        if not self.online:
            return None
        return Decimal.ToDouble(self.device.GetJogStepSize())
        
    @property
    def position_limits(self):
        if not self.online:
            return (None,None)
        return ( Decimal.ToDouble(self.device.AdvancedMotorLimits.LengthMinimum),
            Decimal.ToDouble(self.device.AdvancedMotorLimits.LengthMaximum))
        
if __name__ == "__main__":
    o = TCubeServo()
    o.rescan()
    o.open()
