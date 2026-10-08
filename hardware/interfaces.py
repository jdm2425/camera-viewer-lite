"""Abstract interfaces to various types of hardware."""
import mathx.uniformly_spaced_vector as usv

class Camera:
    """Interface for a Qt object/widget that allows the user to control a camera.
    Should have the following properties:
        online (bool): if True, then camera is ready for image acquisition commands
            and image, x, t and datetime hold valid data. Otherwise they should
            not be accessed.
        image: array of shape (ny,nx) or (3,ny,nx). For efficiency, the internal
            buffer may be reused (i.e. for subsequent images) so users should
            make a copy if necessary
        x: uniformly spaced array of shape (nx,)
        y: uniformly spaced array of shape (ny,1)
        datetime: datetime.datetime object for image
    If online changes, online_changed should be called. In child classes or container
    objects, these can be overridden to e.g. update a GUI. Likewise, if the shape
    or data type of image changes, then format_changed should be called. online_changed
    implies a possible change of format.
    """	
    def trigger(self):
        """Starts acquisition of a frame.
        
        Returns immediately. To ensure that the frame is ready, call wait.
        """
        raise NotImplementedError()
    
    def wait(self,timeout=5000):
        """Wait for the current frame to complete. 
        
        Args:
            timeout (int): timeout in ms
        Returns:
            bool: True if the frame was complete, False if timeout occurred
        """
        raise NotImplementedError()
        
    def acquire_image(self,timeout=5000):
        """Get a new image. The exact meaning of this depends on the camera.
        Default implementation is trigger and wait.
        Args:
            timeout (int): timeout in ms
        Returns:
            bool: True if the frame was complete, False if timeout occurred
        """
        self.trigger()
        return self.wait(timeout)
        
    @property
    def delta_x(self):
        """Get x pixel spacing.
        Only valid when online.
        """
        return self.x[1]-self.x[0]
    
    @property    
    def delta_y(self):
        """Get y pixel spacing.
        Only valid when online.
        """
        return self.y[1]-self.y[0]
        
    def check_validity(self):
        """Checks that some properties are consistent.
        Online valid when online.
        """
        assert usv.is_usv(self.x)
        assert usv.is_usv(self.y)
        image_shape=self.image.shape
        assert len(image_shape) in (2,3)
        nx=image_shape[-1]
        ny=image_shape[-2]
        assert self.x.shape==(nx,)
        assert self.y.shape==(ny,1)
        
    def online_changed(self,online):
        """Respond to change in online state."""
        pass
        
    def format_changed(self):
        """Respond to a change in format."""
        pass
    
class Spectrometer:
    """
    Interface that allows a user to control a spectrometer. 
    Should have the following properties:
        online (bool): if True, then spectrometer is ready for acquisition commands
            and image, x, t and datetime hold valid data. Otherwise they should
            not be accessed.
        wavelengths: array of shape (n,). 
        spectrum: array of shape (n,). For efficiency, the internal
            buffer may be reused (i.e. for subsequent shots) so users should
            make a copy if necessary
        datetime: datetime.datetime object for spectrum
    """	
    def trigger(self):
        """Starts acquisition of a frame.
        
        Returns immediately. To ensure that the frame is ready, call wait.
        """
        raise NotImplementedError()
    
    def wait(self,timeout=1000):
        """Wait for the current frame to complete. 
        
        Args:
            timeout (int): timeout in ms
        Returns:
            bool: True if the frame was complete, False if timeout occurred
        """
        raise NotImplementedError()
        
    def acquire_spectrum(self,timeout=1000):
        """Get a new spectrum. The exact meaning of this depends on the device.
        Default implementation is trigger and wait.
        
        Args:
            timeout (int): timeout in ms
        Returns:
            bool: True if the frame was complete, False if timeout occurred
        """
        self.trigger()
        return self.wait(timeout)
        
