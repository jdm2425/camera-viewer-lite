# import subprocess,os,atexit
# from py4j.java_gateway import JavaGateway
# py4j_path='C:\ProgramData\Miniconda3\envs\lab\share\py4j\py4j0.10.4.jar'
# omnidriver_path=r'C:\Program Files\Ocean Optics\OmniDriverSPAM\OOI_HOME\OmniDriver.jar'
# path=r'C:\Users\reddragon.PH-DRAUSTIN1\Documents\hg\lab\packages\hardware\ocean_optics'
# subprocess.run((r'C:\Program Files\Java\jdk1.8.0_121\bin\javac.exe','-cp',py4j_path+os.pathsep+omnidriver_path,os.path.join(path,'ADC1000USBGateway.java')))
# gateway_process=subprocess.Popen(('java','-cp',path+os.pathsep+py4j_path+os.pathsep+omnidriver_path,'ADC1000USBGateway'))
# gateway=JavaGateway()
# random=gateway.jvm.java.util.Random()
# print(random.nextInt(10))
# app=gateway.entry_point
# driver=app.getDriver()
# driver.openSpectrometer(0)
# intensity=driver.getSpectrum().getSpectrum()
#gateway.entry_point.driver.openSpectrometer(0)

#gateway_process.kill()

#atexit.register(gateway_process.kill)
from hardware.ocean_optics.adc1000usb import adc1000usb
from hardware.ocean_optics.adc1000usb import ADC1000USB,ADC1000USBWidget

s=ADC1000USBWidget()
s.show()
s.acquire_spectrum()
#adc1000usb.gateway_process.kill()
