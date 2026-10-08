# testing of PCO.UV == pixelfly (UV behaves the same way as pixelfly) 
import ctypes
import os
import time, queue
import numpy as np
import threading

dllpath='C:\\Program Files\\Digital Camera Toolbox\\Camware4'
DLLpath = dllpath + '\\SC2_Cam.dll'
PixFlyDLL = ctypes.windll.LoadLibrary(DLLpath)

board = 0
# initialize handles and structs
hCam = ctypes.c_int()
bin = 1
v_max = 1040
h_max = 1392
wXResAct = ctypes.c_uint16()
wYResAct = ctypes.c_uint16()

dwWarn = ctypes.c_ulong
dwErr = ctypes.c_ulong
dwStatus = ctypes.c_ulong
szCameraName = ctypes.c_char
wSZCameraNameLen = ctypes.c_ushort

# Set all buffer size parameters

time_modes = {1: "us", 2: "ms"}
set_params = {'ROI': [1, 1, h_max, v_max],
                    'binning': [1, 1],
                    'Exposure time': [0, '0'],
                    'Camera ROI dimensions': [0, 0]}
armed = False
buffer_numbers = []
buffer_pointers, buffer_events = ([], [])

out = 0
# Queues that hold the data collected in the camera.
q = queue.Queue(maxsize=2)
q_m = queue.Queue(maxsize=2)




# opencamera is the instance of OpenCamera method in DLL
opencamera = PixFlyDLL.PCO_OpenCamera
# PCO_OpenCamera(HANDLE *hCam, int board_num), return int
opencamera.argtypes = (ctypes.POINTER(ctypes.c_int), ctypes.c_int)
opencamera.restype = ctypes.c_int
# return 0 if success, <0 if error
ret_code = opencamera(hCam, board)

print(hCam.value, ret_code)
# check if camera connected and get info
# if ret_code < 0:
#     print('Error connecting camera')
#     # try to identify error
#     return False
# elif ret_code == 0:
#     print('Camera Connected!')
#     return True
# else:
#     return False
            
            
            
            
## binning
h_bin = 1
v_bin = 1 
allowed = [1, 2, 4]
wBinHorz = ctypes.c_uint16(int(h_bin))
wBinVert = ctypes.c_uint16(int(v_bin))
if (h_bin in allowed) and (v_bin in allowed):
    PixFlyDLL.PCO_SetBinning(hCam, wBinHorz, wBinVert)
    PixFlyDLL.PCO_GetBinning(hCam, ctypes.byref(wBinHorz),
                                    ctypes.byref(wBinVert))
    set_params['binning']=[wBinHorz.value, wBinVert.value]
else:
    raise UserWarning("Not allowed binning value pair " + str(h_bin)
                        + "x" + str(v_bin))
                              
