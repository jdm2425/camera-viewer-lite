import ctypes
import numpy as np
import os
from datetime import datetime
from hardware import Camera
import logging

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

class CameraInfo(ctypes.Structure):
    _fields_ = [("lSize",ctypes.c_long),
                ("lWidth",ctypes.c_long),
                ("lHeight",ctypes.c_long),
                ("lGlobalGainMin",ctypes.c_long),
                ("lGlobalGainMax",ctypes.c_long),
                ("lColorGainMin",ctypes.c_long),
                ("lColorGainMax",ctypes.c_long),
                ("lExposureMin",ctypes.c_long),
                ("lExposureMax",ctypes.c_long)]
                
class EHDCamController(Camera):
    """
    Controller class for an EHD 407UV camera, without GUI.
    All variables with _c at the beginning are c types.
    """
    def __init__(self):
        super().__init__()
        logger.debug("Loading DLL...")
        dll_path = os.path.join(os.path.dirname(__file__),'ArtCamSdk_407UV_WOM.dll')
        self.dll = ctypes.cdll.LoadLibrary(dll_path) #load dll
        logger.debug("Loading DLL done")
        self.dll.ArtCam_GetCameraInfo.restype=ctypes.c_bool 
        self.dll.ArtCam_SetColorMode.restype=ctypes.c_bool 
        self.dll.ArtCam_SnapShot.restype=ctypes.c_bool 
        self.dll.ArtCam_SetRealExposureTime.restype = ctypes.c_bool
        self.dll.ArtCam_SetGlobalGain.restype = ctypes.c_bool
        
        self.cam_handle = None
        self.cam_info = CameraInfo(350)#lSize=350
        self.online = False
        self.x = None
        self.y = None
        self.image = None
        self.datetime = None
        
        self._c_buffer_size = None
        self._c_buffer = None
        self._c_updown = None
    
    def open(self):
        """
        Opens camera. Since the SDK does not naturally support enumeration of connected devices, this doesn't either
        """
        if self.online:
            return
        logger.debug("Initializing (ArtCam_Initialize)")
        self.cam_handle = self.dll.ArtCam_Initialize()
        logger.debug("Getting camera info...")
        ret = self.dll.ArtCam_GetCameraInfo(self.cam_handle,ctypes.byref(self.cam_info))
        logger.debug("Camera info done. "+("Success." if ret else "Failed."))
        self.x = np.arange(self.cam_info.lWidth)
        self.y = np.arange(self.cam_info.lHeight)
        ret=self.dll.ArtCam_SetColorMode(self.cam_handle,16)
        logger.debug("Set color mode. "+("Success." if ret else "Failed."))
        self._c_buffer_size = ctypes.c_long(self.cam_info.lWidth*self.cam_info.lHeight*2) #length of the buffer in bytes
        self._c_buffer = (ctypes.c_uint8*(self.cam_info.lWidth*self.cam_info.lHeight*2))() #buffer
        self._c_updown = ctypes.c_bool(False) #read direction of the image
        logger.debug("Getting image to tell if camera is actually present...")
        ret = self.dll.ArtCam_SnapShot(self.cam_handle,self._c_buffer,self._c_buffer_size,self._c_updown)
        logger.debug("Camera found" if ret else "Camera not found")
        if ret:
            self.online = True
            # self.dll.ArtCam_Capture(self.cam_handle) #enable continuous snapshotting (for speed)
            
    def close(self):
        """
        Close camera.
        """
        if not self.online:
            return
        self.dll.ArtCam_Release(self.cam_handle)
        logger.debug("Closed camera.")
        
    def set_exposure_time(self,exposure_time_ms):
        """
        Set exposure time. Note that the camera only supports 1066 levels in exposure time, so the real value is always obtained
        from the property exposure_time_ms
        """
        if not self.online:
            logger.debug("Camera not online. Not setting exposure")
            return
        ret=self.dll.ArtCam_SetRealExposureTime(self.cam_handle,exposure_time_ms*1000)
        logger.debug("Setting exposure time "+("succeeded." if ret else "failed. ")+"Current exposure "+str(self.exposure_time_ms)+" ms.")
        
    def set_gain(self,gain):
        if not self.online:
            return
        ret = self.dll.ArtCam_SetGlobalGain(self.cam_handle,gain)
        return ret
         
    def trigger(self):
        if not self.online:
            logger.debug("Camera not opened. Cannot get image")
            return
        logger.debug("Getting snapshot")
        ret=self.dll.ArtCam_SnapShot(self.cam_handle,self._c_buffer,self._c_buffer_size,self._c_updown)
        logger.debug("Snapshot "+("successful" if ret else "failed"))
        self.datetime = datetime.now()
    
    def wait(self,timeout=1000):
        if self._c_buffer is None:
            logger.debug("Cannot get image: No image present")
            return False
        self.image = np.frombuffer(np.array(self._c_buffer),dtype=np.uint16).reshape(self.cam_info.lHeight,self.cam_info.lWidth).transpose().astype(float)
        return True
    
    @property
    def exposure_time_ms(self):
        if self.online:
            err = ctypes.c_bool(False)
            micros = self.dll.ArtCam_GetRealExposureTime(self.cam_handle,ctypes.byref(err))
            logger.debug("Getting exposure time "+("succeeded." if err else "failed. "))
            return (micros/1000 if err else None)
        else:
            logger.debug("Camera not online. Cannot get exposure")
            return None
            
    @property
    def gain(self):
        if self.online:
            err = ctypes.c_bool(False)
            g= self.dll.ArtCam_GetGlobalGain(self.cam_handle,ctypes.byref(err))
            return (g if err else None)
        else:
            return None
        

if __name__ == "__main__":
    o = EHDCamController()
    o.open()
