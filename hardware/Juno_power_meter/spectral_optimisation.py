import numpy as np

class spectral:

    def __init__(self, array, limits, target_peak, target_limits):
        '''
        Limits is a tuple containing the lowest and highest frequency collected
        by the spectrometer. target_peak is the desired frequency of the peak.
        target_limits is a tuple of the lowest and highest frequency present in the
        target spectrum.
        '''
        self.array = array
        self.limits = limits
        if self.limits[1] < self.limits[0]:
            raise ValueError("Please insert the lower limit first, and then the higher.")
        self.target_peak = target_peak
        if self.target_peak < self.limits[0] or self.target_peak > self.limits[1]:
            raise ValueError("The target peak is outside the spectral range.")
        self.target_limits = target_limits
        if self.target_limits[1] < self.target_limits[0]:
            raise ValueError("Please insert the lower limit first, and then the higher.")
        if self.target_peak < self.target_limits[0] or self.target_peak > self.target_limits[1]:
            raise ValueError("The target peak is outside the target spectral range.")
        
    def frequency2index(self, frequency):
        '''
        Input a frequency; returns the (closest) index in the array.
        '''
        range = self.limits[1]-self.limits[0]
        frequency_step = range/(len(self.array)-1)
        if frequency > self.limits[1] or frequency < self.limits[0]:
            raise ValueError("The desired frequency is outside of the spectral range.")
        else:
            index = int(round((frequency-self.limits[0])/frequency_step))
            return index
            
    def index2frequency(self, index):
        '''
        Input an index; returns the (closest) frequency.
        '''
        range = self.limits[1]-self.limits[0]
        frequency_step = range/len(self.array)
        if frequency > self.limits[1] or frequency < self.limits[0]:
            raise ValueError("The desired frequency is outside of the spectral range of the instrument.")
        else:
            index = int(round((frequency-self.limits[0])/frequency_step))
            return index
        
    def metric(self):
        '''
        This metric is the sum of two parts: one (B) measures the distance of the actual
        peak from the desired peak; the other one (A) counts the non-zero frequency bins
        outside of the desired limits.
        '''
        metr, A, B = 0., 0., 0.
        A = np.sum(self.array[:self.frequency2index(self.target_limits[0])])
        A += np.sum(self.array[self.frequency2index(self.target_limits[1])+1:])
        actual_peak = np.argmax(self.array)
        B = abs(actual_peak-self.frequency2index(self.target_peak))
        metr = A+B
        self.A, self.B = A, B
        return metr
