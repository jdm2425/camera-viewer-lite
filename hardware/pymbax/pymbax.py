import atexit,logging
import numpy as np
from datetime import datetime
import pymba
from hardware import Camera

logger=logging.getLogger(__name__)

vimba=pymba.Vimba()
vimba.startup()
atexit.register(vimba.shutdown)

pixel_format_dtypes={'Mono8':np.uint8,'Mono16':np.uint16,'Mono12Packed':np.uint16}
pixel_formats=list(pixel_format_dtypes.keys())

def get_available_camera():
    for id in vimba.getCameraIds():
        camera=vimba.getCamera(id)
        try:
            camera.openCamera()
        except:
            pass
        else:
            camera.closeCamera()
            return camera.cameraIdString
    return None	  
      
class PymbaCamera(Camera):
    """
    Camera resources are controlled with context manager semantics.
    Camera ID is fixed for object lifetime.
    Only triggered mode available - no continuous.
    """
    def __init__(self,id):
        """Opens connection to camera. Should call close when done."""
        logger.debug('getting camera ID %s',id)
        self.camera=vimba.getCamera(id)
        
    def open(self,**kwargs):
        """kwargs passed to set"""
        logger.debug('opening camera %s',self.id)
        self.camera.openCamera()
        self.set(**kwargs,cleanup=False)
        self._setup_format()
        
    def close(self):
        logger.debug('closing camera %s',self.id)
        try:
            self._cleanup_format()
        finally:
            self.camera.closeCamera()
    
    def __enter__(self):
        self.open()
        return self
        
    def __exit__(self,*exc):
        self.close()
        return False
        
    def _setup_format(self):
        """Setup everything dependent on resolution, binning, pixel format etc.
        Assumes that self.camera isn't capturing."""
        self.frame=self.camera.getFrame()
        logger.info('setting up format, %s, %dx%d, %s',self.iidc_mode_description,
            self.frame.width,self.frame.height,self.camera.PixelFormat)
        self.frame.announceFrame()
        frame_data = self.frame.getBufferByteData()
        self.image=np.ndarray(buffer=frame_data,dtype=pixel_format_dtypes[self.camera.PixelFormat],shape=(self.frame.height,self.frame.width))
        self.camera.startCapture()
        self.x=(self.offset_x+np.arange(self.frame.width))*self.delta_x
        self.y=(self.offset_y+np.arange(self.frame.height)[:,None])*self.delta_y
        self.online=True
        self.online_changed(True)
        
    def _cleanup_format(self):
        logger.info('cleaning up camera')
        self.camera.flushCaptureQueue()
        self.camera.endCapture()
        self.camera.revokeAllFrames()
        self.image=None
        self.x=None
        self.y=None
        self.online=False
        self.online_changed(False)
        
    def trigger(self):
        """Starts acquisition of a frame.
        
        Returns immediately. To ensure that the frame is ready, call wait.
        """
        logger.debug('queueFrameCapture')
        self.frame.queueFrameCapture()
        self.camera.runFeatureCommand("AcquisitionStart")
        self.camera.runFeatureCommand("AcquisitionStop")
        self.datetime=datetime.now()
    
    def wait(self,timeout=1000):
        """Wait for the current frame to complete. 
        
        Args:
            timeout (number): timeout in ms, rounded to int
        Returns:
            bool: True if the frame was complete, False if timeout occurred
        """
        logger.debug('waitFrameCapture ...')
        result=self.frame.waitFrameCapture(int(timeout))
        if result==0:
            return True
        elif result==-12:
            return False
        else:
            raise ValueError('waitFrameCapture returned unknown error code',result)
        logger.debug('... done')
    
    @property
    def pixel_format(self):
        return self.camera.PixelFormat
    
    @property
    def exposure_time(self):
        """Exposure time in microseconds."""
        return self.camera.ExposureTime
        
    @property
    def id(self):
        return self.camera.cameraIdString
        
    @property
    def name(self):
        return self.camera.getInfo().cameraName.decode()
        
    @property
    def iidc_mode_number(self):
        return int(self.camera.IIDCMode[-1])
    
    @property
    def iidc_mode_description(self):
        return self.camera.IIDCModeDescription
        
    @property
    def delta_x(self):
        b=self.binning_horizontal
        d=self.decimation_horizontal
        assert b==1 or d==1
        return max(b,d)
        
    @property
    def delta_y(self):
        b=self.binning_vertical
        d=self.decimation_vertical
        assert b==1 or d==1
        return max(b,d)
            
    @property
    def binning_horizontal(self):
        return self.camera.BinningHorizontal
        
    @property
    def binning_vertical(self):
        return self.camera.BinningVertical
        
    @property
    def decimation_horizontal(self):
        return self.camera.DecimationHorizontal
        
    @property
    def decimation_vertical(self):
        return self.camera.DecimationVertical
        
    @property
    def max_width(self):
        return self.camera.WidthMax
        
    @property
    def max_height(self):
        return self.camera.HeightMax
        
    @property
    def offset_x(self):
        return self.camera.OffsetX
        
    @property
    def offset_y(self):
        return self.camera.OffsetY
        
    @property
    def roi(self):
        return self.camera.OffsetX,self.camera.OffsetY,self.camera.Width,self.camera.Height
    
    def set(self,pixel_format=None,exposure_time=None,roi=None,iidc_mode_number=None,cleanup=True):
        # Don't set if value is the same
        if pixel_format==self.pixel_format:
            pixel_format=None
        if exposure_time==self.exposure_time:
            exposure_time=None        
        if iidc_mode_number==self.iidc_mode_number:
            iidc_mode_number=None
        if roi==self.roi:
            roi=None
        if exposure_time is not None:
            logger.debug('changing exposure time from %d to %d us',self.camera.ExposureTime,exposure_time)
            self.camera.ExposureTime=exposure_time        
        if all(value is None for value in (pixel_format,iidc_mode_number,roi)):
            return
        # These settings nead a new format
        if cleanup:
            self._cleanup_format()
        try:
            if pixel_format is not None:
                logger.debug('changing pixel format from %s to %s',self.camera.PixelFormat,pixel_format)
                self.camera.PixelFormat=pixel_format
            if iidc_mode_number is not None:
                IIDCMode='Mode'+str(iidc_mode_number)
                logger.debug('setting IIDCMode to %s',IIDCMode)
                self.camera.IIDCMode=IIDCMode
                if roi is None:
                    # Set to full range
                    roi=(-1,-1,-1,-1)
            if roi is not None:
                roi=list(roi)
                if roi[0]==-1:
                    roi[0]=0
                if roi[1]==-1:                
                    roi[1]=0
                if roi[2]==-1:
                    roi[2]=self.camera.WidthMax-roi[0]
                if roi[3]==-1:
                    roi[3]=self.camera.HeightMax-roi[1]                
                logger.debug('setting roi to %s',roi)
                # Set offsets to zero before setting widths to avoid error if frame
                # (temporarily) exceeds max size
                self.camera.OffsetX=0
                self.camera.OffsetY=0
                self.camera.Width=roi[2]
                self.camera.Height=roi[3]
                self.camera.OffsetX=roi[0]
                self.camera.OffsetY=roi[1]
        finally:
            if cleanup:
                self._setup_format()
            
    def online_changed(self,value):
        pass
    
    def format_changed(self):
        pass
    
    def check_validity(self):
        super().check_validity()
        assert self.x[0]==self.camera.OffsetX*self.delta_x
        assert self.y[0]==self.camera.OffsetY*self.delta_y
        
    # def _set(self,pixel_format=None,exposure_time=None):
    #     """Apply settings with cleanup and setup."""
    #     if pixel_format==self.camera.PixelFormat: is not None:
    #         =pixel_format
    #     if exposure_time is not None:
            
    
    # Experimented with an optimization to avoid doing cleanup and setup unnecessarily
    # but it caused problems.
        # # Ignore if setting to current value
        # if pixel_format==self.pixel_format:
        #     pixel_format=None
        # if exposure_time==self.exposure_time:
        #     exposure_time=None
        # # 
        # if any(x is not None for x in (pixel_format,exposure_time)):
        #     setup=True
        #     self._cleanup_format()
        # else:
        #     setup=False
        # if pixel_format is not None:
        #     self.camera.PixelFormat=pixel_format
        # if exposure_time is not None:
        #     #self.camera.endCapture()
        #     #self.camera.runFeatureCommand("AcquisitionStop")
        #     self.camera.ExposureTime=exposure_time
        #     #self.camera.startCapture()
        #     #self.camera.runFeatureCommand("AcquisitionStart")
        # if setup:
        #     self._setup_format()
            
