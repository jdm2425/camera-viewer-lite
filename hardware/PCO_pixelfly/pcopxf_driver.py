import numpy as np
from datetime import datetime
from hardware import Camera
import ctypes
import os
import time, queue
#import threading

class PCOpxfException(Exception):
    pass

class PCOpxfCamera(Camera):

    def __init__(self, dllpath='C:\\Program Files\\Digital Camera Toolbox\\Camware4'):
        #self.cam=None
        # Load dynamic link library
        #print("loading DLL: %s" % dllpath)
        self.DLLpath = dllpath + '\\SC2_Cam.dll'
        print("loading DLL: %s" % self.DLLpath)
        self.PixFlyDLL = ctypes.windll.LoadLibrary(self.DLLpath)
        # initialize board number, by default 0
        self.board = 0
        # initialize handles and structs
        self.hCam = ctypes.c_int()
        self.bin = 1
        self.v_max = 1040
        self.h_max = 1392
        self.wXResAct = ctypes.c_uint16()
        self.wYResAct = ctypes.c_uint16()
        self.dwWarn = ctypes.c_ulong
        self.dwErr = ctypes.c_ulong
        self.dwStatus = ctypes.c_ulong
        self.szCameraName = ctypes.c_char
        self.wSZCameraNameLen = ctypes.c_ushort
        # Set all buffer size parameters
        self.time_modes = {0: "ns", 1: "us", 2: "ms"}
        # self.set_params = {'ROI': [1, 1, self.h_max, self.v_max],
        #                    'binning': [1, 1],
        #                    'Exposure time': [0, '0'],
        #                    'Camera ROI dimensions': [0, 0]}
        self.armed = False
        self.buffer_numbers = []
        self.buffer_pointers, self.buffer_events = (
             [], [])
        self.out = 0
        # Queues that hold the data collected in the camera.
        self.q   = queue.Queue(maxsize=2)
        self.q_m = queue.Queue(maxsize=2)
        
    def open(self,camera_num=0):
        # opencamera is the instance of OpenCamera method in DLL
        opencamera = self.PixFlyDLL.PCO_OpenCamera
        # PCO_OpenCamera(HANDLE *hCam, int board_num), return int
        opencamera.argtypes = (ctypes.POINTER(ctypes.c_int), ctypes.c_int)
        opencamera.restype = ctypes.c_int
        ret_code = opencamera(self.hCam, self.board)
        #print(self.hCam.value, ret_code)
        if ret_code < 0:
            raise PCOpxfException("Couldn't open camera!")
            #return False
        elif ret_code == 0:
            self.cam = self.hCam.value
            print("Camera %i connected!" % self.cam)
        else:
            #return False
            raise PCOpxfException("Couldn't open camera!")
        self.setup_image()
            
    def close(self):
        #self.cam.close()
        #self.cam=None
        # closecamera is an instance of the CloseCamera function of the DLL
        # call function and expect 0 if success, <0 if error
        ret_code = self.PixFlyDLL.PCO_CloseCamera(self.hCam)
        if ret_code == 0:
            print("closed PCO camera!")
            self.cam=None
            #self.online=False
            #return True
        else:
            #return False
            raise PCOpxfException("Couldn't close camera!")

    def setup_image(self):
        roi=self.roi
        #bx=self.binning_x
        #by=self.binning_y
        bx,by = self.binning
        self.x=np.arange(roi[0],roi[0]+roi[2])*bx
        self.y=np.arange(roi[1],roi[1]+roi[3])[:,None]*by
        self.image=np.zeros((len(self.y),len(self.x)),dtype=int)
        self.datetime=None
        print("setting up image finished.")
        
    #def trigger(self):
    #    pass
        
    #def wait(self,timeout=5000):
    #    images=list(self.cam.grab_images(1))
    #    assert len(images)==1
    #    self.image=images[0]
    #    self.image=self.image.T
    #    self.datetime=datetime.now()
    #    return True

    def set_binning(self,bin_x,bin_y):
        allowed = [1,2,4]
        wBinHorz = ctypes.c_uint16(int(bin_x))
        wBinVert = ctypes.c_uint16(int(bin_y))
        if (bin_x in allowed) and (bin_y in allowed):
            self.PixFlyDLL.PCO_SetBinning(self.hCam, wBinHorz, wBinVert)
            self.PixFlyDLL.PCO_GetBinning(self.hCam, ctypes.byref(wBinHorz),
                                          ctypes.byref(wBinVert))
            #self.set_params['binning']=[wBinHorz.value, wBinVert.value]
        else:
            raise PCOpxfException("illegal binning value pair " + str(bin_x)
                              + "x" + str(bin_y))
        if p.armed == True:
            self.disarm_camera()
            self.preparerecording()
        return None
        
    def set_exposure(self, exp_time, base_exposure):
        """
        Sets delay and exposure time allowing to choose a base for each parameter
        0x0000 timebase=[ns]=[10^-9 seconds]
        0x0001 timebase=[us]=[10^-6 seconds]
        0x0002 timebase=[ms]=[10^-3 seconds]
        Note: Does not require armed camera to set exp time
        :param exp_time: Exposure time (integer < 1000)
        :param base_exposure: Base 10 order for exposure time in seconds-> ns/us/ms
        :param verbose: True if process should be printed
        :return: None
        """
        if not(base_exposure in [0, 1, 2]):
            raise PCOpxfException("illegal timing mode")
        dwDelay           = ctypes.c_uint32(0)
        wTimeBaseDelay    = ctypes.c_uint16(0)
        dwExposure        = ctypes.c_uint32(int(exp_time))
        wTimeBaseExposure = ctypes.c_uint16(int(base_exposure))
        self.PixFlyDLL.PCO_SetDelayExposureTime(self.hCam,dwDelay, dwExposure,wTimeBaseDelay, wTimeBaseExposure)
        if self.armed == True:
            self.disarm_camera()
            self.preparerecording()
        

    def preparerecording(self):
        # Arm camera
        self.arm_camera()
        # Set recording status to 1
        self.start_recording()
        # Allocate buffers, default=2 buffers
        self.allocate_buffer(1)
        self._prepare_to_record_to_memory()
        print("ready for recording!")
        return None
        
    def arm_camera(self):
        """
        Arms camera and allocates buffers for image recording
        :param num_buffers:
        :param verbose:
        :return:
        """
        if self.armed:
            raise UserWarning("Camera already armed.")

        # Arm camera
        self.PixFlyDLL.PCO_ArmCamera(self.hCam)
        # Get the actual image resolution-needed for buffers
        self.wXResAct, self.wYResAct, wXResMax, wYResMax = (
            ctypes.c_uint16(), ctypes.c_uint16(), ctypes.c_uint16(),
            ctypes.c_uint16())
        self.PixFlyDLL.PCO_GetSizes(self.hCam, ctypes.byref(self.wXResAct),
                                    ctypes.byref(self.wYResAct), ctypes.byref(wXResMax),
                                    ctypes.byref(wYResMax))
        #self.set_params['Camera ROI dimensions'] = [self.wXResAct.value,
        #                                          self.wYResAct.value]
        #self.x
        #self.y
        self.setup_image()
        self.armed = True
        print("Camera armed!")
        return None

    def disarm_camera(self):
        """
        Disarm camera, free allocated buffers and set
        recording to 0
        :return:
        """
        # set recording state to 0
        wRecState = ctypes.c_uint16(0)
        self.PixFlyDLL.PCO_SetRecordingState(self.hCam, wRecState)
        # free all allocated buffers
        self.PixFlyDLL.PCO_RemoveBuffer(self.hCam)
        for buf in self.buffer_numbers:
            self.PixFlyDLL.PCO_FreeBuffer(self.hCam, buf)

        self.buffer_numbers, self.buffer_pointers, self.buffer_events = (
            [], [], [])
        self.armed = False
        print("Camera disarmed!")
        return None

        
    def allocate_buffer(self, num_buffers=10):
        """
        Allocate buffers for image grabbing
        :param num_buffers:
        :return:
        """
        dwSize = ctypes.c_uint32(self.wXResAct.value*self.wYResAct.value*2)  # 2 bytes per pixel
        # set buffer variable to []
        self.buffer_numbers, self.buffer_pointers, self.buffer_events = ([], [], [])
        # now set buffer variables to correct value and pass them to the API
        for i in range(num_buffers):
            self.buffer_numbers.append(ctypes.c_int16(-1))
            self.buffer_pointers.append(ctypes.c_void_p(0))
            self.buffer_events.append(ctypes.c_void_p(0))
            self.PixFlyDLL.PCO_AllocateBuffer(self.hCam, ctypes.byref(self.buffer_numbers[i]),
                                              dwSize, ctypes.byref(self.buffer_pointers[i]),
                                              ctypes.byref(self.buffer_events[i]))

        # Tell camera link what actual resolution to expect
        self.PixFlyDLL.PCO_CamLinkSetImageParameters(
            self.hCam, self.wXResAct, self.wYResAct)

        return None
        
    def start_recording(self):
        """
        Start recording
        :return: message from recording status
        """
        message = self.PixFlyDLL.PCO_SetRecordingState(self.hCam, ctypes.c_int16(1))
        return message

    def _prepare_to_record_to_memory(self):
        """
        Prepares memory for recording
        :return:
        """
        dw1stImage, dwLastImage = ctypes.c_uint32(0), ctypes.c_uint32(0)
        wBitsPerPixel = ctypes.c_uint16(16)
        dwStatusDll, dwStatusDrv = ctypes.c_uint32(), ctypes.c_uint32()
        bytes_per_pixel = ctypes.c_uint32(2)
        pixels_per_image = ctypes.c_uint32(self.wXResAct.value * self.wYResAct.value)
        added_buffers = []
        for which_buf in range(len(self.buffer_numbers)):
            self.PixFlyDLL.PCO_AddBufferEx(
                self.hCam, dw1stImage, dwLastImage,
                self.buffer_numbers[which_buf], self.wXResAct,
                self.wYResAct, wBitsPerPixel)
            added_buffers.append(which_buf)

        # prepare Python data types for receiving data
        # http://stackoverflow.com/questions/7543675/how-to-convert-pointer-to-c-array-to-python-array
        ArrayType = ctypes.c_uint16*pixels_per_image.value
        self._prepared_to_record = (dw1stImage, dwLastImage,
                                    wBitsPerPixel,
                                    dwStatusDll, dwStatusDrv,
                                    bytes_per_pixel, pixels_per_image,
                                    added_buffers, ArrayType)
        return None


   
        
    def record_to_memory_2(self):
        """
        Main recording loop. This function is used for the liew view of frames and starts a loop where the
        newly aquired frames are put in a queue, as well as the max count of the frame.
        """
        if not self.armed:
            raise UserWarning('Cannot record to memory with disarmed camera')

        if not hasattr(self, '_prepared_to_record'):
            self._prepare_to_record_to_memory()
            
        (dw1stImage, dwLastImage, wBitsPerPixel, dwStatusDll,
        dwStatusDrv, bytes_per_pixel, pixels_per_image, added_buffers, ArrayType) = self._prepared_to_record                   
        poll_timeout=5e7
        message = 0
        verbose=False
        timeout_err = False
        self.live = True
        which_buf = 0
        while self.live:
            ts=time.clock()
            num_polls = 0
            polling = True
            while polling:
                num_polls += 1
                message = self.PixFlyDLL.PCO_GetBufferStatus(
                    self.hCam, self.buffer_numbers[added_buffers[0]],
                    ctypes.byref(dwStatusDll), ctypes.byref(dwStatusDrv))
                if dwStatusDll.value == 0xc0008000:
                    which_buf = added_buffers.pop(0)  # Buffer exits the queue
                    if verbose:
                        print("After", num_polls, "polls, buffer")
                        print(self.buffer_numbers[which_buf].value)
                        print("is ready.")
                    polling = False
                    break
                else:
                    time.sleep(0.00005)  # Wait 50 microseconds
                if num_polls > poll_timeout:
                    print("After %i polls, no buffer."%(poll_timeout))
                    timeout_err = True
                        
            if timeout_err:
                print('Time out error')
                self.live = False
                break
            try:
                if dwStatusDrv.value == 0x00000000:
                    pass
                elif dwStatusDrv.value == 0x80332028:
                    raise DMAError('DMA error during record_to_memory')
                else:
                    print("dwStatusDrv:", dwStatusDrv.value)
                    raise UserWarning("Buffer status error")

                if verbose:
                    print("Record to memory result:")
                    print(hex(dwStatusDll.value), hex(dwStatusDrv.value))
                    print(message)

                if self.q.full():
                    print('Frames queue is full.')
                    self.q.queue.clear()
                    
                buffer_ptr = ctypes.cast(self.buffer_pointers[which_buf], ctypes.POINTER(ArrayType))
                out = np.frombuffer(buffer_ptr.contents, dtype=np.uint16).reshape((self.wYResAct.value, self.wXResAct.value))
                out = out/4  # make integer division to convert 16 bit to 14 bit
                
                if self.q_m.full():
                    self.q_m.queue.clear()
                    
                self.q_m.put(np.ndarray.max(out))
                self.q.put(out)
                    
            finally:
                self.PixFlyDLL.PCO_AddBufferEx(  # Put the buffer back in the queue
                    self.hCam, dw1stImage, dwLastImage,
                    self.buffer_numbers[which_buf], self.wXResAct, self.wYResAct,
                    wBitsPerPixel)
                added_buffers.append(which_buf)
                #print('Acquisition time:', time.clock()-ts)

        if timeout_err:
            self.disarm_camera()


 
    def trigger(self):
        self.allocate_buffer(1)
        self._prepare_to_record_to_memory()
        #time.sleep(0.000050)  # Wait 50 microseconds
        time.sleep(0.1)
        return None
        
    def wait(self,timeout=5000):
        #images=list(self.cam.grab_images(1))
        #assert len(images)==1
        #self.image=images[0]
        #self.image=self.image.T
        #self.datetime=datetime.now()
        #return True
        (dw1stImage, dwLastImage, wBitsPerPixel, dwStatusDll,dwStatusDrv,
            bytes_per_pixel, pixels_per_image, added_buffers, ArrayType) = self._prepared_to_record
        #poll_timeout=5e7
        num_polls = 0
        polling = True
        while polling:
            num_polls += 1
            message = self.PixFlyDLL.PCO_GetBufferStatus(
                self.hCam, self.buffer_numbers[added_buffers[0]],
                ctypes.byref(dwStatusDll), ctypes.byref(dwStatusDrv))
            if dwStatusDll.value == 0xc0008000:
                which_buf = added_buffers.pop(0)  # Buffer exits the queue
                if True:
                    print("After", num_polls, "polls, buffer")
                    print(self.buffer_numbers[which_buf].value)
                    print("is ready.")
                polling = False
                break
            else:
                time.sleep(0.00005)  # Wait 50 microseconds
            if num_polls > timeout:
                print("After %i polls, no buffer."%(timeout))
                timeout_err = True
        #which_buf = 0
        buffer_ptr = ctypes.cast(self.buffer_pointers[which_buf], ctypes.POINTER(ArrayType))
        out = np.frombuffer(buffer_ptr.contents, dtype=np.uint16).reshape((self.wYResAct.value, self.wXResAct.value))
        out = out/4  # integer division to convert 16 bit to 14 bit
        self.image = out
        self.image=self.image.T
        self.datetime=datetime.now()
        which_buf = 0
        return True

    @property
    def online(self):
        return self.armed

    @property
    def exposure(self):
        #return self.cam.properties['ExposureTime']
        dwDelay = ctypes.c_uint32(0)
        dwExposure = ctypes.c_uint32(0)
        wTimeBaseDelay = ctypes.c_uint16(0)
        wTimeBaseExposure = ctypes.c_uint16(0)
        # get exposure time
        self.PixFlyDLL.PCO_GetDelayExposureTime(self.hCam, ctypes.byref(dwDelay),
            ctypes.byref(dwExposure),ctypes.byref(wTimeBaseDelay),ctypes.byref(wTimeBaseExposure))
        return [dwExposure.value, self.time_modes[wTimeBaseExposure.value]]

    @property
    def exposure_us(self):
        #return self.cam.properties['ExposureTime']
        dwDelay = ctypes.c_uint32(0)
        dwExposure = ctypes.c_uint32(0)
        wTimeBaseDelay = ctypes.c_uint16(0)
        wTimeBaseExposure = ctypes.c_uint16(0)
        # get exposure time
        self.PixFlyDLL.PCO_GetDelayExposureTime(self.hCam, ctypes.byref(dwDelay),
            ctypes.byref(dwExposure),ctypes.byref(wTimeBaseDelay),ctypes.byref(wTimeBaseExposure))
        exp_us = dwExposure.value
        if  wTimeBaseExposure.value == 1:
            exp_us = dwExposure.value
        elif wTimeBaseExposure.value == 2:
            exp_us = dwExposure.value * 1e3
        return exp_us

        
    @property
    def roi(self):
        wRoiX0 = ctypes.c_uint16(int(0))
        wRoiY0 = ctypes.c_uint16(int(0))
        wRoiX1 = ctypes.c_uint16(int(0))
        wRoiY1 = ctypes.c_uint16(int(0))
        self.PixFlyDLL.PCO_GetROI(self.hCam,
            ctypes.byref(wRoiX0), ctypes.byref(wRoiY0),
            ctypes.byref(wRoiX1), ctypes.byref(wRoiY1))
        print("current ROI: x0=%i, y0=%i, width=%i, height=%i" % (wRoiX0.value,
            wRoiY0.value,  wRoiX1.value,  wRoiY1.value))
        return (wRoiX0.value, wRoiY0.value,  wRoiX1.value,  wRoiY1.value)
    
    @property
    def binning(self):
        wBinHorz = ctypes.c_uint16(int(0))
        wBinVert = ctypes.c_uint16(int(0))
        self.PixFlyDLL.PCO_GetBinning(self.hCam,ctypes.byref(wBinHorz),ctypes.byref(wBinVert))
        #print("binning: %i x %i" % (wBinHorz.value, wBinVert.value))
        return wBinHorz.value,wBinVert.value

    
        
if __name__=="__main__":
    import os
    pcodllpath = os.path.dirname(os.path.realpath("__file__"))
    p = PCOpxfCamera(dllpath=pcodllpath)
    p.open(0)
    p.preparerecording()
    
    if 0:
        ##
        # if p.armed == True:
        #     p.disarm_camera()
        #p.set_exposure(1500,1)
        p.set_exposure(500,1)
        
        #p.set_binning(1,1)
        #p.preparerecording()
        ##
        
        import matplotlib.pyplot as plt
        ##
        #p.take_snapshot()
        #p.allocate_buffer(1)
        #p._prepare_to_record_to_memory()
        ##
        p.trigger()
        p.wait()
        ##
        plt.imshow(p.image)
        plt.show()
        ##
    
        
    
# cam.properties['ExposureTime']
# 
# cam.properties['ExposureTime'] = 1000


    
