import os,sys
import numpy as np
import hardware.Juno_power_meter.Powermeterreader as power
import hardware.Juno_power_meter.spot_optimisation as spot_opt
import hardware.Juno_power_meter.bessel_optimisation as bessel_opt
import cv2
from datetime import datetime

def testfn():
    print("THIS IS A TEST FUNCTION")
    a=100.1
    return a


def LoadPowerMeter():
    reader=power.powermeterreader()
    reader.singleopener()
    return reader

def QuickReader(reader=None,Integration_Time=0.1):
    output=reader.AveragePower(IntTime=Integration_Time)
    if output == 'no data available':
        return 0.0
    return output


def LoadCamera(webcam_index=0, releasecamera=False,Bes=True):
    
    if Bes: beam = bessel_opt.bessel(webcam_index=webcam_index,
                    releasecamera = releasecamera,roots=20,orders=20)
    else:   beam = spot_opt.spot(webcam_index,releasecamera)
    return beam

def QuickImage(beam):
    beam.instance.read()
    image = beam.instance.image
    image = np.array( (image-np.min(image))/(np.max(image)-np.min(image))*255, dtype=np.uint8 )
    cv2.imwrite(os.path.join(os.getcwd(),"Spots",datetime.now().strftime("d_%d_%m_%Y_t_%H_%M_%S.png")),image)

def GetMetric(beam,BesMet=0,SSM=1):
    metrics = beam.get_metric()
    metric = np.prod(metrics)
    return metric
    
# TODO add spectral metric -- acquisition of spectrum needs to be implemented on that file.
