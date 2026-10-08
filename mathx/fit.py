"""General mathematical functions"""
import numpy as np
import math
import scipy as sp
import scipy.interpolate as sci
from scipy.interpolate import krogh_interpolate,interp1d
import scipy.special
from scipy import optimize
import matplotlib.pyplot as plt
import itertools as it
import cv2,sys,os
#from . import *

def gaussian(peak,mu,sigma):
    def f(x):
        return peak*np.exp(-(x-mu)**2/(2*sigma**2))
    return f
    
def fit_gaussian(x,f):
    # Don't want NaNs for initial guess.
    mu_0,sigma_0=mean_and_std(x,abs(f))
    peak_0=max(f)
    def err_fun(params):
        return gaussian(*params)(x)-f
    params,success=optimize.leastsq(err_fun,np.array((peak_0,mu_0,sigma_0)))
    return params
    
def fit_sparse_1d_poly(x,y,f,pows):
    """Fit a sparse polynomial - one with a given set of terms.
    
    Returns the vector c such that the polynomial p(x)=sum_n c[n] x^{pows[n]} is
    the least-squares fit to the set of points (x,y), weighted by f. Broadcasting
    is allowed, so x, y, and f could define the axes and data of an image.

    Args:
        x (array): x axis
        y (array): y axis
        f (array): function to fit to
        pows (sequence): powers of x
        
    Returns:
        array: the coefficients c
        
    Derivation:
        Have f(x,y). Want to fit y=p(x) where p(x)=sum_n c_n x^{b_n}. Want stationary
        points of
            sum f(x,y)(y-p(x))^2
        i.e. zeros of
            sum f(x,y)(y-p(x))dpdc_m(x)
            = sum f(x,y)(y- sum_n c_n x^{b_n})x^{b_m}
            sum f(x,y)yx^{b_m}= sum_n f(x,y) x^{b_n} x^{b_m} c_n
    """
    x=np.asarray(x)
    y=np.asarray(y)
    N=len(pows)
    mat=np.zeros((N,N))
    rhs=np.zeros(N)
    for m in range(N):
        for n in range(N):
            if m>n:
                mat[m,n]=mat[n,m]
            else:
                mat[m,n]=(f*x**(pows[m]+pows[n])).sum()
        rhs[m]=(f*y*x**pows[m]).sum()
    c=np.linalg.solve(mat,rhs)
    return c

def calc_2d_correction_factors(m1,m2,tolerance=1e-6,max_iterations=1e6):
    """Calculate row- and column- dependent factors that when applied to m2 minimize its mean-square deviation from m1."""
    N,M=m1.shape
    assert m2.shape==(N,M)
    fr=np.ones(N)[:,None]
    fc=np.ones(M)
    num_iterations=0
    while num_iterations<max_iterations:
        frl=fr
        fcl=fc
        fr=(m1*m2*fc).sum(1,keepdims=True)/(m2**2*fc**2).sum(1,keepdims=True)
        fc=(m1*m2*fr).sum(0)/(m2**2*fr**2).sum(0)
        if ((((fr-frl)**2).sum()/(fr**2).sum()+((fc-fcl)**2).sum())/(fc**2).sum())<tolerance:
            break
        num_iterations+=1
    return fr,fc,num_iterations
    


def getpeaks(b,threshold=0.1,absval = None):
    c=np.gradient(b)
    d=np.gradient(c)
    miny=threshold*absval if absval else np.amax(b)*threshold
    
    e = np.array([(c[i] * c[i+1] <= 0) and d[i]<0 and b[i]>miny for i in range(0,len(c)-1)])
    f = np.array(np.where(e==True))
    
    return np.vstack((f[0], b[f]))



def getbg(image,margin=5):
    ymax=len(image)
    xmax=len(image[0])
    
    lims=np.ndarray((ymax,xmax,4))
    ylims = np.array([(i - margin if i>margin else 0,i + margin if i< ymax-margin else ymax) for i in range(ymax)])
    xlims = np.array([(i - margin if i>margin else 0,i + margin if i< xmax-margin else xmax) for i in range(xmax)])
    
    #can this be replaced with np.fromiter?
    lims = it.product(xlims,ylims)
    tlim = [np.sum(im2[lim[1][0]:lim[1][1],lim[0][0]:lim[0][1]]) for lim in lims]
    rlim = (np.array(tlim).reshape((xmax,ymax))/pow(2*margin,2)).transpose()
    return rlim

gaus = lambda x,x0,a,s: a*np.exp(pow(((x-x0)/s),2)/-2)

def getsigma(curve, peaks, frac=0.9, delta=0.01):
    
    peaks=peaks.T
    sigs=np.empty((len(peaks)))
    for i,peak in enumerate(peaks):
        val    = peak[1]
        place  = peak[0]
        newval = frac*val
    
        s      = np.array(np.where( (newval - delta < curve)*(curve <newval + delta))).flatten()
        bot    = np.amax(s*(s<place))
        top    = np.amin(s[np.nonzero(s*(s>place))])
        sig1   = (place - bot) / np.sqrt(-2*np.log(frac))
        sig2   = (top - place) / np.sqrt(-2*np.log(frac))
        sigs[i]=min(sig1,sig2)
    
    return sigs


