import time,logging
import numpy as np
import hardware
from hardware.pymbax import PymbaCamera,vimba
import pyqtgraph as pg

logging.getLogger(hardware.__name__).setLevel(level=logging.DEBUG)
logger=logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
camera_ids = vimba.getCameraIds()

def test_open_close():
    camera=PymbaCamera(camera_ids[0])
    camera.open()
    logger.info('setting exposure time once')
    camera.set(exposure_time=1000000)
    # shouldn't happen again
    logger.info('setting exposure time again')
    camera.set(exposure_time=1000000)
    logger.info('done')
    camera.trigger()
    assert not camera.wait(500)
    h,w=camera.image.shape
    assert camera.x.shape==(w,)
    assert camera.y.shape==(h,1)
    camera.close()

def test_exposure_time():
    exposure_times=[100,1000,10000,100000,1000000]
    with PymbaCamera(camera_ids[0]) as camera:
        images=[]
        for exp in exposure_times:
            camera.set(exposure_time=exp)
            print(camera.camera.ExposureTime)
            camera.trigger()
            print(camera.wait())
            images.append(np.array(camera.image))
    
    ##
    gl=pg.GraphicsLayoutWidget()
    for exp,image in zip(exposure_times,images):
        plt=gl.addPlot(title='%g us'%exp)
        imi=pg.ImageItem(image,levels=(0,np.iinfo(image.dtype).max))
        plt.addItem(imi)
        if gl.ci.currentCol==2:
            gl.nextRow()
    gl.show()
    return gl
    

def test_pixel_format():
    ##
    with PymbaCamera(camera_ids[0]) as camera:
        camera.set(exposure_time=100000)
        camera.set(pixel_format='Mono8')
        camera.trigger()
        camera.wait()
        image8=np.array(camera.image)
        camera.set(pixel_format='Mono16')
        camera.trigger()
        camera.wait()
        image16=np.array(camera.image)
    assert image8.dtype==np.uint8
    assert image16.dtype==np.uint16
    ##
    gl=pg.GraphicsLayoutWidget()
    plt=gl.addPlot(title='Mono8')
    imi=pg.ImageItem(image8,levels=(0,2**8))
    plt.addItem(imi)
    plt=gl.addPlot(title='Mono16')
    imi=pg.ImageItem(image16,levels=(0,2**16))
    plt.addItem(imi)
    gl.show()
    return gl
    
def test_thorough():
    with PymbaCamera(camera_ids[0]) as camera:
        for n in range(10):
            for exp_time,pixel_format in ((100,'Mono8'),(10000,'Mono16')):
                camera.set(exposure_time=exp_time)
                camera.set(pixel_format=pixel_format)
                camera.trigger()
                camera.wait()
                
def test_timing():
    ##
    """Check that trigger takes <100 ms and then waiting takes the exposure time.
    """
    for exp_time in (2,0.1,2,0.01):
        with PymbaCamera(camera_ids[0]) as camera:
            camera.set(exposure_time=exp_time*1e6)
            t0=time.perf_counter()
            camera.trigger()
            t1=time.perf_counter()
            camera.wait(exp_time*1e3*1.1)
            t2=time.perf_counter()
            print('trigger:',t1-t0,'wait:',t2-t1)
            assert t1-t0<0.1 and t2-t0>exp_time
    ##
    
def test_iidc_modes():
    ##
    with PymbaCamera(camera_ids[0]) as camera:
        for mode in range(7):
            for roi in ((-1,-1,-1,-1),(100,104,-1,-1),(-1,-1,200,204),(100,104,200,204)):
                camera.set(iidc_mode_number=mode,roi=roi)
            camera.check_validity()
    #camera.close()
    ##
##
if __name__=="__main__":
    figs=[]      
    test_open_close()  
    figs.append(test_exposure_time())
    figs.append(test_pixel_format())
    test_thorough()
    test_timing()
    test_iidc_modes()