class RelativeStage:
    """
    Interface that allows control of a stage which only allows relative movements but no absolute positioning
    Should have the following properties:
        online (bool):  if True, the stage is ready for movement commands
        position:       (N,) element array where N is number of axes, or single number if N=1
                        This should hold the sum of all steps taken since starting the session
                        Movement one way is represented by positive numbers, movement the other way by negative numbers
                        Note that this does not necessarily correspond to the physical position because of backlash, slipping etc
                        This may be calculated inside the python sub-class or come from the stage hardware
    """
    def trigger(self,dist,axis=None):
        """Initiate move by distance dist along axis axis. 
        For controllers with only one axis, it should be possible to omit the axis argument
        Should return immediately, use self.wait() to make sure it has finished"""
        raise NotImplementedError()
        
    def wait(self,axis=None,timeout=5000):
        """Wait until controller has stopped moving along axis
        This will probably use self.is_moving()
        
        Args:
            axis (int):     Axis which should be waited for (in case multiple axes are moving at the same time)
            timeout (int):  timeout in ms
        Returns:
            bool:   True if move was successful, False if timeout occurred or motor was not online"""
        raise NotImplementedError()
    
    def is_moving(self,axis=None):
        """Check if controller is currently moving along axis axis"""
        raise NotImplementedError()
        
    def move(self,dist,axis=None,timeout=5000):
        """Move by a distance dist (pos or neg) on motor axis axis
        For controllers with only one axis, it should be possible to omit the axis argument
        
        Args:
            dist (float):   Distance by which the stage should move
            axis (int):     Index of axis that should be moved (for multi-axis controllers). 
                            Should be 0-based irrespective of the convetion used in the hardware
            timeout (int):  Timeout in ms
        Returns:
            bool:   True if move was successful, False if timeout occurred or motor was not online
        """
        self.trigger(dist,axis=axis)
        return self.wait(axis=axis,timeout=timeout)
        
class MotorisedMirror:
    """Convenience class to group two axes of a controller or two separate controllers into a mirror mount with axes labeld h(orizontal) and v(ertical)
    This handles none of the opening, closing, device selection or similar driver issues.
    The intent is that subclasses should be written for all types of motorised mounts (e.g. Agilis, picomotor mounts) 
    to make interfacing with stabilisers etc easier"""
    def move(self,dir,dist):
        """ Move and wait for finish
        
        Args:
            dir (str):      'v' for vertical or 'h' for horizontal
            dist (float):   distance by which the mirror should be moved in the specified direction
        Returns:
            bool:   The result of the underlying contoller's move() function, i.e. True if successful, False if error or timeout"""
        raise NotImplementedError()
        
    def trigger(self,dir,dist):
        """ Trigger move and return immediately
        
        Args:
            dir (str): 'v' for vertical or 'h' for horizontal
        Should return immediately"""
        raise NotImplementedError()
        
    def wait_both(self):
        """Wait for the mirror to stop moving in both directions
        Returns:
        bool:   The result of the underlying controller's wait(), i.e. True if successful, False if error or timeout"""
        raise NotImplementedError()
        
class AbsoluteStage:
    """
    Interface to control stage that allows absolute positioning. Should have the following properties:
        online:         Bool
                        If True, the stage is ready for input and can move
        position:       (N,) array where N is number of axes, or single number if N=1
                        Contains the current absolute position of the stage
        unit:          string
                        Describes the unit that position is measured in
    Almost all stages with absolute positioning can be homed. In that case, the following property should be present (in addition to a home() method):
        is_homed:          Bool
                            If True, the stage is currently homed and its position is thus comparable across datasets and sessions
    """
    def trigger(self,pos,axis=None):
        """Initiate move to position. 
        
        Args:
            pos (float):    Position to which the stage should move
            axis (int):     Axis in which to move to pos
        Should return immediately."""
        raise NotImplementedError()
        
    def wait(self,axis=None,timeout=30000):
        """Wait for stage to finish moving. 
        
        Args:
            axis (int):     axis which should be waited for
            timeout (int):  timeout in ms
        Returns:
            bool:   True if move was successful, False if timed out or controller was not online"""
        raise NotImplementedError()
        
    def is_moving(self,axis=None):
        """Check if stage is currently moving
        
        Args:
            axis (int): Axis along which we want to check for movement
        Returns:
            bool:   True if stage is currently moving, False if stopped"""
        raise NotImplementedError()
        
    def move(self,pos,axis=None,timeout=30000):
        """Trigger move and wait for move to finish. Standard implementation here, can be overriden of course
        
        Args:
            pos (float):    Position to which the stage should move
            axis (int):     Axis in which to move to pos
            timeout (int):  timeout in ms
        Returns:
            bool:   True if move was successful, False if timed out or controller was not online
        """
        self.trigger(pos,axis)
        return self.wait(axis=axis,timeout=timeout)
        
    def home(self,axis=None,timeout=60000):
        """Only applicable for stages that have a homing function.
        
        Args:
            axis: Axis which should be homed
            timeout:    Timeout in ms"""
        pass
