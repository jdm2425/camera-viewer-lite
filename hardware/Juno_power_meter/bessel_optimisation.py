import numpy as np
from scipy.special import jv, jn_zeros
from scipy.integrate import trapz, simps
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
import time
import spot_optimisation
from matplotlib.colors import Normalize
import itertools as it

class bessel(spot_optimisation.spot):

    def __init__(self,orders=10,roots=10,*args, **kwargs):
        '''
        self.r1D and self.r are intervals from 0 to 1, in which the Bessel
        decomposition is performed by taking advantage of the orthogonality
        of the Bessel functions on this interval.
        To recover the physical distance, self.r1D*pixelsize
        '''
        super().__init__(*args, **kwargs)
        self.selected = self.selector()
        self.phi1D, self.r1D = np.linspace(0, 2*np.pi, self.image.shape[0]), np.linspace(
                                           0, 1, self.image.shape[1])
        self.r, self.phi = np.meshgrid(self.r1D, self.phi1D)
        self.selected_phi1D, self.selected_r1D = np.linspace(0, 2*np.pi, self.selected.shape[0]), np.linspace(
                                           0, 1, self.selected.shape[1])
        self.selected_r, self.selected_phi = np.meshgrid(self.selected_r1D, self.selected_phi1D)
        self.no_orders = orders
        self.no_roots  = roots
      
    def selector(self):
        '''
        Selects only the part of the beam that is inside the fibre.
        '''
        return self.image[:,:self.inner_radius_pixels]
        
    def plot_initial(self):
        fig = plt.figure(1)
        ax = fig.add_subplot(121, projection='polar')
        plt.plot(0., 0., marker='*', ms=8, markerfacecolor='w', markeredgecolor='k')
        circle = plt.Circle((0., 0.), (self.fibreradius/self.pixelsize)/self.image.shape[1],
                            transform=ax.transData._b, color="red", alpha=0.35)
        ax.add_artist(circle)
        ax.axis('off')
        ax.set_title("Input", size=20)
        plt.pcolormesh(self.phi, self.r, self.image)
        plt.plot(0., 0., marker='*', ms=30, markerfacecolor='w', 
                 markeredgecolor='k')
        ax = fig.add_subplot(122, projection='polar')
        ax.axis('off')
        ax.set_title("Selected", size=20)
        plt.pcolormesh(self.selected_phi, self.selected_r, self.selected)
        plt.show()
        
    def double_integral(self, integrand):
        """
        Performs a double integral over the unit disk following
        Simpon's rule.
        """
        return simps(simps(integrand, self.selected_r1D), self.selected_phi1D)
    
    def overlap(self, integrand, order, root):  
        integrandc = integrand*self.selected_r1D*jv(
                order, jn_zeros(order, root+1)[-1]*
                self.selected_r1D)*np.cos(order*self.selected_phi)
        integrands = integrand*self.selected_r1D*jv(
                order, jn_zeros(order, root+1)[-1]*
                self.selected_r1D)*np.sin(order*self.selected_phi)
        return self.double_integral(integrandc),self.double_integral(integrands)

    def coefficients(self):
        """"Computes the coefficients of the Bessel-Fourier expansion."""
        self.coeffs = np.zeros((2, self.no_orders, self.no_roots))      
        for n in range(self.no_orders):
            for i in range(self.no_roots):
                self.coeffs[0][n][i],self.coeffs[1][n][i] = self.overlap(self.selected, 
                           n, i)
                if n == 0:
                    normalisation = 1/(np.pi*(jv(1,jn_zeros(0, i+1)[-1]))**2)
                    self.coeffs[0][n][i] = self.coeffs[0][n][i]*normalisation
                else:
                    normalisation = 2/(np.pi*(jv(n+1,jn_zeros(n, i+1)[-1]))**2)
                    self.coeffs[0][n][i] = self.coeffs[0][n][i]*normalisation
                    self.coeffs[1][n][i] = self.coeffs[1][n][i]*normalisation
                    
        # indlist = np.asarray(list((it.product(np.arange(self.no_orders),
                    # np.arange(self.no_roots)))))
        # self.coeffs = np.array([self.overlap(self.selected,l[0], l[1])\
            # for l in indlist]).reshape(2,self.no_orders, self.no_roots)
        # oldrow = np.array(self.coeffs[1,0,:])
        # norms = [2/(np.pi*(jv(l[0]+1,jn_zeros(l[0],l[1]+1)[-1]))**2)  for l in indlist]
        # self.coeffs *= np.asarray(norms).reshape(self.no_orders, self.no_roots)
        # self.coeffs[1,0,:] = np.array(oldrow)
    
    
    def decompose(self, no_roots, max_order, display = False):
        """
        Call this function to calculate and print the expansion coefficients.
        """
        start = time.time()
        self.no_roots = no_roots
        self.no_orders = max_order+1
        self.coefficients()
        if display is True:
            for n in range(self.no_orders):
                for i in range(self.no_roots):
                    print("coefficient A_%g,%g = %g" % (
                            n, i+1,self.coeffs[0][n][i]))
                    print("coefficient B_%g,%g = %g" % (
                            n, i+1,self.coeffs[1][n][i]))
            end = time.time()
            print("Calculated 2 x %g orders x %g roots = %g coefficients in %g seconds" % (
                    self.no_orders, self.no_roots, self.coeffs.size, end - start))
    
    def plot_reconstructed(self, clip=False):
   
        Z = np.zeros(self.selected_r.shape)

        for n in range(self.no_orders):
            for i in range(self.no_roots):
                Z += self.coeffs[0][n][i]*jv(n, 
                                jn_zeros(n, i+1)[-1]*self.selected_r)*np.cos(n*self.selected_phi)
                Z += self.coeffs[1][n][i]*jv(n, 
                                jn_zeros(n, i+1)[-1]*self.selected_r)*np.sin(n*self.selected_phi)
        
        if clip == True:
            input_max = np.amax(self.input_array)
            for n in range(len(X)):
                for i in range(len(Y)):
                    if Z[i][n] < 0:
                        Z[i][n] = 0
                    if Z[i][n] > input_max:
                        Z[i][n] = input_max
                        
        fig = plt.figure(1)
        plt.title("Reconstructed")
        ax = fig.add_subplot(121, projection='polar')
        plt.plot(0., 0., marker='*', ms=8, markerfacecolor='w', markeredgecolor='k')
        ax.axis('off')
        ax.set_title("Input", size=20)
        plt.pcolormesh(self.selected_phi, self.selected_r, self.selected)
        plt.plot(0., 0., marker='*', ms=30, markerfacecolor='w', 
                 markeredgecolor='k')
        ax = fig.add_subplot(122, projection='polar')
        ax.axis('off')
        ax.set_title("Selected", size=20)
        plt.pcolormesh(self.selected_phi, self.selected_r, Z)
        self.reconstructed = Z
        plt.show()
                              
    def bessel_metric(self):
        """Feedback metric for the beam. To be maximised.
        """
     
        ref = self.coeffs[0][0][0]
        metr = 0.
        
        # for n in range(2):
            # for i in range(self.no_roots):
                # for j in range(self.no_orders):
                    # metr += (self.coeffs[n][j][i]*10**j)/ref
        # metr = metr**(-2)
        
        weights = (np.arange(self.no_roots)-1)/(self.no_roots*(self.no_roots+1)/2)
        submets = np.sum(abs(self.coeffs),axis=(0,2))
        metric  = (np.sum(submets[:1]) - np.sum((weights*submets)[1:]))/np.sum(submets[:1])
        
        
        return metric
        
    def get_metric(self):
        """
        Order of returned metrics is [spot metric, bessel metric].
        """
    
        smetric = super().get_metric()
        self.coefficients()
        metric = np.append(smetric,self.bessel_metric())
        return metric
