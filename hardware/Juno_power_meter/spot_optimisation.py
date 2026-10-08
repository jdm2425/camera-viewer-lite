import numpy as np
max_, min_ = max, min
from cv2 import *
import time, math
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from IPython import embed
import matplotlib.image as mpimg

class image_processing:

    def __init__(self, webcam_index=0, width=320, height=240, exposure=-5,
                 gain=200, autodisconnect=True):
        """Loads image."""
        
        # To load an existing file (e.g. for testing purposes), use:
        # source = imread(webcam_index)
        # self.image = source
        
        # To acquire an image from an available webcam, use:
        self.cam=VideoCapture(webcam_index)
        cam = self.cam
        #cam.set(3, width)
        #cam.set(4, height)
        #cam.set(3, gain)
        #cam.set(15, exposure)
        self.read()
       
        if autodisconnect: self.disconnect()

    def read(self):
        bin, source = self.cam.read()
        if not bin:
            raise Exception("The image was not loaded. Check camera connection.")
        else:
            image = np.flip(np.array(source), 0) # Corrects y being upside down
            self.image = self.image2array(np.array(image))


    def disconnect(self):
        self.cam.release()
  
    def sharecamera(self):
        return self.cam
    
    def reshape2dimage(self,ndarray, new_shape, operation='mean'):
        operation = operation.lower()
        if not operation in ['sum', 'mean']:
            raise ValueError("Operation not supported.")
        if ndarray.ndim != len(new_shape):
            raise ValueError("Shape mismatch: {} -> {}".format(ndarray.shape,
                                                               new_shape))
        compression_pairs = [(d, c//d) for d,c in zip(new_shape,
                                                      ndarray.shape)]
        flattened = [l for p in compression_pairs for l in p]
        ndarray = ndarray.reshape(flattened)
        for i in range(len(new_shape)):
            op = getattr(ndarray, operation)
            ndarray = op(-1*(i+1))
        return ndarray

    
    def image2array(self, image):
        """
        Converts an image into an array containing the brightness of each
        pixel.
        """
        array = np.array(image)
        array = np.sum(array,axis=2)
        return array
        
    def makesquare(self, input):
        """Pads array with zeros until it is square."""
        diff = int(input.shape[0] - input.shape[1])
        if diff < 0:
            final = np.vstack(
                    (input, np.zeros((abs(diff), input.shape[1]))))
        if diff > 0:
            final = np.hstack(
                    (input, np.zeros((input.shape[0], diff))))
        return final
    
    def find_centre(self, input):
        """Finds the centre of mass of the image."""
        x_mean = np.average(np.arange(input.shape[1]), 
                            weights = np.array(np.sum(input,axis=0)+0.01))
        y_mean = np.average(np.arange(input.shape[0]), 
                            weights = np.array(np.sum(input,axis=1)+0.01))
        return int(round(x_mean)), int(round(y_mean))
        
    def peak_selector(self, input_array):
        """Identifies one of the peaks and replaces the other one with zeros."""
        start = time.time()
        new_array = np.zeros((input_array.shape[0], input_array.shape[1])) # generate empty image array
        j = 5
        new_array[:,:j] =  input_array[:,:j]
        new_array[:,j:] = np.where(input_array[:,j:]>0.1*np.amax(input_array), input_array[:,j:], 0) # pad remaining array w/ zeros unless > threshold
        test_otherpeak = np.where(np.array([max_(row[i:]) for row, i in zip(new_array[:,j:], new_array[:,j:].argmin(axis=1)-(input_array.shape[1]-j))]) > 0.14*np.amax(input_array), True, False) # array of True or False for each row if it has another peak
        argmax_test_otherpeak = np.array([np.argmax(row[i:]) for row, i in zip(new_array[:,j:], new_array[:,j:].argmin(axis=1))])
        
        def no_zeros(a):
            iszero = np.concatenate(([0], np.equal(a, 0).view(np.int8), [0]))
            absdiff = np.abs(np.diff(iszero))
            ranges = np.where(absdiff == 1)[0].reshape(-1, 2)
            return ranges[:,1]-ranges[:,0]

        n = 0
        while n < len(test_otherpeak):
            if test_otherpeak[n] is True:
                index = j+new_array[:,j:].argmin(axis=1)[n]+int(argmax_test_otherpeak[n]/2)
                new_array[n,index:] -= new_array[n,index:] # sets them to zero
            else:
                runs = no_zeros(new_array[n])
                for i in range(len(runs)):
                    if runs[i] > 20:
                        index = j+new_array[:,j:].argmin(axis=1)[n]+np.sum(runs[:i+1])
                        new_array[n,index:] -= new_array[n,index:] # sets them to zero
            n += 1
        end = time.time()
        #print("Time taken by peak_selector: ", end - start)
        return new_array
        
    def cartesian2polar(self, input_array, weighted_centre=False, inverse=False):
        start = time.time()
        if inverse is False:
            if weighted_centre is False:
                y, x = np.unravel_index(input_array.argmax(), input_array.shape)
            elif weighted_centre is True:
                x, y = self.find_centre(input_array)
            value = self.image.shape[0]
            try:
                return warpPolar(input_array, (int(value), int(value)), 
                                   (x, y), value/2, WARP_POLAR_LINEAR)
            except:
                #plt.imshow(linearPolar(input_array, (x, y), value/2, WARP_FILL_OUTLIERS))
                #plt.show()
                return linearPolar(input_array, (x, y), np.sqrt(2)*value/2, WARP_FILL_OUTLIERS)
        elif inverse is True:
            try:
                return warpPolar(input_array, (input_array.shape[0],input_array.shape[1]),
                        (int(input_array.shape[0]/2), int(input_array.shape[1]/2)),
                        #(0,int(input_array.shape[1]/2)),
                        input_array.shape[0]/2, WARP_INVERSE_MAP)
            except:
                #plt.imshow(linearPolar(input_array, (int(input_array.shape[0]/2), int(input_array.shape[1]/2)),
                #                   self.image.shape[0]/2, WARP_INVERSE_MAP))
                #plt.show()
                return linearPolar(input_array, (int(input_array.shape[0]/2), int(input_array.shape[1]/2)),
                                   np.sqrt(2)*self.image.shape[0]/2, WARP_INVERSE_MAP)
                