def reconstructgaussians(peaks,sigs,axlen):
    recon = np.sum(np.array([gaus(np.arange(axlen),peaks[0,i],peaks[1,i],sigs[i]) for i in range(len(peaks[0]))]),
                axis=0)
    return recon

def getdif(peaks,sigs,curve):
    recon   = reconstructgaussians(peaks,sigs,len(curve))
    dif     = curve - recon
    return dif

def getgausresidual(peaks,sigs,curve):
    dif     = getdif(peaks,sigs,curve)
    return np.sum(abs(dif))

def fitgaussians(curve,tol=0.001):
    #Get the peaks and get sigmas
    peaks   = getpeaks(curve,0.1)
    sigs    = getsigma(curve,peaks,0.9)
    #Find the initial errors in the reconstructed gaussians
    dif     = getdif(peaks,sigs,curve)
    newpks  = getpeaks(dif,0.1,np.amax(peaks[1]))
    
    #Find any peaks that were hidden by larger features
    while len(newpks[0])>0: 
        npk      = getpeaks(dif,0.1,np.amax(peaks[1]))
        nsig     = getsigma(dif,npk)
        peaks    = np.append(peaks,npk,axis=1)
        sigs     = np.append(sigs,nsig)
        dif      = getdif(peaks,sigs,curve)
        newpks   = getpeaks(dif,0.1,np.amax(peaks[1]))
        

    leftover = getpeaks(pow(dif,2),tol,np.amax(peaks[1]))
    residual  = getgausresidual(peaks,sigs,curve)
    print("Initial residual is ",residual)
    counter = 1
    maxcounter=1000
    while len(leftover)>0 and counter<maxcounter:
        for i in leftover.T:
            nearpeaks = (sigs /(abs(i[0]-peaks[0])*pow(np.e,2)))>tol
            newpeaks  = np.array(peaks)
            for j,peak in enumerate(nearpeaks):
                if peak:
                    newpeaks[1,j]  = newpeaks[1,j] + ((np.random.rand()-0.5) * (dif[int(i[0])])/(5*len(nearpeaks)))
                    newres  = getgausresidual(newpeaks,sigs,curve)
                    if (newres < residual):
                        peaks=newpeaks
                        residual=newres
                
        residual  = getgausresidual(peaks,sigs,curve)
        for i in leftover.T:
            newpeaks  = np.array(peaks)
            nearpeaks = abs(i[0]-peaks[0])<int(0.1*len(curve))

            #nearestpeak = nearpeaks*False
            #nearestpeak[np.argmin(abs(peaks[0] - i[0]))] = True
            for j,peak in enumerate(nearpeaks):
                if peak:
                    newpeaks[0,j]  = peaks[0,j] + ( (np.random.rand()-0.5)*np.sign(dif[int(i[0])] * peak * ((peaks[0,j]-i[0])/10)))
                    newres  = getgausresidual(newpeaks,sigs,curve)
                    if (newres<residual):
                        peaks=newpeaks
                        residual=newres

        residual  = getgausresidual(peaks,sigs,curve)
        for j in range(len(sigs)):
            testsig   = np.array(sigs)
            testsig[j]= testsig[j]*pow(1.01,(np.random.rand()-0.5))
            newres    = getgausresidual(peaks,testsig,curve)      
            if (newres<residual):
                sigs=testsig
                residual=newres
        
        counter +=1
        if (counter%100)==0: print("Progress at {}%".format(counter*100/maxcounter) )

    print("Final residual is ",residual)

    return peaks,sigs

def randomgaussians(axis, maxgauss=5):
    numgaus = int(np.random.rand()*maxgauss)
    peaks   = np.array((np.random.rand()*len(axis),np.random.rand()*6))
    for i in range(numgaus): peaks   = np.vstack((peaks,((np.random.rand()*len(axis),np.random.rand()*6))))
    peaks=peaks.T
    sigs    = np.array((np.random.rand()*len(axis)/20))
    for i in range(numgaus): sigs    = np.append(sigs, (np.random.rand()*len(axis)/20))
    curve = reconstructgaussians(peaks,sigs,len(axis))
    return peaks,sigs,curve

if __name__ == '__main__':
        
    axis    = np.linspace(-10,10,10000)
    spacing = axis[1]-axis[0]
    cats    = gaus(axis,-2,2,1) + gaus(axis,3,1.5,1.5) + gaus(axis,5,3,0.7)
    spikes  = lambda x: pow(np.sin(3*x) * np.sin(7.23476*x)/3 * np.sin(13.26843*x),2)/7
    beats   = lambda x: pow(np.sin(0.7*x) * np.sin(17.23476*x)/5 * np.sin(33.26843*x),2)/9
    testpeaks,testsigs,rands   = randomgaussians(axis)

    curve = rands


    peaks,sigs = fitgaussians(curve)
    recon = reconstructgaussians(peaks,sigs,len(curve))
    plt.plot(curve)
    plt.plot(recon)
    plt.plot(getdif(peaks,sigs,curve))
    plt.legend(("Curve","Reconstructed curve","Residuals"))
    plt.show()

