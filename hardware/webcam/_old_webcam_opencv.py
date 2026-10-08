import numpy as np
import logging
from datetime import datetime
from hardware import Camera
import cv2

image_formats = {'320x240':(320,240),'640x480':(640,480),'800x600':(800,600),'960x720':(960,720),'1280x960':(1280,960)}
# image_format_names = sorted(list(image_formats.keys()))
image_format_names = ['320x240','640x480','800x600','960x720','1280x960'] #have to create this manually to get the order actually right

class WebcamController(Camera):
    """
    Webcam controller without GUI, using opencv
    """
    def __init__(self):
        self.cams_found = None
        self.online = False
        self.x = None
        self.y = None
        self.image = None
        self.datetime = None
        
    def rescan(self):
        logging.debug('Getting # of available cameras')
        cams_found = np.int_([])
        for ii in range(0,10):
            cap_temp = cv2.VideoCapture(ii)
            if cap_temp.isOpened() is True:
                cams_found = np.append(cams_found,ii)
            cap_temp.release()
        logging.debug('Found %s cameras',cams_found.size)
        self.cams_found = cams_found
        
    def open(self,index=0):
        """ opens one of the webcams that have been found. 
        index is 0 based and refers to the index within the found cameras, not the device ID passed to cv2.VideoCapture!
        """
        if index > (self.cams_found.size-1):
            raise Exception('Camera index out of bounds')     
        self.close()
        logging.debug('Opening camera no %s which is device ID %s...',index, self.cams_found[index])
        self.cap_obj = cv2.VideoCapture(self.cams_found[index])
        if self.cap_obj.isOpened() is False:
            raise Exception('Could not open camera')
        self._setup_format()
        self.cam_deviceID = self.cams_found[index]
        self.cam_index = index
        self.online = True
        self.online_changed(True)
        self.running = True
        logging.debug('...done opening')
            
    def close(self):
        """ Closes currently opened camera """
        logging.debug('Closing camera')
        if hasattr(self,'cap_obj') is True and self.cap_obj.isOpened() is True:
            self.cap_obj.release()
            del self.cap_obj
        self.online = False
        self.online_changed(False)
        
    def _setup_format(self):
        """
        Setup x and y axes
        """
        logging.debug('Setting up axes: Reading image size')
        ret,tmp = self.cap_obj.read() #read one frame to get data into cap_obj
        w = self.cap_obj.get(cv2.CAP_PROP_FRAME_WIDTH)
        h = self.cap_obj.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.x = np.arange(w)
        self.y = np.arange(h)[:,None] #make column vector
        self.format_changed()
        
    def set(self,exposure_time = None,format = None):
        """
        Set exposure time, format and others(?)
        format can be any of the strings that are keys in the image_formats dict. All the usual resolutions are available,
        320x240 and upwards
        """
        if exposure_time is not None and exposure_time != self.exposure_time:
            logging.debug('Setting exposure time to %s',exposure_time)
            self.cap_obj.set(cv2.CAP_PROP_EXPOSURE,exposure_time)
        if format is not None:
            newformat = image_formats[format]
            logging.debug('Setting image size: Width %s, Height %s',newformat[0],newformat[1])
            self.cap_obj.set(cv2.CAP_PROP_FRAME_WIDTH,newformat[0])
            self.cap_obj.set(cv2.CAP_PROP_FRAME_HEIGHT,newformat[1])
        self._setup_format()
        
        
    def trigger(self):
        assert self.online
        ret,img = self.cap_obj.read()#need to read one image first to clear the buffer
        ret,img = self.cap_obj.read()
        self.datetime = datetime.now()
        img = img.transpose(1,0,2) #opencv returns x and y swapped, so swap them here
        img = np.fliplr(img)
        self.image = img
        assert ret
    
    def wait(self,timeout = 5000):
        logging.debug('Retrieving frame from webcam - no work to be done since webcam is buffered')
        return True
        
    def acquire_image(self,timeout=1000):
        if self.online is False:
            return False
        logging.debug('Reading frame...')
        ret,img = self.cap_obj.read()#need to read one image first to clear the buffer
        ret,img = self.cap_obj.read()
        self.datetime = datetime.now()
        if ret is False:
            return False
        img = img.transpose(1,0,2) #opencv returns x and y swapped, so swap them here
        img = np.fliplr(img)
        logging.debug('...done')
        self.image = img
        return True
    
    @property
    def exposure_time(self):
        if self.online is True:
            return self.cap_obj.get(cv2.CAP_PROP_EXPOSURE)
        else:
            return None
    
    @property
    def image_size(self):
        if self.online is True:
            return (self.cap_obj.get(cv2.CAP_PROP_FRAME_WIDTH),self.cap_obj.get(cv2.CAP_PROP_FRAME_HEIGHT))
        else:
            return None
            
if __name__=="__main__":
    o = WebcamController()
    o.rescan()
    o.open()
        
