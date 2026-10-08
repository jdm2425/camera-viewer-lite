import numpy as np
from datetime import datetime
from hardware import Camera
import pypylon

class BaslerException(Exception):
    pass

class BaslerCamera(Camera):
    def __init__(self):
        self.cam=None
        
    def get_available_cameras(self):
        return pypylon.factory.find_devices()
        
    def open(self,camera_num=0):
        device=self.get_available_cameras()[camera_num]
        self.cam = pypylon.factory.create_device(device)
        self.cam.open()
        self.cam.properties['DeviceLinkThroughputLimitMode'] = 'Off'
        #self.cam.properties['BinningHorizontal'] = 4
        #self.cam.properties['BinningVertical']   = 4
        if not self.cam.opened:
            raise BaslerException("Couldn't open camera number %d with name %s.",camera_num,device.friendly_name)
        self.setup_image()
            
    def close(self):
        self.cam.close()
        self.cam=None
        
    def setup_image(self):
        roi=self.roi
        bx=self.binning_x
        by=self.binning_y
        self.x=np.arange(roi[0],roi[0]+roi[2])*bx
        self.y=np.arange(roi[1],roi[1]+roi[3])[:,None]*by
        self.image=np.zeros((len(self.y),len(self.x)),dtype=int)
        self.datetime=None
        print("setting up image finished")
        
    def trigger(self):
        pass
        
    def wait(self,timeout=5000):
        images=list(self.cam.grab_images(1))
        assert len(images)==1
        self.image=images[0]
        self.image=self.image.T
        self.datetime=datetime.now()
        return True

    def set_binning_x(self,binx):
        if binx != self.binning_x:
            self.cam.properties['BinningHorizontal'] = binx
            self.setup_image()
    
    def set_binning_y(self,biny):        
        if biny != self.binning_y:
            self.cam.properties['BinningVertical']   = biny
            self.setup_image()
    def set_pixelformat(self,pixelformat):
        self.cam.properties['PixelFormat'] = pixelformat
        
    def set_roi(self,roi):
        if roi != self.roi:
            self.cam.properties['Height']  = roi[3]
            self.cam.properties['Width']   = roi[2]
            self.cam.properties['OffsetX'] = roi[0]
            self.cam.properties['OffsetY'] = roi[1]
            self.setup_image()

    def set_exposure(self, exposure_us):
        self.cam.properties['ExposureTime'] = exposure_us
    
    def set_gain(self, gain):
        self.cam.properties['Gain'] = gain    
    
    @property
    def online(self):
        return self.cam is not None and self.cam.opened

    @property
    def exposure_us(self):
        return self.cam.properties['ExposureTime']
        
    @property
    def gain(self):
        return self.cam.properties['Gain']

    @property
    def roi(self):
        return tuple(self.cam.properties[key] for key in ('OffsetX','OffsetY','Width','Height'))
    
    @property
    def pixelformat(self): 
        return self.cam.properties['PixelFormat']
       
    # @property
    # def binning(self):
    #     #return self.cam.properties['BinningHorizontal'] 
    #     return tuple(self.cam.properties[key] for key in ('BinningHorizontal','BinningVertical'))

    @property
    def binning_x(self):
       return self.cam.properties['BinningHorizontal'] 
       
    @property
    def binning_y(self):
       return self.cam.properties['BinningVertical'] 
        
if __name__=="__main__":
    b=BaslerCamera()
    b.open(0)
    
    
    import matplotlib.pyplot as plt
    ##
    b.acquire_image()
    plt.imshow(b.image)
    plt.show()
    ##
    
        
    
# cam.properties['ExposureTime']
# 
# cam.properties['ExposureTime'] = 1000


    
