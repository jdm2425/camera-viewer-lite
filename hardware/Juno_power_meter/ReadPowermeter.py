import os,sys
import numpy as np
import hardware.Juno_power_meter.Powermeterreader as power

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