class spot(image_processing):
    
    def __init__(self, webcam_index=0, releasecamera=False, fibreradius=225., pixelsize=2.8, plot=False,preimage = None):
        """ Pixel size is actually 2.8u. Base assumption is that fibre hole is 450u"""
        self.instance = image_processing(webcam_index, autodisconnect = releasecamera)
        self.releasecamera=releasecamera
        self.fibreradius = fibreradius*0.64
        self.pixelsize = pixelsize
        self.plot=plot
        self.preimage = preimage
        self.processimage()
        self.inner_radius_pixels = math.ceil(self.fibreradius/self.pixelsize)
    
    def set_image(self,preimage):
        self.preimage = preimage
    
    def processimage(self):
        if self.releasecamera and not self.preimage: self.instance.read()
        elif self.preimage : self.instance.image = mpimg.imread(self.preimage)
        square = self.instance.makesquare(self.instance.image)
        polar_brightness_raw_full = self.instance.cartesian2polar(square)
        lenpol=int(len(polar_brightness_raw_full)/4)
        
        tester = 0

        polar_brightness_raw = self.instance.reshape2dimage(ndarray=polar_brightness_raw_full,new_shape=(lenpol,lenpol))
        plt.figure()
        if self.plot:
            fig = plt.figure(1)
            ax = fig.add_subplot(111, projection='polar')
            ax.axis('off')
            phi, r = np.meshgrid(np.linspace(0, 2*np.pi, polar_brightness_raw.shape[0]),
                                 np.linspace(0,self.pixelsize*polar_brightness_raw.shape[1],
                                 polar_brightness_raw.shape[1]))
            plt.pcolormesh(phi, r, np.transpose(polar_brightness_raw))
            plt.plot(0., 0., marker='*', ms=8, markerfacecolor='w', markeredgecolor='k')
            plt.colorbar()
            plt.show()
            
        selected = self.instance.peak_selector(polar_brightness_raw)
        if self.plot:
            fig = plt.figure(2)
            ax = fig.add_subplot(111, projection='polar')
            ax.axis('off')
            phi, r = np.meshgrid(np.linspace(0, 2*np.pi, selected.shape[0]),
                                 np.linspace(0,self.pixelsize*selected.shape[1],
                                 selected.shape[1]))
            plt.pcolormesh(phi, r, np.transpose(selected))
            plt.plot(0., 0., marker='*', ms=8, markerfacecolor='w', markeredgecolor='k')
            plt.colorbar()
            plt.show()

        cartesian_processed = self.instance.cartesian2polar(selected,inverse = True)
        if self.plot:
            fig = plt.figure(3)
            ax = fig.add_subplot(111)
            im = ax.imshow(cartesian_processed)
            plt.show()

        polar_processed = self.instance.cartesian2polar(cartesian_processed, weighted_centre = True)
        if self.plot:
            fig = plt.figure(4)
            ax = fig.add_subplot(111, projection='polar')
            ax.axis('off')
            phi, r = np.meshgrid(np.linspace(0, 2*np.pi, polar_processed.shape[0]),
                                 np.linspace(0,self.pixelsize*polar_processed.shape[1],
                                             polar_processed.shape[1]))
            plt.pcolormesh(phi, r, np.transpose(polar_processed))
            plt.plot(0., 0., marker='*', ms=8, markerfacecolor='w', markeredgecolor='k')
            circle = plt.Circle((0., 0.), self.fibreradius,
                                transform=ax.transData._b, color="red", alpha=0.35)
            ax.add_artist(circle)
            plt.colorbar()
            plt.show()
        
        def normalise(array):
            maximum=np.amax(array)
            return (array/maximum)
        
        self.image = normalise(polar_processed)
        
        
    def spot_metric(self):
        """
        Returns a fitness function to be maximised.
        A, B defined as in Nouman-ul-Haq et al., Nuclear Inst. and Methods in 
        Physics Researchs, A 883 (2018).
        Here we use the inverse of their metric, since we seek to maximise it rather than
        minimise it.
        """
        
        start = time.time()
        
        if self.inner_radius_pixels > self.image.shape[0] or self.inner_radius_pixels > self.image.shape[1]:
            raise Exception("The desired spot size is bigger than the image.")
                
        B = np.sum(np.nonzero(self.image[:,:self.inner_radius_pixels]))
        A = np.sum(np.nonzero(self.image[:,self.inner_radius_pixels:]))
        satpix = np.pi*pow(self.fibreradius,2)/pow(self.pixelsize,2)
        if A <= A.size * 0.001: metr = (satpix /B)
        else: metr = B/(B + A)
        end = time.time()
        #print("Time taken by metric: ", end - start)
        return metr
        
    def get_metric(self):
        if self.releasecamera: self.processimage()
        metric = self.spot_metric()
        return np.array(metric)
