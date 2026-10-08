import pypylon
pypylon.pylon_version.version


import time
import matplotlib.pyplot as plt

available_cameras = pypylon.factory.find_devices()
available_cameras

cam = pypylon.factory.create_device(available_cameras[0])
cam.opened

cam.open()

cam.properties.keys() # lists all available properties

cam.properties['GainRaw'] = 192

wmax = cam.properties['WidthMax']
hmax = cam.properties['HeightMax']

cam.properties['Width'] = wmax
cam.properties['Height'] = hmax
cam.properties['OffsetX']
cam.properties['OffsetY']

cam.properties['BinningHorizontal'] = 1
cam.properties['BinningVertical']   = 1

cam.properties['Width']
cam.properties['Height']

cam.properties['ExposureTimeAbs'] = 5000

#cam.properties['DeviceLinkThroughputLimitMode'] = 'Off'

#cam.properties['PixelFormat'] = 'Mono8'
cam.properties['PixelFormat'] = 'Mono16'


cam.properties['PixelDynamicRangeMin']
cam.properties['PixelDynamicRangeMax']



# image = cam.grab_images(1)
# plt.imshow(image)
# plt.show()
def getoneimage():
    images=list(cam.grab_images(1))
    assert len(images)==1
    return images[0]

def getoneimage2():
    image = cam.grab_image()
    return image

#for image in cam.grab_images(1):
    
## 
#images=list(cam.grab_images(1))
#assert len(images)==1
#image=images[0]

image = getoneimage2()
plt.imshow(image)
plt.show()
##

## test speed

start = time.time()
Nimages = 50
for n in range(Nimages):
    image = getoneimage2()

stop  = time.time()
etime = stop-start
FPS = 1/(etime/Nimages)
print("speed is %.1f FPS" % FPS)

##
